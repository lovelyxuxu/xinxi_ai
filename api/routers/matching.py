"""
心犀AI - 匹配路由
==================
处理匹配推荐和匹配历史相关的 HTTP 接口。

接口列表：
  POST /api/match           触发匹配（调用 Agent 工作流）
  GET  /api/match/{id}      获取单次匹配结果
  GET  /api/match/history/{user_id}  获取用户的匹配历史
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends

from api.schemas import (
    MatchRequest, MatchResult, MatchCandidate,
    MatchHistoryResponse, MessageResponse,
)
from api.deps import get_services, AppServices, generate_match_id
from src.agent.state import AgentState
from src.models.user_profile import UserProfile

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


# ============================================================
# POST /api/match - 触发匹配
# ============================================================
@router.post("", response_model=MatchResult)
def trigger_match(body: MatchRequest, svc: AppServices = Depends(get_services)):
    """
    为指定用户触发一次完整的 AI 匹配流程。

    这是系统最核心的接口！内部流程：
    1. 从 Chroma 加载用户资料
    2. 构建 LangGraph Agent 工作流的初始状态
    3. 执行工作流：意图解析 → 混合检索 → LLM 评分 → (反思循环) → 生成推荐信
    4. 将结果存入匹配历史
    5. 返回匹配结果
    """
    # 1. 重建用户画像
    user_profile = _rebuild_user_profile(body.user_id, svc)

    # 2. 构建初始状态
    initial_state: AgentState = {
        "user_profile": user_profile,
        "loop_count": 0,
        "messages": [],
    }

    # 3. 执行 LangGraph 工作流
    final_state = svc.matching_graph.invoke(initial_state)

    # 4. 整理结果
    match_id = generate_match_id()
    now = datetime.now().isoformat()

    candidates = []
    for m in final_state.get("top_matches", []):
        candidates.append(MatchCandidate(
            user_id=m.get("user_id", ""),
            nickname=m.get("nickname", ""),
            score=m.get("score", 0),
            reason=m.get("reason", ""),
        ))

    result = MatchResult(
        match_id=match_id,
        user_id=body.user_id,
        candidates=candidates,
        match_letters=final_state.get("match_letters", []),
        created_at=now,
        agent_log=final_state.get("messages", []),
    )

    # 5. 存入匹配历史
    if body.user_id not in svc.match_history:
        svc.match_history[body.user_id] = []
    svc.match_history[body.user_id].append(result.model_dump())

    return result


# ============================================================
# GET /api/match/history/{user_id} - 获取匹配历史
# ============================================================
# 注意：这个路由必须放在 /{match_id} 前面，
# 否则 FastAPI 会把 "history" 当作 match_id 来匹配！
@router.get("/history/{user_id}", response_model=MatchHistoryResponse)
def get_match_history(
    user_id: str,
    svc: AppServices = Depends(get_services),
):
    """
    获取指定用户的所有匹配历史记录。
    按时间倒序排列（最新的在前面）。
    """
    records = svc.match_history.get(user_id, [])

    # 按时间倒序
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
    """根据 match_id 获取一次匹配的完整结果"""
    # 遍历所有用户的历史记录查找
    for user_id, records in svc.match_history.items():
        for record in records:
            if record.get("match_id") == match_id:
                return MatchResult(**record)

    raise HTTPException(status_code=404, detail=f"匹配记录 {match_id} 不存在")
