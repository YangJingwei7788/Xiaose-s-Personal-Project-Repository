"""密码加密与 JWT 鉴权工具"""
import types
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from passlib.context import CryptContext

from xiaosemiao_ai.config.settings import settings

# 兼容新版 bcrypt（移除 __about__ 后 passlib 读取版本号会告警，这里补齐避免噪音日志）
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = types.SimpleNamespace(__version__=getattr(bcrypt, "__version__", "4.1.3"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """bcrypt 加密密码"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码与加密密码是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)


def create_token(user_id: int) -> str:
    """生成 JWT 访问令牌（有效期 7 天，jti 保证同一秒内多次登录令牌唯一）"""
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": str(user_id),
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> int | None:
    """解析 JWT 令牌，成功返回用户 ID，失败返回 None"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        return None