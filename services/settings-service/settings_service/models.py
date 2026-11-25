from sqlalchemy import Column, DateTime, LargeBinary, String
from sqlalchemy.orm import declarative_base

from kiosk_common.outbox import make_outbox_model
from kiosk_common.timeutil import utcnow

Base = declarative_base()


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(String, default="")


class PaymentQr(Base):
    """An uploaded QR code image of a payment method, served at /api/images/<name>."""

    __tablename__ = "payment_qr"

    name = Column(String, primary_key=True)
    content_type = Column(String, nullable=False)
    data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=utcnow)


Outbox = make_outbox_model(Base)

DEFAULTS = {
    "store_name": "My Kiosk Store",
    "receipt_footer": "Thank you for your purchase!",
    "currency": "EUR",
    "payment_due_date": "",
    "kiosk_idle_seconds": "90",
    "kiosk_barcode_scanning": "false",
    "backup_interval_hours": "24",
    "backup_keep": "7",
    # How customers can pay (the kiosk's Pay screen), chosen by the admin.
    "payment_methods": "[]",
    "pay_instructions": "",
}
