# Workspace Guidelines: HK Speaks TTS Platform

## Server Architecture & Continuous Availability
- **Continuous Supervisor**: The project uses `scripts/supervisor.py` to maintain continuous availability of both the FastAPI Backend (`http://127.0.0.1:8000`) and Next.js Frontend (`http://localhost:3000`).
- **Fixed Ports**: Never use temporary or random ports. The Backend must strictly bind to port `8000`, and the Frontend to port `3000`.
- **Auto-Recovery**: If either service stops or crashes, the supervisor automatically detects it and restarts the service.
- **Starting Services**:
  - `start.bat` or `python scripts/supervisor.py` launches the supervisor.
  - `python scripts/supervisor.py --status` checks the health of both services.
  - `.vscode/tasks.json` automatically triggers `Start TTS Platform (Continuous Supervisor)` on folder open.
