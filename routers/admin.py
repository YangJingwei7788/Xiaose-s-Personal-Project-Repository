"""后台登录、配置、密码与图片上传接口。"""
import secrets
import uuid

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from sqlalchemy import select

from database import db, uploads_dir
from models import PUBLIC_SETTING_KEYS, Setting
from schemas import LoginRequest, PasswordUpdate, SettingsUpdate

router = APIRouter()

# 内存中的有效登录令牌（服务重启后需重新登录）
_TOKENS: set[str] = set()

ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


def require_admin(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    token = authorization[len("Bearer "):].strip()
    if token not in _TOKENS:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    return token


@router.post("/api/admin/login")
def login(payload: LoginRequest):
    with db() as session:
        setting = session.execute(
            select(Setting).where(Setting.key == "admin_password")
        ).scalar_one_or_none()
    if setting is None or setting.value != payload.password:
        raise HTTPException(status_code=401, detail="密码错误")
    token = secrets.token_hex(16)
    _TOKENS.add(token)
    return {"code": 0, "message": "登录成功", "data": {"token": token}}


@router.post("/api/admin/upload")
async def upload_image(file: UploadFile = File(...), _=Depends(require_admin)):
    """上传图片（品类图/轮播图通用），返回可访问的 URL。"""
    ext = ""
    if file.filename:
        ext = (file.filename.rsplit(".", 1)[-1] if "." in file.filename else "").lower()
    ext = "." + ext if ext else ""
    if ext not in ALLOWED_IMAGE_EXT:
        raise HTTPException(status_code=400, detail="仅支持 jpg/jpeg/png/gif/webp 格式图片")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="图片不能超过 5MB")
    name = f"{uuid.uuid4().hex}{ext}"
    uploads = uploads_dir()
    uploads.mkdir(parents=True, exist_ok=True)
    (uploads / name).write_bytes(content)
    return {"code": 0, "data": {"url": f"/uploads/{name}", "name": name}}


@router.get("/api/settings/public")
def get_public_settings():
    """前台公开：返回除后台密码外的全部门店配置。"""
    with db() as session:
        rows = session.execute(select(Setting)).scalars().all()
    data = {r.key: r.value for r in rows}
    data.pop("admin_password", None)
    return {"code": 0, "data": data}


@router.get("/api/admin/settings")
def get_admin_settings(_=Depends(require_admin)):
    with db() as session:
        rows = session.execute(
            select(Setting).where(Setting.key != "admin_password")
        ).scalars().all()
    return {"code": 0, "data": {r.key: r.value for r in rows}}


@router.put("/api/admin/settings")
def update_settings(payload: SettingsUpdate, _=Depends(require_admin)):
    with db() as session:
        for key, value in payload.settings.items():
            if key not in PUBLIC_SETTING_KEYS:
                raise HTTPException(status_code=400, detail=f"不允许修改配置项：{key}")
            setting = session.execute(
                select(Setting).where(Setting.key == key)
            ).scalar_one_or_none()
            if setting is None:
                session.add(Setting(key=key, value=value))
            else:
                setting.value = value
    return {"code": 0, "message": "保存成功"}


@router.put("/api/admin/password")
def update_password(payload: PasswordUpdate, _=Depends(require_admin)):
    with db() as session:
        setting = session.execute(
            select(Setting).where(Setting.key == "admin_password")
        ).scalar_one_or_none()
        if setting is None or setting.value != payload.old_password:
            raise HTTPException(status_code=400, detail="原密码错误")
        setting.value = payload.new_password
    return {"code": 0, "message": "密码修改成功"}