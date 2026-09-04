import re
import requests
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class BaseExtractor(ABC):
    """Base class for all coding platform extractors."""

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9'
    }

    TIMEOUT = 10

    @classmethod
    def extract_username(cls, url_or_handle: str, platform: str = '') -> str:
        """Extract sanitized username from handle or full profile URL."""
        if not url_or_handle:
            return ""
        
        text = str(url_or_handle).strip()
        
        # Remove trailing slash
        text = text.rstrip('/')
        
        patterns = {
            'leetcode': r'(?:https?:\/\/)?(?:www\.)?leetcode\.com\/(?:u\/)?([A-Za-z0-9_-]+)',
            'codechef': r'(?:https?:\/\/)?(?:www\.)?codechef\.com\/users\/([A-Za-z0-9_]+)',
            'codeforces': r'(?:https?:\/\/)?(?:www\.)?codeforces\.com\/profile\/([A-Za-z0-9_.-]+)',
            'github': r'(?:https?:\/\/)?(?:www\.)?github\.com\/([A-Za-z0-9_-]+)',
            'hackerrank': r'(?:https?:\/\/)?(?:www\.)?hackerrank\.com\/(?:profile\/)?([A-Za-z0-9_.-]+)',
            'gfg': r'(?:https?:\/\/)?(?:www\.)?geeksforgeeks\.org\/user\/([A-Za-z0-9_.-]+)',
            'atcoder': r'(?:https?:\/\/)?(?:www\.)?atcoder\.jp\/users\/([A-Za-z0-9_]+)',
            'interviewbit': r'(?:https?:\/\/)?(?:www\.)?interviewbit\.com\/profile\/([A-Za-z0-9_-]+)',
            'kaggle': r'(?:https?:\/\/)?(?:www\.)?kaggle\.com\/([A-Za-z0-9_.-]+)',
            'codingninjas': r'(?:https?:\/\/)?(?:www\.)?naukri\.com\/code360\/profile\/([A-Za-z0-9_-]+)'
        }
        
        if platform and platform in patterns:
            match = re.search(patterns[platform], text, re.IGNORECASE)
            if match:
                return match.group(1)
                
        # Generic url check if not matched above
        if 'http://' in text or 'https://' in text:
            # Check all known platform patterns
            for p_name, p_pattern in patterns.items():
                m = re.search(p_pattern, text, re.IGNORECASE)
                if m:
                    return m.group(1)
            # Fallback to last segment of URL path
            parts = text.split('/')
            return parts[-1] if parts[-1] else (parts[-2] if len(parts) > 1 else text)
            
        # Clean plain username of any @ or whitespace
        return text.lstrip('@').strip()

    @abstractmethod
    def extract(self, url_or_handle: str) -> Optional[Any]:
        """Extract metrics from the platform."""
        pass
