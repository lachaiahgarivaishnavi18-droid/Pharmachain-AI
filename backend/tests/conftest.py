import os, secrets
TEST_PASSWORD = secrets.token_urlsafe(24)
os.environ['SEED_DEMO'] = 'false'
os.environ['AUTO_CREATE_SCHEMA'] = 'false'
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models import User, Product, Warehouse, Supplier, SupplierProduct
from backend.app.auth import hash_password

@pytest.fixture
def db():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session=sessionmaker(bind=engine,expire_on_commit=False)()
    for role in ['admin','operator','quality','viewer']:
        session.add(User(username=role,password_hash=hash_password(TEST_PASSWORD),role=role))
    session.add(Product(name='Synthetic insulin',temperature_sensitive=True,temp_min=2,temp_max=8))
    session.add(Warehouse(name='Test warehouse',region='test',capacity=10000,cold_capacity=5000))
    session.add(Warehouse(name='Destination',region='test',capacity=10000,cold_capacity=5000))
    session.add(Supplier(name='Synthetic supplier',lead_days=5,reliability=.95));session.flush()
    session.add(SupplierProduct(supplier_id=1,product_id=1,unit_cost=20,minimum_order=10));session.commit()
    yield session
    session.close();engine.dispose()

@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setattr('backend.app.main.SessionLocal', sessionmaker(bind=db.get_bind(),expire_on_commit=False))
    def override():
        try:yield db;db.commit()
        except Exception:db.rollback();raise
    app.dependency_overrides[get_db]=override
    with TestClient(app,raise_server_exceptions=True) as c:yield c
    app.dependency_overrides.clear()

@pytest.fixture
def headers(client):
    def auth(role='admin'):
        result=client.post('/api/auth/login',json={'username':role,'password':TEST_PASSWORD})
        assert result.status_code==200,result.text
        return {'Authorization':'Bearer '+result.json()['access_token']}
    return auth
