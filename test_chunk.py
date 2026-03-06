import asyncio
from agents.extractor import AIExtractionAgent
from core.config import settings
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    agent = AIExtractionAgent(api_key=settings.openrouter_api_key)
    with open('benchmark_extracted_data.json', 'r', encoding='utf-8') as f:
        pass # Just to ensure we're in the right dir, but we actually want html
    html = "Sample HTML <a href='abc'>Name: John Doe Title: CEO Email: john@doe.com</a>"
    res = await agent._extract_chunk(html)
    print("Result:")
    print(res)

if __name__ == '__main__':
    asyncio.run(main())
