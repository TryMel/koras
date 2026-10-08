import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from fastapi.testclient import TestClient

from app import main as main_module
from app.database.session import Base, get_db


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_path = (tmp_path / "koras-test.db").as_posix()
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}", poolclass=NullPool)
    test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    main_module.app.state.test_session_factory = test_session_factory

    async def init_test_db():
        async with test_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with test_session_factory() as session:
            yield session

    monkeypatch.setattr(main_module, "init_db", init_test_db)
    main_module.app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(main_module.app) as test_client:
            yield test_client
    finally:
        main_module.app.dependency_overrides.clear()
        asyncio.run(test_engine.dispose())


@pytest.fixture
def registered_user(client):
    def register(phone="+2250700000001", device_identifier="test-device-1"):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "phone": phone,
                "display_name": "Test User",
                "password": "test-password-123",
                "device_identifier": device_identifier,
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()
        return {
            "headers": {"Authorization": f"Bearer {data['access_token']}"},
            "device_identifier": device_identifier,
            "user_id": data["user_id"],
            "session_id": data["session_id"],
        }

    return register
