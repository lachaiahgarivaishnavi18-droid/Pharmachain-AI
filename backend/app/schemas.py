from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field, model_validator, ConfigDict

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Login(Strict):
    username: str
    password: str

class ProductInput(Strict):
    name: str = Field(min_length=2, max_length=150)
    generic_name: str = ''
    category: str = 'General'
    dosage_form: str = 'Tablet'
    strength: str = ''
    manufacturer: str = 'Synthetic Pharma'
    unit: str = 'units'
    temp_min: float = Field(default=15, ge=-100, le=80)
    temp_max: float = Field(default=25, ge=-100, le=80)
    temperature_sensitive: bool = False
    min_stock: int = Field(default=100, ge=0)
    max_stock: int = Field(default=3000, gt=0)
    reorder_point: int = Field(default=300, ge=0)
    safety_stock: int = Field(default=100, ge=0)
    criticality: Literal['standard', 'high', 'critical'] = 'standard'
    unit_cost: float = Field(default=10, ge=0, allow_inf_nan=False)
    @model_validator(mode='after')
    def valid_ranges(self):
        if self.temp_min >= self.temp_max or self.min_stock > self.max_stock:
            raise ValueError('Invalid temperature or stock range')
        return self

class BatchInput(Strict):
    number: str = Field(min_length=1, max_length=120)
    product_id: int
    warehouse_id: int
    quantity: int = Field(gt=0)
    manufacturing_date: date
    expiry_date: date
    @model_validator(mode='after')
    def dates(self):
        if self.manufacturing_date > date.today() or self.expiry_date <= max(self.manufacturing_date, date.today()):
            raise ValueError('Stock-in requires valid manufacturing and future expiry dates')
        return self

class StockOut(Strict):
    product_id: int
    warehouse_id: int
    quantity: int = Field(gt=0)
    reference: str = Field(min_length=3)

class Transfer(StockOut):
    destination_id: int

class SupplierInput(Strict):
    name: str = Field(min_length=2)
    lead_days: int = Field(default=7, ge=1, le=365)
    reliability: float = Field(default=.95, ge=0, le=1)
    email: str = 'demo@example.invalid'

class OrderLine(Strict):
    product_id: int
    quantity: int = Field(gt=0, le=1000000)

class OrderInput(Strict):
    supplier_id: int
    items: list[OrderLine] = Field(min_length=1, max_length=100)

class Decision(Strict):
    reason: str = Field(min_length=5, max_length=2000)

class ReadingInput(Strict):
    sensor_id: int
    timestamp: datetime
    temperature: float = Field(ge=-100, le=100, allow_inf_nan=False)
    humidity: float = Field(default=50, ge=0, le=100, allow_inf_nan=False)
    source: Literal['synthetic', 'device'] = 'synthetic'
    sensor_status: Literal['healthy', 'failed'] = 'healthy'

class ForecastInput(Strict):
    product_id: int
    horizon: int = Field(default=30, ge=1, le=90)
    advanced: bool = False

class TrainInput(Strict):
    algorithm: Literal['PPO', 'DQN'] = 'PPO'
    timesteps: int = Field(default=4096, ge=1024, le=200000)
    seed: int = Field(default=42, ge=0)

class RecommendInput(Strict):
    product_id: int

class AgentOutput(BaseModel):
    summary: str
    evidence: dict
    recommendations: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class UserInput(Strict):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=12, max_length=128)
    role: Literal['viewer', 'operator', 'manager', 'quality', 'admin']

class BatchAdjustment(Strict):
    quantity: int = Field(ge=0)
    reserved: int = Field(ge=0)
    reason: str = Field(min_length=5)
    @model_validator(mode='after')
    def reservation(self):
        if self.reserved > self.quantity: raise ValueError('Reserved stock exceeds physical quantity')
        return self

class WarehouseInput(Strict):
    name: str = Field(min_length=2)
    region: str = Field(min_length=2)
    capacity: int = Field(gt=0)
    cold_capacity: int = Field(ge=0)
    @model_validator(mode='after')
    def capacity_valid(self):
        if self.cold_capacity > self.capacity: raise ValueError('Cold capacity exceeds total capacity')
        return self

class SensorInput(Strict):
    name: str = Field(min_length=2)
    warehouse_id: int | None = None
    shipment_id: int | None = None
    product_id: int
    @model_validator(mode='after')
    def location(self):
        if bool(self.warehouse_id) == bool(self.shipment_id): raise ValueError('Specify exactly one warehouse or shipment')
        return self

class CatalogInput(Strict):
    product_id: int
    unit_cost: float = Field(ge=0,allow_inf_nan=False)
    minimum_order: int = Field(default=50,gt=0)
