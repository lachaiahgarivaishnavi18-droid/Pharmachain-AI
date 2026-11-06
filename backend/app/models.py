from datetime import datetime, timezone, date
from sqlalchemy import String, ForeignKey, CheckConstraint, UniqueConstraint, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Entity:
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class User(Entity, Base):
    __tablename__ = 'users'
    username: Mapped[str] = mapped_column(String(120), unique=True)
    password_hash: Mapped[str]
    role: Mapped[str] = mapped_column(default='viewer')

class ProductCategory(Entity, Base):
    __tablename__ = 'product_categories'
    name: Mapped[str] = mapped_column(unique=True)

class Product(Entity, Base):
    __tablename__ = 'products'
    name: Mapped[str]
    generic_name: Mapped[str] = mapped_column(default='')
    category: Mapped[str] = mapped_column(default='General')
    dosage_form: Mapped[str] = mapped_column(default='Tablet')
    strength: Mapped[str] = mapped_column(default='')
    manufacturer: Mapped[str] = mapped_column(default='Synthetic Pharma')
    unit: Mapped[str] = mapped_column(default='units')
    temp_min: Mapped[float] = mapped_column(default=15)
    temp_max: Mapped[float] = mapped_column(default=25)
    temperature_sensitive: Mapped[bool] = mapped_column(default=False)
    min_stock: Mapped[int] = mapped_column(default=100)
    max_stock: Mapped[int] = mapped_column(default=3000)
    reorder_point: Mapped[int] = mapped_column(default=300)
    safety_stock: Mapped[int] = mapped_column(default=100)
    criticality: Mapped[str] = mapped_column(default='standard')
    unit_cost: Mapped[float] = mapped_column(default=10)
    __table_args__ = (CheckConstraint('temp_min < temp_max'), CheckConstraint('min_stock >= 0 AND max_stock >= min_stock AND unit_cost >= 0'))

class Warehouse(Entity, Base):
    __tablename__ = 'warehouses'
    name: Mapped[str]
    region: Mapped[str]
    capacity: Mapped[int] = mapped_column(default=100000)
    cold_capacity: Mapped[int] = mapped_column(default=40000)

class Batch(Entity, Base):
    __tablename__ = 'batches'
    number: Mapped[str] = mapped_column(index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey('warehouses.id'), index=True)
    quantity: Mapped[int]
    reserved: Mapped[int] = mapped_column(default=0)
    manufacturing_date: Mapped[date]
    expiry_date: Mapped[date] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(default='available')
    __table_args__ = (CheckConstraint('quantity >= 0 AND reserved >= 0 AND reserved <= quantity'), CheckConstraint('expiry_date > manufacturing_date'), UniqueConstraint('number', 'product_id', 'warehouse_id'))

class InventoryTransaction(Entity, Base):
    __tablename__ = 'inventory_transactions'
    batch_id: Mapped[int] = mapped_column(ForeignKey('batches.id'))
    kind: Mapped[str]
    quantity: Mapped[int]
    actor: Mapped[str]
    reference: Mapped[str] = mapped_column(default='')
    synthetic: Mapped[bool] = mapped_column(default=True)

class Supplier(Entity, Base):
    __tablename__ = 'suppliers'
    name: Mapped[str]
    lead_days: Mapped[int] = mapped_column(default=7)
    reliability: Mapped[float] = mapped_column(default=.95)
    email: Mapped[str] = mapped_column(default='demo@example.invalid')

class SupplierProduct(Entity, Base):
    __tablename__ = 'supplier_products'
    supplier_id: Mapped[int] = mapped_column(ForeignKey('suppliers.id'))
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))
    unit_cost: Mapped[float]
    minimum_order: Mapped[int] = mapped_column(default=50)

class PurchaseOrder(Entity, Base):
    __tablename__ = 'purchase_orders'
    supplier_id: Mapped[int] = mapped_column(ForeignKey('suppliers.id'))
    status: Mapped[str] = mapped_column(default='draft')
    total: Mapped[float]
    expected_date: Mapped[date]
    requested_by: Mapped[str]
    approved_by: Mapped[str | None]

class PurchaseOrderItem(Entity, Base):
    __tablename__ = 'purchase_order_items'
    order_id: Mapped[int] = mapped_column(ForeignKey('purchase_orders.id'))
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))
    quantity: Mapped[int]
    unit_cost: Mapped[float]

class DemandHistory(Entity, Base):
    __tablename__ = 'demand_history'
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), index=True)
    day: Mapped[date] = mapped_column(index=True)
    quantity: Mapped[int]
    __table_args__ = (UniqueConstraint('product_id', 'day'), CheckConstraint('quantity >= 0'))

class DemandForecast(Entity, Base):
    __tablename__ = 'demand_forecasts'
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))
    result: Mapped[dict] = mapped_column(JSON)

class TemperatureSensor(Entity, Base):
    __tablename__ = 'temperature_sensors'
    name: Mapped[str]
    warehouse_id: Mapped[int | None] = mapped_column(ForeignKey('warehouses.id'))
    shipment_id: Mapped[int | None] = mapped_column(ForeignKey('shipments.id'))
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))
    status: Mapped[str] = mapped_column(default='healthy')

class TemperatureReading(Entity, Base):
    __tablename__ = 'temperature_readings'
    sensor_id: Mapped[int] = mapped_column(ForeignKey('temperature_sensors.id'), index=True)
    timestamp: Mapped[datetime] = mapped_column(index=True)
    temperature: Mapped[float]
    humidity: Mapped[float] = mapped_column(default=50)
    source: Mapped[str] = mapped_column(default='synthetic')
    sensor_status: Mapped[str] = mapped_column(default='healthy')
    __table_args__ = (UniqueConstraint('sensor_id', 'timestamp'),)

class TemperatureExcursion(Entity, Base):
    __tablename__ = 'temperature_excursions'
    sensor_id: Mapped[int] = mapped_column(ForeignKey('temperature_sensors.id'))
    started_at: Mapped[datetime]
    ended_at: Mapped[datetime | None]
    duration_minutes: Mapped[float] = mapped_column(default=0)
    minimum: Mapped[float]
    maximum: Mapped[float]
    affected_batches: Mapped[list] = mapped_column(JSON, default=list)

class ColdChainAlert(Entity, Base):
    __tablename__ = 'cold_chain_alerts'
    sensor_id: Mapped[int] = mapped_column(ForeignKey('temperature_sensors.id'))
    excursion_id: Mapped[int | None] = mapped_column(ForeignKey('temperature_excursions.id'))
    severity: Mapped[str] = mapped_column(default='high')
    message: Mapped[str]
    status: Mapped[str] = mapped_column(default='open')
    investigation: Mapped[str] = mapped_column(default='')

class Shipment(Entity, Base):
    __tablename__ = 'shipments'
    reference: Mapped[str]
    origin: Mapped[str]
    destination: Mapped[str]
    status: Mapped[str]
    eta: Mapped[datetime]

class ShipmentItem(Entity, Base):
    __tablename__ = 'shipment_items'
    shipment_id: Mapped[int] = mapped_column(ForeignKey('shipments.id'))
    batch_id: Mapped[int] = mapped_column(ForeignKey('batches.id'))
    quantity: Mapped[int]

class AgentExecution(Entity, Base):
    __tablename__ = 'agent_executions'
    run_id: Mapped[str] = mapped_column(index=True)
    agent: Mapped[str]
    status: Mapped[str]
    duration_ms: Mapped[float]
    input_summary: Mapped[dict] = mapped_column(JSON)
    output: Mapped[dict] = mapped_column(JSON)
    error: Mapped[str | None]

class AuditLog(Entity, Base):
    __tablename__ = 'audit_logs'
    actor: Mapped[str]
    action: Mapped[str]
    entity: Mapped[str]
    detail: Mapped[dict] = mapped_column(JSON)

class HumanApproval(Entity, Base):
    __tablename__ = 'human_approvals'
    order_id: Mapped[int] = mapped_column(ForeignKey('purchase_orders.id'))
    actor: Mapped[str]
    decision: Mapped[str]
    reason: Mapped[str]

class SystemConfiguration(Entity, Base):
    __tablename__ = 'system_configuration'
    key: Mapped[str] = mapped_column(unique=True)
    value: Mapped[dict] = mapped_column(JSON)

class RLTrainingRun(Entity, Base):
    __tablename__ = 'rl_training_runs'
    status: Mapped[str] = mapped_column(default='queued')
    config: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON, default=dict)

class RLModel(Entity, Base):
    __tablename__ = 'rl_models'
    version: Mapped[str] = mapped_column(unique=True)
    path: Mapped[str]
    algorithm: Mapped[str]
    training_run_id: Mapped[int] = mapped_column(ForeignKey('rl_training_runs.id'))

class RLPolicyEvaluation(Entity, Base):
    __tablename__ = 'rl_policy_evaluations'
    result: Mapped[dict] = mapped_column(JSON)

class RiskAssessment(Entity, Base):
    __tablename__ = 'risk_assessments'
    result: Mapped[dict] = mapped_column(JSON)

class RLRecommendation(Entity, Base):
    __tablename__ = 'rl_recommendations'
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))
    result: Mapped[dict] = mapped_column(JSON)

class ForecastEvaluation(Entity, Base):
    __tablename__ = 'forecast_evaluations'
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))
    result: Mapped[dict] = mapped_column(JSON)
