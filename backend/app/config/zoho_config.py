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

# Validate on import
ZohoConfig.validate()
