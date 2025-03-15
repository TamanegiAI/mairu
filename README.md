# Google Docs Automation Chrome Extension 🚀

## Overview
This project is a **Chrome extension** that automates document generation and email sending using **Google Sheets, Google Docs, and Gmail APIs**. The backend is built with **FastAPI**, and the frontend is a Chrome extension that interacts with the backend API.

## Features
✅ **Authenticate with Google** using OAuth 2.0  
✅ **Fetch Google Sheets** and extract column names  
✅ **Map columns** from Sheets to Google Docs placeholders  
✅ **Generate a document** by replacing placeholders with sheet data  
✅ **Send the generated document** via email  
✅ **Schedule emails** to be sent at a later time  
✅ **Token management**: Stores and refreshes access tokens automatically  
✅ **SQLite database integration** to store user tokens, mappings, and email history  

## Project Structure

chrome_extension/
├── backend/                 # FastAPI Backend
│   ├── app/
│   │   ├── main.py          # FastAPI main entry point
│   │   ├── config.py        # Application configuration
│   │   ├── dependencies.py  # Dependency injection
│   │   ├── database.py      # SQLite Database setup
│   │   ├── database_models.py  # SQLAlchemy models
│   │   ├── services/        # Business logic
│   │   │   ├── auth.py      # Google OAuth 2.0 authentication
│   │   │   ├── sheets.py    # Fetching and processing Google Sheets data
│   │   │   ├── docs.py      # Document generation logic
│   │   │   ├── gmail.py     # Email sending functionality
│   │   │   ├── scheduler.py # Email scheduling logic
│   │   ├── api/             # API routes
│   │   │   ├── routes.py    # Defines API endpoints
│   ├── .env                 # Environment variables (not committed to Git)
│   ├── alembic/             # Database migrations
│   ├── alembic.ini          # Alembic configuration
│   ├── requirements.txt     # Backend dependencies
│   ├── README.md            # Backend documentation
│
├── frontend/                # Chrome Extension Frontend
│   ├── manifest.json        # Chrome extension configuration
│   ├── popup.html           # Popup UI
│   ├── popup.js             # JavaScript logic
│   ├── styles.css           # Extension styles
│   ├── background.js        # Handles background tasks
│   ├── images/              # Extension icons
│   ├── README.md            # Frontend documentation
│
└── README.md                # Main project documentation

---

## Backend Setup (FastAPI)
### 1️⃣ Install dependencies
```bash
cd backend
pip install -r requirements.tx
```
### Create a .env file
```
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
DATABASE_URL=sqlite:///./app.db
```
### Run the database migration
```
alembic upgrade head
```

### Start the backend server
```
uvicorn app.main:app --reload
```

