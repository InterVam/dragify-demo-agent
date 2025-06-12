# Dragify Demo Agent

A LangChain-powered AI agent that processes unstructured Slack messages to extract lead information and manage demo requests.

## Features

- Slack integration with OAuth 2.0
- LangChain agent with Google's Gemini Pro for natural language processing
- Lead extraction from unstructured messages
- CRM integration (mock or real)
- Email notifications
- Event logging and tracking

## Setup

### Prerequisites

- Python 3.8+
- PostgreSQL
- Slack App credentials
- Google API key (for Gemini)

### Environment Variables

Create a `.env` file in the `backend` directory with:

```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost/dragify

# Slack
SLACK_CLIENT_ID=your_client_id
SLACK_CLIENT_SECRET=your_client_secret
SLACK_SIGNING_SECRET=your_signing_secret
SLACK_REDIRECT_URI=http://localhost:8000/slack/oauth/callback

# Google
GOOGLE_API_KEY=your_google_api_key

# JWT
JWT_SECRET=your_jwt_secret
JWT_ALGORITHM=HS256
```

### Installation

1. Clone the repository
2. Set up the backend:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

3. Set up the database:
```bash
# Create PostgreSQL database
createdb dragify

# Run migrations (when implemented)
alembic upgrade head
```

4. Start the backend:
```bash
uvicorn app.main:app --reload
```

### Slack App Setup

1. Create a new Slack app at https://api.slack.com/apps
2. Enable OAuth & Permissions
3. Add the following scopes:
   - chat:write
   - channels:read
   - channels:history
   - commands
4. Set up Event Subscriptions:
   - Enable events
   - Add your endpoint URL (e.g., http://localhost:8000/slack/events)
   - Subscribe to bot events: message.channels
5. Install the app to your workspace

### Google API Setup

1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Add the API key to your .env file as GOOGLE_API_KEY

## Development

### Project Structure

```
dragify-demo-agent/
├── backend/
│   ├── app/
│   │   ├── agent/          # LangChain agent and tools
│   │   ├── api/            # FastAPI routes
│   │   ├── services/       # External service integrations
│   │   └── db/             # Database models and connection
│   ├── requirements.txt
│   └── .env
└── frontend/               # React frontend (coming soon)
```

### Running Tests

```bash
pytest
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 