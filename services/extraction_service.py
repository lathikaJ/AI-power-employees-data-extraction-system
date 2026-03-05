import logging
import asyncio
from typing import Dict, Any

from agents.input_agent import InputAgent, InvalidURLError, SSRFViolationError
from agents.crawl_agent import CrawlAgent
from agents.extractor import AIExtractionAgent
from agents.clean_agent import CleanAgent
from core.config import settings

logger = logging.getLogger(__name__)

class ExtractionService:
    """
    Orchestrates the entire employee extraction workflow by coordinating:
    1. Input validation & SSRF prevention
    2. HTML targeted crawling
    3. AI intelligent extraction 
    4. Entity cleaning & deduplication
    """
    def __init__(self):
        # Initialize specialized agents
        self.input_agent = InputAgent()
        self.crawl_agent = CrawlAgent()
        self.ai_agent = AIExtractionAgent(api_key=settings.openrouter_api_key)
        self.clean_agent = CleanAgent()

    async def execute_extraction(self, original_url: str) -> Dict[str, Any]:
        """
        Executes the extraction pipeline sequentially.
        
        Args:
            original_url (str): The requested target URL.
            
        Returns:
            Dict[str, Any]: Standardized JSON structure.
        """
        try:
            # Step 1: Validate URL and block SSRF
            logger.info(f"Validating URL: {original_url}")
            validated_url = self.input_agent.validate_and_normalize_url(original_url)

            # Step 2: Crawl target paths concurrently (/team, /about, etc.)
            logger.info(f"Crawling URL: {validated_url}")
            html_pages = await self.crawl_agent.crawl(validated_url)

            if not html_pages:
                logger.warning(f"No valid pages found to crawl for {validated_url}")
                return {
                    "status": "success",
                    "total_count": 0,
                    "employees": []
                }

            # Step 3: Extract entities using AI on each crawled page
            all_raw_employees = []
            for num, raw_html in enumerate(html_pages, 1):
                logger.info(f"Running AI extraction for page chunk {num} of {len(html_pages)}")
                extracted_list = await self.ai_agent.extract_employees(raw_html)
                logger.info(f"Extracted {len(extracted_list)} raw employees from page chunk {num}")
                all_raw_employees.extend(extracted_list)

            # Step 3.5: Resolve relative URLs to absolute
            from urllib.parse import urljoin
            for emp in all_raw_employees:
                if emp.get("profile_url") and not emp.get("profile_url").startswith("http"):
                    emp["profile_url"] = urljoin(validated_url, emp["profile_url"])

            # Step 4: Deep Crawling (Follow bio pages for missing social links)
            profile_url_map = {}
            from urllib.parse import urljoin

            for idx, emp in enumerate(all_raw_employees):
                p_url = emp.get("profile_url")
                if p_url and not (emp.get("linkedin") and emp.get("instagram")):
                    full_p_url = urljoin(validated_url, p_url)
                    if full_p_url not in profile_url_map:
                        profile_url_map[full_p_url] = []
                    profile_url_map[full_p_url].append(idx)
            
            if profile_url_map:
                # Limit concurrent bio crawling to avoid excessive load or rate-limiting
                target_bio_urls = list(profile_url_map.keys())[:40]
                logger.info(f"Deep crawling {len(target_bio_urls)} bio pages with concurrency limit 5.")
                
                semaphore = asyncio.Semaphore(5)
                
                async def process_bio(p_url, client, count_obj):
                    async with semaphore:
                        try:
                            resp = await client.get(p_url)
                            if resp.status_code == 200:
                                bio_extract = await self.ai_agent.extract_employees(resp.text)
                                logger.info(f"Bio extract for {p_url}: found {len(bio_extract)} records")
                                count_obj["done"] += 1

                                if count_obj["done"] % 5 == 0:
                                    logger.info(f"Deep crawl progress: {count_obj['done']}/{len(target_bio_urls)}")
                                return p_url, bio_extract[0] if bio_extract else None
                        except Exception as e:
                            logger.warning(f"Failed bio crawl for {p_url}: {e}")
                        return p_url, None

                import httpx
                progress = {"done": 0}
                async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True) as client:
                    bio_results = await asyncio.gather(*(process_bio(u, client, progress) for u in target_bio_urls))
                    
                    for p_url, top_match in bio_results:
                        if top_match:
                            for idx in profile_url_map[p_url]:
                                all_raw_employees[idx].update({
                                    k: v for k, v in top_match.items() 
                                    if v and not all_raw_employees[idx].get(k)
                                })

            # Step 5: Clean, deduplicate, and normalize the merged results
            logger.info(f"DEBUG: all_raw_employees count: {len(all_raw_employees)}")
            logger.info(f"Cleaning {len(all_raw_employees)} merged employee records.")
            cleaned_employees = self.clean_agent.clean(all_raw_employees)


            # Step 6: Wrap and return standardized structured response format
            logger.info(f"Successfully processed {len(cleaned_employees)} unique employee records.")
            return {
                "status": "success",
                "total_count": len(cleaned_employees),
                "employees": cleaned_employees
            }

        except (InvalidURLError, SSRFViolationError) as e:
            logger.error(f"Input Validation Error: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
        except Exception as e:
            logger.exception(f"Unexpected orchestration error: {e}")
            return {
                "status": "error",
                "message": "An internal unexpected error occurred during the extraction workflow."
            }
