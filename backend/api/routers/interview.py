"""
心犀AI - 用户访谈路由（WebSocket）
==================================
处理用户完善画像的对话接口。

学习要点：
---------
Phase 5 多 Agent 子图：
  访谈 Agent 是一个独立的 LangGraph 子图，有自己的状态（InterviewState）和节点。
  主匹配图和访谈子图共享同一个 checkpointer，但使用不同的 thread_id 隔离状态。

  访谈子图的流程：
    parse_answer（解析用户回复）→ generate_question（生成下一个问题）→ END（等待用户）
  每次用户发消息时，图会从头运行一遍，然后将状态保存到 checkpoint。
  下次连接时，可以从 checkpoint 恢复上次对话的状态继续。

注意：
  由于 SqliteSaver 不支持 async 方法，这里使用同步 invoke 而非 ainvoke。
  LangGraph 的 invoke 在 async 函数中也能正常使用（只是会阻塞事件循环）。
  对于学习项目来说这完全足够，生产环境建议换用 AsyncSqliteSaver。
"""

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from langchain_core.messages import HumanMessage, AIMessage

from api.deps import get_services
from core.agent.interview.state import InterviewState
# Phase 3: LangFuse 可观测性集成
from core.utils.observability import create_langfuse_callback, flush_langfuse

router = APIRouter(prefix="/api/interview", tags=["用户访谈"])


@router.websocket("/ws/{user_id}")
async def ws_interview(websocket: WebSocket, user_id: str):
    """
    WebSocket 访谈接口。

    流程：
    1. 连接建立后，由 AI 发出第一个问题（或欢迎语）
    2. 用户回复，AI 解析并更新画像，生成下一个问题
    3. 循环直到画像完善
    """
    await websocket.accept()
    svc = get_services()
    langfuse_handler = None  # Phase 3: 在 finally 中使用，需要先初始化

    # 1. 验证用户并重建/初始化访谈状态
    user_data = svc.chroma_store.get_user(user_id)
    if not user_data:
        await websocket.send_json({"type": "error", "message": "用户不存在"})
        await websocket.close()
        return

    # 从依赖中重建 UserProfile（复用 matching 的逻辑）
    from api.routers.matching import _rebuild_user_profile
    user_profile = _rebuild_user_profile(user_id, svc)

    # 2. 初始状态
    # 尝试从检查点获取状态，如果不存在则初始化
    # 访谈使用固定的 thread_id（interview_{user_id}），支持跨会话继续
    config = {"configurable": {"thread_id": f"interview_{user_id}"}}

    # Phase 3: 创建 LangFuse 回调处理器（如果已启用）
    # 访谈的 session_id 使用 interview_{user_id}，可以追踪用户的所有访谈对话
    langfuse_handler = create_langfuse_callback(
        user_id=user_id,
        session_id=f"interview_{user_id}",
        tags=["interview"],
    )
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]

    state = svc.interview_graph.get_state(config)

    if not state.values:
        # 第一次进入，初始化
        initial_state: InterviewState = {
            "messages": [],
            "draft_profile": user_profile,
            "missing_fields": [],
            "is_complete": False,
            "user_id": user_id
        }
        # 使用同步 invoke（兼容 SqliteSaver）
        # 在线程池中运行以避免阻塞事件循环
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: svc.interview_graph.invoke(initial_state, config=config)
        )

        # 发送 AI 的第一个问题
        if result["messages"]:
            await websocket.send_json({
                "type": "ai_message",
                "message": result["messages"][-1].content
            })
    else:
        # 已有状态（从 checkpoint 恢复），发送最后一条 AI 消息
        last_msg = state.values["messages"][-1]
        await websocket.send_json({
            "type": "ai_message",
            "message": last_msg.content if isinstance(last_msg, AIMessage) else "请继续告诉我你的情况"
        })

    # 3. 循环交互
    try:
        while True:
            # 等待用户输入
            data = await websocket.receive_text()
            user_msg = HumanMessage(content=data)

            # 运行图：parse_answer（解析回复）→ generate_question（生成新问题）
            # 使用 run_in_executor 避免阻塞事件循环
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: svc.interview_graph.invoke(
                    {"messages": [user_msg]},
                    config=config
                )
            )

            # 发送 AI 回复
            ai_msg = result["messages"][-1].content
            await websocket.send_json({
                "type": "ai_message",
                "message": ai_msg,
                "is_complete": result.get("is_complete", False)
            })

            # 如果访谈完成，同步更新到 ChromaDB
            if result.get("is_complete"):
                svc.chroma_store.upsert_user(result["draft_profile"])
                await websocket.send_json({
                    "type": "system",
                    "message": "画像已更新并持久化到数据库"
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"type": "error", "message": f"访谈异常: {str(e)}"})
    finally:
        # Phase 3: 确保所有追踪数据发送到 LangFuse 服务器
        flush_langfuse(langfuse_handler)
        try:
            await websocket.close()
        except:
            pass
