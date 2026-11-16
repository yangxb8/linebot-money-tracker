# Audio Abuse Limits Contract

**Feature**: 022-voice-expense-input  
**Type**: Shared validation module + usage config

## Constants (v1 product defaults)

| Limit | Value | Notes |
| ----- | ----- | ----- |
| Max duration | **60 seconds** | `60_000` milliseconds |
| Max file size | **5 MiB** | `5 * 1024 * 1024` bytes |

Env override (size only, mirror image pattern):

| Env | Default | Purpose |
| --- | ------- | ------- |
| `USAGE_MAX_AUDIO_BYTES` | `5242880` | Max accepted audio payload bytes |

Duration remains a fixed product constant in v1 (no per-tenant override). Optional later: `USAGE_MAX_AUDIO_SECONDS` if ops need tuning without code change — not required for v1 ship.

## Module

`services/audio_limits.py` (name flexible)

```text
MAX_AUDIO_DURATION_MS = 60_000
MAX_AUDIO_BYTES = from usage_config (default 5 MiB)

class AudioLimitViolation(Enum):
  DURATION
  SIZE

check_audio_duration(duration_ms: int | None) -> AudioLimitViolation | None
check_audio_size(audio_bytes: bytes) -> AudioLimitViolation | None
```

### Semantics

- `check_audio_duration(None)` → `None` (no duration-based reject; size still applies).  
- `check_audio_duration(60_000)` → `None` (inclusive upper bound).  
- `check_audio_duration(60_001)` → `DURATION`.  
- `check_audio_size` with `len == MAX` → `None`; `len == MAX+1` → `SIZE`.  
- Prefer duration check **before** content download when `duration_ms` is known.  
- Size check **before** Gemini transcription.

## Usage limiter integration

`prepare_inbound_usage` / `check_payload_*`:

- Add `check_payload_audio(audio_bytes)` analogous to `check_payload_image`.  
- Audio inbound MUST NOT set receipt-analysis sub-quota (`image_bytes is not None` path).  
- Monthly/general rate limits still apply as for other AI-assisted messages.

## User-facing mapping

| Violation | Reply requirement |
| --------- | ----------------- |
| DURATION | Name 60 second limit; suggest shorter recording or text; no expense |
| SIZE | Name 5 MB limit; suggest shorter recording or text; no expense |

## Test contract

Automated tests MUST assert:

1. Over-duration → rejection reply, **zero** Gemini transcription calls, **zero** expense inserts.  
2. Over-size → rejection reply, **zero** Gemini transcription calls, **zero** expense inserts.  
3. Within both limits → transcription path invoked (may still fail later as unusable/non-expense).
