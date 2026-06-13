"""
心犀AI - JWT 认证工具模块
==========================
提供密码加密、JWT Token 生成/验证、FastAPI 依赖注入。

学习要点：
---------
1. bcrypt 密码加密：
   - passlib 是 Python 最常用的密码加密库
   - bcrypt 算法自带"盐值"（salt），同一个密码加密两次结果不同
   - 这样即使数据库泄露，攻击者也无法反推原始密码

2. JWT (JSON Web Token)：
   - 一种无状态认证方案：服务端不需要存储 session
   - Token 包含用户信息（payload），用密钥签名防篡改
   - 每次请求带上 Token，服务端验证签名即可确认身份
   - 优点：简单、跨域友好、适合前后端分离
   - 缺点：Token 一旦发出无法主动失效（所以设置短过期时间）

3. FastAPI Depends() 注入：
   - get_current_user: 必须登录的接口用这个
   - get_optional_user: 可选登录（游客也能访问）
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

# ============================================================
# 配置
# ============================================================

# 【学习要点】
# SECRET_KEY 是 JWT 签名的密钥，必须保密！
# 生产环境务必使用随机生成的强密钥，不要用默认值。
SECRET_KEY = os.getenv("JWT_SECRET", "xinxi-ai-dev-secret-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# ============================================================
# 密码加密
# ============================================================

# 【学习要点】
# CryptContext 是 passlib 的高级接口：
# - schemes=["bcrypt"]: 使用 bcrypt 算法
# - deprecated="auto": 自动升级旧算法（如果将来换算法，旧密码会自动迁移）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    将明文密码加密为哈希值。

    学习要点：
    - bcrypt 会自动生成随机盐值（salt）
    - 所以同一个密码每次加密结果都不同（这是安全的！）
    - 返回的字符串包含算法版本、盐值和哈希值
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码是否与存储的哈希值匹配。

    学习要点：
    - passlib 会从 hashed_password 中提取盐值
    - 用同一个盐值加密 plain_password，然后比较结果
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================
# JWT Token 管理
# ============================================================

# 【学习要点】
# HTTPBearer 是 FastAPI 的安全方案类：
# - 自动从请求头提取 Authorization: Bearer <token>
# - 如果缺少 Token，自动返回 401 Unauthorized
# - 比手动解析 Header 更安全、更规范
security = HTTPBearer(auto_error=False)
security_required = HTTPBearer(auto_error=True)


def create_access_token(user_id: str, nickname: str) -> str:
    """
    创建访问 Token（短期有效，用于 API 请求鉴权）。

    学习要点：
    - sub (subject): Token 的主题，这里放 user_id
    - exp (expiration): 过期时间，超时后 Token 失效
    - type: 自定义字段，区分 access 和 refresh Token
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "nickname": nickname,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """
    创建刷新 Token（长期有效，用于获取新的 access Token）。

    学习要点：
    - refresh Token 过期时间更长（7天）
    - 当 access Token 过期时，用 refresh Token 换一个新的 access Token
    - 这样用户不需要频繁登录，同时 access Token 的短有效期也更安全
    """
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    解码并验证 JWT Token。

    学习要点：
    - jwt.decode 会验证签名和过期时间
    - 如果签名不匹配或已过期，抛出 JWTError
    - 返回 payload 字典，包含 sub（user_id）等信息
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============================================================
# FastAPI 依赖注入
# ============================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_required),
):
    """
    必须登录才能访问的接口依赖。

    使用方式：
        @router.get("/my-data")
        async def my_data(user_id: str = Depends(get_current_user)):
            ...  # 只有登录用户才能执行

    学习要点：
    - Depends(security_required) 自动从 Header 提取 Bearer Token
    - 如果缺少 Token → 401
    - 如果 Token 无效 → 401
    - 返回 user_id 字符串
    """
    token = credentials.credentials
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(401, "请使用 access Token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "Token 中缺少用户信息")

    return user_id


def verify_token_str(token: str) -> Optional[str]:
    """
    验证 JWT token 字符串，返回 user_id 或 None。
    专为 SSE 端点使用（EventSource 不支持自定义 Header，通过 query param 传 token）。

    学习要点：
    SSE（Server-Sent Events）使用浏览器原生的 EventSource API，
    EventSource 不允许设置自定义 Headers（包括 Authorization）。
    因此 SSE 端点需要通过 URL query string 传递 token：
      GET /api/match/{session_id}/stream?token=<jwt_token>
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return payload.get("sub")
    except HTTPException:
        return None


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """
    可选登录依赖（游客也能访问，登录用户有额外功能）。

    使用方式：
        @router.get("/user/{user_id}")
        async def user_detail(
            user_id: str,
            current_user: Optional[str] = Depends(get_optional_user),
        ):
            if current_user:
                ...  # 已登录：显示更多功能（关注按钮等）
            else:
                ...  # 游客：基本信息

    学习要点：
    - Depends(security) 的 auto_error=False，缺少 Token 不会报错
    - 如果没有 Token 或 Token 无效，返回 None（而不是抛异常）
    """
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            return None
        return payload.get("sub")
    except HTTPException:
        return None
