import json
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from kiosk_common import audit
from kiosk_common.auth import Principal, get_current_user
from kiosk_common.db import get_db
from settings_service import payment_info
from settings_service.models import Outbox, PaymentQr, Setting

router = APIRouter(prefix="/api/settings", tags=["settings"])
# Public: the kiosk shows the QR codes to everyone. The gateway sends /api/images/pay-* here.
images = APIRouter(prefix="/api/images", tags=["settings"])

ALLOWED_IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
_SIGNATURES = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
]


def _detect_image_type(data: bytes) -> str | None:
    for sig, mime in _SIGNATURES:
        if data.startswith(sig):
            return mime
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return None


class SettingIn(BaseModel):
    key: str
    value: str


@router.get("")
def list_settings(db: Session = Depends(get_db)):
    return {s.key: s.value for s in db.query(Setting).all()}


@router.post("/payment-qr")
def upload_payment_qr(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: Principal = Depends(get_current_user),
):
    """Upload the QR code image of a payment method (e.g. a Swish or bank QR).

    The image is only referenced once the admin saves `payment_methods` with its name.
    """
    ext = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if not ext:
        raise HTTPException(status_code=400, detail="Only PNG, JPEG, WebP and GIF images are allowed")
    data = file.file.read(MAX_IMAGE_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 5 MB)")
    actual_type = _detect_image_type(data)
    if actual_type is None or ALLOWED_IMAGE_TYPES.get(actual_type) != ext:
        raise HTTPException(status_code=400, detail="File content does not match the declared image type")
    name = f"pay-{uuid.uuid4().hex}{ext}"
    db.add(PaymentQr(name=name, content_type=actual_type, data=data))
    audit.record(db, Outbox, user.username, "settings.payment_qr_upload", "setting", payment_info.METHODS_SETTING, name)
    db.commit()
    return {"image": name, "url": f"/api/images/{name}"}


@images.get("/{name}")
def get_payment_qr(name: str, db: Session = Depends(get_db)):
    if not payment_info.QR_NAME_RE.match(name):
        raise HTTPException(status_code=404, detail="Not Found")
    row = db.get(PaymentQr, name)
    if row is None:
        raise HTTPException(status_code=404, detail="Not Found")
    return Response(
        content=row.data,
        media_type=row.content_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable", "X-Content-Type-Options": "nosniff"},
    )


@router.put("/{key}")
def upsert_setting(
    key: str,
    data: SettingIn,
    db: Session = Depends(get_db),
    user: Principal = Depends(get_current_user),
):
    value = data.value
    # The kiosk shows these to every customer, so they are checked and stored canonically.
    try:
        if key == payment_info.METHODS_SETTING:
            known = {name for (name,) in db.query(PaymentQr.name).all()}
            value = payment_info.normalize_methods(value, known)
        elif key == payment_info.INSTRUCTIONS_SETTING:
            value = payment_info.normalize_instructions(value)
    except payment_info.PaymentInfoError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    setting = db.get(Setting, key)
    previous = setting.value if setting else None
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)
    if previous != value:
        if key == payment_info.METHODS_SETTING:
            methods = json.loads(value)
            details = f"{len(methods)} payment method(s), {sum(m['enabled'] for m in methods)} shown"
        else:
            details = audit.describe_changes({key: previous}, {key: value})
        audit.record(db, Outbox, user.username, "settings.update", "setting", key, details)
    if key == payment_info.METHODS_SETTING:
        # Remove QR images that are no longer used by any method (same transaction).
        for name in payment_info.qr_images(previous) - payment_info.qr_images(value):
            db.query(PaymentQr).filter(PaymentQr.name == name).delete(synchronize_session=False)
    db.commit()
    return {"key": key, "value": setting.value}
