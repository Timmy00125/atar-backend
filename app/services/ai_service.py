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
    Analyze the provided images/documents. Identify and extract information for the following types:
    
    1. **Logistics/Delivery Receipt** (e.g., Jumia, Food Delivery):
       - Extract: Delivery Address, Recipient Name, Date.
    
    2. **House Image**:
       - Identify if it is a picture of a residential building.
       - Note any visible address numbers or landmarks if present.
    
    3. **Trust Score Documents** (Employment Letter, Pay Slip, School Admission, School Fees, etc.):
       - Extract: Document Type, Organization Name, Person Name, Date.
    
    Return a JSON object with a list of analyzed documents, e.g.:
    {
      "documents": [
        {
          "type": "Logistics Receipt",
          "address": "...",
          "name": "...",
          "date": "..."
        },
        {
          "type": "House Image",
          "is_residential": true,
          "visible_address": "..."
        },
        {
          "type": "Employment Letter",
          "organization": "...",
          "name": "..."
        }
      ]
    }
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
    model_id = "gemini-2.5-flash"  # Adjust to 2.5 when available

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
    file_metadata = session.file_metadata or {}

    prompt = f"""
    You are a verification agent. Compare the extracted information with the user claims, geolocation, and file metadata.
    
    User Claims: {json.dumps(user_claims)}
    Extracted Data: {json.dumps(extracted_data)}
    Geolocation (Claimed): {json.dumps(geolocation)}
    File Metadata (EXIF/GPS): {json.dumps(file_metadata)}
    
    Task:
    1. **Location Verification**:
       - Check if any 'House Image' has GPS metadata in 'File Metadata'.
       - If yes, calculate the distance between Claimed Geolocation and Image GPS.
       - Match if distance < 100 meters.
    
    2. **Address Verification**:
       - Check if any 'Logistics Receipt' has an address matching the Claimed Address.
    
    3. **Trust Score Calculation**:
       - Base Score: 0
       - **Location Match (GPS)**: +30 points (if House Image GPS matches Claimed Location).
       - **Address Match (Logistics)**: +30 points (if Receipt Address matches Claimed Address).
       - **Trust Documents**: +10 points for each valid verified document (Employment, School, etc.), up to +40 points.
       - **Recency**: +10 points if documents are recent (< 3 months).
    
    Return a JSON object with:
    - trust_score: integer (0-100)
    - breakdown: object with details of matches (location_match, address_match, trust_docs_match)
    - verdict: "Approved" (Score >= 70), "Review" (Score 50-69), "Rejected" (Score < 50)
    """

    # Call Gemini Pro
    model_id = "gemini-2.5-pro"  # Adjust to 2.5 Pro when available

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
