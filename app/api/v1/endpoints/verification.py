from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
import shutil
import os
import uuid

from app.core.database import get_db
from app.models.session import VerificationSession
from app.schemas.session import SessionCreateResponse, SessionResult
from app.services.ai_service import process_verification

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/session", response_model=SessionCreateResponse)
async def create_session(db: AsyncSession = Depends(get_db)):
    new_session = VerificationSession()
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return SessionCreateResponse(
        session_id=new_session.session_id, status=new_session.status
    )


@router.post("/{session_id}/submit")
async def submit_verification_data(
    session_id: UUID,
    background_tasks: BackgroundTasks,
    street: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    organization_name: Optional[str] = Form(None),
    organization_type: Optional[str] = Form(None),
    documents: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    # Check if session exists
    result = await db.execute(
        select(VerificationSession).where(VerificationSession.session_id == session_id)
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Save files
    file_paths = []
    session_upload_dir = os.path.join(UPLOAD_DIR, str(session_id))
    os.makedirs(session_upload_dir, exist_ok=True)

    for doc in documents:
        file_path = os.path.join(session_upload_dir, doc.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(doc.file, buffer)
        file_paths.append(file_path)

    # Update session data
    session.street = street
    session.city = city
    session.state = state
    session.latitude = latitude
    session.longitude = longitude
    session.organization_name = organization_name
    session.organization_type = organization_type
    session.document_paths = file_paths
    session.status = "processing"

    await db.commit()

    # Trigger background task
    background_tasks.add_task(process_verification, session_id)

    return {"message": "Submission received", "status": "processing"}


@router.get("/{session_id}/results", response_model=SessionResult)
async def get_results(session_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VerificationSession).where(VerificationSession.session_id == session_id)
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "processing":
        # Return 202 Accepted if still processing, but FastAPI response_model might expect the full object.
        # The README says "Return HTTP 202".
        # We can raise an HTTPException or return a Response object.
        # For now, let's just return the session object, the client can check the status.
        # Or strictly follow the requirement:
        from fastapi import Response

        return Response(status_code=status.HTTP_202_ACCEPTED)

    return session
