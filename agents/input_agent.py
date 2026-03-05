import socket
import ipaddress
import logging
from urllib.parse import urlparse
from pydantic import HttpUrl, TypeAdapter, ValidationError

logger = logging.getLogger(__name__)

class SSRFViolationError(Exception):
    """Exception raised for SSRF attack attempts where a domain points to a blocked IP."""
    pass

class InvalidURLError(Exception):
    """Exception raised for poorly formatted or unresolvable URLs."""
    pass

class InputAgent:
    """
    Agent responsible for input handling, specifically validating URLs and preventing SSRF.
    Does NOT contain crawling logic.
    """
    def __init__(self):
        # Using Pydantic V2's TypeAdapter for HttpUrl validation
        self.url_validator = TypeAdapter(HttpUrl)

    def validate_and_normalize_url(self, url: str) -> str:
        """
        Validates the URL using Pydantic, checks for SSRF (blocking local IPs), 
        and returns the normalized URL.
        
        Args:
            url (str): The raw input URL string.
            
        Returns:
            str: The normalized URL string.
            
        Raises:
            InvalidURLError: If the URL is incorrectly formatted or unresolvable.
            SSRFViolationError: If the URL resolves to a local, private, or restricted IP.
        """
        # 1. Validate structure using Pydantic HttpUrl
        try:
            validated_url = self.url_validator.validate_python(url)
        except ValidationError as e:
            raise InvalidURLError(f"Invalid URL format: {e}")

        # Convert to string to get normalized URL
        normalized_url = str(validated_url)
        
        # 2. Extract hostname
        parsed_url = urlparse(normalized_url)
        hostname = parsed_url.hostname
        
        if not hostname:
            raise InvalidURLError("Hostname could not be extracted from the URL.")

        # 3. Resolve IP address to check for SSRF
        try:
            ip_address_str = socket.gethostbyname(hostname)
        except socket.gaierror:
            logger.warning(f"Suspicious input: Could not resolve hostname for {hostname}")
            raise InvalidURLError(f"Could not resolve hostname: {hostname}")

        # 4. Check against local / private / reserved IP addresses
        try:
            ip_obj = ipaddress.ip_address(ip_address_str)
        except ValueError:
            logger.warning(f"Suspicious input: Resolved IP address is invalid for {hostname}: {ip_address_str}")
            raise InvalidURLError(f"Resolved IP address is invalid: {ip_address_str}")

        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved or ip_obj.is_multicast:
            logger.warning(f"Suspicious input detected: SSRF attempt on {hostname} ({ip_address_str})")
            raise SSRFViolationError(
                f"SSRF Attempt Blocked: URL resolves to a restricted IP address ({ip_address_str})."
            )

        return normalized_url
