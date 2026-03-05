import asyncio
import json
import logging
import sys
import os

# Add root project path to allow `agents` module to import accurately
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.extraction_service import ExtractionService

# Configure logging
logging.basicConfig(level=logging.INFO)

async def extract_and_save(url: str, output_filename: str):
    print(f"Starting extraction for: {url}")
    service = ExtractionService()
    
    # Run the extraction
    result = await service.execute_extraction(url)
    
    # Save the result to a JSON file
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)
        
    print(f"Extraction complete! Data saved to: {output_filename}")
    print(f"Found {result.get('total_count', 0)} employees.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
    else:
        target_url = input("Enter the URL to extract employees from: ").strip()
        
    if not target_url:
        print("Error: No URL provided.")
        sys.exit(1)
        
    output_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output.json")
    
    asyncio.run(extract_and_save(target_url, output_file))
