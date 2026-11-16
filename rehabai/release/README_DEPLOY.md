# RehabAI deployment bundle

This release contains inference-only deployment files. It intentionally does
not contain datasets, training code, raw checkpoints, or experiment logs.

Run from this directory with Docker Desktop running:

```powershell
docker compose -f compose.yaml up --build
```

Open http://localhost:8080. The backend health endpoint is available at
http://localhost:8000/api/health for local diagnostics.

The bundled model is RehabMotionNet upper-limb v2. It is a research/demo
system and does not replace a qualified healthcare professional.
