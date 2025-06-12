import os
from slack_sdk import WebClient
from slack_sdk.signature import SignatureVerifier

class SlackConfig:
    def __init__(self):
        self.bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.signing_secret = os.getenv("SLACK_SIGNING_SECRET")
        self.client_id = os.getenv("SLACK_CLIENT_ID")
        self.client_secret = os.getenv("SLACK_CLIENT_SECRET")
        self.redirect_uri = os.getenv("SLACK_REDIRECT_URI")

        self._validate_env_vars()

        self.client = WebClient(token=self.bot_token)
        self.signature_verifier = SignatureVerifier(self.signing_secret)

    def _validate_env_vars(self):
        missing = []
        if not self.bot_token: missing.append("SLACK_BOT_TOKEN")
        if not self.signing_secret: missing.append("SLACK_SIGNING_SECRET")
        if not self.client_id: missing.append("SLACK_CLIENT_ID")
        if not self.client_secret: missing.append("SLACK_CLIENT_SECRET")
        if not self.redirect_uri: missing.append("SLACK_REDIRECT_URI")

        if missing:
            raise ValueError(f"Missing Slack environment variables: {', '.join(missing)}")
