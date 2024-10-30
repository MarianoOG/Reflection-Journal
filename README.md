# Reflection Journal

This repository represents my journey of personal growth and philosophical exploration. It's a systematic approach to understanding life, making better decisions, and continuously improving.

## Key Features

- **Reflections**: Capture thoughts based on questions that you create
- **Insights**: LLM-assisted analysis of reflection entries to identify patterns and blind spots.
- **Challenge Assumptions**: LLM-assisted questioning of assumptions based on reflection entries.
- **Goal Management**: Set and review goals based on what is important for you based on insights and reflection entries.
- **Task Generation**: Convert insights and goals into actionable tasks.
- **Structured Storage**: MySQL database with efficient querying
- **Easy Deployment**: Containerized deployment on Cloud Run

## System Overview

### Core Components

1. **Self-Reflection Engine**
   - LLM analysis of journal entries to identify patterns, blind spots and insights
   - LLM-powered exploration of philosophical concepts
   - Automated questioning system to challenge assumptions

2. **Goal Management System**
   - LLM-assisted goal setting and definition
   - Questioning of goals to clarify and refine
   - Periodic review and adjustment of goals

3. **Actionable Insights**
   - LLM-assisted insight-to-action generation 
   - Plan and prioritize actions based on insights
   - Integration with Todoist for task management

### Technical Stack

- **Frontend**: Streamlit for interactive interfaces
- **Backend**: FastAPI for RESTful services
- **Storage**: MySQL for structured data
- **Infrastructure**: GCP Cloud Run for containerized services
- **Third Party APIs**: 
  - Todoist for task management
  - OpenAI for LLM integration

## Project Structure

```
reflection-journal/
├── backend/                      # Backend application
│   ├── alembic/                  # Created by 'alembic init'
│   │   ├── versions/             # Migration versions
│   │   ├── env.py                # Alembic environment configuration
│   │   └── script.py.mako        # Template for migration files
│   ├── core/                     # Core application modules
│   │   ├── config.py             # Application configuration
│   │   ├── database.py           # SQLAlchemy database setup
│   │   └── models/               # SQLAlchemy models
│   │       ├── __init__.py       # Initialization
│   │       ├── journal.py        # Journal model
│   │       └── goals.py          # Goals model
│   ├── services/                 # Business logic services
│   |   ├── todoist_service.py    # Task management
│   |   └── llm_service.py        # AI integration
│   ├── tests/                    # Test directory
│   ├── Dockerfile                # Backend container configuration
│   ├── main.py                   # FastAPI application
│   └── requirements.txt          # Backend dependencies
├── frontend/                     # Frontend application
│   └── pages/                    # Streamlit pages     
│   ├── Dockerfile                # Frontend container configuration
│   ├── main.py                   # Streamlit application
│   └── requirements.txt          # Frontend dependencies
├── .env                          # Environment variables
├── .gitignore                    # Git ignore file
├── docker-compose.yml            # Docker compose file
├── README.md                     # This file
└── TODO.md                       # Development roadmap
```

## Getting Started

1. **Prerequisites**
   - MySQL database setup
   - Todoist API key
   - OpenAI API key

2. **Database Setup**
   ```bash
   # Create MySQL database
   mysql -u root -p
   CREATE DATABASE reflection_journal;
   CREATE USER 'journal_user'@'localhost' IDENTIFIED BY 'your_password';
   GRANT ALL PRIVILEGES ON reflection_journal.* TO 'journal_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

3. **Local Development**
   ```bash
   # Install dependencies
   cd backend && pip install -r requirements.txt
   cd frontend && pip install -r requirements.txt

   # Initialize database and Alembic
   cd backend
   alembic init alembic  # This creates the alembic directory and configuration

   # Edit alembic/env.py to import your models and set up SQLAlchemy URL
   # Edit alembic.ini with your database URL:
   # sqlalchemy.url = mysql+mysqlconnector://user:password@localhost/reflection_journal
   
   # Create and run initial migration
   alembic revision --autogenerate -m "Initial migration"
   alembic upgrade head

   # Run services
   # Terminal 1: Backend
   uvicorn main:app --reload --port 8000

   # Terminal 2: Frontend  
   cd ../frontend
   streamlit run main.py --server.port 8501
   ```

4. **Deployment**
   - Automated deployment is configured via GitHub Actions
   - Workflow configuration is in [.github/workflows/deploy.yml](.github/workflows/deploy.yml)
   - Requires GCP credentials configured as repository secrets

## Configuration

Create a [`.env`](.env) file with the following:
```
TODOIST_API_KEY=your_todoist_key
OPENAI_API_KEY=your_openai_key
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_HOST=your_mysql_host
MYSQL_DATABASE=reflection_journal
```

## Data Structure

The database schema is managed through SQLAlchemy models and Alembic migrations in the `backend/core/schemas/` directory.

## Contributing

You can contribute to the project by adding new features or fixing bugs. Please, refer to the [TODO.md](TODO.md) file for the development roadmap and to know what to work on.

## License

MIT License - see LICENSE file for details