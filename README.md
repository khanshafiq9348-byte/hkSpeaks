# HK Speaks — AI Voice Studio & Text-to-Speech SaaS Platform

HK Speaks is a production-ready, extensible **AI Text-to-Speech (TTS) SaaS Platform** designed for creators, businesses, and developers.

## Key Features

- **AI Voice Studio**: Multiline script editor, character/duration estimation, acoustic parameter sliders (speed, pitch), and voice presets (Natural, Documentary, Storytelling, Podcast, Energetic, Calm).
- **Accessible Audio Player**: Custom waveform scrubber, variable playback speeds (0.8x to 1.5x), and instant MP3/WAV download.
- **Provider Abstraction**: Pluggable TTS adapters (`MockTTSProvider`, `ElevenLabsAdapter`, `OpenAITTSAdapter`) behind a central `TTSRouter` with automatic failover. Zero external keys required for local development.
- **Voice Cloning Safeguards**: Private-by-default custom voice cloning with mandatory legal consent and rights verification checkboxes.
- **Entitlement & Fair-Use Engine**: Atomic credit reservations in a double-entry credit ledger with automated refund on task failure. Configurable tiers: Free, Starter, Creator, Pro, and fair-use Unlimited.
- **Developer API**: SHA-256 hashed API keys with `hk_live_` prefixes, idempotency key deduplication, and non-blocking background queueing.
- **Admin Portal**: Platform metrics, gross contribution calculations, and live TTS provider health diagnostics.

---

## Technology Stack

- **Frontend**: Next.js 15 (App Router), TypeScript, Tailwind CSS, Lucide Icons.
- **Backend**: Python 3.12+ / FastAPI, Pydantic v2, SQLAlchemy 2.0, Asyncpg / Aiosqlite.
- **Audio Processing**: FFmpeg 8.x (chunk stitching, loudness normalization, WAV/MP3 conversion).
- **Storage**: S3-compatible storage with signed URLs & local filesystem driver.

---

## Quickstart (Continuous Auto-Recovery Server)

### 1-Click Startup (Recommended)
Simply run the supervisor to launch both Frontend & Backend with continuous monitoring and automatic crash recovery:
```bash
# Windows Batch:
.\start.bat

# Or PowerShell:
.\start.ps1

# Or Python directly:
.\backend\.venv\Scripts\python.exe scripts\supervisor.py
```
- **Web Studio**: [http://localhost:3000](http://localhost:3000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Status Check**: `.\start.bat --status`
- **Clean Stop**: `.\start.bat --stop`

> [!NOTE]
> When opened in VS Code or Antigravity IDE, the platform supervisor launches automatically via `.vscode/tasks.json`.

---

### Manual Setup (Optional)

#### Backend Setup
```bash
py -m venv backend/.venv
.\backend\.venv\Scripts\activate
pip install -r backend\requirements.txt
python backend/app/db/seed.py
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

#### Frontend Setup
```bash
cd apps/web
npm install
npm start -p 3000
```

### 3. Demo Credentials
- **Admin**: `admin@hkspeaks.ai` / `AdminPass123!`
- **Creator**: `creator@hkspeaks.ai` / `CreatorPass123!`

---

## Running Automated Tests

```bash
.\backend\.venv\Scripts\pytest.exe backend/tests -v
```

---

## Docker Compose Deployment

```bash
docker compose up --build
```
Services started:
- `postgres` (port 5432)
- `redis` (port 6379)
- `backend` (port 8000)
- `worker` (background queue processor)
- `web` (port 3000)
