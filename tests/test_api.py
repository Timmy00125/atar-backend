import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4, UUID


@pytest.mark.asyncio
async def test_create_session(client):
    response = await client.post("/api/v1/verification/session")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "session_id" in data["data"]
    assert data["data"]["status"] == "pending"


@pytest.mark.asyncio
async def test_submit_verification_data(client, mock_db_session):
    # 1. Create Session
    response = await client.post("/api/v1/verification/session")
    session_id = response.json()["data"]["session_id"]

    # 2. Submit Data
    # Mock file handling to avoid disk I/O
    mock_file = MagicMock()
    mock_file.write = AsyncMock()

    mock_ctx = MagicMock()

    async def aenter(*args):
        return mock_file

    async def aexit(*args):
        pass

    mock_ctx.__aenter__ = aenter
    mock_ctx.__aexit__ = aexit

    mock_open = MagicMock(return_value=mock_ctx)

    with (
        patch("aiofiles.open", mock_open),
        patch("os.makedirs", MagicMock()),
    ):
        # Mock background task function to verify it's called
        with (
            patch(
                "app.api.v1.endpoints.verification.process_verification"
            ) as mock_process,
            patch(
                "app.api.v1.endpoints.verification.extract_metadata_from_image"
            ) as mock_extract,
        ):
            mock_extract.return_value = {"gps": {"latitude": 1.0, "longitude": 1.0}}

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
            assert response.json()["data"]["status"] == "processing"

            # Verify session was updated in DB
            sid = UUID(session_id)
            session = mock_db_session.store[sid]
            assert session.street == "123 Test St"
            assert session.status == "processing"


@pytest.mark.asyncio
async def test_get_results(client, mock_db_session):
    # 1. Create Session
    response = await client.post("/api/v1/verification/session")
    session_id = response.json()["data"]["session_id"]

    # 2. Get Results (Initial)
    response = await client.get(f"/api/v1/verification/{session_id}/results")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["status"] == "pending"

    # 3. Simulate Completion
    # Manually update the session in the mock DB
    sid = UUID(session_id)
    session = mock_db_session.store[sid]
    session.status = "completed"
    session.trust_score = 90
    session.verification_results = {
        "trust_score": 90,
        "verdict": "Approved",
        "breakdown": {"house_match_score": 30},
    }

    # 4. Get Results (Completed)
    response = await client.get(f"/api/v1/verification/{session_id}/results")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["status"] == "completed"
    assert data["data"]["trust_score"] == 90
    assert data["data"]["verification_results"]["verdict"] == "Approved"
    assert data["data"]["trust_analysis"]["trust_score"] == 90
    assert data["data"]["trust_analysis"]["verdict"] == "Approved"
    assert data["data"]["trust_analysis"]["breakdown"]["house_match_score"] == 30


@pytest.mark.asyncio
async def test_get_results_not_found(client):
    random_id = uuid4()
    response = await client.get(f"/api/v1/verification/{random_id}/results")
    assert response.status_code == 404
