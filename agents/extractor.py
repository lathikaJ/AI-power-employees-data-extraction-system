import json
import re
import logging
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from pydantic import BaseModel, ValidationError, Field
import openai
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Pydantic schemas for structured extraction validation
class EmployeeExtraction(BaseModel):
    name: str | None = None
    designation: str | None = Field(default=None, alias="title")
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    instagram: str | None = None
    profile_url: str | None = None
    department: str | None = None

    class Config:
        populate_by_name = True
        extra = "allow" # Allow extra fields like 'title' if not aliased correctly

class ExtractionResponse(BaseModel):
    employees: List[EmployeeExtraction]

# Prompt template
PROMPT_TEMPLATE = """
Extract all available employee details from the provided text.
Look for names, job titles, email addresses, phone numbers, LinkedIn profiles, Instagram profiles, and individual bio/profile page URLs.

Return a precise JSON object with exactly one key: "employees".
The value of "employees" must be a list of employee data objects.

Data Object Schema:
{{
  "name": "Full Name",
  "designation": "Job Title or Role",
  "email": "Email address if found (else null)",
  "phone": "Phone number if found (else null)",
  "linkedin": "LinkedIn profile URL if found (else null)",
  "instagram": "Instagram profile URL or handle if found (else null)",
  "profile_url": "URL to the individual employee's bio or full profile page if found (else null)",
  "department": "Department or Team name if found (else null)"
}}

Rules:
1. Only return valid JSON. No conversational text.
2. If multiple employees are found, include them all.
3. If no employees are found, return {{"employees": []}}.
4. Be accurate and do not hallucinate data.

Text Content:
-------------------
{html_content}
-------------------
"""

class AIExtractionAgent:
    """
    Agent responsible for safely taking raw HTML and using a Large Language
    Model (via OpenAI API) to pull out structured employee records as JSON.
    """
    def __init__(self, api_key: str, model: str = "openrouter/free"):
        """
        Initializes the AI Extraction Agent.
        
        Args:
            api_key (str): OpenRouter API Key.
            model (str): The OpenRouter model to use.
        """
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/infynd/employee-scraper",
                "X-Title": "Employee Data Scraper"
            }
        )
        self.model = model

    def _clean_html_for_llm(self, raw_html: str) -> str:
        """
        Strips massive unnecessary DOM elements with granular logging for debugging.
        """
        logger.info(f"Cleaning HTML. Initial length: {len(raw_html)}")
        soup = BeautifulSoup(raw_html, "html.parser")
        
        # Remove noisy non-content tags
        for tag in soup(["script", "style", "meta", "noscript", "svg", "path", "head"]):
            tag.decompose()
        logger.info("Decomposed boilerplate tags (style, meta, svg, etc.)")

        # Transform <a> tags into Markdown-like links so the LLM sees the href
        for a in soup.find_all("a", href=True):
            link_text = a.get_text(strip=True)
            # If link text is empty, try title or aria-label
            if not link_text:
                link_text = a.get("title") or a.get("aria-label") or ""
                
            href = a["href"]
            
            # Check for social or contact links
            is_social = False
            for domain in ["linkedin", "instagram", "twitter", "facebook"]:
                if domain in href.lower():
                    is_social = True
                    if not link_text:
                        link_text = domain
                    break
            
            if is_social or any(scheme in href.lower() for scheme in ["mailto:", "tel:"]):
                if not link_text:
                    link_text = "contact"
                a.replace_with(f" [Link: {link_text} ({href})] ")
            else:
                if any(p in href.lower() for p in ["/leadership/", "/team/", "/people/", "/person/"]):
                    a.replace_with(f" [Profile: {link_text} ({href})] ")
                else:
                    a.replace_with(link_text)
            
        cleaned_text = soup.get_text(separator=" ", strip=True)
        # Collapse multiple spaces
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        logger.info(f"Final cleaned text length: {len(cleaned_text)}")
        return cleaned_text

    async def extract_employees(self, raw_html: str) -> List[Dict[str, Any]]:
        """
        Processes a raw HTML string through OpenAI, forcing a JSON object
        response, parsing the JSON, validating via Pydantic, and returning
        the sanitized list of employees.
        
        Args:
            raw_html (str): The raw HTML string.
            
        Returns:
            List[Dict[str, Any]]: Validated list of employee dicts.
        """
        if not raw_html or not raw_html.strip():
            logger.warning("Empty HTML string provided. Skipping extraction.")
            return []

        # Minimize token usage by stripping the raw HTML down
        minimized_content = self._clean_html_for_llm(raw_html)
        logger.info(f"Minimized HTML extraction payload: {len(minimized_content)} characters.")
        
        # Guard rail against pages with no readable text after DOM stripping
        if not minimized_content:
            return []

        # TRUNCATE to 5000 characters for high precision
        if len(minimized_content) > 5000:
            logger.warning(f"Payload too large ({len(minimized_content)}). Truncating to 5k for accuracy.")
        minimized_content = minimized_content[:5000]

        # Schema nudge to include social links
        prompt = f"List persons as JSON (name, title, profile_url, linkedin, instagram):\n\n{minimized_content}"

        for attempt in range(4):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=3000
                )
                
                content = response.choices[0].message.content
                if not content:
                    logger.error("OpenAI returned an empty response.")
                    await asyncio.sleep(3)
                    continue

                # Clean up the output in case it is wrapped in markdown code blocks or has a preamble

                # Layer 1: Try to find a JSON block with regex
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if not json_match:
                    json_match = re.search(r'(\{.*?\})', content, re.DOTALL)
                
                if json_match:
                    json_str = json_match.group(1).strip()
                else:
                    json_str = content.strip()

                # Step 1: Parse the string into JSON
                parsed_json = json.loads(json_str)
                
                # Normalize if current model returned a raw list
                if isinstance(parsed_json, list):
                    parsed_json = {"employees": parsed_json}
                elif isinstance(parsed_json, dict) and "employees" not in parsed_json:
                    parsed_json = {"employees": [parsed_json]}

                # Step 2: Validate the parsed JSON strictly using Pydantic
                validated_data = ExtractionResponse(**parsed_json)
                
                # Filter placeholders
                final_list = []
                for emp in validated_data.employees:
                    name_str = (emp.name or "").lower()
                    if not name_str or any(p in name_str for p in ["not specified", "person name", "placeholder"]):
                        continue
                    final_list.append(emp.model_dump())
                return final_list

            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON from OpenAI response (Attempt {attempt+1}): {e}")
                # Continue loop to try generating valid JSON again
                await asyncio.sleep(2)
                continue
            except ValidationError as e:
                logger.error(f"Validation error for extracted data (Attempt {attempt+1}): {e}")
                # Continue loop to try generating valid structure again
                await asyncio.sleep(2)
                continue
            except Exception as e:
                # Handle Rate Limits and general Provider Errors by retrying
                wait_time = (attempt + 1) * 5 
                logger.warning(f"Error during AI extraction: {e}. Waiting {wait_time}s... (Attempt {attempt+1}/4)")
                await asyncio.sleep(wait_time)
                if attempt == 3:
                    logger.error(f"Failed after 4 attempts due to error: {e}")
                    return []
                continue

        return []
