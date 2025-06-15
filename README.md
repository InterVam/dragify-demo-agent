# Dragify AI Agent - Real Estate Lead Processing System

A comprehensive AI-powered agent that automates real estate lead processing workflows using LangChain, FastAPI, and React. The system processes Slack messages to extract lead information, matches them with available properties from a PostgreSQL database, inserts leads into Zoho CRM, and sends email notifications.

## 🚀 Live Demo

- **Frontend Dashboard**: https://dragify-demo-agent.vercel.app/
- **API Documentation**: Available when backend is running at `/docs`

## 🏗️ Architecture Overview

### Core Components
1. **Trigger System**: Slack integration with real-time message processing
2. **Data Collection**: PostgreSQL database with property/project data
3. **AI Agent**: LangChain-powered orchestrator with lead matching
4. **CRM Integration**: Zoho CRM for lead storage
5. **Notification System**: Gmail integration for status updates
6. **Multi-Team Support**: Complete team isolation and management

### 🔄 **Multi-Team Architecture**
The system supports multiple Slack teams with isolated data and configurations:
- **Teams Table**: Central team management with metadata
- **Foreign Key Relationships**: All integrations linked to specific teams
- **Team Selector**: Frontend dropdown for team switching
- **Isolated Data**: Leads, events, and integrations are team-specific

### Tech Stack
- **Backend**: FastAPI (Python) with async support
- **Frontend**: React + Next.js + TailwindCSS
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI/ML**: LangChain with Groq LLM integration
- **Authentication**: OAuth 2.0 for all integrations
- **Deployment**: Vercel (Frontend), Docker (Full stack)

## 🛠️ Setup Instructions

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.8+ (for local backend development)

### 1. Clone Repository
```bash
git clone <repository-url>
cd dragify-demo-agent
```

### 2. Environment Configuration

Create a `.env` file in the root directory:

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

# Groq LLM Configuration (for AI agent)
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

### 3. Start the Application

```bash
# Start all services (backend, frontend, database)
docker-compose up --build

# Or start in detached mode
docker-compose up --build -d
```

### 4. Expose Backend with ngrok (Required for OAuth & Webhooks)

For OAuth callbacks and Slack webhooks to work properly, your backend needs to be accessible from the internet. Use ngrok to expose your local backend:

#### Install ngrok
1. **Download ngrok**: https://ngrok.com/download
2. **Sign up** for a free account
3. **Install and authenticate**:
```bash
# Install ngrok (example for macOS)
brew install ngrok/ngrok/ngrok

# Or download and extract from website
# Authenticate with your token
ngrok config add-authtoken YOUR_NGROK_TOKEN
```

#### Expose Backend
```bash
# In a new terminal, expose port 8000
ngrok http 8000
```

You'll see output like:
```
Forwarding    https://abc123.ngrok-free.app -> http://localhost:8000
```

#### Update Environment Variables
Update your `.env` file with the ngrok URL:
```env
# Replace localhost URLs with your ngrok URL
SLACK_REDIRECT_URI=https://abc123.ngrok-free.app/slack/oauth/callback
ZOHO_REDIRECT_URI=https://abc123.ngrok-free.app/zoho/oauth/callback
GMAIL_REDIRECT_URI=https://abc123.ngrok-free.app/gmail/oauth/callback
```

#### Update Frontend Environment
Create `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=https://abc123.ngrok-free.app
```

### 5. Access the Application
- **Frontend Dashboard**: http://localhost:3000
- **Backend API**: https://abc123.ngrok-free.app (your ngrok URL)
- **API Documentation**: https://abc123.ngrok-free.app/docs
- **Database**: localhost:5432

## 🔐 OAuth Setup Guide

⚠️ **Important**: Use your ngrok URL (e.g., `https://abc123.ngrok-free.app`) instead of `localhost` for all OAuth configurations below.

### Slack App Configuration

1. **Create Slack App**
   - Go to https://api.slack.com/apps
   - Click "Create New App" → "From scratch"
   - Name your app and select your workspace

2. **OAuth & Permissions**
   - Navigate to "OAuth & Permissions"
   - Add Redirect URL: `https://abc123.ngrok-free.app/slack/oauth/callback` (use your ngrok URL)
   - Add Bot Token Scopes:
     - `app_mentions:read`
     - `channels:history`
     - `chat:write`
     - `im:history`
     - `im:read`
     - `im:write`

3. **Event Subscriptions**
   - Enable Events: ON
   - Request URL: `https://abc123.ngrok-free.app/slack/events` (use your ngrok URL)
   - Subscribe to bot events:
     - `app_mention`
     - `message.channels`
     - `message.im`

4. **Get Credentials**
   - Copy Client ID, Client Secret, and Signing Secret to your `.env` file

### Zoho CRM Configuration

1. **Create Zoho App**
   - Go to https://api-console.zoho.com/
   - Click "Add Client" → "Server-based Applications"
   - Fill in app details

2. **Configure OAuth**
   - Authorized Redirect URI: `https://abc123.ngrok-free.app/zoho/oauth/callback` (use your ngrok URL)
   - Scopes: `ZohoCRM.modules.ALL`

3. **Get Credentials**
   - Copy Client ID and Client Secret to your `.env` file

### Gmail API Configuration

1. **Google Cloud Console**
   - Go to https://console.cloud.google.com/
   - Create a new project or select existing
   - Enable Gmail API

2. **OAuth 2.0 Setup**
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
   - Application type: Web application
   - Authorized redirect URI: `https://abc123.ngrok-free.app/gmail/oauth/callback` (use your ngrok URL)

3. **Get Credentials**
   - Download the JSON file or copy Client ID and Client Secret to your `.env` file

### Groq API Setup

1. **Get API Key**
   - Go to https://console.groq.com/
   - Create account and generate API key
   - Add to your `.env` file as `GROQ_API_KEY`

## 📊 Database Setup & Data Population

### 🔄 Multi-Team Migration (Required for Multi-Team Support)

If you're upgrading from single-team to multi-team support, run this migration:

1. **Run the migration SQL**:
```bash
docker exec -i dragify-demo-agent-postgres-1 psql -U postgres -d mydb < backend/migrations/add_teams_table.sql
```

2. **Verify migration success**:
```bash
docker exec -it dragify-demo-agent-postgres-1 psql -U postgres -d mydb -c "
SELECT 
    t.team_id, 
    t.team_name, 
    t.is_active,
    CASE WHEN s.team_id IS NOT NULL THEN 'Yes' ELSE 'No' END as has_slack,
    CASE WHEN z.team_id IS NOT NULL THEN 'Yes' ELSE 'No' END as has_zoho,
    CASE WHEN g.team_id IS NOT NULL THEN 'Yes' ELSE 'No' END as has_gmail
FROM teams t
LEFT JOIN slack_installations s ON t.team_id = s.team_id
LEFT JOIN zoho_installations z ON t.team_id = z.team_id
LEFT JOIN gmail_installations g ON t.team_id = g.team_id
ORDER BY t.created_at DESC;
"
```

3. **Check foreign key constraints**:
```bash
docker exec -it dragify-demo-agent-postgres-1 psql -U postgres -d mydb -c "
SELECT 
    tc.table_name, 
    tc.constraint_name, 
    tc.constraint_type
FROM information_schema.table_constraints tc
WHERE tc.constraint_type = 'FOREIGN KEY' 
AND tc.table_name IN ('slack_installations', 'zoho_installations', 'gmail_installations', 'leads', 'event_logs')
ORDER BY tc.table_name;
"
```

### Populate Projects Table

The system needs property/project data to match against leads. Here's how to populate the database:

#### Method 1: Using Docker Exec (Recommended)

1. **Start the containers**:
```bash
docker-compose up -d
```

2. **Access PostgreSQL container**:
```bash
docker exec -it dragify-demo-agent-postgres-1 psql -U postgres -d mydb
```

3. **Insert sample property data**:
```sql
-- Insert sample real estate projects
INSERT INTO projects (name, location, property_type, bedrooms, min_budget, max_budget) VALUES
('Al Burouj Phase 3', 'Sheikh Zayed', 'apartment', 2, 3000000, 4500000),
('Swan Lake Phase 2', 'New Cairo', 'duplex', 3, 4500000, 6500000),
('Badya Phase 5', 'October', 'villa', 4, 7000000, 12000000),
('Compound 90', 'New Cairo', 'apartment', 1, 2000000, 3000000),
('Palm Hills October', 'October', 'townhouse', 3, 5000000, 8000000),
('Madinaty Residential', 'New Cairo', 'apartment', 2, 3500000, 5000000),
('Zayed Dunes', 'Sheikh Zayed', 'villa', 5, 8000000, 15000000),
('Mountain View Hyde Park', 'New Cairo', 'duplex', 3, 4000000, 6000000),
('Sodic West', 'Sheikh Zayed', 'townhouse', 4, 6000000, 9000000),
('Capital Gardens', 'New Capital', 'apartment', 2, 2500000, 4000000);

-- Verify data insertion
SELECT * FROM projects;
```

4. **Exit PostgreSQL**:
```sql
\q
```

#### Method 2: Using CSV File (Recommended)

The project includes a CSV file with real estate project data. Here's how to import it:

1. **Copy CSV file to PostgreSQL container**:
```bash
docker cp backend/app/data/projects3.csv dragify-demo-agent-postgres-1:/tmp/projects.csv
```

2. **Import CSV data using COPY command**:
```bash
docker exec -it dragify-demo-agent-postgres-1 psql -U postgres -d mydb -c "
COPY projects (name, location, min_budget, max_budget, bedrooms, bedrooms, property_type) 
FROM '/tmp/projects.csv' 
WITH (FORMAT csv, HEADER true, DELIMITER ',');
"
```

**Note**: The CSV has `min_price,max_price,min_bedrooms,max_bedrooms` but our table uses `min_budget,max_budget,bedrooms`. We'll use the average of min/max bedrooms for the bedrooms field.

3. **Alternative: Import with data transformation**:
```bash
docker exec -it dragify-demo-agent-postgres-1 psql -U postgres -d mydb -c "
CREATE TEMP TABLE temp_projects (
    name VARCHAR(255),
    location VARCHAR(255),
    min_price BIGINT,
    max_price BIGINT,
    min_bedrooms INTEGER,
    max_bedrooms INTEGER,
    property_type VARCHAR(100)
);

COPY temp_projects FROM '/tmp/projects.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

INSERT INTO projects (name, location, property_type, bedrooms, min_budget, max_budget)
SELECT 
    name,
    location,
    property_type,
    ROUND((min_bedrooms + max_bedrooms) / 2.0) as bedrooms,
    min_price as min_budget,
    max_price as max_budget
FROM temp_projects;

DROP TABLE temp_projects;
"
```

4. **Verify the import**:
```bash
docker exec -it dragify-demo-agent-postgres-1 psql -U postgres -d mydb -c "SELECT COUNT(*) FROM projects;"
```

#### Method 3: Using SQL File (Manual Data)

1. **Create a SQL file** (`sample_data.sql`):
```sql
INSERT INTO projects (name, location, property_type, bedrooms, min_budget, max_budget) VALUES
('Al Burouj Phase 3', 'Sheikh Zayed', 'apartment', 2, 3000000, 4500000),
('Swan Lake Phase 2', 'New Cairo', 'duplex', 3, 4500000, 6500000),
('Badya Phase 5', 'October', 'villa', 4, 7000000, 12000000),
('Compound 90', 'New Cairo', 'apartment', 1, 2000000, 3000000),
('Palm Hills October', 'October', 'townhouse', 3, 5000000, 8000000),
('Madinaty Residential', 'New Cairo', 'apartment', 2, 3500000, 5000000),
('Zayed Dunes', 'Sheikh Zayed', 'villa', 5, 8000000, 15000000),
('Mountain View Hyde Park', 'New Cairo', 'duplex', 3, 4000000, 6000000),
('Sodic West', 'Sheikh Zayed', 'townhouse', 4, 6000000, 9000000),
('Capital Gardens', 'New Capital', 'apartment', 2, 2500000, 4000000);
```

2. **Execute the SQL file**:
```bash
docker exec -i dragify-demo-agent-postgres-1 psql -U postgres -d mydb < sample_data.sql
```

### Database Schema

The system uses the following main tables:

```sql
-- Projects table (property listings)
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    property_type VARCHAR(100),
    bedrooms INTEGER,
    min_budget BIGINT,
    max_budget BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Event logs table (system activity tracking)
CREATE TABLE event_logs (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    team_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## 🚀 Usage Guide

### 1. Multi-Team Setup

The system now supports multiple Slack teams with isolated data and configurations:

1. **Access Dashboard**: https://dragify-demo-agent.vercel.app/
2. **Team Selection**: Use the dropdown in the header to select/switch teams
3. **Team Creation**: Teams are automatically created during OAuth flows
4. **Data Isolation**: Each team has separate leads, events, and integrations

### 2. Connect Integrations

1. **Select Team**: Choose your team from the dropdown (required)
2. **Connect Services**: Click OAuth buttons for Slack, Zoho, and Gmail
3. **Team-Specific Auth**: Each team maintains separate OAuth tokens
4. **Verify Connections**: Check that all services show "Connected" status

### 3. Test Lead Processing

1. **Send Test Message in Slack**:
   ```
   @YourBotName I have a new lead: Yasmine Ahmed, phone 01023456789, 
   looking for a 3-bedroom duplex in Sheikh Zayed with budget 5.5M EGP
   ```

2. **Monitor Dashboard**: Watch real-time processing in the dashboard
3. **Check CRM**: Verify lead appears in Zoho CRM
4. **Check Email**: Confirm notification email sent via Gmail

### 4. Dashboard Features

- **Real-time Logs**: Live updates via WebSocket
- **Lead Data Display**: Formatted lead information
- **System Status**: OAuth connection status
- **Event History**: Complete processing timeline

## 🔧 Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### Project Structure

```
dragify-demo-agent/
├── backend/
│   ├── app/
│   │   ├── agent/              # LangChain agent and tools
│   │   │   ├── orchestrator.py # Main agent orchestrator
│   │   │   ├── tools/          # Agent tools (CRM, email, etc.)
│   │   │   └── prompt.py       # Agent prompts
│   │   ├── api/                # FastAPI routes
│   │   │   ├── slack.py        # Slack integration
│   │   │   ├── zoho.py         # Zoho CRM integration
│   │   │   └── gmail.py        # Gmail integration
│   │   ├── services/           # External service integrations
│   │   ├── db/                 # Database models and connection
│   │   ├── config/             # Configuration files
│   │   └── main.py             # FastAPI application
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── page.tsx            # Main dashboard
│   │   ├── layout.tsx          # App layout
│   │   └── globals.css         # Global styles
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml          # Multi-service orchestration
└── README.md
```

## 🧪 Testing

### Manual Testing

1. **Health Check**: `GET http://localhost:8000/health`
2. **Create Test Event**: `POST http://localhost:8000/api/test-event`
3. **View Logs**: `GET http://localhost:8000/api/logs`

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | System health check |
| GET | `/api/logs?team_id={id}` | Retrieve event logs (team-specific) |
| POST | `/api/test-event` | Create test event |
| **Teams Management** | | |
| GET | `/teams/` | List all teams with integration status |
| GET | `/teams/{team_id}` | Get detailed team information |
| POST | `/teams/{team_id}/ensure` | Create/update team record |
| GET | `/teams/{team_id}/integrations` | Get team integration status |
| **OAuth Endpoints** | | |
| GET | `/slack/oauth/authorize?team_id={id}` | Slack OAuth initiation |
| POST | `/slack/oauth/callback` | Slack OAuth callback |
| GET | `/zoho/oauth/authorize?team_id={id}` | Zoho OAuth initiation |
| POST | `/zoho/oauth/callback` | Zoho OAuth callback |
| GET | `/gmail/oauth/authorize?team_id={id}` | Gmail OAuth initiation |
| POST | `/gmail/oauth/callback` | Gmail OAuth callback |
| **Webhooks** | | |
| POST | `/slack/events` | Slack event webhook |
| WebSocket | `/ws/logs` | Real-time log updates |

## 🐛 Troubleshooting

### Common Issues

1. **OAuth Redirect Mismatch**
   - Ensure redirect URIs in OAuth apps match exactly
   - Check for trailing slashes and protocol (http/https)

2. **Database Connection Issues**
   - Verify PostgreSQL container is running: `docker ps`
   - Check database credentials in `.env`

3. **Slack Events Not Received**
   - Verify webhook URL is accessible
   - Check Slack app event subscriptions
   - Ensure bot is added to channels

4. **CORS Issues**
   - Frontend and backend CORS settings are configured
   - Check browser console for specific errors

5. **ngrok Issues**
   - Ensure ngrok is running and accessible
   - Update OAuth redirect URIs when ngrok URL changes
   - Check ngrok dashboard for request logs: https://dashboard.ngrok.com/

### Viewing Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs backend
docker-compose logs frontend
docker-compose logs postgres

# Follow logs in real-time
docker-compose logs -f backend
```

### Database Access

```bash
# Access PostgreSQL directly
docker exec -it dragify-demo-agent-postgres-1 psql -U postgres -d mydb

# View tables
\dt

# View project data
SELECT * FROM projects;

# View event logs
SELECT * FROM event_logs ORDER BY created_at DESC LIMIT 10;

# View Gmail installations (OAuth tokens)
SELECT * FROM gmail_installations;

# View all database tables
\dt

# View Gmail table structure
\d gmail_installations;
```

## 🚀 Deployment

### Frontend (Vercel)
- **Live URL**: https://dragify-demo-agent.vercel.app/
- **Deployment**: Automatic via Vercel GitHub integration

### Backend Deployment Options
- **Docker**: Use provided Dockerfile
- **Cloud Platforms**: AWS, GCP, Azure with container support
- **Environment Variables**: Update OAuth redirect URIs for production

## 📋 Assessment Compliance

This project fulfills all Dragify Engineering Assessment requirements:

### ✅ Core Requirements
- **Modular AI Agent Template**: LangChain-based with configurable tools
- **Trigger System**: Slack real-time message processing
- **Data Collection**: PostgreSQL database with property data
- **CRM Integration**: Zoho CRM with OAuth 2.0
- **Email Notifications**: Gmail integration with OAuth 2.0
- **Frontend Interface**: React + TailwindCSS dashboard
- **Deployment**: Vercel frontend deployment

### ✅ Technical Standards
- **Clean Architecture**: SOLID principles, OOP, modular design
- **OAuth 2.0**: Full token exchange and secure storage
- **Scalable Design**: Multi-user support, extensible architecture
- **Documentation**: Comprehensive setup and usage guide

### ✅ Bonus Features
- **Real-time Updates**: WebSocket integration
- **Error Handling**: Comprehensive error logging
- **Health Monitoring**: System status endpoints
- **Docker Support**: Complete containerization

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is part of the Dragify Engineering Assessment.

## 📞 Support

For questions or issues:
1. Check the troubleshooting section
2. Review API documentation at `/docs`
3. Check Docker logs for error details
4. Verify OAuth configurations

---

**Built with ❤️ for Dragify Engineering Assessment** 