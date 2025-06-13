import os
from dotenv import load_dotenv

load_dotenv()

class ZohoConfig:
    CLIENT_ID: str = os.getenv("ZOHO_CLIENT_ID", "")
    CLIENT_SECRET: str = os.getenv("ZOHO_CLIENT_SECRET", "")
    REDIRECT_URI: str = os.getenv("ZOHO_REDIRECT_URI", "http://localhost:8000/zoho/oauth/callback")

zoho_config = ZohoConfig()
