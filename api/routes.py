import logging
from fastapi import APIRouter, HTTPException, status, Request
from pydantic import ValidationError
from slowapi import Limiter
from slowapi.util import get_remote_address

from models.schemas import ExtractRequest, ExtractResponse
from services.extraction_service import ExtractionService

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Instantiate the service
extraction_service = ExtractionService()

@router.post("/extract", response_model=ExtractResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def extract_employee_data(request: Request, extract_request: ExtractRequest):
    """
    Endpoint to trigger the employee extraction pipeline.
    Accepts a URL, crawls target pages, uses AI to extract structured employee data,
    cleans duplicates/invalid entries, and returns a unified JSON payload.
    """
    logger.info(f"Received extraction request for URL: {extract_request.url}")
    
    try:
        # Execute the orchestrator
        result = await extraction_service.execute_extraction(extract_request.url)

        # The service returns a dict mapping. If status is error, raise HTTPException here
        if result.get("status") == "error":
            logger.warning(f"Extraction failed with error from service: {result.get('message')}")
            if "Unexpected" in result.get("message", "") or "internal" in result.get("message", "").lower():
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("message")
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.get("message", "Invalid URL or blocked request.")
                )

        # Log success metrics matching returned count
        logger.info(f"Returning {result.get('total_count', 0)} employees for {extract_request.url}")
        
        return result

    except HTTPException as http_exc:
        # Re-raise intended HTTP errors
        raise http_exc
    except Exception as e:
        # Catch unexpected pipeline failures
        logger.exception(f"Unexpected error while processing /extract for {extract_request.url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during extraction."
        )
