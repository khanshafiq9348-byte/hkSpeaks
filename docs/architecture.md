# Architecture Overview — HK Speaks

## High-Level System Architecture

```text
                        ┌──────────────────────┐
                        │      Next.js Web     │
                        │   Dashboard/Studio   │
                        └──────────┬───────────┘
                                   │ HTTPS
                                   ▼
                        ┌──────────────────────┐
                        │     FastAPI API      │
                        │ Auth / TTS / Billing │
                        │ Voices / Projects    │
                        └───────┬───────┬──────┘
                                │       │
                         PostgreSQL     Redis
                                │       │
                                │       ▼
                                │   Job Queue
                                │       │
                                │       ▼
                                │  ┌──────────────┐
                                │  │ TTS Worker   │
                                │  │ Clone Worker │
                                │  │ Audio Worker │
                                │  └──────┬───────┘
                                │         │
                                │         ▼
                                │   Provider Router
                                │      │    │
                                │      ▼    ▼
                                │ Provider A/B/Mock
                                │
                                ▼
                         Object Storage
                         MP3/WAV/metadata
```

## Provider Abstraction

The platform isolates all TTS synthesis behind a unified `TTSProvider` interface:
```python
class TTSProvider(ABC):
    async def synthesize(self, request: TTSRequest) -> TTSResult: ...
    async def get_voices(self) -> List[Dict[str, Any]]: ...
    async def health_check(self) -> bool: ...
    def estimate_cost(self, request: TTSRequest) -> CostEstimate: ...
```

Business logic calls `TTSRouter.synthesize(...)`, which handles provider selection, model routing, and automatic fallback without exposing vendor details to the frontend or database.

## Audio Processing Pipeline

Using FFmpeg:
1. Long scripts are parsed and chunked at sentence and paragraph boundaries (default 1,000 characters).
2. Chunks are generated through the selected provider adapter.
3. Chunks are stitched together into a seamless output with loudness normalization.
4. Duration is verified via container inspection (`ffprobe`).
5. Output is encoded to MP3 or WAV and transferred to storage.

## Accounting & Double-Entry Credit Ledger

- Usage is accounted using credit ledger transactions (`subscription_grant`, `generation_reservation`, `generation_debit`, `refund`).
- Before background generation begins, required character credits are atomically reserved.
- When generation completes, the reservation is converted to a final debit.
- If generation fails or is cancelled, the reserved credits are immediately and atomically refunded.
