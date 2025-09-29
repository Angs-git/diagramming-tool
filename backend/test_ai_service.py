import asyncio
from services.ai_service import clean_diagram

async def main():
    with open("sample_diagram.png", "rb") as f:
        image_bytes = f.read()

    result = await clean_diagram(image_bytes)
    print("Cleaned Result:", result)  # 👉 Already a dict if parsing succeeds

if __name__ == "__main__":
    asyncio.run(main())

