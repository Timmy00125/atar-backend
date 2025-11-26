import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://user:password@localhost/atar_db"


async def fix_db():
    engine = create_async_engine(DATABASE_URL, echo=True)

    print("Adding file_metadata column...")
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("ALTER TABLE sessions ADD COLUMN file_metadata JSON;")
            )
        print("Added file_metadata.")
    except Exception as e:
        print(f"Error adding file_metadata: {e}")

    print("Adding extracted_data column...")
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("ALTER TABLE sessions ADD COLUMN extracted_data JSON;")
            )
        print("Added extracted_data.")
    except Exception as e:
        print(f"Error adding extracted_data: {e}")

    print("Adding verification_results column...")
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("ALTER TABLE sessions ADD COLUMN verification_results JSON;")
            )
        print("Added verification_results.")
    except Exception as e:
        print(f"Error adding verification_results: {e}")

    print("Adding trust_score column...")
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("ALTER TABLE sessions ADD COLUMN trust_score INTEGER;")
            )
        print("Added trust_score.")
    except Exception as e:
        print(f"Error adding trust_score: {e}")

    print("Adding document_paths column...")
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("ALTER TABLE sessions ADD COLUMN document_paths VARCHAR[];")
            )
        print("Added document_paths.")
    except Exception as e:
        print(f"Error adding document_paths: {e}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(fix_db())
