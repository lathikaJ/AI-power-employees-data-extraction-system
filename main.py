from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

app = FastAPI(
    title="AI-Powered Employee Data Extraction System",
    description="API for extracting employee data from company websites",
    version="1.0.0"
)

import logging
from api.routes import router as api_router

# Setup global logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Apply SlowAPI custom exception handler globally
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers from api module
app.include_router(api_router, prefix="/api/v1", tags=["Extraction"])
