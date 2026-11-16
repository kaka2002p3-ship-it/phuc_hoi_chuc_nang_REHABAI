from pathlib import Path
import re

PROMPT_VERSION = "master-vi-en-1.0"
PACKAGED_PROMPT = Path(__file__).resolve().parents[1] / "prompts" / "rehabai_system_vi_en.txt"
# The source document is available in a workspace checkout, but is intentionally
# not required at runtime (the Docker build context is the rehabai directory).
MASTER = Path(__file__).resolve().parents[3] / "RehabAI_Ollama_Chatbot_MASTER_VI_EN.md"


def _extract_master_prompt() -> str:
    raw = MASTER.read_text(encoding="utf-8")
    match = re.search(
        r"<!-- BEGIN_OLLAMA_SYSTEM_PROMPT -->\s*```text\s*(.*?)\s*```\s*<!-- END_OLLAMA_SYSTEM_PROMPT -->",
        raw,
        re.S,
    )
    if not match:
        raise RuntimeError("Ollama system prompt block is missing from the master document")
    return match.group(1).strip()


def load_system_prompt() -> str:
    if not PACKAGED_PROMPT.exists():
        raise RuntimeError(f"Packaged Ollama system prompt is missing: {PACKAGED_PROMPT}")
    prompt = PACKAGED_PROMPT.read_text(encoding="utf-8").strip()
    # Detect accidental drift whenever the source document is present. In a
    # production image MASTER is absent, so the packaged, reviewed copy is used.
    if MASTER.exists() and prompt != _extract_master_prompt():
        raise RuntimeError("Packaged Ollama system prompt differs from the master document")
    return prompt
