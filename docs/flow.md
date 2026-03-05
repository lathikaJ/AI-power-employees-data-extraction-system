# System Flow

## Step 1: User Input
User enters:
https://companywebsite.com

---

## Step 2: Validation
- Validate URL format
- Prevent local IP access
- DNS resolution check

---

## Step 3: Crawling
- Identify relevant pages
- Download HTML content

---

## Step 4: AI Extraction
- Send HTML to AI model
- Extract structured employee data

Example Output:
[
  {
    "name": "John Doe",
    "designation": "CTO",
    "email": "john@example.com",
    "phone": "+1-123456789"
  }
]

---

## Step 5: Data Cleaning
- Remove duplicates
- Validate fields
- Normalize formats

---

## Step 6: Output
- Display table on frontend
- Provide CSV download

---

## Step 7: Logging
- Execution time
- Extraction accuracy
- Error handling