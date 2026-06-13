"""
心犀AI - 匹配路由（v3: WebSocket + Checkpointing）
==================================================
处理匹配推荐和匹配历史相关的 HTTP 接口 + WebSocket。

接口列表：
  POST /api/match                    触发匹配（同步，等待完成后返回）
  WS   /api/match/ws/{user_id}       触发匹配（WebSocket，实时推送进度）
  GET  /api/match/history/{user_id}  获取用户的匹配历史
  GET  /api/match/{match_id}         获取单次匹配结果
  GET  /api/match/state/{user_id}    获取用户最近一次匹配的检查点状态

学习要点：
---------
WebSocket vs HTTP：
  - HTTP：请求→等待→响应（像发短信）
  - WebSocket：建立持久连接，服务端可以随时推送消息（像打电话）
  - 匹配流程耗时较长（LLM 调用），用 WebSocket 可以实时展示进度
  - 这就是 Phase 3 的 Streaming 功能

Phase 4 Checkpointing：
  - 每次匹配使用唯一 thread_id（match_{user_id}_{timestamp}）
  - 确保每次匹配都是全新运行，不会受之前检查点影响
  - 如需恢复中断的匹配，可用原始 thread_id 继续执行
  - 访谈子图使用固定 thread_id（interview_{user_id}），支持跨会话继续
"""

import json
import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from api.schemas import (
    MatchRequest, MatchResult, MatchCandidate,
    MatchHistoryResponse, MessageResponse,
    MatchStartRequest, MatchStartResponse, MatchResumeRequest,
)
from api.deps import get_services, AppServices, generate_match_id, MatchSession
from api.auth import get_current_user, verify_token_str
from core.agent.state import AgentState
from core.models.user_profile import UserProfile
# Phase 3: LangFuse 可观测性集成
from core.utils.observability import (
    create_langfuse_callback,
    flush_langfuse,
)

router = APIRouter(prefix="/api/match", tags=["匹配推荐"])


def _rebuild_user_profile(user_id: str, svc: AppServices) -> UserProfile:
    """
    从 Chroma 中读取用户数据，重建 UserProfile 对象。
    因为 Agent 工作流需要完整的 UserProfile，而 API 层只有 user_id。
    """
    data = svc.chroma_store.get_user(user_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

    meta = data["metadata"]
    return UserProfile(
        user_id=user_id,
        nickname=meta.get("nickname", ""),
        gender=meta.get("gender", ""),
        age=meta.get("age", 0),
        city=meta.get("city", ""),
        province=meta.get("province", ""),
        education=meta.get("education", ""),
        annual_income=meta.get("annual_income", "未填写"),
        marital_status=meta.get("marital_status", "未婚"),
        target_gender=meta.get("target_gender", ""),
        target_age_min=meta.get("target_age_min", 18),
        target_age_max=meta.get("target_age_max", 45),
        target_city=meta.get("target_city", "不限"),
        about_me=meta.get("about_me", ""),
        ideal_partner=meta.get("ideal_partner", ""),
        hobbies=meta.get("hobbies", ""),
        mbti=meta.get("mbti", "未知"),
    )


def _build_final_result(final_state: dict, user_id: str) -> dict:
    """从 Agent 最终状态中构建匹配结果"""
    match_id = generate_match_id()
    now = datetime.now().isoformat()

    candidates = []
    for m in final_state.get("top_matches", []):
        candidates.append({
            "user_id": m.get("user_id", ""),
            "nickname": m.get("nickname", ""),
            "score": m.get("score", 0),
            "reason": m.get("reason", ""),
        })

    return {
        "match_id": match_id,
        "user_id": user_id,
        "candidates": candidates,
        "match_letters": final_state.get("match_letters", []),
        "created_at": now,
        "agent_log": final_state.get("messages", []),
    }


# ============================================================
# POST /api/match - 触发匹配（同步版本，保持向后兼容）
# ============================================================
@router.post("", response_model=MatchResult)
def trigger_match(body: MatchRequest, svc: AppServices = Depends(get_services)):
    """
    为指定用户触发一次完整的 AI 匹配流程（同步版）。
    等待整个 Agent 工作流完成后才返回结果。
    如果需要实时进度，请使用 WebSocket 接口。
    """
    user_profile = _rebuild_user_profile(body.user_id, svc)

    initial_state: AgentState = {
        "user_profile": user_profile,
        "loop_count": 0,
        "messages": [],
    }

    # Phase 4: 每次匹配使用唯一 thread_id，确保全新运行
    # 格式：match_{user_id}_{timestamp}，既唯一又可追溯
    match_thread_id = f"match_{body.user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    config = {"configurable": {"thread_id": match_thread_id}}

    # Phase 3: 创建 LangFuse 回调处理器（如果已启用）
    # CallbackHandler 会自动追踪所有 LLM 调用并上报到 LangFuse Dashboard
    langfuse_handler = create_langfuse_callback(
        user_id=body.user_id,
        session_id=match_thread_id,
        tags=["match", "sync"],
    )
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]
        # 将 trace_id 存入初始状态，供 Judge Agent 上报评分使用
        initial_state["langfuse_trace_id"] = langfuse_handler._xinxi_trace_id

    final_state = svc.matching_graph.invoke(initial_state, config=config)

    # Phase 3: 确保所有追踪数据都发送到 LangFuse 服务器
    flush_langfuse(langfuse_handler)

    result_data = _build_final_result(final_state, body.user_id)
    result = MatchResult(**result_data)

    # 持久化到内存 + SQLite（双写，确保重启不丢失）
    svc.save_match_record(body.user_id, result.model_dump())

    return result


# ============================================================
# WebSocket /api/ws/match/{user_id} - 实时匹配（Streaming 版本）
# ============================================================

# 节点名称到中文描述的映射
# 学习要点：Supervisor 架构引入了新的节点名（如 supervisor, intent_agent 等）
# 这里同时包含旧版和新版的节点名，确保两种架构都能正确显示中文描述
_NODE_LABELS = {
    # === 旧版单 Agent 图节点名（保持向后兼容）===
    "parse_intent": ("🔍", "意图解析", "正在分析用户资料和择偶偏好..."),
    "hybrid_search": ("📋", "混合检索", "正在向量数据库中搜索候选人..."),
    "post_analysis": ("🧠", "深度分析", "LLM 正在评估每位候选人的契合度..."),
    "reflection": ("🔄", "策略反思", "匹配结果不够理想，正在调整搜索策略..."),
    "generate_match": ("💌", "生成推荐信", "正在为最佳候选人撰写缘分推荐信..."),

    # === 新版 Supervisor 多 Agent 图节点名 ===
    "supervisor": ("🤖", "调度中心", "Supervisor 正在决定下一步执行哪个 Agent..."),
    "intent_agent": ("🔍", "意图解析", "正在分析用户资料和择偶偏好..."),
    "retrieval_agent": ("📋", "混合检索", "正在向量数据库中搜索候选人..."),
    "analysis_agent": ("🧠", "深度分析", "LLM 正在评估每位候选人的契合度..."),
    "reflection_agent": ("🔄", "策略反思", "匹配结果不够理想，正在调整搜索策略..."),
    "letter_agent": ("💌", "生成推荐信", "正在为最佳候选人撰写缘分推荐信..."),
    "judge_agent": ("⚖️", "质量评估", "LLM-as-Judge 正在评估匹配质量..."),
}


@router.websocket("/ws/{user_id}")
async def ws_match(websocket: WebSocket, user_id: str):
    """
    WebSocket 实时匹配接口。

    学习要点：
    ---------
    LangGraph 的 astream_events() 方法会在每个节点开始和结束时发出事件：
      - on_chain_start: 节点开始执行
      - on_chain_end:   节点执行完毕，包含该节点的输出
    我们可以监听这些事件，实时推送给前端，让用户看到 Agent 的"思考过程"。
    """
    await websocket.accept()

    svc = get_services()

    # 1. 验证用户存在
    try:
        user_profile = _rebuild_user_profile(user_id, svc)
    except HTTPException:
        await websocket.send_json({
            "type": "error",
            "message": f"用户 {user_id} 不存在",
        })
        await websocket.close(code=4004)
        return

    # 2. 发送开始事件
    await websocket.send_json({
        "type": "start",
        "user_id": user_id,
        "nickname": user_profile.nickname,
        "message": f"开始为 {user_profile.nickname} 寻找缘分...",
    })

    # 3. 构建初始状态
    initial_state: AgentState = {
        "user_profile": user_profile,
        "loop_count": 0,
        "messages": [],
    }

    # 4. 使用 astream_events 流式执行，逐节点推送进度
    #    同时收集各节点输出，拼成完整的 final_state
    final_state: dict = {}
    langfuse_handler = None
    try:
        # Phase 4: 每次匹配使用唯一 thread_id
        match_thread_id = f"match_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        config = {"configurable": {"thread_id": match_thread_id}}

        # Phase 3: 创建 LangFuse 回调处理器
        # CallbackHandler 会追踪所有 LLM 调用，并自动关联到这个 trace
        langfuse_handler = create_langfuse_callback(
            user_id=user_id,
            session_id=match_thread_id,
            tags=["match", "websocket"],
        )
        if langfuse_handler:
            config["callbacks"] = [langfuse_handler]
            # 将 trace_id 存入初始状态，供 Judge Agent 上报评分使用
            initial_state["langfuse_trace_id"] = langfuse_handler._xinxi_trace_id
        
        async for event in svc.matching_graph.astream_events(
            initial_state,
            config=config,
            version="v2",
        ):
            kind = event.get("event", "")

            # 节点开始：推送"正在执行"状态
            if kind == "on_chain_start" and event.get("metadata", {}).get("langgraph_node"):
                node_name = event["metadata"]["langgraph_node"]
                if node_name in _NODE_LABELS:
                    emoji, label, desc = _NODE_LABELS[node_name]
                    await websocket.send_json({
                        "type": "node_start",
                        "node": node_name,
                        "emoji": emoji,
                        "label": label,
                        "message": desc,
                    })

            # 节点结束：推送节点输出摘要 + 累积状态
            elif kind == "on_chain_end" and event.get("metadata", {}).get("langgraph_node"):
                node_name = event["metadata"]["langgraph_node"]
                output = event.get("data", {}).get("output", {})

                if node_name in _NODE_LABELS and isinstance(output, dict):
                    # 累积每个节点的输出到 final_state
                    for key, value in output.items():
                        final_state[key] = value

                    # 提取该节点产生的 messages
                    new_messages = output.get("messages", [])
                    summary = new_messages[-1] if new_messages else ""

                    await websocket.send_json({
                        "type": "node_end",
                        "node": node_name,
                        "message": summary,
                    })

    except WebSocketDisconnect:
        # Phase 3: 即使客户端断开，也要 flush 已收集的追踪数据
        flush_langfuse(langfuse_handler)
        return
    except Exception as e:
        # Phase 3: 出错时也要 flush 追踪数据（记录到出错位置的信息）
        flush_langfuse(langfuse_handler)
        await websocket.send_json({
            "type": "error",
            "message": f"匹配流程出错: {str(e)}",
        })
        await websocket.close(code=1011)
        return

    # Phase 3: 流式执行完成，flush 所有追踪数据到 LangFuse 服务器
    flush_langfuse(langfuse_handler)

    # 5. 如果 final_state 为空（异常情况），给一个兜底
    if not final_state:
        final_state = {"messages": []}

    # 6. 发送完成事件
    result_data = _build_final_result(final_state, user_id)

    await websocket.send_json({
        "type": "complete",
        "result": result_data,
    })

    # 7. 持久化到内存 + SQLite（双写）
    svc.save_match_record(user_id, result_data)

    await websocket.close()


# ============================================================
# GET /api/match/state/{user_id} - 检查点状态查询（Phase 4）
# ============================================================
@router.get("/state/{user_id}")
def get_checkpoint_state(user_id: str, svc: AppServices = Depends(get_services)):
    """
    查询用户最近一次匹配的检查点状态。

    学习要点：
    ---------
    LangGraph 的 checkpointer 会自动在每个节点执行完毕后保存状态快照。
    通过 get_state() 可以读取最近一次运行的最终状态。

    这在以下场景非常有用：
    - 调试：查看 Agent 的中间状态和决策过程
    - 恢复：服务重启后可以从检查点继续执行
    - 审计：回溯 Agent 的完整执行轨迹
    """
    # 查找该用户最近的匹配 thread_id
    history = svc.match_history.get(user_id, [])
    if not history:
        return {"has_checkpoint": False, "message": "该用户尚无匹配记录"}

    latest = history[-1]
    match_id = latest.get("match_id", "")

    # 尝试用匹配时的 thread_id 格式查找检查点
    # 注意：由于每次匹配使用唯一 thread_id，这里返回的是历史记录中的 Agent 日志
    return {
        "has_checkpoint": True,
        "user_id": user_id,
        "match_id": match_id,
        "agent_log": latest.get("agent_log", []),
        "candidates_count": len(latest.get("candidates", [])),
        "created_at": latest.get("created_at", ""),
        "note": (
            "Checkpointing 已启用。每次匹配使用唯一 thread_id，"
            "可通过 LangGraph 的 graph.get_state(config) API 恢复任意检查点。"
        ),
    }


# ============================================================
# GET /api/match/history/{user_id} - 获取匹配历史
# ============================================================
@router.get("/history/{user_id}", response_model=MatchHistoryResponse)
def get_match_history(
    user_id: str,
    svc: AppServices = Depends(get_services),
):
    """
    获取指定用户的所有匹配历史记录（按时间倒序）。

    学习要点：
    - 优先从内存 dict 读取（最快）
    - 内存为空时从 SQLite 回退读取（确保重启后仍有数据）
    """
    records = svc.match_history.get(user_id, [])

    # 内存中没有记录时，从 SQLite 回退查询
    if not records:
        records = svc.history_store.get_by_user(user_id)

    sorted_records = sorted(records, key=lambda r: r.get("created_at", ""), reverse=True)

    return MatchHistoryResponse(
        records=[MatchResult(**r) for r in sorted_records],
        total=len(sorted_records),
    )


# ============================================================
# GET /api/match/{match_id} - 获取单次匹配结果
# ============================================================
@router.get("/{match_id}", response_model=MatchResult)
def get_match_result(match_id: str, svc: AppServices = Depends(get_services)):
    """
    根据 match_id 获取一次匹配的完整结果。

    学习要点：
    - 先从内存中遍历查找（O(n) 但数据量小，足够快）
    - 找不到时从 SQLite 精确查询（O(1)，有 match_id 索引）
    """
    # 1. 优先从内存查找
    for user_id, records in svc.match_history.items():
        for record in records:
            if record.get("match_id") == match_id:
                return MatchResult(**record)

    # 2. 内存中找不到 → 从 SQLite 回退
    record = svc.history_store.get_by_match_id(match_id)
    if record:
        return MatchResult(**record)

    raise HTTPException(status_code=404, detail=f"匹配记录 {match_id} 不存在")


# ============================================================
# POST /api/match/evaluate/{match_id} - LLM-as-Judge 评估（Phase 7）
# ============================================================
@router.post("/evaluate/{match_id}")
def evaluate_match_result(match_id: str, svc: AppServices = Depends(get_services)):
    """
    使用 LLM-as-Judge 评估一次匹配结果的质量。

    学习要点：
    ---------
    Phase 7 LLM-as-Judge 评估：
    - 用一个独立的 LLM（Judge）来"评审"匹配推荐的质量
    - 从相关性、契合度、解释力、一致性、温度感 5 个维度打分
    - 输出结构化的评估报告（整体评分 + 各维度评分 + 优缺点 + 改进建议）
    - 这是自动化评估 RAG/Agent 系统质量的重要技术
    """
    from core.evaluation.judge import evaluate_match

    # 1. 查找匹配记录
    match_record = None
    match_user_id = None
    for uid, records in svc.match_history.items():
        for record in records:
            if record.get("match_id") == match_id:
                match_record = record
                match_user_id = uid
                break
        if match_record:
            break

    if not match_record:
        raise HTTPException(status_code=404, detail=f"匹配记录 {match_id} 不存在")

    # 2. 重建用户画像
    user_profile = _rebuild_user_profile(match_user_id, svc)

    # 3. 调用 Judge 评估
    evaluation = evaluate_match(
        user_profile=user_profile,
        match_results=match_record.get("candidates", []),
        match_letters=match_record.get("match_letters", []),
    )

    return {
        "match_id": match_id,
        "evaluation": evaluation.model_dump(),
    }


# ============================================================
# Phase 3c：SSE 匹配流 — 辅助函数
# ============================================================

# LangGraph 节点名 → SSE 展示标签
_SSE_NODE_LABELS: dict[str, tuple[str, str]] = {
    "supervisor":       ("🤖", "Supervisor 调度中"),
    "intent_agent":     ("🔍", "正在解析你的偏好..."),
    "retrieval_agent":  ("📋", "向量数据库检索中..."),
    "hitl_node":        ("👀", "预览候选人，等待确认..."),
    "analysis_agent":   ("🧠", "深度分析匹配维度..."),
    "reflection_agent": ("🔄", "优化匹配策略..."),
    "letter_agent":     ("💌", "生成个性化推荐词..."),
    "judge_agent":      ("⚖️", "质量评估中..."),
}


def _langgraph_event_to_sse(event: dict) -> dict | None:
    """
    将 LangGraph astream_events(version="v2") 产生的原始事件转换为 SSE 格式。

    学习要点：
    astream_events(version="v2") 的主要事件类型：
      on_chain_start  - 节点（chain）开始执行
      on_chain_end    - 节点执行完毕，output 在 data.output 中
      on_tool_start   - LLM 决定调用工具，开始执行
      on_tool_end     - 工具执行完毕
      on_chat_model_stream - LLM 流式 token（本项目暂不使用）

    metadata.langgraph_node 包含当前执行的节点名。
    """
    kind = event.get("event", "")
    node_name = event.get("metadata", {}).get("langgraph_node", "")

    # 节点开始事件
    if kind == "on_chain_start" and node_name in _SSE_NODE_LABELS:
        emoji, msg = _SSE_NODE_LABELS[node_name]
        return {"event": "agent_start", "node": node_name, "emoji": emoji, "msg": msg}

    # 工具调用开始
    if kind == "on_tool_start":
        tool_name = event.get("name", "unknown_tool")
        return {"event": "tool_call", "node": node_name, "tool": tool_name, "status": "calling"}

    # 工具调用完成
    if kind == "on_tool_end":
        tool_name = event.get("name", "unknown_tool")
        return {"event": "tool_result", "node": node_name, "tool": tool_name, "status": "done"}

    # 节点完成：提取最后一条 message 作为摘要
    if kind == "on_chain_end" and node_name in _SSE_NODE_LABELS:
        output = event.get("data", {}).get("output", {})
        if isinstance(output, dict):
            node_messages = output.get("messages", [])
            summary = node_messages[-1] if node_messages else ""
            if summary:
                return {"event": "agent_complete", "node": node_name, "msg": summary}

    return None  # 不感兴趣的事件


async def _run_match_background(
    session: MatchSession,
    svc: AppServices,
    user_filters: dict | None,
):
    """
    匹配流程后台任务：在 asyncio 任务中运行 LangGraph 图，
    将事件通过 session.event_queue 推送给 SSE generator。

    学习要点：
    ---------
    这是 SSE + HITL 实现的核心逻辑，分为两个阶段：

    阶段1（run until interrupt）：
      graph.astream_events() 持续产生事件，直到遇到 interrupt() 暂停
      astream_events() 的 async for 循环结束后，
      用 graph.aget_state(config) 检查是否有 pending interrupt

    阶段2（wait for resume, then continue）：
      等待用户通过 POST /resume 发送恢复信号（asyncio.Event）
      用 Command(resume=...) 继续图执行
    """
    config = {"configurable": {"thread_id": session.session_id}}

    try:
        user_profile = _rebuild_user_profile(session.user_id, svc)
    except Exception as e:
        session.status = "error"
        session.error = str(e)
        await session.event_queue.put({"event": "error", "msg": str(e)})
        await session.event_queue.put(None)
        return

    # 临时覆盖偏好参数（不修改用户档案）
    if user_filters:
        if "target_age_min" in user_filters:
            user_profile.target_age_min = user_filters["target_age_min"]
        if "target_age_max" in user_filters:
            user_profile.target_age_max = user_filters["target_age_max"]
        if "target_city" in user_filters:
            user_profile.target_city = user_filters["target_city"]

    initial_state: AgentState = {
        "user_profile": user_profile,
        "loop_count": 0,
        "messages": [],
    }

    await session.event_queue.put({
        "event": "agent_start",
        "node": "start",
        "emoji": "✨",
        "msg": f"开始为 {user_profile.nickname} 寻找缘分...",
    })

    try:
        # ============================
        # 阶段1：运行图直到 interrupt 或完成
        # 学习要点：astream_events() 会在遇到 interrupt() 时自然停止
        # ============================
        async for raw_event in svc.matching_graph.astream_events(
            initial_state, config=config, version="v2"
        ):
            sse = _langgraph_event_to_sse(raw_event)
            if sse:
                await session.event_queue.put(sse)

        # 检查是否因 interrupt() 而暂停
        # 学习要点：graph.aget_state(config) 返回最近一次执行的快照
        #   snapshot.tasks: 还未完成的任务列表
        #   task.interrupts: 该任务触发的 interrupt() 列表（含 payload）
        snapshot = await svc.matching_graph.aget_state(config)

        has_interrupt = snapshot.tasks and any(
            t.interrupts for t in snapshot.tasks
        )

        if has_interrupt:
            # 找到 interrupt payload
            interrupt_value = snapshot.tasks[0].interrupts[0].value
            session.status = "waiting_hitl"

            # 通过 SSE 把候选人预览推送给前端
            await session.event_queue.put({
                "event": "hitl_preview",
                "candidates": interrupt_value.get("candidates", []),
                "retrieval_note": interrupt_value.get("retrieval_note", ""),
                "candidate_count": interrupt_value.get("candidate_count", 0),
            })

            # ============================
            # 等待 POST /resume 的信号
            # 学习要点：asyncio.Event.wait() 会挂起协程，
            # 直到 resume_event.set() 被调用（由 /resume 端点触发）
            # ============================
            await session.resume_event.wait()
            session.status = "running"

            await session.event_queue.put({
                "event": "agent_start",
                "node": "resume",
                "emoji": "🚀",
                "msg": "开始深度分析匹配维度...",
            })

            # ============================
            # 阶段2：用 Command(resume=...) 继续执行
            # 学习要点：Command(resume=value) 告诉 LangGraph
            # "以 value 作为 interrupt() 的返回值，从中断点恢复执行"
            # ============================
            async for raw_event in svc.matching_graph.astream_events(
                Command(resume=session.resume_payload),
                config=config,
                version="v2",
            ):
                sse = _langgraph_event_to_sse(raw_event)
                if sse:
                    await session.event_queue.put(sse)

        # 获取最终状态，构建结果
        final_snapshot = await svc.matching_graph.aget_state(config)
        final_values = final_snapshot.values if final_snapshot else {}

        result = _build_final_result(final_values, session.user_id)
        svc.save_match_record(session.user_id, result)

        session.result = result
        session.status = "done"

        await session.event_queue.put({
            "event": "complete",
            "match_id": result["match_id"],
            "result_count": len(result.get("candidates", [])),
        })

    except Exception as e:
        session.status = "error"
        session.error = str(e)
        await session.event_queue.put({"event": "error", "msg": f"匹配出错: {str(e)}"})

    finally:
        # 哨兵值：通知 SSE generator 流已结束
        await session.event_queue.put(None)


# ============================================================
# Phase 3c：SSE 匹配流 API 端点
# ============================================================

@router.post("/start", response_model=MatchStartResponse)
async def start_match(
    body: MatchStartRequest,
    background_tasks: BackgroundTasks,
    svc: AppServices = Depends(get_services),
    current_user_id: str = Depends(get_current_user),
):
    """
    创建匹配会话并启动后台 Agent 工作流。

    学习要点：
    ---------
    BackgroundTasks：
    - FastAPI 内置后台任务工具
    - add_task(fn, ...) 在当前请求返回后异步执行 fn
    - 同一进程内运行（不是新进程），适合轻量级后台工作
    - 使用场景：响应不依赖任务结果，但需要在后台触发某些操作
    """
    import uuid as _uuid
    session_id = "MS" + _uuid.uuid4().hex[:12].upper()

    session = MatchSession(session_id=session_id, user_id=current_user_id)
    svc.match_sessions[session_id] = session

    background_tasks.add_task(
        _run_match_background,
        session=session,
        svc=svc,
        user_filters=body.user_filters,
    )

    return MatchStartResponse(session_id=session_id)


@router.get("/{session_id}/stream")
async def stream_match(
    session_id: str,
    svc: AppServices = Depends(get_services),
    token: str = Query(..., description="JWT token（EventSource 不支持 Header，通过 query param 传递）"),
):
    """
    SSE 流：实时推送匹配进度。

    学习要点：
    ---------
    1. Server-Sent Events（SSE）格式：
       每条事件格式为：data: <JSON字符串>\\n\\n
       浏览器通过 EventSource API 自动解析，触发 onmessage 回调

    2. StreamingResponse + async generator：
       - media_type="text/event-stream" 告知浏览器这是 SSE 流
       - Cache-Control: no-cache 防止浏览器缓存
       - X-Accel-Buffering: no 防止 nginx 缓冲导致事件延迟

    3. asyncio.Queue 生产者-消费者模式：
       - 生产者：_run_match_background() 把事件 put() 进队列
       - 消费者：event_generator() 从队列 get() 事件并 yield 到响应流
       - None 作为哨兵值：生产者放入 None 表示流结束

    4. 为什么 token 放 query param：
       - EventSource API 不支持设置自定义 HTTP Headers
       - 通过 URL query string 传递 JWT token
       - HTTPS 下 URL 参数是加密的，安全性可接受
    """
    user_id = verify_token_str(token)
    if not user_id:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=401, content={"detail": "无效 Token"})

    session = svc.match_sessions.get(session_id)
    if not session:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"detail": "会话不存在"})

    if session.user_id != user_id:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=403, content={"detail": "无权访问此会话"})

    async def event_generator():
        """SSE 事件生成器：从队列读取事件，格式化为 SSE 文本"""
        while True:
            try:
                # 等待下一个事件（超时 60s 防止永久挂起）
                event = await asyncio.wait_for(session.event_queue.get(), timeout=60.0)
            except asyncio.TimeoutError:
                yield 'data: {"event": "keepalive"}\n\n'
                continue

            if event is None:
                # 哨兵值：流结束
                yield 'data: {"event": "stream_end"}\n\n'
                return

            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.post("/{session_id}/resume", status_code=204)
async def resume_match(
    session_id: str,
    body: MatchResumeRequest,
    svc: AppServices = Depends(get_services),
    current_user_id: str = Depends(get_current_user),
):
    """
    HITL 恢复端点：用户确认候选人预览后，继续深度分析。

    学习要点：
    ---------
    asyncio.Event 信号机制：
    - session.resume_event.wait() 在后台任务中挂起协程
    - session.resume_event.set() 在这里唤醒等待的协程
    - 这是 Python asyncio 中协程间通信的标准方式之一
    - 对比 asyncio.Queue：Event 适合"一次性信号"，Queue 适合"持续消息"
    """
    session = svc.match_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="无权操作此会话")
    if session.status != "waiting_hitl":
        raise HTTPException(
            status_code=400,
            detail=f"会话当前状态为 {session.status}，不在 HITL 等待状态"
        )

    # 存储用户决策并唤醒后台任务
    session.resume_payload = {"action": body.action}
    session.resume_event.set()


@router.get("/{session_id}/result")
async def get_match_session_result(
    session_id: str,
    svc: AppServices = Depends(get_services),
    current_user_id: str = Depends(get_current_user),
):
    """获取匹配会话的最终结果"""
    session = svc.match_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="无权访问此会话")
    if session.status in ("running", "waiting_hitl"):
        return {"status": session.status, "result": None}
    if session.status == "error":
        raise HTTPException(status_code=500, detail=session.error or "匹配失败")
    return {"status": "done", "result": session.result}
