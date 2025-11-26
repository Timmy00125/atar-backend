import httpx
import asyncio
import os

BASE_URL = "http://localhost:8000/api/v1/verification"
IMAGE_PATH = "Meter bill .png"


async def main():
    async with httpx.AsyncClient() as client:
        # 1. Create Session
        print("Creating session...")
        try:
            response = await client.post(f"{BASE_URL}/session")
        except httpx.ConnectError:
            print("Failed to connect to the server. Is it running?")
            return

        if response.status_code != 200:
            print(f"Failed to create session: {response.text}")
            return

        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"Session created: {session_id}")

        # 2. Submit Data
        print("Submitting data...")
        if not os.path.exists(IMAGE_PATH):
            print(f"File not found: {IMAGE_PATH}")
            return

        # Re-open file for each request if needed, but here we just send it once.
        with open(IMAGE_PATH, "rb") as f:
            files = {"documents": (os.path.basename(IMAGE_PATH), f, "image/png")}
            data = {
                "street": "123 Test St",
                "city": "Test City",
                "state": "Test State",
                "latitude": "0.0",
                "longitude": "0.0",
                "organization_name": "Test Org",
            }

            response = await client.post(
                f"{BASE_URL}/{session_id}/submit", data=data, files=files
            )

        if response.status_code != 200:
            print(f"Failed to submit data: {response.text}")
            return

        print("Data submitted successfully.")

        # 3. Poll for results
        print("Polling for results...")
        for _ in range(30):  # Timeout after 60 seconds
            response = await client.get(f"{BASE_URL}/{session_id}/results")
            if response.status_code == 200:
                result = response.json()
                status = result.get("status")
                print(f"Current status: {status}")
                if status in ["completed", "failed"]:
                    print("Final Result:")
                    print(result)
                    break
            elif response.status_code == 202:
                print("Still processing...")
            else:
                print(f"Error getting results: {response.status_code} {response.text}")
                break

            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
