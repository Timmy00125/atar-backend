from uuid import UUID
from sqlalchemy import select
import json
import os
from google import genai
from google.genai import types
from app.core.database import AsyncSessionLocal
from app.models.session import VerificationSession
from app.core.config import settings

# Initialize Gemini Client
# Ensure GOOGLE_API_KEY is set in .env
client = genai.Client(api_key=settings.GOOGLE_API_KEY)


async def process_verification(session_id: UUID):
    """
    Trigger background task (Stage 1 -> Stage 2).
    """
    async with AsyncSessionLocal() as db:
        # 1. Load session
        result = await db.execute(
            select(VerificationSession).where(
                VerificationSession.session_id == session_id
            )
        )
        session = result.scalars().first()

        if not session:
            print(f"Session {session_id} not found in background task.")
            return

        try:
            # 2. Call Gemini Flash (Stage 1) - Extraction
            extracted_data = await run_stage_1_extraction(session.document_paths)
            session.extracted_data = extracted_data

            # 3. Call Gemini Pro (Stage 2) - Verification
            verification_results = await run_stage_2_verification(
                session, extracted_data
            )

            session.verification_results = verification_results
            session.trust_score = verification_results.get("trust_score", 0)
            session.status = "completed"

        except Exception as e:
            print(f"Error in verification process: {e}")
            session.status = "failed"
            # Optionally save error details

        await db.commit()


async def run_stage_1_extraction(file_paths: list[str]) -> dict:
    """
    Stage 1: Extraction using Gemini 2.5 Flash (or similar fast model).
    """
    # Prepare contents
    contents = []
    prompt = """
    Extract the following information from the provided document(s):
    - Document Type (Utility Bill, ID, Admission Letter, CAC Certificate, etc.)
    - Full Name
    - Address (Street, City, State)
    - Date (Issue Date, Bill Date)
    - Organization Name (if applicable, e.g., for Tier 3 documents)
    
    Return the result as a valid JSON object.
    """
    contents.append(prompt)

    for path in file_paths:
        if not os.path.exists(path):
            continue

        with open(path, "rb") as f:
            image_data = f.read()
            # Assuming images. For PDFs, might need different handling or mime type.
            # Simple mime type detection based on extension
            mime_type = "image/jpeg"
            if path.lower().endswith(".png"):
                mime_type = "image/png"
            elif path.lower().endswith(".pdf"):
                mime_type = "application/pdf"

            contents.append(types.Part.from_bytes(data=image_data, mime_type=mime_type))

    # Call Gemini Flash
    model_id = "gemini-1.5-flash"  # Adjust to 2.5 when available

    try:
        response = await client.aio.models.generate_content(
            model=model_id,
            contents=contents,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Stage 1 Error: {e}")
        return {"error": str(e)}


async def run_stage_2_verification(
    session: VerificationSession, extracted_data: dict
) -> dict:
    """
    Stage 2: Verification using Gemini 2.5 Pro.
    """
    user_claims = {
        "street": session.street,
        "city": session.city,
        "state": session.state,
        "organization_name": session.organization_name,
        "organization_type": session.organization_type,
    }

    geolocation = {"latitude": session.latitude, "longitude": session.longitude}

    prompt = f"""
    You are a verification agent. Compare the extracted information with the user claims and geolocation.
    
    User Claims: {json.dumps(user_claims)}
    Extracted Data: {json.dumps(extracted_data)}
    Geolocation: {json.dumps(geolocation)}
    
    Task:
    1. Compare Name: Does the name in the document match the user (implied or claimed)?
    2. Compare Address: Does the extracted address match the claimed address?
    3. Check Recency: Is the document recent (within last 3 months)?
    4. Tier 3 Check: If Organization Name is claimed, does it match the extracted Organization Name?
       - If match confidence >= 90%: Auto-Approve (+25 Trust Score)
       - If 70-89%: Flag for Review
       - If < 70%: Reject
    
    Calculate a Trust Score (0-100).
    - Base score starts at 0.
    - Address Match: +40
    - Name Match: +20
    - Recency: +15
    - Tier 3 Match (if applicable): +25
    
    Return a JSON object with:
    - trust_score: integer
    - breakdown: object with details of matches
    - verdict: "Approved", "Review", or "Rejected"
    """

    # Call Gemini Pro
    model_id = "gemini-1.5-pro"  # Adjust to 2.5 Pro when available

    try:
        response = await client.aio.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Stage 2 Error: {e}")
        return {"error": str(e)}
