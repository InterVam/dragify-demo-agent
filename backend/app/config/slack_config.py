import os
from dotenv import load_dotenv

load_dotenv()

class SlackConfig:
    SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
    CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
    CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
    REDIRECT_URI = os.getenv("SLACK_REDIRECT_URI")

    @classmethod
    def validate(cls):
        missing = [
            key for key in ["SIGNING_SECRET", "CLIENT_ID", "CLIENT_SECRET", "REDIRECT_URI"]
            if not getattr(cls, key)
        ]
        if missing:
            raise ValueError(f"Missing Slack config values: {', '.join(missing)}")

# Validate on import
SlackConfig.validate()
