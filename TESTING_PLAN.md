# System Testing Plan

We need to perform a full front-to-back test of the ATAR Address Verification system.

## Test Data Requirements

### 1. User Claim Data

- **street**: e.g., `123 Alara Street`
- **city**: e.g., `Yaba`
- **state**: e.g., `Lagos`
- **latitude**: e.g., `6.5167`
- **longitude**: e.g., `3.3865`
- **organization_name** (Tier 3): e.g., `University of Lagos`
- **organization_type** (Tier 3): `School` or `Business`

### 2. Document Images

Required: Clear images matching the claim data.

- **Residential**: Utility Bill, Bank Statement, or Gov ID.
- **Organization**: Admission Letter, Employment Letter, or CAC Certificate.

## Test Scenarios

### Scenario A: Residential Verification

- Input: Utility bill image + matching address data.
- Expected Result: Successful verification with high trust score.

### Scenario B: Organization Verification

- Input: Admission letter image + matching school data.
- Expected Result: Successful verification.

## Execution Steps

1. Start server: `uvicorn app.main:app --reload`
2. Create session: `POST /api/v1/verification/session`
3. Submit data: `POST /api/v1/verification/{session_id}/submit`
4. Check results: `GET /api/v1/verification/{session_id}/results`
