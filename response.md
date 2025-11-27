# API Response Formats & Types

All API responses follow a standard generic wrapper format.

## Shared Types

```typescript
interface APIResponse<T> {
  success: boolean;
  message: string;
  data: T | null;
}
```

## Endpoints

### 1. Create Session

**POST** `/api/v1/verification/session`

**Type Definition:**

```typescript
interface SessionCreateResponse {
  session_id: string; // UUID
  status: string; // e.g., "pending", "created"
}

type CreateSessionResponse = APIResponse<SessionCreateResponse>;
```

**Example Response:**

```json
{
  "success": true,
  "message": "Session created successfully",
  "data": {
    "session_id": "123e4567-e89b-12d3-a456-426614174000",
    "status": "pending"
  }
}
```

### 2. Submit Verification Data

**POST** `/api/v1/verification/{session_id}/submit`

**Type Definition:**

```typescript
interface SessionSubmitResponseData {
  status: string; // e.g., "processing"
}

type SubmitResponse = APIResponse<SessionSubmitResponseData>;
```

**Example Response:**

```json
{
  "success": true,
  "message": "Submission received",
  "data": {
    "status": "processing"
  }
}
```

### 3. Get Results

**GET** `/api/v1/verification/{session_id}/results`

**Type Definitions:**

```typescript
interface TrustScoreBreakdown {
  house_match_score: number;
  logistics_match_score: number;
  institutional_proofs_score: number;
  recency_score: number;
  [key: string]: any; // Allow extra fields
}

interface TrustScoreData {
  trust_score: number;
  verdict: string;
  breakdown?: TrustScoreBreakdown;
}

interface SessionResult {
  session_id: string; // UUID
  status: string; // "processing", "completed", "failed"
  trust_score?: number;
  trust_analysis?: TrustScoreData;
  verification_results?: Record<string, any>; // Dynamic dictionary
  extracted_data?: Record<string, any>; // Dynamic dictionary
  created_at: string; // ISO 8601 Date String
}

type GetResultsResponse = APIResponse<SessionResult>;
```

**Response (Processing - HTTP 202):**

```json
{
  "success": true,
  "message": "Verification is still in progress",
  "data": null
}
```

**Response (Completed - HTTP 200):**

```json
{
  "success": true,
  "message": "Verification results retrieved",
  "data": {
    "session_id": "123e4567-e89b-12d3-a456-426614174000",
    "status": "completed",
    "trust_score": 85,
    "trust_analysis": {
      "trust_score": 85,
      "verdict": "High Trust",
      "breakdown": {
        "house_match_score": 20,
        "logistics_match_score": 20,
        "institutional_proofs_score": 30,
        "recency_score": 15
      }
    },
    "verification_results": {
      "face_match": true,
      "document_valid": true
    },
    "extracted_data": {
      "name": "John Doe",
      "address": "123 Main St"
    },
    "created_at": "2023-10-27T10:00:00Z"
  }
}
```

### 4. Health Check

**GET** `/api/v1/health`

**Type Definition:**

```typescript
interface HealthCheckData {
  status: string;
}

type HealthCheckResponse = APIResponse<HealthCheckData>;
```

**Example Response:**

```json
{
  "success": true,
  "message": "Health check passed",
  "data": {
    "status": "ok"
  }
}
```

## Error Responses

**Type Definition:**

```typescript
type ErrorResponse = APIResponse<null>;
```

**404 Not Found:**

```json
{
  "success": false,
  "message": "Session not found",
  "data": null
}
```

**500 Internal Server Error:**

```json
{
  "success": false,
  "message": "Internal Server Error: [Error Details]",
  "data": null
}
```
