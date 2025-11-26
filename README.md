# ATAR Backend - Address Verification API

## 1. Project Overview

This is the backend service for the ATAR Address Verification system. It is a Python FastAPI application designed to verify user addresses (Residential and Tier 3 Work/School/Business) using a two-stage AI pipeline.

**Key Goals:**

- **Latency:** Calculate Trust Score within 60 seconds.
- **Flow:** Asynchronous processing (Submit -> Ack -> Process -> Poll).
- **AI Models:** Google Gemini 2.5 Flash (Speed/OCR) and Gemini 2.5 Pro (Reasoning/Scoring).

## 2. System Architecture & Logic

### The Workflow

1.  **Frontend**: Collects user input, captures document images, and retrieves **Geolocation (Latitude/Longitude)** directly from the user's device.
2.  **Backend**: Receives data, stores it, and orchestrates the AI verification.
3.  **AI Pipeline**:
    - **Stage 1: Extraction (Gemini 2.5 Flash)**
      - **Role:** High-speed OCR and data extraction.
      - **Input:** Document images (Utility bills, IDs, Admission letters, CAC certificates).
      - **Action:** Extracts text, addresses, dates, and organization names.
    - **Stage 2: Verification & Scoring (Gemini 2.5 Pro)**
      - **Role:** Logic, comparison, and scoring.
      - **Input:** Extracted data (from Stage 1) + User Claims + Geolocation (from Frontend).
      - **Action:** Compares extracted address/org against claims and GPS. Calculates the final **Trust Score (0-100)**.

## 3. Tech Stack

- **Language:** Python 3.12+
- **Framework:** FastAPI (Uvicorn)
- **Database:** PostgreSQL (Supabase/Neon recommended)
- **ORM:** SQLAlchemy
- **AI SDK:** `google-genai`

## 4. Verification Tiers

### Tier 1 & 2: Residential Verification

Verifies a user's home address using utility bills or IDs.

- **Checks:** Document validity, Address match, Name match, Recency.

### Tier 3: Work/School/Business Verification

Verifies stability by confirming affiliation with an organization.

**Accepted Documents:**

- **Students:** School Fees Receipt, Admission Letter.
- **Employees:** Employment Offer Letter, Payslip.
- **Business:** CAC Certificate (BN1/CO7).

**Logic:**

1.  User claims an Organization Name (e.g., "Veritas University").
2.  **Gemini Flash** extracts the Organization Name from the uploaded document.
3.  **Gemini Pro** compares the claimed name vs. extracted name.
    - **Confidence >= 90%**: Auto-Approve (+25 Trust Score).
    - **Confidence 70-89%**: Flag for Review.
    - **Confidence < 70%**: Reject.

## 5. API Endpoints

### A. Core Session Management

- **GET** `/api/v1/health`: Check API status.
- **POST** `/api/v1/verification/session`: Start a new verification session. Returns `session_id`.

### B. Submission (Async)

- **POST** `/api/v1/verification/{session_id}/submit`
  - **Body:** Multipart form-data.
  - **Data:** `street`, `city`, `state`, `latitude`, `longitude`, `organization_name` (if Tier 3).
  - **Files:** `documents[]`.
  - **Process:**
    1.  Save files locally.
    2.  Save metadata to Postgres.
    3.  Trigger background task (Stage 1 -> Stage 2).
    4.  Return `200 OK` immediately.

### C. Polling Results

- **GET** `/api/v1/verification/{session_id}/results`
  - **Status `processing`**: Return HTTP 202.
  - **Status `completed`**: Return JSON with `trust_score`, `breakdown`, and `verdict`.

## 6. Database Schema (PostgreSQL)

**Table: `sessions`**

```sql
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY,
    status VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed
    created_at TIMESTAMP DEFAULT NOW(),

    -- User Claims
    street TEXT,
    city TEXT,
    state TEXT,
    latitude FLOAT,  -- From Frontend
    longitude FLOAT, -- From Frontend

    -- Tier 3 Specifics
    organization_type VARCHAR(50), -- school, work, business
    organization_name TEXT,

    -- AI Results
    document_paths TEXT[],
    extracted_data JSONB,       -- Output from Gemini Flash
    verification_results JSONB, -- Output from Gemini Pro (Score & Breakdown)
    trust_score INTEGER
);
```

## 7. Development Checklist

- [ ] **Setup**: FastAPI, Uvicorn, SQLAlchemy, Google GenAI SDK.
- [ ] **DB**: Init Postgres `sessions` table.
- [ ] **Endpoints**: Implement Health, Session, Submit, Results.
- [ ] **AI Stage 1 (Flash)**: Implement async function for OCR/Extraction.
- [ ] **AI Stage 2 (Pro)**: Implement logic to calculate Trust Score based on Flash output + Geo.
- [ ] **Tier 3 Logic**: Add specific prompt handling for Org Name comparison.
- [ ] **Testing**: Verify latency < 60s and JSON structure.
