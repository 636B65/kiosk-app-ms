"""Purchases, extra payments, the store balance and the Pay screen's payment info (kiosk-app 1.6.0).

Runs after test_flows on the shared stack, so balances are asserted as deltas from what the
earlier tests left behind.
"""

import json
from datetime import date, timedelta

import pytest

from tests.integration.conftest import ADMIN_PASSWORD  # noqa: F401  (stack fixtures live in conftest)

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def balance(client, headers):
    response = client.get("/api/reports/balance", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def buy(client, username, quantity=1, product="Cola"):
    products = client.get("/api/products?active_only=false").json()
    product_id = next(p["id"] for p in products if p["name"] == product)
    response = client.post(
        "/api/orders",
        json={"customer_username": username, "items": [{"product_id": product_id, "quantity": quantity}]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def settle_everybody(client, headers):
    for customer in client.get("/api/customers", headers=headers).json():
        assert client.post(f"/api/customers/{customer['username']}/reset-payment", headers=headers).status_code == 200


# ---- purchases ------------------------------------------------------------------


def test_purchases_crud_validation_and_audit(client, admin_headers, stack):
    assert client.get("/api/purchases").status_code == 401
    assert client.post("/api/purchases", json={"amount": 5}).status_code == 401

    today = date.today()
    old = (today - timedelta(days=40)).isoformat()
    created = client.post(
        "/api/purchases", headers=admin_headers,
        json={"amount": 120.5, "purchased_on": old, "supplier": " Wholesale ", "note": " first batch "},
    )
    assert created.status_code == 201, created.text
    purchase = created.json()
    assert purchase["purchased_on"] == old and purchase["supplier"] == "Wholesale" and purchase["note"] == "first batch"
    assert purchase["created_by"] == "admin"

    # default date is today; newest date first
    todays = client.post("/api/purchases", headers=admin_headers, json={"amount": 10}).json()
    listed = client.get("/api/purchases", headers=admin_headers).json()
    ids = [p["id"] for p in listed]
    assert ids.index(todays["id"]) < ids.index(purchase["id"])

    for bad in ({"amount": 0}, {"amount": -3}, {"amount": 1e12}, {"amount": 5, "supplier": "x" * 101}):
        assert client.post("/api/purchases", headers=admin_headers, json=bad).status_code == 422, bad
    future = (today + timedelta(days=5)).isoformat()
    assert client.post("/api/purchases", headers=admin_headers, json={"amount": 5, "purchased_on": future}).status_code == 422

    updated = client.put(f"/api/purchases/{purchase['id']}", headers=admin_headers, json={"amount": 99.99, "note": "fixed"})
    assert updated.status_code == 200 and updated.json()["amount"] == 99.99 and updated.json()["supplier"] == "Wholesale"
    assert client.put(f"/api/purchases/{purchase['id']}", headers=admin_headers, json={"purchased_on": future}).status_code == 422
    assert client.put("/api/purchases/999999", headers=admin_headers, json={"amount": 1}).status_code == 404

    assert client.delete(f"/api/purchases/{todays['id']}", headers=admin_headers).status_code == 204
    assert client.delete(f"/api/purchases/{todays['id']}", headers=admin_headers).status_code == 404

    stack.flush_outboxes()
    actions = {a["action"] for a in client.get("/api/audit?action=purchase.", headers=admin_headers).json()}
    assert {"purchase.create", "purchase.update", "purchase.delete"} <= actions


# ---- the store balance ----------------------------------------------------------


def test_balance_status_rounds_to_the_cent():
    from report_service.reports import balance_status

    assert balance_status(0) == "even" and balance_status(0.004) == "even" and balance_status(-0.004) == "even"
    assert balance_status(0.01) == "plus" and balance_status(-0.01) == "minus"


def test_balance_is_paid_plus_extra_minus_purchases_and_follows_the_data(client, admin_headers):
    before = balance(client, admin_headers)
    order = buy(client, "money_ann", quantity=2)

    # an unpaid order is outstanding, not in the balance
    now = balance(client, admin_headers)
    assert now["balance"] == before["balance"]
    assert now["outstanding"] == pytest.approx(before["outstanding"] + order["total"])
    assert now["pending_orders"] == before["pending_orders"] + 1
    assert now["settled"] is False
    assert now["projected_balance"] == pytest.approx(before["projected_balance"] + order["total"])

    # paid: it moves into the balance; back to pending it leaves again; cancelled it is gone
    patch = lambda status: client.patch(f"/api/orders/{order['id']}/status?new_status={status}", headers=admin_headers)  # noqa: E731
    assert patch("paid").status_code == 200
    paid = balance(client, admin_headers)
    assert paid["balance"] == pytest.approx(before["balance"] + order["total"])
    assert paid["paid_total"] == pytest.approx(before["paid_total"] + order["total"])
    assert patch("pending").status_code == 200
    assert balance(client, admin_headers)["balance"] == pytest.approx(before["balance"])
    assert patch("cancelled").status_code == 200
    gone = balance(client, admin_headers)
    assert gone["balance"] == pytest.approx(before["balance"])
    assert gone["outstanding"] == pytest.approx(before["outstanding"])

    # a purchase (even an old one) is subtracted and can be edited afterwards
    created = client.post(
        "/api/purchases", headers=admin_headers,
        json={"amount": 40, "purchased_on": (date.today() - timedelta(days=90)).isoformat()},
    ).json()
    assert balance(client, admin_headers)["balance"] == pytest.approx(before["balance"] - 40)
    client.put(f"/api/purchases/{created['id']}", headers=admin_headers, json={"amount": 25})
    assert balance(client, admin_headers)["balance"] == pytest.approx(before["balance"] - 25)
    client.delete(f"/api/purchases/{created['id']}", headers=admin_headers)
    assert balance(client, admin_headers)["balance"] == pytest.approx(before["balance"])
    assert client.get("/api/reports/balance").status_code == 401


def test_balance_is_plus_minus_or_even_once_everybody_has_paid(client, admin_headers):
    settle_everybody(client, admin_headers)
    settled = balance(client, admin_headers)
    assert settled["settled"] is True and settled["pending_orders"] == 0 and settled["outstanding"] == 0
    assert settled["status"] == settled["projected_status"]

    # buy in exactly what has been taken in so far -> even
    gap = round(settled["balance"], 2)
    assert gap != 0
    # push the balance to exactly zero with one purchase (or an extra payment when it is negative)
    if gap > 0:
        client.post("/api/purchases", headers=admin_headers, json={"amount": gap})
    else:
        client.post("/api/customers/money_ann/extra-payment", headers=admin_headers, json={"amount": -gap})
    assert balance(client, admin_headers)["status"] == "even"

    client.post("/api/purchases", headers=admin_headers, json={"amount": 7})
    minus = balance(client, admin_headers)
    assert minus["status"] == "minus" and minus["balance"] == pytest.approx(-7)
    client.post("/api/customers/money_ann/extra-payment", headers=admin_headers, json={"amount": 20})
    assert balance(client, admin_headers)["status"] == "plus"


# ---- extra payments -------------------------------------------------------------


def test_reset_payment_with_an_extra_amount_is_income_not_customer_credit(client, admin_headers, stack):
    order = buy(client, "money_bea", quantity=1)
    customer_before = next(c for c in client.get("/api/customers", headers=admin_headers).json() if c["username"] == "money_bea")
    assert customer_before["balance"] == pytest.approx(order["total"])
    before = balance(client, admin_headers)

    response = client.post(
        "/api/customers/money_bea/reset-payment", headers=admin_headers, json={"extra_amount": 2.5, "note": "keep the change"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["settled"] == 1 and body["amount"] == order["total"] and body["extra"] == 2.5

    after = balance(client, admin_headers)
    assert after["extra_total"] == pytest.approx(before["extra_total"] + 2.5)
    assert after["extra_count"] == before["extra_count"] + 1
    assert after["balance"] == pytest.approx(before["balance"] + order["total"] + 2.5)

    # not credit: the customer owes nothing and their totals only count the paid order
    customer = next(c for c in client.get("/api/customers", headers=admin_headers).json() if c["username"] == "money_bea")
    assert customer["balance"] == 0 and customer["total_paid"] == pytest.approx(order["total"])

    extras = client.get("/api/extra-payments", headers=admin_headers).json()
    mine = next(e for e in extras if e["username"] == "money_bea")
    assert mine["amount"] == 2.5 and mine["note"] == "keep the change" and mine["created_by"] == "admin"

    stack.flush_outboxes()
    log = client.get("/api/audit?action=customer.extra_payment", headers=admin_headers).json()
    assert any("extra payment of 2.50" in a["details"] for a in log)

    # no body still works, and 0 books nothing
    buy(client, "money_bea")
    plain = client.post("/api/customers/money_bea/reset-payment", headers=admin_headers)
    assert plain.status_code == 200 and plain.json()["extra"] == 0.0
    buy(client, "money_bea")
    zero = client.post("/api/customers/money_bea/reset-payment", headers=admin_headers, json={"extra_amount": 0})
    assert zero.status_code == 200 and zero.json()["extra"] == 0.0
    assert balance(client, admin_headers)["extra_count"] == after["extra_count"]


def test_extra_payment_endpoint_validation_listing_and_delete(client, admin_headers, stack):
    assert client.post("/api/customers/money_bea/extra-payment", json={"amount": 1}).status_code == 401
    assert client.get("/api/extra-payments").status_code == 401
    assert client.post("/api/customers/nobody_here/extra-payment", headers=admin_headers, json={"amount": 1}).status_code == 404
    for bad in ({"amount": 0}, {"amount": -1}, {"amount": 1e12}, {"amount": 1, "note": "x" * 201}):
        assert client.post("/api/customers/money_bea/extra-payment", headers=admin_headers, json=bad).status_code == 422, bad
    for bad in ({"extra_amount": -1}, {"extra_amount": 1e12}):
        assert client.post("/api/customers/money_bea/reset-payment", headers=admin_headers, json=bad).status_code == 422, bad

    before = balance(client, admin_headers)
    created = client.post("/api/customers/money_bea/extra-payment", headers=admin_headers, json={"amount": 3, "note": " tip "})
    assert created.status_code == 201, created.text
    extra = created.json()
    assert extra["username"] == "money_bea" and extra["amount"] == 3 and extra["note"] == "tip"
    assert balance(client, admin_headers)["extra_total"] == pytest.approx(before["extra_total"] + 3)

    assert client.delete(f"/api/extra-payments/{extra['id']}", headers=admin_headers).status_code == 204
    assert client.delete(f"/api/extra-payments/{extra['id']}", headers=admin_headers).status_code == 404
    assert balance(client, admin_headers)["extra_total"] == pytest.approx(before["extra_total"])
    stack.flush_outboxes()
    actions = {a["action"] for a in client.get("/api/audit?action=customer.extra_payment", headers=admin_headers).json()}
    assert {"customer.extra_payment", "customer.extra_payment_delete"} <= actions


def test_shrinkage_is_covered_by_extra_payments_for_information_only(client, admin_headers):
    state = balance(client, admin_headers)
    shrinkage = client.get("/api/reports/shrinkage?period=all", headers=admin_headers).json()["totals"]["value_lost"]
    assert shrinkage > 0 and state["shrinkage_value"] == pytest.approx(shrinkage)
    assert state["shrinkage_covered"] == pytest.approx(min(state["extra_total"], shrinkage))
    assert state["shrinkage_uncovered"] == pytest.approx(max(0, shrinkage - state["extra_total"]))
    assert state["extra_surplus"] == pytest.approx(max(0, state["extra_total"] - shrinkage))
    # informational: the balance does not subtract the shrinkage
    assert state["balance"] == pytest.approx(state["paid_total"] + state["extra_total"] - state["purchases_total"])


def test_summary_and_csv_carry_the_store_balance(client, admin_headers):
    summary = client.get("/api/reports/summary", headers=admin_headers).json()
    assert summary["store_balance"]["balance"] == pytest.approx(balance(client, admin_headers)["balance"])
    client.post("/api/purchases", headers=admin_headers, json={"amount": 1.23, "supplier": "=cmd|' /C calc'!A0"})
    text = client.get("/api/reports/export.csv", headers=admin_headers).text
    assert "\nstore_balance,,balance," in text and "\nstore_balance,,extra_payments," in text
    assert "\npurchases," in text
    assert ",=cmd" not in text  # spreadsheet formulas are neutralised by csv_safe


# ---- payment info (the Pay screen) ----------------------------------------------


def put_methods(client, headers, methods):
    return client.put("/api/settings/payment_methods", headers=headers, json={"key": "payment_methods", "value": json.dumps(methods)})


def test_payment_settings_are_public_defaults_and_validated(client, admin_headers, stack):
    settings = client.get("/api/settings").json()
    assert settings["payment_methods"] == "[]" and settings["pay_instructions"] == ""

    ok = put_methods(client, admin_headers, [
        {"type": "bank", "label": " Bank ", "value": "SE12 3456", "note": "msg: username"},
        {"type": "phone", "label": "Swish", "value": "070-123 45 67", "enabled": False},
        {"type": "link", "label": "Pay", "value": "https://pay.example.com/me"},
        {"type": "text", "label": "Cash", "value": "tin\non the counter"},
    ])
    assert ok.status_code == 200, ok.text
    stored = json.loads(client.get("/api/settings").json()["payment_methods"])
    assert [m["type"] for m in stored] == ["bank", "phone", "link", "text"]
    assert stored[0]["label"] == "Bank" and stored[1]["enabled"] is False and stored[0]["enabled"] is True
    assert set(stored[0]) == {"type", "label", "value", "note", "image", "enabled"}

    bad = [
        "not json", "{}", [1], [{"type": "crypto", "value": "x"}], [{"type": "bank", "value": ""}],
        [{"type": "link", "value": "javascript:alert(1)"}], [{"type": "bank", "value": "x" * 301}],
        [{"type": "bank", "value": "a\x00b"}], [{"type": "bank", "value": "x", "enabled": "yes"}],
        [{"type": "qr", "image": "pay-" + "0" * 32 + ".png"}], [{"type": "qr", "image": "../../etc/passwd"}],
        [{"type": "bank", "value": "x"}] * 11,
    ]
    for value in bad:
        raw = value if isinstance(value, str) else json.dumps(value)
        response = client.put("/api/settings/payment_methods", headers=admin_headers, json={"key": "payment_methods", "value": raw})
        assert response.status_code == 422, (value, response.text)
    long = client.put("/api/settings/pay_instructions", headers=admin_headers, json={"key": "pay_instructions", "value": "x" * 501})
    assert long.status_code == 422
    fine = client.put("/api/settings/pay_instructions", headers=admin_headers, json={"key": "pay_instructions", "value": " Pay in 14 days "})
    assert fine.json()["value"] == "Pay in 14 days"
    assert client.put("/api/settings/payment_methods", json={"key": "payment_methods", "value": "[]"}).status_code == 401

    stack.flush_outboxes()
    details = [a["details"] for a in client.get("/api/audit?action=settings.update", headers=admin_headers).json()]
    assert any("4 payment method(s), 3 shown" in d for d in details)


def test_payment_qr_upload_is_served_publicly_and_cleaned_up(client, admin_headers):
    put_methods(client, admin_headers, [])
    files = {"file": ("qr.png", PNG, "image/png")}
    assert client.post("/api/settings/payment-qr", files=files).status_code == 401
    assert client.post("/api/settings/payment-qr", headers=admin_headers, files={"file": ("q.txt", b"hi", "text/plain")}).status_code == 400
    assert client.post("/api/settings/payment-qr", headers=admin_headers, files={"file": ("q.png", b"not a png", "image/png")}).status_code == 400
    assert client.post("/api/settings/payment-qr", headers=admin_headers, files={"file": ("q.png", b"", "image/png")}).status_code == 400

    uploaded = client.post("/api/settings/payment-qr", headers=admin_headers, files=files)
    assert uploaded.status_code == 200, uploaded.text
    name = uploaded.json()["image"]
    assert uploaded.json()["url"] == f"/api/images/{name}"

    # public, correct type, and the product image mount is untouched
    served = client.get(f"/api/images/{name}")
    assert served.status_code == 200 and served.content == PNG
    assert served.headers["content-type"] == "image/png" and served.headers["x-content-type-options"] == "nosniff"
    assert client.get("/api/images/pay-" + "0" * 32 + ".png").status_code == 404
    assert client.get("/api/images/pay-../../x").status_code == 404

    assert put_methods(client, admin_headers, [{"type": "qr", "label": "Swish QR", "image": name}]).status_code == 200
    assert client.get(f"/api/images/{name}").status_code == 200

    # removing the method deletes the now unused image; an unreferenced upload goes with the next save
    other = client.post("/api/settings/payment-qr", headers=admin_headers, files=files).json()["image"]
    assert put_methods(client, admin_headers, []).status_code == 200
    assert client.get(f"/api/images/{name}").status_code == 404
    assert client.get(f"/api/images/{other}").status_code == 200  # never referenced: kept until referenced and dropped
