from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class ExtractRequest(BaseModel):
    url: str

class EmployeeOutput(BaseModel):
    name: Optional[str] = None
    designation: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    department: Optional[str] = None

class ExtractResponse(BaseModel):
    status: str
    total_count: int
    employees: List[EmployeeOutput]
