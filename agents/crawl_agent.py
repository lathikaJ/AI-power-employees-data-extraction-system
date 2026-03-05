import asyncio
import httpx
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class CrawlAgent:
    """
    Agent responsible for crawling predefined paths of a given validated URL
    using asynchronous HTTP requests to retrieve raw HTML content.
    Does NOT contain AI extraction logic.
    """
    def __init__(self, timeout: int = 15, max_concurrent: int = 3, retries: int = 2):
        """
        Initializes the CrawlAgent.
        
        Args:
            timeout (int): Request timeout in seconds.
            max_concurrent (int): Maximum number of concurrent requests allowed.
            retries (int): Number of retries for failing requests.
        """
        self.target_paths = [
            "/",
            "/about",
            "/about-us",
            "/team",
            "/our-team"
        ]
        self.timeout = timeout
        self.retries = retries
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def _fetch_page(self, client: httpx.AsyncClient, base_url: str, path: str) -> Optional[str]:
        """
        Asynchronously fetches a single page with semaphores, retries, and timeout handling.
        
        Args:
            client (httpx.AsyncClient): The HTTPX client.
            base_url (str): The base URL.
            path (str): The specific path to fetch.
            
        Returns:
            Optional[str]: The raw HTML text if successful and 200 OK, else None.
        """
        url = urljoin(base_url, path)
        
        async with self.semaphore:
            for attempt in range(1, self.retries + 2):
                try:
                    logger.info(f"Fetching: {url} (Attempt {attempt})")
                    # Provide an explicit timeout control alongside the client's timeout scope
                    response = await client.get(url, timeout=self.timeout)
                    
                    if response.status_code == 200:
                        logger.info(f"Successfully fetched: {url}")
                        return response.text
                    else:
                        logger.warning(f"Failed to fetch {url} (Attempt {attempt}): Status code {response.status_code}")
                        
                        # Stop retrying if we hit a 404 since it likely inherently doesn't exist
                        if response.status_code == 404:
                            break
                            
                except httpx.TimeoutException:
                    logger.warning(f"Timeout while fetching {url} (Attempt {attempt})")
                except httpx.RequestError as e:
                    logger.warning(f"Request error while fetching {url} (Attempt {attempt}): {e}")
                    
                if attempt <= self.retries:
                    await asyncio.sleep(2 ** attempt) # Exponential backoff
                    
    async def _check_robots(self, client: httpx.AsyncClient, base_url: str) -> RobotFileParser:
        """
        Asynchronously fetches and parses the destination's robots.txt file.
        
        Args:
            client (httpx.AsyncClient): The HTTPX client.
            base_url (str): The base URL.
            
        Returns:
            RobotFileParser: A populated or open-allowed RobotFileParser instance.
        """
        rp = RobotFileParser()
        robots_url = urljoin(base_url, "/robots.txt")
        try:
            response = await client.get(robots_url, timeout=self.timeout)
            if response.status_code == 200:
                rp.parse(response.text.splitlines())
            else:
                setattr(rp, 'allow_all', True)  # If it doesn't exist, we permit access
        except Exception as e:
            logger.warning(f"Could not fetch robots.txt for {base_url}: {e}. Defaulting to allow all.")
            setattr(rp, 'allow_all', True)
        
        return rp

    async def crawl(self, validated_url: str) -> List[str]:
        """
        Crawls the predefined paths for the given validated URL concurrently utilizing gather.
        
        Args:
            validated_url (str): The valid URL to crawl.
            
        Returns:
            List[str]: A list of raw HTML strings from the successful requests.
        """
        if not validated_url.endswith('/'):
            validated_url += '/'

        html_pages: List[str] = []

        timeout_config = httpx.Timeout(self.timeout)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        async with httpx.AsyncClient(timeout=timeout_config, headers=headers, follow_redirects=True) as client:
            
            tasks = []
            # Always crawl the exact validated URL itself first
            tasks.append(self._fetch_page(client, validated_url, ""))
            
            # Only crawl default target paths if the user provided a root-like domain URL
            # This avoids noise when the user gives a specific deep link like /about/leadership
            path_parts = [p for p in urlparse(validated_url).path.split('/') if p]
            if len(path_parts) <= 1:
                logger.info(f"Root-like domain detected. Crawling default target paths: {self.target_paths}")
                for path in self.target_paths:
                    # Avoid duplicated crawl of the root if it's already done
                    if path != "/":
                        tasks.append(self._fetch_page(client, validated_url, path))
            else:
                logger.info(f"Deep link detected ({validated_url}). Skipping sub-path crawling to stay focused.")
            
            if not tasks:
                logger.info(f"No valid paths allowed for {validated_url}")
                return []
            
            # Execute tasks resiliently via gather
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, str):
                    html_pages.append(result)

        return html_pages
