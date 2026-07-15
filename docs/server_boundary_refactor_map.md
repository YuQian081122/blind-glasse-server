# Server Boundary And Refactor Map

Date: 2026-06-26

## Scope

This document records the server repository boundary and the first safe
refactor path. It intentionally does not remove files or change runtime
behavior.

## Canonical Runtime Boundary

- Canonical Git repository: `blind-glasse-server/`
- Canonical runtime entry point: `blind-glasse-server/main.py`
- Canonical config file: `blind-glasse-server/config.py`
- Current run scripts start `uvicorn main:app` from the repository root.
- `blind-glasse-server/server/` is currently an untracked duplicate copy. Do
  not edit it for runtime behavior unless a later cleanup explicitly chooses
  to migrate or delete it.
- Workspace-root `server/` belongs to the outer workspace Git history, not the
  canonical server GitHub repository. It is currently incomplete and should not
  be used as the active server implementation.

## Conservative Marking Status

As of 2026-06-27, the user chose conservative marking instead of moving the
duplicate copy. The nested `blind-glasse-server/server/` directory remains on
disk, but `blind-glasse-server/.gitignore` now marks it as ignored so future
status output does not present it as active source.

Current meaning:

- Active runtime source remains `blind-glasse-server/main.py`.
- The nested `server/` directory is reference material only.
- Do not edit nested `server/` for behavior changes.
- Do not commit nested `.env`, `.env.cloudflare`, model files, virtualenvs, or
  duplicated source files.

Observed nested duplicate contents before marking:

- 58 non-venv, non-vendor files.
- About 403.78 MB under `server/models/`.
- About 45 source-like files, around 277 KB.
- Includes ignored local environment files such as `.env` and `.env.cloudflare`.

## Duplicate Inventory

Observed duplicate pairs between `blind-glasse-server/` and
`blind-glasse-server/server/`:

| File | Root lines | Nested lines | Diff lines |
| --- | ---: | ---: | ---: |
| `main.py` | 1282 | 1279 | 149 |
| `config.py` | 224 | 233 | 135 |
| `vision_controller.py` | 339 | 241 | 254 |
| `stream_manager.py` | 267 | 258 | 41 |
| `yolomedia.py` | 207 | 212 | 25 |
| `README.md` | 183 | 226 | 121 |

The nested copy is close enough to confuse future edits, but different enough
that it cannot be deleted or replaced casually.

## Contract Protected By Smoke Tests

`tests/test_server_contract_static.py` protects these contracts without
importing heavy runtime dependencies:

- run scripts keep using root `main:app`
- nested `server/` stays untracked by the server Git repo
- device API paths still exist:
  - `GET /health`
  - `POST /api/frame`
  - `POST /api/imu`
  - `POST /api/gps`
  - `POST /api/asr`
  - `GET /audio/latest`
- monitor subset paths still exist:
  - `GET /api/monitor/state`
  - `GET /api/monitor/events`
  - `GET /api/monitor/frame`
  - `GET /api/monitor/health`
  - `GET /api/monitor/latency`
- family/status paths still exist
- token-protected device mutation paths remain explicit

## Refactor Phases

1. Boundary freeze
   - Keep root `main.py` as the only active server entry point.
   - Keep nested `server/` untouched until the user explicitly approves a
     cleanup or archival step.

2. Test gate
   - Keep dependency-free static smoke tests.
   - After the Python virtual environment is repaired, add FastAPI TestClient
     tests for `/health`, `/api/status`, `/api/monitor/state`, and
     `/api/monitor/frame`.

3. Router extraction
   - Move device routes to a device router:
     `/api/frame`, `/api/imu`, `/api/gps`, `/api/asr`, `/audio/latest`.
   - Move family routes to a family router:
     `/api/family/location`, `/api/family/status`, `/api/family/emergency`.
   - Keep monitor routes in `monitor_api.py`.

4. Service extraction
   - Move mutable server state behind small service objects:
     frame state, IMU/GPS state, TTS state, device status, and latency health.
   - Keep external integrations isolated:
     Gemini, LINE, Google Maps, ASR, YOLO.

5. Duplicate cleanup
   - The duplicate copy is conservatively marked ignored for now.
   - Only after tests pass and the user confirms a stronger cleanup, remove or
     archive the nested `blind-glasse-server/server/` copy.
   - Do not mix this cleanup with behavior refactors.

## Verification Commands

Current dependency-free gate:

```powershell
python -m unittest discover -s tests
```

Future full server gate after virtualenv repair:

```powershell
python -m pip check
python -c "import main; print('main import ok')"
python -m pytest
```

## Risks

- The current `.venv` cannot be executed from this Codex environment because
  its Python launcher path is stale.
- Global Python lacks `fastapi`, `cv2`, and `pytest`, so full runtime tests are
  blocked until the server environment is repaired.
- `blind-glasse-server/server/` and workspace-root `server/` can still confuse
  future edits until they are explicitly cleaned up.
- Several tracked server files are already dirty; future commits must stage
  only the intended files.
