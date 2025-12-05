import re
from typing import Dict, Optional

class ContactExtractor:
    """
    Extracts contact information (email, phone, website) from text descriptions.
    """
    
    # Regex patterns
    EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    PHONE_PATTERN = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    URL_PATTERN = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*'
    
    @staticmethod
    def extract(text: str) -> Dict[str, Optional[str]]:
        if not text:
            return {"email": None, "phone": None, "website": None}
            
        info = {
            "email": None,
            "phone": None,
            "website": None
        }
        
        # Extract Email
        emails = re.findall(ContactExtractor.EMAIL_PATTERN, text)
        if emails:
            # Filter out common false positives or generic emails if needed
            info["email"] = emails[0]
            
        # Extract Phone
        phones = re.findall(ContactExtractor.PHONE_PATTERN, text)
        if phones:
            info["phone"] = phones[0]
            
        # Extract Website
        urls = re.findall(ContactExtractor.URL_PATTERN, text)
        if urls:
            # Filter out common non-shelter URLs (like facebook, petfinder, etc if desired, but for now keep first)
            # Maybe prioritize non-social media links
            shelter_url = None
            for url in urls:
                if "facebook.com" not in url and "twitter.com" not in url and "instagram.com" not in url:
                    shelter_url = url
                    break
            
            info["website"] = shelter_url if shelter_url else urls[0]
            
        return info
