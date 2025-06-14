import os
from dotenv import load_dotenv

load_dotenv()

class GmailConfig:
    CLIENT_ID = os.getenv("GMAIL_CLIENT_ID", "")
    CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET", "")
    REDIRECT_URI = os.getenv("GMAIL_REDIRECT_URI", "http://localhost:8000/gmail/oauth/callback")
    
    # Gmail-specific scopes - including openid to match Google's response
    SCOPES = [
        'openid',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/userinfo.email'
    ]
    
    # Default notification settings
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
    FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@dragify.com")

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
            raise ValueError(f"Missing Gmail config values: {', '.join(missing)}")

# Validate on import - COMMENTED OUT to allow backend to start
# GmailConfig.validate() 