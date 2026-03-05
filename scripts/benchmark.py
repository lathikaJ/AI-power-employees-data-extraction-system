import asyncio
import time
import logging
import sys
import os
from typing import List, Dict, Any

# Add root project path to allow `agents` module to import accurately
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.input_agent import InputAgent, InvalidURLError, SSRFViolationError
from agents.crawl_agent import CrawlAgent
from agents.extractor import AIExtractionAgent
from agents.clean_agent import CleanAgent
from core.config import settings

# Configure logging for the benchmark script specifically
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("benchmark")

# List of 20 URLs (Mix of expected valid and potentially failing domains for a realistic benchmark)
TARGET_URLS = [
    "https://corporate.walmart.com/about/leadership",
    "https://klodev.com",
    "https://www.medivoy.ae"
]

class BenchmarkRunner:
    """
    Utility designed to run the entire extraction stack securely over 
    a subset of 20 URLs while compiling the following metrics:
    - Average Execution Time
    - Extraction Accuracy Percentage
    - Failure Rate
    - AI Response Latency
    """
    def __init__(self):
        self.input_agent = InputAgent()
        self.crawl_agent = CrawlAgent(timeout=10, max_concurrent=2, retries=1)
        self.ai_agent = AIExtractionAgent(api_key=settings.openrouter_api_key)
        self.clean_agent = CleanAgent()
        
    async def process_single_url(self, url: str) -> Dict[str, Any]:
        """
        Executes the extraction pipeline against a single URL tracking 
        metric timestamps internally.
        """
        result = {
            "url": url,
            "success": False,
            "total_time": 0.0,
            "ai_time": 0.0,
            "employees_found": 0
        }
        
        start_time = time.time()
        
        try:
            # 1. Validate
            validated_url = self.input_agent.validate_and_normalize_url(url)
            
            # 2. Crawl
            html_pages = await self.crawl_agent.crawl(validated_url)
            if not html_pages:
                raise ValueError("No valid crawled pages found (empty or robots.txt blocked)")
                
            # 3. AI Extraction (Tracking Latency Specifically)
            all_raw_employees = []
            
            ai_start_time = time.time()
            for raw_html in html_pages:
                extracted_list = await self.ai_agent.extract_employees(raw_html)
                all_raw_employees.extend(extracted_list)
            ai_end_time = time.time()
            
            result["ai_time"] = ai_end_time - ai_start_time

            # 4. Cleaning
            cleaned_employees = self.clean_agent.clean(all_raw_employees)
            
            # Mark Success if completion was reached without exception interruptions
            result["success"] = True
            result["employees_found"] = len(cleaned_employees)
            result["employees"] = cleaned_employees # STORES THE EXTRACTED DATA
            
        except Exception as e:
            print(f"Error processing {url}: {e}")
            pass
            
        end_time = time.time()
        result["total_time"] = end_time - start_time
        
        return result

    async def run_benchmark(self, urls: List[str]):
        """
        Executes the benchmark against the provided list.
        """
        print(f"--- Starting Benchmark on {len(urls)} URLs ---")
        
        # We'll execute them sequentially to simulate 20 individual API calls accurately
        # Note: You could use `asyncio.gather` here to blast them concurrently, 
        # but that would skew the AI latency tracking and potentially trigger OpenRouter rate limits.
        
        results = []
        for url in urls:
            print(f"Processing: {url}")
            res = await self.process_single_url(url)
            results.append(res)
            # Polite delay for free tier rate limits
            await asyncio.sleep(3)
            
        # -----------------------------
        # Compute Metrics
        # -----------------------------
        total_urls = len(results)
        successful_runs = [r for r in results if r["success"]]
        failed_runs = [r for r in results if not r["success"]]
        
        # 1. Total & Average Execution Time
        total_execution_time = sum(r["total_time"] for r in results)
        avg_execution_time = total_execution_time / total_urls if total_urls else 0
        
        # 2. AI Response Latency (Only calculated from successful calls that touched the AI)
        ai_times = [r["ai_time"] for r in results if r["ai_time"] > 0]
        avg_ai_latency = sum(ai_times) / len(ai_times) if ai_times else 0
        
        # 3. Failure Rate
        failure_rate = (len(failed_runs) / total_urls) * 100
        
        # 4. Extraction Accuracy Percentage
        # For this logic, we'll define "Accuracy" as out of the *successful* responses, 
        # what percentage of them found `> 0` employees?
        urls_with_employees = [r for r in successful_runs if r["employees_found"] > 0]
        if successful_runs:
            accuracy_percentage = (len(urls_with_employees) / len(successful_runs)) * 100
        else:
            accuracy_percentage = 0.0

        # Output formatting
        print("\n=======================================================")
        print("                 BENCHMARK RESULTS                     ")
        print("=======================================================")
        print(f"Total URLs Processed      : {total_urls}")
        print(f"Total Execution Time      : {total_execution_time:.2f} seconds")
        print(f"Average Execution Time    : {avg_execution_time:.2f} seconds")
        print(f"Average AI Latency        : {avg_ai_latency:.2f} seconds")
        print(f"Extraction Accuracy       : {accuracy_percentage:.2f}%")
        print(f"Failure Rate              : {failure_rate:.2f}% ({len(failed_runs)} failures)")
        print("=======================================================")

        # Save the actual extracted data to a file so we can view it
        output_file = "benchmark_extracted_data.json"
        with open(output_file, "w", encoding="utf-8") as f:
            import json
            json.dump(results, f, indent=4)
        print(f"\n[+] Full extracted output data has been saved to: {output_file}")

if __name__ == "__main__":
    runner = BenchmarkRunner()
    asyncio.run(runner.run_benchmark(TARGET_URLS))
