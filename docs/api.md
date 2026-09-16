# Developer API Reference — HK Speaks

Base URL: `http://localhost:8000/v1`

## Authentication

All API requests must include an API key in the `Authorization` header:
```http
Authorization: Bearer hk_live_xxxxxxxxxxxxxxxxxxxxxxxx
```

API keys are created in the web dashboard under `/app/api`. Keys are hashed with SHA-256 before storage.

## Endpoints

### 1. Synthesize Speech
```http
POST /v1/text-to-speech
Idempotency-Key: optional-unique-key-string
Content-Type: application/json
```

**Request Body:**
```json
{
  "text": "The quick brown fox jumps over the lazy dog.",
  "voice_id": "sarah-natural",
  "format": "mp3",
  "speed": 1.0,
  "pitch": 0.0,
  "stability": 0.5,
  "style": 0.0
}
```

**Response (200 OK):**
```json
{
  "id": "gen_817293a",
  "status": "queued",
  "voice_id": "sarah-natural",
  "input_characters": 44,
  "estimated_audio_seconds": 2.93,
  "format": "mp3",
  "created_at": "2026-09-11T12:00:00Z"
}
```

### 2. Poll Generation Status
```http
GET /v1/generations/{generation_id}
```

**Response (Completed):**
```json
{
  "id": "gen_817293a",
  "status": "completed",
  "actual_audio_seconds": 2.93,
  "audio_url": "http://localhost:8000/v1/storage/users/.../output.mp3",
  "format": "mp3",
  "completed_at": "2026-09-11T12:00:03Z"
}
```

### 3. List Available Voices
```http
GET /v1/voices?language=en&tier=standard
```

### 4. Cancel Queued Generation
```http
POST /v1/generations/{generation_id}/cancel
```
