import asyncio
import httpx
import os
import json

BASE_URL = "http://localhost:8000/api/v1"
TEST_FILES_DIR = "Testing_stuff"

# Data from Test_files.md
CLAIMED_DATA = {
    "street": "NO 5 kings court close, dawaki model city",
    "city": "Dawaki",
    "state": "Abuja",
    "latitude": "9.1538",  # Approx for Dawaki, Abuja
    "longitude": "7.3633",
    "organization_name": "SEVENBITLABS LTD",  # Inferred from file names
    "organization_type": "Company",
}


async def run_test():
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Check Health
        try:
            resp = await client.get(f"{BASE_URL}/health")
            resp.raise_for_status()
            print("✅ Server is healthy")
        except Exception as e:
            print(f"❌ Server not reachable: {e}")
            return

        # 2. Create Session
        print("Creating session...")
        resp = await client.post(f"{BASE_URL}/verification/session")
        if resp.status_code != 200:
            print(f"❌ Failed to create session: {resp.text}")
            return

        session_data = resp.json()
        session_id = session_data["session_id"]
        print(f"✅ Session created: {session_id}")

        # 3. Submit Data
        print("Submitting data and files...")

        files_to_upload = []
        file_handles = []

        try:
            # Gather files
            for filename in os.listdir(TEST_FILES_DIR):
                if filename.endswith(".md"):
                    continue

                filepath = os.path.join(TEST_FILES_DIR, filename)
                f = open(filepath, "rb")
                file_handles.append(f)
                files_to_upload.append(
                    ("documents", (filename, f, "application/octet-stream"))
                )

            if not files_to_upload:
                print("❌ No files found to upload")
                return

            print(f"Uploading {len(files_to_upload)} files...")

            resp = await client.post(
                f"{BASE_URL}/verification/{session_id}/submit",
                data=CLAIMED_DATA,
                files=files_to_upload,
            )

            if resp.status_code != 200:
                print(f"❌ Failed to submit data: {resp.text}")
                return

            print("✅ Data submitted successfully")

        finally:
            # Close file handles
            for f in file_handles:
                f.close()

        # 4. Poll for Results
        print("Polling for results...")
        while True:
            resp = await client.get(f"{BASE_URL}/verification/{session_id}/results")

            if resp.status_code == 202:
                print("⏳ Processing...")
                await asyncio.sleep(2)
                continue

            if resp.status_code == 200:
                result = resp.json()
                status = result.get("status")
                print(f"Current status: {status}")

                if status in ["completed", "failed", "verified", "rejected"]:
                    print("\n🎉 Verification Finished!")

                    # Pretty print the result
                    print(f"Status: {status}")
                    print(f"Trust Score: {result.get('trust_score')}")

                    verification_results = result.get("verification_results", {})
                    if verification_results:
                        print("\n--- Verification Breakdown ---")
                        print(
                            json.dumps(verification_results.get("breakdown"), indent=2)
                        )
                        print(f"\nVerdict: {verification_results.get('verdict')}")

                    extracted_data = result.get("extracted_data", {})
                    if extracted_data:
                        print("\n--- Extracted Data ---")
                        # Check for name match
                        claimed_name = "Oluwaseyi Timilehin Victor"
                        found_name = False
                        for doc in extracted_data.get("documents", []):
                            print(
                                f"- {doc.get('type')}: {doc.get('name')} ({doc.get('organization')})"
                            )
                            if doc.get("name") and any(
                                part.lower() in doc.get("name").lower()
                                for part in claimed_name.split()
                            ):
                                found_name = True

                        if found_name:
                            print(
                                f"\n✅ Found name matching '{claimed_name}' in documents."
                            )
                        else:
                            print(
                                f"\n⚠️ Could not find name matching '{claimed_name}' in documents."
                            )

                    break

                await asyncio.sleep(2)
            else:
                print(f"❌ Error polling results: {resp.status_code} - {resp.text}")
                break


if __name__ == "__main__":
    asyncio.run(run_test())
