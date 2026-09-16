# Local Development Guide

## Prerequisites
- Python 3.12+ (Python 3.14 supported)
- Node.js 20+ (Node 24 supported)
- FFmpeg 6.0+ (FFmpeg 8.1 supported)
- Git

## Starting the Application Locally

### 1. Database & Seeding
From repository root:
```bash
# Activate python environment
.\backend\.venv\Scripts\activate

# Initialize tables and seed plans, voices, and demo accounts
python backend/app/db/seed.py
```

### 2. Run Backend API Server
```bash
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

### 3. Run Frontend Web Studio
In another terminal:
```bash
cd apps/web
npm run dev
```

Visit:
- Web Studio: `http://localhost:3000`
- Interactive API Docs: `http://localhost:8000/docs`

## Demo Accounts
- **Admin**: `admin@hkspeaks.ai` / `AdminPass123!`
- **Creator**: `creator@hkspeaks.ai` / `CreatorPass123!`

## Running Automated Tests
```bash
.\backend\.venv\Scripts\pytest.exe backend/tests -v
```
