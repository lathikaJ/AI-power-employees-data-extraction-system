# Backend Architecture

## 1. Architecture Overview

Client → API → Input Module → Crawl Module → AI Extraction Module → Clean Module → Output Module

---

## 2. Modules

### 2.1 Input Module
- Validate URL
- Prevent SSRF
- Normalize domain

### 2.2 Crawl Module
- Fetch HTML pages
- Target:
  - /team
  - /about
  - /people
  - /leadership
- Use async crawling

### 2.3 AI Extraction Module
Uses LLM to extract structured data.

Example Prompt:
-------------------------------------
Extract employee details from the following HTML.
Return JSON format:
[
  {
    "name": "",
    "designation": "",
    "email": "",
    "phone": "",
    "linkedin": "",
    "department": ""
  }
]
-------------------------------------

### 2.4 Clean Module
- Remove duplicates
- Validate emails
- Normalize phone numbers
- Remove invalid entries

### 2.5 Output Module
- Return JSON response
- Convert to CSV
- Send response to frontend

---

## 3. API Endpoint

POST /api/v1/extract

Request:
{
  "url": "https://example.com"
}

Response:
{
  "status": "success",
  "total_count": 10,
  "employees": [...]
}