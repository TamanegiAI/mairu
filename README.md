# Google Docs Automation Chrome Extension 🚀

## Overview
This project is a **Chrome extension** that automates document generation and email sending using **Google Sheets, Google Docs, and Gmail APIs**. The backend is built with **FastAPI**, and the frontend is available both as a Chrome extension and a Streamlit web application that interact with the backend API.

## Features
✅ **Authenticate with Google** using OAuth 2.0  
✅ **Fetch Google Sheets** and extract column names  
✅ **Map columns** from Sheets to Google Docs placeholders  
✅ **Generate a document** by replacing placeholders with sheet data  
✅ **Send the generated document** via email  
✅ **Schedule emails** to be sent at a later time  
✅ **Token management**: Stores and refreshes access tokens automatically  
✅ **SQLite database integration** to store user tokens, mappings, and email history  

## 🎥 Video Tutorial

**Watch the full tutorial on YouTube**: [Image + Quote Automation with Google Slides](https://youtu.be/momZTxYmLA8)

This comprehensive video tutorial walks you through:
- How the image + quote automation works
- Using Google Slides as a design engine
- Automatically replacing text and images
- Exporting the final designs
- Sending them via email automatically
- How to customize this system for your use case

Perfect for content creators, social media managers, and anyone wanting to automate their visual content creation!

## Project Structure

```
mairu/
├── src/                     # Main package source code
│   ├── app/                 # Application module
│   │   ├── main.py          # FastAPI main entry point
│   │   ├── config.py        # Application configuration
│   │   ├── dependencies.py  # Dependency injection
│   │   ├── database.py      # SQLite Database setup
│   │   ├── models/          # Data models
│   │   │   ├── schemas.py   # API schemas (Pydantic models)
│   │   │   ├── database_models.py # SQLAlchemy models
│   │   ├── services/        # Business logic
│   │   │   ├── auth.py      # Google OAuth 2.0 authentication
│   │   │   ├── sheets.py    # Fetching and processing Google Sheets data
│   │   │   ├── docs.py      # Document generation logic
│   │   │   ├── gmail.py     # Email sending functionality
│   │   │   ├── scheduler.py # Email scheduling logic
│   │   │   ├── database.py  # Database operations
│   │   ├── api/             # API routes
│   │   │   ├── routes.py    # Defines API endpoints
│   │   ├── frontend/        # Streamlit frontend application
│   │   │   ├── app.py       # Main Streamlit UI
│   │   │   ├── components/  # Streamlit UI components
│   │   │   ├── utils/       # Frontend utilities
│   │   │   │   ├── api_helper.py # API integration for Streamlit
│   │   ├── utils/           # Common utilities
│
├── alembic/                 # Database migrations
├── .env                     # Environment variables (not committed to Git)
├── run.py                   # Main executable to run the application
├── requirements.txt         # Backend dependencies
├── README.md                # Project documentation
```

## Setup Instructions

### 1️⃣ Install dependencies
```bash
pip install -r requirements.txt
pip install -r src/app/frontend/requirements.txt
```

### 2️⃣ Set up Google OAuth credentials
1. **Download credentials from Google Cloud Console**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google Sheets, Gmail, Drive, and Slides APIs
   - Create OAuth 2.0 credentials
   - Download the JSON file and rename it to `credentials.json`
   - Place it in the project root directory

2. **Alternatively, create a .env file**:
   ```bash
   cp env.example .env
   # Edit .env with your credentials
   ```

### 3️⃣ Run the database migration
```bash
alembic upgrade head
```

### 4️⃣ Run the application

#### Run both backend and frontend
```bash
./run.py
```

#### Run only the backend
```bash
./run.py --backend-only
```

#### Run only the frontend
```bash
./run.py --frontend-only
```

#### Run with custom ports
```bash
./run.py --backend-port 9000 --frontend-port 9501
```

## Poetry Installation

### Install Poetry
If you don't have Poetry installed, you can install it by following these steps:

1. **Using the official installer**:
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Verify the installation**:
   ```bash
   poetry --version
   ```

3. **Add Poetry to your PATH** (if not already added):
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```
   Add this line to your shell configuration file (e.g., `~/.zshrc` or `~/.bashrc`) to make it permanent.

### Configure Poetry for the Project

Run the following commands to configure Poetry for this project:

```bash
poetry config --local virtualenvs.create true
poetry config --local virtualenvs.in-project true
poetry config --local virtualenvs.path "./.venv"
poetry config --local installer.parallel true
poetry config --local keyring.enabled true
poetry config --local warnings.export true
```

Once configured, you can install the project dependencies using:

```bash
poetry install
```

## Accessing the Application

- **Backend API**: http://localhost:8000
- **Frontend UI**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs

## Chrome Extension Setup

For the Chrome extension:

1. Open Chrome and go to chrome://extensions/
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `src/app/frontend` directory
5. The extension icon should appear in your browser toolbar

## Development

This project uses:
- Poetry for dependency management
- Alembic for database migrations
- FastAPI for the backend API
- Streamlit for the web UI frontend
- Google API libraries for integrating with Google services

## 📄 License

This project is licensed under a **Custom Non-Commercial License**:
- ✅ **Free for personal, educational, and non-commercial use**
- ✅ **Open source code** - you can view, modify, and learn from it
- ✅ **Patent protection** included
- ❌ **Commercial use requires a separate license**

For commercial use, please contact the project owner.

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## ⚠️ Important Security Notes

- **Never commit** `credentials.json`, `token.json`, or `.env` files
- **Keep your Google API credentials secure**
- **Use test emails** when testing email functionality
- **Review the `.gitignore`** before committing changes

