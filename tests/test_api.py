import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4, UUID


@pytest.mark.asyncio
async def test_create_session(client):
    response = await client.post("/api/v1/verification/session")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_submit_verification_data(client, mock_db_session):
    # 1. Create Session
    response = await client.post("/api/v1/verification/session")
    session_id = response.json()["session_id"]

    # 2. Submit Data
    # Mock file handling to avoid disk I/O
    with (
        patch("builtins.open", MagicMock()) as mock_open,
        patch("shutil.copyfileobj", MagicMock()) as mock_copy,
        patch("os.makedirs", MagicMock()),
    ):
        # Mock background task function to verify it's called
        with patch(
            "app.api.v1.endpoints.verification.process_verification"
        ) as mock_process:
            files = {"documents": ("test_doc.jpg", b"fake image content", "image/jpeg")}
            data = {
                "street": "123 Test St",
                "city": "Test City",
                "state": "Test State",
                "latitude": "0.0",
                "longitude": "0.0",
                "organization_name": "Test Org",
            }

            response = await client.post(
                f"/api/v1/verification/{session_id}/submit", data=data, files=files
            )

            assert response.status_code == 200
            assert response.json()["status"] == "processing"

            # Verify session was updated in DB
            sid = UUID(session_id)
            session = mock_db_session.store[sid]
            assert session.street == "123 Test St"
            assert session.status == "processing"


@pytest.mark.asyncio
async def test_get_results(client, mock_db_session):
    # 1. Create Session
    response = await client.post("/api/v1/verification/session")
    session_id = response.json()["session_id"]

    # 2. Get Results (Initial)
    response = await client.get(f"/api/v1/verification/{session_id}/results")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"

    # 3. Simulate Completion
    # Manually update the session in the mock DB
    sid = UUID(session_id)
    session = mock_db_session.store[sid]
    session.status = "completed"
    session.trust_score = 90
    session.verification_results = {"verdict": "Approved"}

    # 4. Get Results (Completed)
    response = await client.get(f"/api/v1/verification/{session_id}/results")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["trust_score"] == 90
    assert data["verification_results"]["verdict"] == "Approved"


@pytest.mark.asyncio
async def test_get_results_not_found(client):
    random_id = uuid4()
    response = await client.get(f"/api/v1/verification/{random_id}/results")
    assert response.status_code == 404
