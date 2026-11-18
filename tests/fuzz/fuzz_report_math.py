"""Fuzz the report computations with arbitrary orders: they must never crash
and the totals must stay consistent with the per-product rows."""

import sys
from datetime import datetime, timedelta

import atheris

with atheris.instrument_imports():
    import _paths  # noqa: F401

    from report_service import reports as R

STATUSES = ("pending", "paid", "cancelled")
BASE = datetime(2026, 1, 1)


def _orders(fdp):
    orders = []
    for order_id in range(fdp.ConsumeIntInRange(0, 12)):
        created = BASE + timedelta(minutes=fdp.ConsumeIntInRange(0, 60 * 24 * 90))
        items = []
        for _ in range(fdp.ConsumeIntInRange(0, 5)):
            cost = fdp.ConsumeIntInRange(0, 10_000) / 100
            items.append({
                "product_id": fdp.ConsumeIntInRange(1, 6),
                "product_name": f"P{fdp.ConsumeIntInRange(1, 6)}",
                "quantity": fdp.ConsumeIntInRange(1, 50),
                "unit_price": fdp.ConsumeIntInRange(0, 10_000) / 100,
                "unit_cost": cost if fdp.ConsumeBool() else None,
            })
        status = STATUSES[fdp.ConsumeIntInRange(0, 2)]
        orders.append({
            "id": order_id,
            "status": status,
            "total": round(sum(i["unit_price"] * i["quantity"] for i in items), 2),
            "customer_username": f"u{fdp.ConsumeIntInRange(1, 4)}",
            "created_at": created,
            "completed_at": created + timedelta(hours=fdp.ConsumeIntInRange(0, 200)) if status == "paid" else None,
            "items": items,
        })
    return orders


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    orders = _orders(fdp)
    basis = "paid" if fdp.ConsumeBool() else "sales"
    margins = R.margins_for_period(orders, basis=basis)
    totals = margins["totals"]
    assert totals["quantity"] == sum(p["quantity"] for p in margins["products"])
    assert abs(totals["revenue"] - sum(p["revenue"] for p in margins["products"])) < 0.05 * (len(margins["products"]) + 1)
    assert R.outstanding_total(orders) >= 0
    R.revenue_for_period(orders, basis=basis)
    R.top_customers_for_period(orders, None, 5, basis=basis)
    R.top_products_for_period(orders, None, 5, basis=basis)
    R.sales_by_day(orders, BASE, basis)
    products = [
        {"id": i, "name": f"P{i}", "is_active": True, "stock": fdp.ConsumeIntInRange(0, 100),
         "low_stock_threshold": fdp.ConsumeIntInRange(0, 10), "cost_price": None, "category_name": ""}
        for i in range(1, 7)
    ]
    report = R.reorder_suggestions(orders, products, days=fdp.ConsumeIntInRange(1, 60),
                                   cover_days=fdp.ConsumeIntInRange(1, 30), now=BASE + timedelta(days=90))
    assert all(row["suggested"] > 0 for row in report["products"])


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
