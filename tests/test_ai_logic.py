import pytest
import json
from uuid import uuid4
from app.models.session import VerificationSession
from app.services.ai_service import run_stage_2_verification, run_stage_1_extraction
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_stage_2_verification_high_trust(mock_gemini_client):
    # Setup
    session = VerificationSession(
        session_id=uuid4(),
        street="123 Main St",
        city="Lagos",
        state="Lagos",
        latitude=6.5244,
        longitude=3.3792,
        organization_name=None,
        organization_type=None,
    )

    extracted_data = {
        "Full Name": "John Doe",
        "Address": "123 Main St, Lagos, Lagos",
        "Date": "2023-10-01",
    }

    expected_response = {
        "trust_score": 85,
        "breakdown": {
            "house_match_score": 30,
            "logistics_match_score": 35,
            "institutional_proofs_score": 10,
            "recency_score": 10,
        },
        "verdict": "Approved",
    }

    # Mock Gemini Response
    mock_response = MagicMock()
    mock_response.text = json.dumps(expected_response)
    mock_gemini_client.aio.models.generate_content.return_value = mock_response

    # Execute
    result = await run_stage_2_verification(session, extracted_data)

    # Verify
    assert result["trust_score"] == 85
    assert result["verdict"] == "Approved"

    # Verify prompt contained correct info
    call_args = mock_gemini_client.aio.models.generate_content.call_args
    assert call_args is not None
    prompt_sent = call_args.kwargs["contents"]
    assert "123 Main St" in prompt_sent
    assert "John Doe" in prompt_sent


@pytest.mark.asyncio
async def test_stage_2_verification_tier_3_approve(mock_gemini_client):
    # Setup
    session = VerificationSession(
        session_id=uuid4(),
        street="123 Main St",
        city="Abuja",
        state="FCT",
        latitude=9.0765,
        longitude=7.3986,
        organization_name="Veritas University",
        organization_type="school",
    )

    extracted_data = {
        "Full Name": "Jane Doe",
        "Organization Name": "Veritas University Abuja",
        "Date": "2023-10-01",
    }

    expected_response = {
        "trust_score": 95,
        "breakdown": {
            "house_match_score": 0,
            "logistics_match_score": 0,
            "institutional_proofs_score": 40,
            "recency_score": 10,
        },
        "verdict": "Approved",
    }

    # Mock Gemini Response
    mock_response = MagicMock()
    mock_response.text = json.dumps(expected_response)
    mock_gemini_client.aio.models.generate_content.return_value = mock_response

    # Execute
    result = await run_stage_2_verification(session, extracted_data)

    # Verify
    assert result["trust_score"] == 95
    assert result["verdict"] == "Approved"


@pytest.mark.asyncio
async def test_stage_2_verification_tier_3_reject(mock_gemini_client):
    # Setup
    session = VerificationSession(
        session_id=uuid4(),
        street="123 Main St",
        city="Abuja",
        state="FCT",
        latitude=9.0765,
        longitude=7.3986,
        organization_name="Veritas University",
        organization_type="school",
    )

    extracted_data = {
        "Full Name": "Jane Doe",
        "Organization Name": "University of Lagos",  # Mismatch
        "Date": "2023-10-01",
    }

    expected_response = {
        "trust_score": 20,
        "breakdown": {
            "house_match_score": 0,
            "logistics_match_score": 0,
            "institutional_proofs_score": 0,
            "recency_score": 10,
        },
        "verdict": "Rejected",
    }

    # Mock Gemini Response
    mock_response = MagicMock()
    mock_response.text = json.dumps(expected_response)
    mock_gemini_client.aio.models.generate_content.return_value = mock_response

    # Execute
    result = await run_stage_2_verification(session, extracted_data)

    # Verify
    assert result["trust_score"] == 20
    assert result["verdict"] == "Rejected"


@pytest.mark.asyncio
async def test_stage_1_extraction(mock_gemini_client):
    # Setup
    file_paths = ["/tmp/test_doc.jpg"]

    expected_extraction = {
        "Document Type": "Utility Bill",
        "Full Name": "John Doe",
        "Address": "123 Main St, Lagos",
        "Date": "2023-10-01",
    }

    # Mock Gemini Response
    mock_response = MagicMock()
    mock_response.text = json.dumps(expected_extraction)
    mock_gemini_client.aio.models.generate_content.return_value = mock_response

    # Mock file reading
    mock_open = MagicMock()
    mock_file = MagicMock()

    async def async_read(*args, **kwargs):
        return b"fake image content"

    mock_file.read.side_effect = async_read
    mock_open.return_value.__aenter__.return_value = mock_file

    with (
        patch("app.services.ai_service.aiofiles.open", mock_open),
        patch("os.path.exists", return_value=True),
    ):
        # Execute
        result = await run_stage_1_extraction(file_paths)

        # Verify
        assert result["Document Type"] == "Utility Bill"
        assert result["Full Name"] == "John Doe"
