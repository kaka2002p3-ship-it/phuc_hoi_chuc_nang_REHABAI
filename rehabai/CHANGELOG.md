# Changelog

## [0.1.1] - 2026-10-27

### Fixed
- Restored `artifacts/model_v2/model.pt` integrity: re-exported via
  `scripts/export_model.py` so the bundle SHA-256 manifest verifies again
  (`model_loader` health check returns 200 instead of 503; 12 previously
  blocked test files collect normally).
- Added the missing `export_model_bundle()` exporter (strict, staging-based,
  fails without corrupting an existing bundle) to `scripts/export_model.py`.
- `tests/test_websocket_auth.py`: aligned assertion with the actual error
  payload (`"Invalid JSON format"`).

### Security
- Strengthened `deployment/.env`: JWT secret and Postgres password replaced
  with 64/32-character random values (previous placeholders were guessable).
  Keep this file out of version control (see `.gitignore`).
- Hardened root `.gitignore`: secrets (`deployment/.env`, `.secrets/`),
  databases, raw/experimental data, `node_modules/`, build outputs, and
  heavy checkpoints are no longer trackable. `*.env.example` stays tracked.

### Notes
- Full test suite: 241 passed, 1 skipped (was 218 passing with 12 test files
  blocked by the P0 artifact mismatch; the "143 passing tests" note in
  [0.1.0] was stale).
- `backend/core/rate_limit.py` is per-process in-memory; it does not
  coordinate across replicas. Acceptable for a single-worker dev/demo setup;
  use Redis (or an equivalent shared store) before multi-replica production.

### Added
- `LICENSE` (MIT), matching the license already declared in `pyproject.toml`.
- `.github/workflows/ci.yml`: CI for the backend test suite and the
  frontend production build.

### Changed
- Moved ad-hoc root scripts into `scripts/`:
  - `test_load_jit.py` -> `scripts/test_load_jit.py`
  - `check_overfit.py` -> `scripts/check_overfit.py`
  - `test_ws.py` -> `scripts/smoke_ws_client.py` (renamed to reflect that it
    is a manual smoke client, not a pytest test)
- Completed `.env.example` (root) with the variables the backend actually
  reads: `DATABASE_URL`, `REHABAI_DB_PATH`, `REHABAI_AUTO_CREATE_SCHEMA`,
  `JWT_TTL_SECONDS`, `ARTIFACTS_DIR`, `MATCH_CONFIDENCE_THRESHOLD`,
  `LOG_LEVEL`, `LOG_FILE`.
- Documented the per-process limitation of `backend/core/rate_limit.py` in
  its module docstring.

## [0.1.0] - 2026-10-04

### Added
- Initial release
- RehabMotionNet v2 model (TorchScript)
- FastAPI backend with WebSocket inference
- React frontend with Vietnamese UI
- LOSO cross-validation (10-fold, 10 subjects)
- Authentication system (JWT)
- Database migration support
- Docker deployment
- Full test suite (143 passing tests)

### Known Issues
- Model accuracy: 43.79% ± 23.35% (research level)
- Small dataset: 10 subjects, 387 samples
- High variance between folds
