# Chatbot test plan

## Automated regression

`pytest -q` currently covers prompt packaging/drift, strict JSON and evidence
validation, deterministic safety bypass (including Vietnamese without diacritics
and English templates), fallback states, auth/ownership, session scope and
privacy deletion. The latest run is recorded in
`reports/chatbot/implementation_status.md`.

## Reviewer matrix

The GPT-5.6 Sol reviewer defines the frozen T01–T60 matrix. Each case must store
the user message, owned backend context, knowledge version, actual Ollama output,
HTTP status, model/prompt/schema versions, automated checks and human review.
`PASS` is reserved for observed evidence; `NOT_RUN` and `BLOCKED` are never
converted to pass.

Health, safety, emotional-support and bilingual cases require human review even
when automated schema checks pass. Camera/Ollama resource measurements are a
separate Gate C requirement.
