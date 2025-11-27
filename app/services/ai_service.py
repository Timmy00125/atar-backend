from uuid import UUID
from sqlalchemy import select
import json
import os
import aiofiles
from datetime import datetime
from google import genai
from google.genai import types
from app.core.database import AsyncSessionLocal
from app.models.session import VerificationSession
from app.core.config import settings
from app.core.utils import calculate_haversine_distance
from tenacity import retry, stop_after_attempt, wait_random_exponential

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


@retry(wait=wait_random_exponential(multiplier=1, max=60), stop=stop_after_attempt(5))
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
       - Extract: Document Type, Organization Name, Person Name, Date, Address (if present).
    
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

        async with aiofiles.open(path, "rb") as f:
            image_data = await f.read()
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

    response = await client.aio.models.generate_content(
        model=model_id,
        contents=contents,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return json.loads(response.text)


@retry(wait=wait_random_exponential(multiplier=1, max=60), stop=stop_after_attempt(5))
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
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Calculate Haversine distances for images with GPS data
    gps_analysis = []
    for filename, meta in file_metadata.items():
        if "gps" in meta:
            img_lat = meta["gps"]["latitude"]
            img_lon = meta["gps"]["longitude"]
            distance = calculate_haversine_distance(
                session.latitude, session.longitude, img_lat, img_lon
            )
            gps_analysis.append(
                {
                    "filename": filename,
                    "distance_meters": round(distance, 2),
                    "image_coords": {"lat": img_lat, "lon": img_lon},
                    "match_status": "MATCH"
                    if distance < 100
                    else "MISMATCH",  # Threshold of 100m
                }
            )

    prompt = f"""
    You are a verification agent. Your goal is to verify that the User's Claimed Address is genuine based on the provided evidence.
    
    Current Date: {current_date}
    User Claims: {json.dumps(user_claims)}
    Extracted Data: {json.dumps(extracted_data)}
    Geolocation (Claimed): {json.dumps(geolocation)}
    File Metadata (EXIF/GPS): {json.dumps(file_metadata)}
    Computed GPS Distances (Haversine): {json.dumps(gps_analysis)}
    
    Analyze ALL provided data to calculate a Trust Score (0-100).
    
    Scoring Criteria:
    1. **Physical Location Evidence (House Image)**:
       - If House Image is present AND GPS metadata matches Claimed Geolocation (< 100m): 30 points.
       - If House Image is present but no GPS match (visual confirmation only): 10 points.
       - No House Image: 0 points.
    
    2. **Logistics/Activity Evidence (Delivery Receipts)**:
       - If a recent Logistics/Delivery Receipt matches the Claimed Address: 30 points.
       - If the name on the receipt also matches the User: +5 bonus points.
       - Max: 35 points.
    
    3. **Institutional/Trust Evidence (Employment, School, etc.)**:
       - For EACH valid document (Employment Letter, Pay Slip, School Admission, School Fees, etc.) that verifies the User's Identity: 10 points.
       - If the document ALSO contains the Claimed Address: +5 bonus points per document.
       - Max points for this category: 40.
    
    4. **Recency Check**:
       - If the majority of documents are recent (< 3 months): 10 points.
       - Otherwise: 0 points.
    
    Total Score cannot exceed 100.
    
    Return a JSON object with:
    - trust_score: integer (0-100)
    - breakdown: object with details (house_match_score, logistics_match_score, institutional_proofs_score, recency_score)
    - verdict: "Approved" (Score >= 70), "Review" (Score 50-69), "Rejected" (Score < 50)
    """

    # Call Gemini Pro
    model_id = "gemini-2.5-pro"  # Adjust to 2.5 Pro when available

    response = await client.aio.models.generate_content(
        model=model_id,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return json.loads(response.text)
