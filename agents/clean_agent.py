import re
from typing import List, Dict, Any

class CleanAgent:
    """
    Agent responsible for cleaning, normalizing, and deduplicating
    extracted employee data.
    """
    def __init__(self):
        # Basic regex for email validation
        self.email_regex = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")
        # Regex for phone normalization (keeps only digits and the '+' sign)
        self.phone_regex = re.compile(r"[^\d\+]")

    def clean(self, employees: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Cleans the list of extracted employees by:
        - Removing empty entries
        - Validating email formats
        - Normalizing phone numbers
        - Removing duplicates based on email or name
        
        Args:
            employees (List[Dict[str, Any]]): Raw list of employee dictionaries.
            
        Returns:
            List[Dict[str, Any]]: Cleaned and deduplicated list of employees.
        """
        cleaned_list = []
        seen_emails = set()
        seen_names = set()

        for emp in employees:
            # Safely extract and strip core identifiers
            name = str(emp.get("name") or "").strip()
            email = str(emp.get("email") or "").strip()
            
            # 1. Remove empty entries
            # If both name and email are empty, it's considered an empty/invalid entry
            if not name and not email:
                continue
                
            # 2. Validate email format
            if email and not self.email_regex.match(email):
                email = ""  # Clear invalid emails instead of discarding the whole entry
            
            # 3. Remove duplicate employees
            email_key = email.lower() if email else None
            name_key = name.lower() if name else None
            
            # If the email is known, it's a duplicate
            if email_key and email_key in seen_emails:
                continue
            
            # If the name is known, it's a duplicate
            if name_key and name_key in seen_names:
                continue
                
            # Add to seen sets to prevent future duplicates
            if email_key:
                seen_emails.add(email_key)
            if name_key:
                seen_names.add(name_key)
                
            # 4. Normalize phone numbers
            phone = str(emp.get("phone") or "").strip()
            if phone:
                normalized_phone = self.phone_regex.sub("", phone)
                emp["phone"] = normalized_phone if normalized_phone else None
            else:
                emp["phone"] = None
                
            # Update the cleaned values
            emp["name"] = name if name else None
            emp["email"] = email if email else None
            
            # Clean up remaining fields (strip strings, convert empty to None)
            for k, v in emp.items():
                if k not in ("name", "email", "phone"):
                    if isinstance(v, str):
                        emp[k] = v.strip() if v.strip() else None
                        
            cleaned_list.append(emp)
            
        return cleaned_list
