import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, ARRAY, JSON
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from app.core.database import Base


def utc_now():
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class VerificationSession(Base):
    __tablename__ = "sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String, default="pending")  # pending, processing, completed
    created_at = Column(TIMESTAMP(timezone=True), default=utc_now)

    # User Claims
    street = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Tier 3 Specifics
    organization_type = Column(String, nullable=True)  # school, work, business
    organization_name = Column(String, nullable=True)

    # AI Results
    document_paths = Column(ARRAY(String), nullable=True)
    file_metadata = Column(JSON, nullable=True)  # Store EXIF/Meta data from files
    extracted_data = Column(JSON, nullable=True)
    verification_results = Column(JSON, nullable=True)
    trust_score = Column(Integer, nullable=True)
