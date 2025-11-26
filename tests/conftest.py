import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import get_db
from app.services import ai_service


# Mock Database Session
class MockAsyncSession:
    def __init__(self):
        self.store = {}
        self.added = []
        self.committed = False

    def add(self, instance):
        self.added.append(instance)
        # Simulate ID generation if needed
        if not instance.session_id:
            import uuid

            instance.session_id = uuid.uuid4()
        # Simulate default values
        if hasattr(instance, "status") and instance.status is None:
            instance.status = "pending"
        if hasattr(instance, "created_at") and instance.created_at is None:
            from datetime import datetime

            instance.created_at = datetime.utcnow()
        self.store[instance.session_id] = instance

    async def commit(self):
        self.committed = True
        for instance in self.added:
            self.store[instance.session_id] = instance
        self.added = []

    async def refresh(self, instance):
        pass

    async def execute(self, statement):
        # This is a basic mock for execute/scalars/first
        # It assumes we are selecting VerificationSession by session_id
        mock_result = MagicMock()

        # Try to find session_id in the statement's where clause parameters if possible
        # This is hard to do reliably with just the statement object in a mock
        # So we will rely on the fact that we only have one session in the store for most tests
        # OR we can try to parse the compiled statement (complex)

        # Better approach: Just return a list of all sessions in the store
        # The application logic usually filters by ID, but if we return the correct one it works.
        # If the test creates multiple sessions, this might be ambiguous, but for unit tests usually fine.

        # However, we can try to be a bit smarter.
        # If the statement is a Select, we return the values.

        vals = list(self.store.values())

        # If we want to support "not found", we need to know which ID was requested.
        # Since we can't easily extract it, we will assume if store is empty, return None.
        # If store has items, return them.

        # To support specific ID lookup, we can inspect the statement string representation
        str_stmt = str(statement)
        found_session = None

        for session in vals:
            if str(session.session_id) in str_stmt:
                found_session = session
                break

        # If we couldn't find the ID in the statement string (it might be a bind param),
        # fallback to returning the first one if there's only one.
        if not found_session and len(vals) == 1:
            found_session = vals[0]

        # If we still have nothing, and there are values, maybe return the last one added?
        # Let's stick to: if we found it by ID in string, good. Else if only 1, good. Else None.

        # Actually, for `submit` endpoint, it queries by ID.
        # If we just return the session we created in the test, it should be fine.

        def get_first():
            return found_session

        mock_result.scalars.return_value.first.side_effect = get_first
        mock_result.scalars.return_value.all.return_value = vals
        return mock_result

    async def close(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# Fixture to override get_db
@pytest_asyncio.fixture
async def mock_db_session():
    session = MockAsyncSession()
    return session


@pytest_asyncio.fixture
async def client(mock_db_session):
    # Override the dependency
    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# Mock Gemini Client
@pytest.fixture(autouse=True)
def mock_gemini_client(monkeypatch):
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock()

    monkeypatch.setattr(ai_service, "client", mock_client)
    return mock_client
