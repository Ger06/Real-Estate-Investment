import asyncio
import httpx
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en-US;q=0.8,en;q=0.7",
}

async def test_url(client, url, name):
    print(f"\n--- Testing {name} ---")
    print(f"URL: {url}")
    try:
        response = await client.get(url, headers=HEADERS, timeout=30.0, follow_redirects=True)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Success! Content length:", len(response.content))
            # Check for "There are no listings" text if possible, though hard to know without seeing it.
            # But 200 OK on a search page usually means it worked.
        else:
            print("Failed.")
    except Exception as e:
        print(f"Error: {e}")

async def test_connection():
    async with httpx.AsyncClient() as client:
        # 1. Slug based
        slug_url = "https://www.remax.com.ar/departamentos-en-venta-en-palermo"
        await test_url(client, slug_url, "Slug URL")

        # 2. User Example (Query param based)
        # Note: I shortened it slightly to basic params
        # user_url = "https://www.remax.com.ar/listings/buy?page=0&pageSize=24&sort=-createdAt&in:operationId=1&in:typeId=12&locations=in::::25043@%3Cb%3EVilla%3C%2Fb%3E%20del%20Parque#%20Capital%20Federal:::" 
        # Using a safer version presumably
        user_url = "https://www.remax.com.ar/listings/buy?in:operationId=1&in:typeId=1&locations=in::::25043@Villa%20del%20Parque:::"
        await test_url(client, user_url, "Query URL (Simulated)")

if __name__ == "__main__":
    asyncio.run(test_connection())
