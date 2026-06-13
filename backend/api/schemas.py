"""
心犀AI - API 请求/响应数据模型
================================
定义所有 HTTP 接口的输入输出格式。

学习要点：
---------
- 这些 Schema 和 src/models/user_profile.py 里的 UserProfile 是不同层次的模型
- UserProfile 是"领域模型"——系统内部使用的完整数据
- 这里的 Schema 是"传输模型"——对外暴露的、可能做了裁剪或组合的数据
- 分离两者的好处：内部改动不影响 API 契约，API 也能隐藏敏感字段
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============================================================
# 用户相关 Schema
# ============================================================

class UserCreate(BaseModel):
    """
    注册请求体 - 简化版，只需 4 个字段。
    其他资料可在注册后通过 PUT /api/auth/me 完善。
    """
    nickname: str = Field(description="用户昵称", min_length=2, max_length=20)
    gender: str = Field(description="性别: 男 / 女", pattern="^(男|女)$")
    phone: str = Field(description="手机号", pattern=r"^1[3-9]\d{9}$")
    password: str = Field(description="密码（至少8位）", min_length=8, max_length=50)


class UserUpdate(BaseModel):
    """
    更新用户时的请求体。
    所有字段都是可选的，只传需要修改的字段即可。
    """
    nickname: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=18, le=80)
    city: Optional[str] = None
    province: Optional[str] = None
    education: Optional[str] = None
    annual_income: Optional[str] = None
    marital_status: Optional[str] = None
    height_cm: Optional[int] = None

    birth_date: Optional[str] = None  # 格式: YYYY-MM-DD，自动计算星座/属相/年龄

    target_gender: Optional[str] = None
    target_age_min: Optional[int] = Field(default=None, ge=18, le=80)
    target_age_max: Optional[int] = Field(default=None, ge=18, le=80)
    target_city: Optional[str] = None
    target_height_min: Optional[int] = None
    target_height_max: Optional[int] = None
    target_education: Optional[str] = None

    about_me: Optional[str] = Field(default=None, min_length=5)
    ideal_partner: Optional[str] = Field(default=None, min_length=5)
    hobbies: Optional[str] = None
    mbti: Optional[str] = None


class UserResponse(BaseModel):
    """
    用户信息的响应体（登录用户自己的完整信息）。
    """
    user_id: str
    nickname: str
    gender: str
    age: Optional[int] = None
    city: Optional[str] = None
    province: Optional[str] = None
    education: Optional[str] = None
    annual_income: Optional[str] = None
    marital_status: Optional[str] = None
    target_gender: Optional[str] = None
    target_age_min: Optional[int] = None
    target_age_max: Optional[int] = None
    target_city: Optional[str] = None
    target_height_min: Optional[int] = None
    target_height_max: Optional[int] = None
    target_education: Optional[str] = None
    about_me: Optional[str] = None
    ideal_partner: Optional[str] = None
    hobbies: Optional[str] = None
    mbti: Optional[str] = None
    height_cm: Optional[int] = None
    avatar_url: Optional[str] = None
    photos: list[str] = []
    birth_date: Optional[str] = None
    zodiac_sign: Optional[str] = None
    chinese_zodiac: Optional[str] = None
    profile_complete: bool = False
    created_at: Optional[str] = None

    # 认证 Token（仅注册/登录时返回）
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


class UserPublicResponse(BaseModel):
    """
    用户公开主页响应。

    学习要点：
    - 公开信息不包含 target_* 择偶偏好、邮箱、手机等私密字段
    - 任何人（含未登录用户）都能访问用户公开主页
    - 与 UserResponse（登录用户自己的完整信息）区分开
    """
    user_id: str
    nickname: str
    gender: str
    age: Optional[int] = None
    city: Optional[str] = None
    province: Optional[str] = None
    education: Optional[str] = None
    annual_income: Optional[str] = None
    marital_status: Optional[str] = None
    mbti: Optional[str] = None
    height_cm: Optional[int] = None
    about_me: str = ""
    hobbies: str = ""
    avatar_url: Optional[str] = None
    photos: list[str] = []
    birth_date: Optional[str] = None
    zodiac_sign: Optional[str] = None
    chinese_zodiac: Optional[str] = None
    profile_complete: bool = False
    created_at: Optional[str] = None


class UserListResponse(BaseModel):
    """用户列表响应（带分页）"""
    users: list[UserPublicResponse]
    total: int
    page: int
    page_size: int


# ============================================================
# 匹配相关 Schema
# ============================================================

class MatchRequest(BaseModel):
    """触发匹配的请求体"""
    user_id: str = Field(description="要为其执行匹配的用户ID")


class MatchCandidate(BaseModel):
    """单个匹配候选人"""
    user_id: str
    nickname: str
    score: int = Field(description="契合指数 0-100")
    reason: str = Field(description="匹配理由")


class MatchResult(BaseModel):
    """一次匹配的完整结果"""
    match_id: str = Field(description="本次匹配的唯一ID")
    user_id: str = Field(description="发起匹配的用户ID")
    candidates: list[MatchCandidate] = Field(description="推荐的候选人列表")
    match_letters: list[str] = Field(description="每位候选人的推荐信")
    created_at: str = Field(description="匹配时间")
    agent_log: list[str] = Field(default_factory=list, description="Agent 执行日志")


class MatchHistoryResponse(BaseModel):
    """匹配历史列表"""
    records: list[MatchResult]
    total: int


# ============================================================
# 通用响应
# ============================================================

class PhotoUploadResponse(BaseModel):
    """图片上传响应"""
    url: str = Field(description="图片访问 URL")
    photos: list[str] = Field(description="更新后的照片列表")


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
    success: bool = True
    data: Optional[dict] = None


# ============================================================
# 心动 TA 们 / 缘分分析 / 通知 Schema
# ============================================================

class FateCandidateResponse(BaseModel):
    """心动清单中的单个候选者"""
    candidate_id: str
    note: Optional[str] = None
    added_at: str
    candidate: UserPublicResponse


class FateCandidateListResponse(BaseModel):
    """心动清单列表"""
    items: List[FateCandidateResponse]
    total: int


class FateAnalysisCreate(BaseModel):
    """发起缘分分析的请求体"""
    analysis_type: str = Field(
        ...,
        pattern="^(group_overview|deep_compatibility|comm_advice|comparison)$",
        description="分析类型: group_overview(一层) | deep_compatibility/comm_advice/comparison(二层三路径)",
    )
    candidate_ids: List[str] = Field(..., min_length=1, max_length=20, description="候选者 user_id 列表")
    match_params_override: Optional[dict] = Field(default=None, description="临时覆盖的偏好参数（仅本次有效）")
    parent_analysis_id: Optional[str] = Field(default=None, description="关联的第一层分析 ID（二层时传入）")


class FateAnalysisResponse(BaseModel):
    """缘分分析记录响应"""
    analysis_id: str
    analysis_type: str
    candidate_ids: List[str]
    result: Optional[dict] = None
    status: str
    created_at: str


class NotificationResponse(BaseModel):
    """通知响应"""
    notif_id: str
    type: str
    actor_id: Optional[str] = None
    payload: dict = {}
    is_read: bool
    created_at: str


class NotificationListResponse(BaseModel):
    """通知列表响应"""
    items: List[NotificationResponse]
    unread_count: int


# ============================================================
# Phase 3c：匹配会话相关 Schema（SSE + HITL）
# ============================================================

class MatchStartRequest(BaseModel):
    """
    开始匹配请求体。
    user_filters 允许用户临时调整匹配参数（不修改个人资料）。
    """
    user_filters: Optional[dict] = Field(
        default=None,
        description="临时筛选参数，覆盖用户默认偏好（可选）",
    )


class MatchStartResponse(BaseModel):
    """开始匹配响应：返回 session_id，前端用它订阅 SSE 流"""
    session_id: str
    message: str = "匹配已启动，请订阅 SSE 流获取实时进度"


class MatchResumeRequest(BaseModel):
    """
    HITL 恢复请求体。
    用户在查看候选人预览后，决定继续分析还是调整条件。
    """
    action: str = Field(
        default="proceed",
        description="proceed = 开始深度分析（目前只支持 proceed）",
    )
