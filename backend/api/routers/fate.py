"""
/api/fate 路由 - 心动 TA 们清单 + 缘分分析。

接口列表：
  POST   /api/fate/candidates/{candidate_id}  加入心动清单
  DELETE /api/fate/candidates/{candidate_id}  移出心动清单
  GET    /api/fate/candidates                 获取我的心动清单
  POST   /api/fate/analyses                   发起缘分分析（后台运行 Agent）
  GET    /api/fate/analyses                   获取历史分析列表
  GET    /api/fate/analyses/{analysis_id}     获取单条分析结果（前端轮询）

权限规则：
  - 必须登录才能使用所有接口
  - 发起缘分分析还需 profile_complete=True
"""
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from api.auth import get_current_user, get_optional_user
from api.schemas import (
    FateCandidateListResponse,
    FateCandidateResponse,
    FateAnalysisCreate,
    FateAnalysisResponse,
    UserPublicResponse,
)
from core.database.session import get_db
from core.database.models import User, FateCandidate, FateAnalysis, Notification
from core.agents.fate.agent import run_fate_analysis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/fate", tags=["fate"])


# ── 辅助函数 ─────────────────────────────────────────────────

def _to_public(user: User) -> dict:
    """转换为公开资料（不含手机号/密码等敏感字段）。"""
    return {
        "user_id": user.user_id,
        "nickname": user.nickname,
        "gender": user.gender,
        "age": user.age,
        "city": user.city,
        "province": user.province,
        "education": user.education,
        "annual_income": user.annual_income,
        "marital_status": user.marital_status,
        "mbti": user.mbti,
        "height_cm": user.height_cm,
        "about_me": user.about_me,
        "hobbies": user.hobbies or "",
        "avatar_url": user.avatar_url,
        "photos": user.photos or [],
        "zodiac_sign": user.zodiac_sign,
        "chinese_zodiac": user.chinese_zodiac,
        "birth_date": user.birth_date.isoformat() if user.birth_date else None,
        "profile_complete": user.profile_complete,
    }


async def _get_user_or_404(db: AsyncSession, user_id: str) -> User:
    """获取用户，不存在则抛 404。"""
    user = await db.scalar(select(User).where(User.user_id == user_id))
    if not user:
        raise HTTPException(404, "用户不存在")
    return user


# ── 心动候选接口 ──────────────────────────────────────────────

@router.post("/candidates/{candidate_id}", status_code=201)
async def add_fate_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """
    加入心动 TA 们清单。

    - 不能加入自己
    - 重复加入返回提示而非报错
    - 双方互相加入时触发"双向心动"通知
    """
    if candidate_id == current_user_id:
        raise HTTPException(400, "不能把自己加入心动清单")

    # 确认候选者存在
    candidate = await db.scalar(select(User).where(User.user_id == candidate_id))
    if not candidate:
        raise HTTPException(404, "用户不存在")

    # 检查是否已加入
    existing = await db.scalar(
        select(FateCandidate).where(
            FateCandidate.user_id == current_user_id,
            FateCandidate.candidate_id == candidate_id,
        )
    )
    if existing:
        return {"message": "已在心动清单中", "mutual_fate": False}

    fc = FateCandidate(user_id=current_user_id, candidate_id=candidate_id)
    db.add(fc)

    # 通知被加入的用户
    current_user = await db.scalar(select(User).where(User.user_id == current_user_id))
    notif = Notification(
        notif_id=str(uuid.uuid4()),
        recipient_id=candidate_id,
        type="fate_added",
        actor_id=current_user_id,
        payload={"actor_name": current_user.nickname if current_user else "某用户"},
    )
    db.add(notif)
    await db.flush()  # 先 flush 写入，再检查双向

    # 检查是否双向心动
    reverse = await db.scalar(
        select(FateCandidate).where(
            FateCandidate.user_id == candidate_id,
            FateCandidate.candidate_id == current_user_id,
        )
    )
    mutual = bool(reverse)
    if mutual:
        # 双向心动！通知双方
        for (recipient_id, actor_id) in [
            (current_user_id, candidate_id),
            (candidate_id, current_user_id),
        ]:
            mutual_notif = Notification(
                notif_id=str(uuid.uuid4()),
                recipient_id=recipient_id,
                type="mutual_fate",
                actor_id=actor_id,
                payload={"message": "你们互相心动了！"},
            )
            db.add(mutual_notif)

    return {"message": "加入成功", "mutual_fate": mutual}


@router.delete("/candidates/{candidate_id}", status_code=204)
async def remove_fate_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """从心动清单移除候选者。"""
    await db.execute(
        delete(FateCandidate).where(
            FateCandidate.user_id == current_user_id,
            FateCandidate.candidate_id == candidate_id,
        )
    )


@router.get("/candidates", response_model=FateCandidateListResponse)
async def get_fate_candidates(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """获取我的心动 TA 们清单（含候选者详情）。"""
    result = await db.execute(
        select(FateCandidate)
        .where(FateCandidate.user_id == current_user_id)
        .order_by(FateCandidate.added_at.desc())
    )
    fcs = result.scalars().all()

    items = []
    for fc in fcs:
        candidate = await db.scalar(select(User).where(User.user_id == fc.candidate_id))
        if candidate:
            items.append(
                FateCandidateResponse(
                    candidate_id=fc.candidate_id,
                    note=fc.note,
                    added_at=fc.added_at.isoformat() if fc.added_at else "",
                    candidate=UserPublicResponse(**_to_public(candidate)),
                )
            )

    return FateCandidateListResponse(items=items, total=len(items))


# ── 缘分分析接口 ──────────────────────────────────────────────

@router.post("/analyses", response_model=FateAnalysisResponse, status_code=201)
async def create_fate_analysis(
    data: FateAnalysisCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """
    发起缘分分析（异步执行）。

    流程：
    1. 权限校验（必须 profile_complete=True）
    2. 获取候选者数据
    3. 创建 FateAnalysis 记录（status=pending）
    4. 后台启动 FateAnalysisAgent
    5. 返回 analysis_id，前端轮询 GET /analyses/{id}
    """
    current_user = await _get_user_or_404(db, current_user_id)

    if not current_user.profile_complete:
        raise HTTPException(403, "请先完善个人资料后再发起缘分分析")

    # 获取候选者数据
    candidates_data = []
    for cid in data.candidate_ids:
        c = await db.scalar(select(User).where(User.user_id == cid))
        if c:
            candidates_data.append(c.to_dict())

    if not candidates_data:
        raise HTTPException(400, "候选者列表为空或用户不存在")

    analysis_id = str(uuid.uuid4())
    analysis = FateAnalysis(
        analysis_id=analysis_id,
        initiator_id=current_user_id,
        analysis_type=data.analysis_type,
        candidate_ids=data.candidate_ids,
        match_params_snapshot=data.match_params_override,
        parent_analysis_id=data.parent_analysis_id,
        status="pending",
    )
    db.add(analysis)
    await db.flush()

    # 后台执行 Agent（不阻塞响应）
    background_tasks.add_task(
        _run_analysis_background,
        analysis_id=analysis_id,
        analysis_type=data.analysis_type,
        initiator=current_user.to_dict(),
        candidates=candidates_data,
        match_params=data.match_params_override or {},
    )

    return FateAnalysisResponse(
        analysis_id=analysis_id,
        analysis_type=data.analysis_type,
        candidate_ids=data.candidate_ids,
        result=None,
        status="pending",
        created_at=analysis.created_at.isoformat() if analysis.created_at else "",
    )


async def _run_analysis_background(
    analysis_id: str,
    analysis_type: str,
    initiator: dict,
    candidates: list,
    match_params: dict,
):
    """
    后台任务：运行 FateAnalysisAgent 并将结果写入数据库。

    学习要点：
    - FastAPI BackgroundTasks 在响应发送后异步执行
    - 这里使用独立的 AsyncSessionLocal 创建新会话（原请求会话已关闭）
    - 分析完成后发送"analysis_done"通知
    """
    from core.database.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        try:
            logger.info(f"[FateAgent] Starting analysis {analysis_id} type={analysis_type}")
            report = await run_fate_analysis(
                analysis_id=analysis_id,
                analysis_type=analysis_type,
                initiator=initiator,
                candidates=candidates,
                match_params=match_params,
            )

            analysis = await db.scalar(
                select(FateAnalysis).where(FateAnalysis.analysis_id == analysis_id)
            )
            if analysis:
                analysis.result = report
                analysis.status = "done"

            # 发送分析完成通知
            notif = Notification(
                notif_id=str(uuid.uuid4()),
                recipient_id=initiator["user_id"],
                type="analysis_done",
                payload={"analysis_id": analysis_id, "analysis_type": analysis_type},
            )
            db.add(notif)
            await db.commit()
            logger.info(f"[FateAgent] Analysis {analysis_id} done")

        except Exception as e:
            logger.error(f"[FateAgent] Analysis {analysis_id} failed: {e}", exc_info=True)
            try:
                analysis = await db.scalar(
                    select(FateAnalysis).where(FateAnalysis.analysis_id == analysis_id)
                )
                if analysis:
                    analysis.status = "failed"
                    analysis.result = {"error": str(e)}
                    await db.commit()
            except Exception:
                pass


@router.get("/analyses/{analysis_id}", response_model=FateAnalysisResponse)
async def get_fate_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """
    获取单条分析结果。

    前端使用轮询模式：每 2 秒请求一次，直到 status 变为 done 或 failed。
    """
    analysis = await db.scalar(
        select(FateAnalysis).where(
            FateAnalysis.analysis_id == analysis_id,
            FateAnalysis.initiator_id == current_user_id,
        )
    )
    if not analysis:
        raise HTTPException(404, "分析记录不存在")

    return FateAnalysisResponse(
        analysis_id=analysis.analysis_id,
        analysis_type=analysis.analysis_type,
        candidate_ids=analysis.candidate_ids,
        result=analysis.result,
        status=analysis.status,
        created_at=analysis.created_at.isoformat() if analysis.created_at else "",
    )


@router.get("/analyses", response_model=list[FateAnalysisResponse])
async def list_fate_analyses(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
    limit: int = Query(default=20, le=50),
):
    """获取我的历史缘分分析列表（最新在前）。"""
    result = await db.execute(
        select(FateAnalysis)
        .where(FateAnalysis.initiator_id == current_user_id)
        .order_by(FateAnalysis.created_at.desc())
        .limit(limit)
    )
    analyses = result.scalars().all()
    return [
        FateAnalysisResponse(
            analysis_id=a.analysis_id,
            analysis_type=a.analysis_type,
            candidate_ids=a.candidate_ids,
            result=a.result,
            status=a.status,
            created_at=a.created_at.isoformat() if a.created_at else "",
        )
        for a in analyses
    ]


# ── 我是否被他人加入心动清单（对称接口）────────────────────────

@router.get("/candidates/status/{target_user_id}")
async def get_candidate_status(
    target_user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user_id: Optional[str] = Depends(get_optional_user),
):
    """
    检查当前用户是否已将目标用户加入心动清单（用于 UserCard 心动按钮状态）。
    游客返回 is_hearted=false。
    """
    if not current_user_id:
        return {"is_hearted": False}

    existing = await db.scalar(
        select(FateCandidate).where(
            FateCandidate.user_id == current_user_id,
            FateCandidate.candidate_id == target_user_id,
        )
    )
    return {"is_hearted": bool(existing)}
