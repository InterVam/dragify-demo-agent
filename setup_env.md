# Environment Variables Setup

## Required Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=mydb

# Zoho CRM Configuration (REQUIRED for CRM integration)
ZOHO_CLIENT_ID=1000.8CJ9QKG8K8TZKUUX5AU6VSPTMR6JFH
ZOHO_CLIENT_SECRET=d75fd06b8954d31954a1589af7aed60ed6f63c3b94
ZOHO_REDIRECT_URI=https://your-ngrok-url.ngrok.io/zoho/oauth/callback

# Slack Configuration (REQUIRED for Slack integration)
SLACK_SIGNING_SECRET=your_slack_signing_secret
SLACK_CLIENT_ID=your_slack_client_id
SLACK_CLIENT_SECRET=your_slack_client_secret
SLACK_REDIRECT_URI=https://your-ngrok-url.ngrok.io/slack/oauth/callback

# Gmail Configuration (REQUIRED for email notifications)
GMAIL_CLIENT_ID=your_gmail_client_id
GMAIL_CLIENT_SECRET=your_gmail_client_secret
GMAIL_REDIRECT_URI=https://your-ngrok-url.ngrok.io/gmail/oauth/callback
ADMIN_EMAIL=your_admin_email@gmail.com
FROM_EMAIL=your_from_email@gmail.com

# Groq API Key (REQUIRED for AI processing)
GROQ_API_KEY=your_groq_api_key
```

## Quick Setup

1. **Copy the template:**
   ```bash
   cp setup_env.md .env
   ```

2. **Update your ngrok URL:**
   Replace `https://your-ngrok-url.ngrok.io` with your actual ngrok URL

3. **Add your API keys:**
   - Get Slack credentials from https://api.slack.com/apps
   - Get Gmail credentials from https://console.cloud.google.com/
   - Get Groq API key from https://console.groq.com/

4. **Restart the backend:**
   ```bash
   docker-compose restart backend
   ```

## Notes

- The `.env` file is gitignored for security
- Zoho credentials are already configured for the demo
- Update redirect URIs when your ngrok URL changes
- All integrations will show "not configured" until environment variables are set 