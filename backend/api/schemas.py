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
from typing import Optional
from datetime import datetime


# ============================================================
# 用户相关 Schema
# ============================================================

class UserCreate(BaseModel):
    """
    创建用户时的请求体。
    不需要传 user_id，系统会自动生成。
    """
    nickname: str = Field(description="用户昵称", min_length=1, max_length=20)
    gender: str = Field(description="性别: male / female")
    age: int = Field(description="年龄", ge=18, le=80)
    city: str = Field(description="所在城市")
    province: str = Field(description="所在省份")
    education: str = Field(default="本科", description="学历")
    annual_income: str = Field(default="未填写", description="年收入范围")
    marital_status: str = Field(default="未婚", description="婚姻状况")

    target_gender: str = Field(description="期望对方性别")
    target_age_min: int = Field(default=18, ge=18, le=80)
    target_age_max: int = Field(default=45, ge=18, le=80)
    target_city: str = Field(default="不限")

    about_me: str = Field(description="关于我", min_length=10)
    ideal_partner: str = Field(description="理想的Ta", min_length=10)
    hobbies: str = Field(default="", description="兴趣爱好，逗号分隔")
    mbti: str = Field(default="未知", description="MBTI 性格类型")

    # v2: 认证字段
    password: str = Field(description="密码（至少6位）", min_length=6)
    email: Optional[str] = Field(default=None, description="邮箱（可选）")
    phone: Optional[str] = Field(default=None, description="手机号（可选）")


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

    target_gender: Optional[str] = None
    target_age_min: Optional[int] = Field(default=None, ge=18, le=80)
    target_age_max: Optional[int] = Field(default=None, ge=18, le=80)
    target_city: Optional[str] = None

    about_me: Optional[str] = Field(default=None, min_length=10)
    ideal_partner: Optional[str] = Field(default=None, min_length=10)
    hobbies: Optional[str] = None
    mbti: Optional[str] = None


class UserResponse(BaseModel):
    """
    用户信息的响应体（对外暴露的公开信息）。
    """
    user_id: str
    nickname: str
    gender: str
    age: int
    city: str
    province: str
    education: str
    annual_income: str
    marital_status: str
    target_gender: str
    target_age_min: int
    target_age_max: int
    target_city: str
    about_me: str
    ideal_partner: str
    hobbies: str
    mbti: str
    height_cm: Optional[int] = None
    avatar_url: Optional[str] = None
    photos: list[str] = []
    created_at: Optional[str] = None

    # v2: 认证 Token（仅注册/登录时返回）
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
    age: int
    city: str
    province: str
    education: str
    annual_income: str
    marital_status: str
    mbti: str
    height_cm: Optional[int] = None
    about_me: str = ""
    hobbies: str = ""
    avatar_url: Optional[str] = None
    photos: list[str] = []
    created_at: Optional[str] = None
    follower_count: int = 0
    following_count: int = 0
    match_count: int = 0


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
