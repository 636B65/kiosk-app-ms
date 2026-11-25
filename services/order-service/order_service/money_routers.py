"""Purchases and extra payments: the money side of the store balance."""

from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from kiosk_common import audit
from kiosk_common.auth import Principal, get_current_user
from kiosk_common.db import get_db
from kiosk_common.internal import require_internal
from kiosk_common.timeutil import utcnow
from order_service.models import ExtraPayment, Outbox, Purchase
from order_service.schemas import ExtraPaymentOut, PurchaseIn, PurchaseOut, PurchaseUpdate

purchases = APIRouter(prefix="/api/purchases", tags=["purchases"])
extra_payments = APIRouter(prefix="/api/extra-payments", tags=["extra-payments"])
internal = APIRouter(prefix="/internal/money", tags=["internal"], dependencies=[Depends(require_internal)])


def _check_date(day) -> None:
    # A batch can be entered long after it was bought, never before it exists.
    # One day of slack covers a clock that is ahead of UTC.
    if day is not None and day > (utcnow() + timedelta(days=1)).date():
        raise HTTPException(status_code=422, detail="The purchase date cannot be in the future")


def _describe(p: Purchase) -> str:
    who = f" from {p.supplier}" if p.supplier else ""
    return f"{p.amount:.2f} on {p.purchased_on.isoformat()}{who}"


def _newest_purchases(db: Session, limit: int | None = None):
    query = db.query(Purchase).order_by(Purchase.purchased_on.desc(), Purchase.id.desc())
    return query.limit(limit).all() if limit else query.all()


def _newest_extras(db: Session, limit: int | None = None):
    query = db.query(ExtraPayment).order_by(ExtraPayment.created_at.desc(), ExtraPayment.id.desc())
    return query.limit(limit).all() if limit else query.all()


@purchases.get("", response_model=List[PurchaseOut])
def list_purchases(
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_user),
):
    """Newest purchase date first."""
    return _newest_purchases(db, limit)


@purchases.post("", response_model=PurchaseOut, status_code=201)
def create_purchase(data: PurchaseIn, db: Session = Depends(get_db), user: Principal = Depends(get_current_user)):
    _check_date(data.purchased_on)
    purchase = Purchase(
        purchased_on=data.purchased_on or utcnow().date(),
        amount=round(data.amount, 2),
        supplier=data.supplier.strip(),
        note=data.note.strip(),
        created_by=user.username,
    )
    db.add(purchase)
    db.flush()
    audit.record(db, Outbox, user.username, "purchase.create", "purchase", purchase.id, _describe(purchase))
    db.commit()
    db.refresh(purchase)
    return purchase


@purchases.put("/{purchase_id}", response_model=PurchaseOut)
def update_purchase(
    purchase_id: int,
    data: PurchaseUpdate,
    db: Session = Depends(get_db),
    user: Principal = Depends(get_current_user),
):
    purchase = db.get(Purchase, purchase_id)
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    values = data.model_dump(exclude_unset=True)
    _check_date(values.get("purchased_on"))

    def snapshot() -> dict:
        return {
            "amount": purchase.amount,
            "date": purchase.purchased_on,
            "supplier": purchase.supplier,
            "note": purchase.note,
        }

    before = snapshot()
    if values.get("amount") is not None:
        purchase.amount = round(values["amount"], 2)
    if values.get("purchased_on") is not None:
        purchase.purchased_on = values["purchased_on"]
    if values.get("supplier") is not None:
        purchase.supplier = values["supplier"].strip()
    if values.get("note") is not None:
        purchase.note = values["note"].strip()
    changes = audit.describe_changes(before, snapshot())
    if changes:
        audit.record(db, Outbox, user.username, "purchase.update", "purchase", purchase.id, changes)
    db.commit()
    db.refresh(purchase)
    return purchase


@purchases.delete("/{purchase_id}", status_code=204)
def delete_purchase(purchase_id: int, db: Session = Depends(get_db), user: Principal = Depends(get_current_user)):
    purchase = db.get(Purchase, purchase_id)
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    audit.record(db, Outbox, user.username, "purchase.delete", "purchase", purchase.id, _describe(purchase))
    db.delete(purchase)
    db.commit()


@extra_payments.get("", response_model=List[ExtraPaymentOut])
def list_extra_payments(
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_user),
):
    """What customers paid on top of their debt, newest first."""
    return _newest_extras(db, limit)


@extra_payments.delete("/{extra_id}", status_code=204)
def delete_extra_payment(extra_id: int, db: Session = Depends(get_db), user: Principal = Depends(get_current_user)):
    """Remove an entry made by mistake."""
    extra = db.get(ExtraPayment, extra_id)
    if not extra:
        raise HTTPException(status_code=404, detail="Extra payment not found")
    audit.record(
        db, Outbox, user.username, "customer.extra_payment_delete", "customer", extra.username,
        f"extra payment #{extra.id} of {extra.amount:.2f} removed",
    )
    db.delete(extra)
    db.commit()


@internal.get("/purchases", response_model=List[PurchaseOut])
def export_purchases(db: Session = Depends(get_db)):
    """Every purchase (oldest first) for the report service."""
    return list(reversed(_newest_purchases(db)))


@internal.get("/extra-payments", response_model=List[ExtraPaymentOut])
def export_extra_payments(db: Session = Depends(get_db)):
    return list(reversed(_newest_extras(db)))
