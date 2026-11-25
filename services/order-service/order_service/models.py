from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

from kiosk_common.outbox import make_outbox_model
from kiosk_common.timeutil import utcnow

Base = declarative_base()


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="pending")  # pending, paid, cancelled
    subtotal = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    notes = Column(Text, default="")
    # The customer lives in the customer service; the username is its stable key.
    customer_id = Column(Integer, nullable=True)
    customer_username = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, nullable=True, index=True)
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, default=0.0)
    unit_cost = Column(Float, nullable=True)

    order = relationship("Order", back_populates="items")


class Purchase(Base):
    """Money spent on goods for the store (a batch may be entered long after it was bought)."""

    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    purchased_on = Column(Date, nullable=False, default=lambda: utcnow().date(), index=True)
    amount = Column(Float, nullable=False)
    supplier = Column(String, default="")
    note = Column(String, default="")
    created_by = Column(String, default="")
    created_at = Column(DateTime, default=utcnow)


class ExtraPayment(Base):
    """What a customer paid on top of their debt: store income, never customer credit."""

    __tablename__ = "extra_payments"

    id = Column(Integer, primary_key=True, index=True)
    # The customer lives in the customer service; the username is its stable key.
    customer_id = Column(Integer, nullable=True)
    username = Column(String, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    note = Column(String, default="")
    created_by = Column(String, default="")
    created_at = Column(DateTime, default=utcnow, index=True)


Outbox = make_outbox_model(Base)
