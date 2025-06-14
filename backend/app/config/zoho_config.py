# app/config/zoho_config.py

import os
from dotenv import load_dotenv

load_dotenv()

class ZohoConfig:
    CLIENT_ID = os.getenv("ZOHO_CLIENT_ID", "")
    CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET", "")
    REDIRECT_URI = os.getenv("ZOHO_REDIRECT_URI", "http://localhost:8000/zoho/oauth/callback")

    @property
    def client_id(self):
        return self.CLIENT_ID
    
    @property
    def client_secret(self):
        return self.CLIENT_SECRET
    
    @property
    def redirect_uri(self):
        return self.REDIRECT_URI

    @classmethod
    def validate(cls):
        missing = [
            key for key in ["CLIENT_ID", "CLIENT_SECRET", "REDIRECT_URI"]
            if not getattr(cls, key)
        ]
        if missing:
            raise ValueError(f"Missing Zoho config values: {', '.join(missing)}")
    
    @classmethod
    def is_configured(cls):
        """Check if Zoho is properly configured without raising an exception"""
        return bool(cls.CLIENT_ID and cls.CLIENT_SECRET and cls.REDIRECT_URI)

# Only validate if we're trying to use Zoho (don't fail on import)
# ZohoConfig.validate()
