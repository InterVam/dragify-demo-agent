# Dragify AI Agent Dashboard Setup

## Overview
This is a comprehensive real estate lead processing system with a React frontend dashboard and FastAPI backend.

## Features
- **OAuth Integration**: Connect Slack, Zoho CRM, and Gmail
- **Lead Processing**: Automated lead extraction, enrichment, and CRM insertion
- **Email Notifications**: Automated email notifications via Gmail
- **Dashboard**: Real-time monitoring of lead processing and system status

## Quick Start

### 1. Environment Setup
Create a `.env` file in the root directory with the following variables:

```env
# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=mydb

# Slack Configuration
SLACK_SIGNING_SECRET=your_slack_signing_secret_here
SLACK_CLIENT_ID=your_slack_client_id_here
SLACK_CLIENT_SECRET=your_slack_client_secret_here
SLACK_REDIRECT_URI=http://localhost:8000/slack/oauth/callback

# Groq LLM Configuration
GROQ_API_KEY=your_groq_api_key_here

# Zoho CRM Configuration
ZOHO_CLIENT_ID=your_zoho_client_id_here
ZOHO_CLIENT_SECRET=your_zoho_client_secret_here
ZOHO_REDIRECT_URI=http://localhost:8000/zoho/oauth/callback

# Gmail Configuration
GMAIL_CLIENT_ID=your_gmail_client_id_here
GMAIL_CLIENT_SECRET=your_gmail_client_secret_here
GMAIL_REDIRECT_URI=http://localhost:8000/gmail/oauth/callback
ADMIN_EMAIL=your_admin_email@example.com
FROM_EMAIL=your_from_email@example.com
```

### 2. Start the Application
```bash
# Start all services (backend, frontend, database)
docker-compose up --build

# Or start in detached mode
docker-compose up --build -d
```

### 3. Access the Application
- **Frontend Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Services

### Frontend (Port 3000)
- React + Next.js + TailwindCSS
- OAuth integration buttons
- Real-time lead processing logs
- System status monitoring

### Backend (Port 8000)
- FastAPI with async support
- LangChain agent orchestration
- OAuth integrations (Slack, Zoho, Gmail)
- PostgreSQL database integration

### Database (Port 5432)
- PostgreSQL 15
- Automatic migrations
- Lead and integration data storage

## OAuth Setup

### Slack App
1. Create a Slack app at https://api.slack.com/apps
2. Add OAuth scopes: `app_mentions:read`, `channels:history`, `chat:write`, `im:history`, `im:read`, `im:write`
3. Set redirect URI: `http://localhost:8000/slack/oauth/callback`

### Zoho CRM
1. Create a Zoho app at https://api-console.zoho.com/
2. Add CRM scope: `ZohoCRM.modules.ALL`
3. Set redirect URI: `http://localhost:8000/zoho/oauth/callback`

### Gmail API
1. Create a Google Cloud project
2. Enable Gmail API
3. Create OAuth 2.0 credentials
4. Set redirect URI: `http://localhost:8000/gmail/oauth/callback`

## Usage

1. **Connect Integrations**: Use the OAuth buttons in the dashboard to connect Slack, Zoho, and Gmail
2. **Send Test Message**: Send a lead message in your connected Slack channel
3. **Monitor Processing**: Watch the dashboard for real-time lead processing updates
4. **Check Email**: Verify email notifications are sent via Gmail

## Development

### Backend Development
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

## Troubleshooting

### Common Issues
1. **OAuth Errors**: Check redirect URIs match exactly
2. **Database Connection**: Ensure PostgreSQL is running
3. **API Errors**: Check environment variables are set correctly
4. **CORS Issues**: Verify frontend URL is allowed in backend CORS settings

### Logs
```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs postgres
``` 