"""用户登录、注册、信息管理、头像上传接口"""
import asyncio
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from xiaosemiao_ai.config.cache_conf import cache_delete, cache_set, get_user_token_key
from xiaosemiao_ai.config.settings import settings
from xiaosemiao_ai.crud import user as crud_user
from xiaosemiao_ai.models.user import User
from xiaosemiao_ai.routers.deps import get_current_user, get_db
from xiaosemiao_ai.schemas.user import (
    LLMSettingsOut,
    LLMSettingsUpdate,
    LoginResult,
    PasswordUpdate,
    UserInfo,
    UserLogin,
    UserRegister,
    UserUpdate,
)
from xiaosemiao_ai.utils.common import success
from xiaosemiao_ai.utils.security import create_token, verify_password

router = APIRouter()

# 头像上传相关配置
AVATAR_DIR = Path(__file__).resolve().parent.parent / "static" / "avatars"
AVATAR_URL_PREFIX = "/static/avatars/"
ALLOWED_AVATAR_EXTS = {"jpg", "jpeg", "png", "gif", "webp"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/register", summary="用户注册")
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    if await crud_user.get_user_by_username(db, payload.username):
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = await crud_user.create_user(db, payload.username, payload.password)
    return success(UserInfo.model_validate(user).model_dump(mode="json"), "注册成功")


@router.post("/login", summary="用户登录")
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await crud_user.get_user_by_username(db, payload.username)
    if user is None or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=401, detail="账户名或密码错误")

    token = create_token(user.id)
    expires_at = datetime.now() + timedelta(days=settings.JWT_EXPIRE_DAYS)
    await crud_user.create_user_token(db, user.id, token, expires_at)
    await cache_set(get_user_token_key(user.id), token, ttl=settings.JWT_EXPIRE_DAYS * 24 * 3600)

    result = LoginResult(token=token, user=UserInfo.model_validate(user)).model_dump(mode="json")
    return success(result, "登录成功")


@router.get("/info", summary="获取当前用户信息")
async def get_info(user: User = Depends(get_current_user)):
    return success(UserInfo.model_validate(user).model_dump(mode="json"))


@router.put("/update", summary="更新用户信息")
async def update_info(
    payload: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await crud_user.update_user(db, user, nickname=payload.nickname, avatar=payload.avatar)
    return success(UserInfo.model_validate(user).model_dump(mode="json"), "更新成功")


@router.put("/password", summary="修改密码")
async def change_password(
    payload: PasswordUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.old_password, user.password):
        raise HTTPException(status_code=400, detail="原密码错误")
    await crud_user.update_user_password(db, user, payload.new_password)
    return success(message="密码修改成功")


@router.post("/avatar", summary="上传头像（新头像自动替换旧头像）")
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 1. 校验格式
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_AVATAR_EXTS:
        raise HTTPException(status_code=400, detail="仅支持 jpg/jpeg/png/gif/webp 格式图片")
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    # 2. 校验大小与内容
    data = await file.read()
    if len(data) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=400, detail="图片大小不能超过 5MB")
    if not data:
        raise HTTPException(status_code=400, detail="图片内容为空")

    # 3. 保存新头像（随机文件名，避免重名覆盖）
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    new_name = f"{uuid.uuid4().hex}.{ext}"
    await asyncio.to_thread((AVATAR_DIR / new_name).write_bytes, data)

    # 4. 删除旧头像文件（仅删除本地上传的头像，避免误删外链资源）
    if user.avatar and user.avatar.startswith(AVATAR_URL_PREFIX):
        old_name = user.avatar.rsplit("/", 1)[-1]
        old_path = (AVATAR_DIR / old_name).resolve()
        avatar_dir_resolved = AVATAR_DIR.resolve()
        if old_path.is_relative_to(avatar_dir_resolved) and old_path.exists():
            try:
                old_path.unlink()
            except OSError:
                pass

    # 5. 更新数据库并返回最新用户信息
    user = await crud_user.update_user(db, user, avatar=f"{AVATAR_URL_PREFIX}{new_name}")
    return success(UserInfo.model_validate(user).model_dump(mode="json"), "头像上传成功")


@router.post("/logout", summary="用户登出")
async def logout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    token = (authorization or "").removeprefix("Bearer ").strip()
    await crud_user.delete_user_token(db, user.id, token)
    await cache_delete(get_user_token_key(user.id))
    return success(message="退出登录成功")

@router.get("/settings/llm", summary="获取我的大模型设置")
async def get_llm_settings(user: User = Depends(get_current_user)):
    data = LLMSettingsOut(
        llm_provider=user.llm_provider,
        llm_base_url=user.llm_base_url,
        llm_has_api_key=bool(user.llm_api_key),
        llm_model=user.llm_model,
        server_default_model=settings.OLLAMA_MODEL,
    ).model_dump(mode="json")
    return success(data, "获取成功")


@router.put("/settings/llm", summary="保存我的大模型设置")
async def save_llm_settings(
    payload: LLMSettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # api_key 传空表示保留原值（不覆盖已保存的 Key）
    api_key = payload.llm_api_key if payload.llm_api_key else user.llm_api_key
    user = await crud_user.update_user_llm_settings(
        db,
        user,
        provider=payload.llm_provider,
        base_url=payload.llm_base_url,
        api_key=api_key,
        model=payload.llm_model,
    )
    data = LLMSettingsOut(
        llm_provider=user.llm_provider,
        llm_base_url=user.llm_base_url,
        llm_has_api_key=bool(user.llm_api_key),
        llm_model=user.llm_model,
        server_default_model=settings.OLLAMA_MODEL,
    ).model_dump(mode="json")
    return success(data, "设置已保存")
