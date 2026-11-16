"""Model loader for RehabAI inference.

This module provides a singleton ModelLoader that loads and manages
the TorchScript model, normalization statistics, and exercise registry.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar
from threading import Lock

import numpy as np
import torch

# Type variable for generic decorator
F = TypeVar('F', bound=Callable[..., Any])

# Initialize logger
logger = logging.getLogger("rehabai.model_loader")

_default_artifact = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../artifacts/model_v2"))
ARTIFACTS_DIR = os.path.abspath(os.environ.get("ARTIFACTS_DIR", _default_artifact))


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 0.1,
    backoff: float = 2.0,
    exceptions: Tuple[type, ...] = (RuntimeError, torch.cuda.OutOfMemoryError)
) -> Callable[[F], F]:
    """
    Decorator that retries a function on transient failures.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch and retry

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries:
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        break

            # If all retries failed, try one more time without catching
            return func(*args, **kwargs)

        return wrapper  # type: ignore
    return decorator


class ModelLoadError(Exception):
    """Custom exception for model loading errors."""
    pass


class ModelLoader:
    """
    Singleton model loader for RehabAI inference.

    Loads TorchScript model, normalization statistics, and exercise registry
    from the configured artifacts directory. Provides thread-safe access
    to model predictions with automatic retry logic.
    """

    _instance: Optional["ModelLoader"] = None
    _lock = Lock()

    def __new__(cls) -> "ModelLoader":
        # Double-checked locking for thread safety
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (useful for testing)."""
        with cls._lock:
            cls._instance = None

    def _initialize(self) -> None:
        """Initialize the model loader by loading all required artifacts."""
        # Training is GPU-locked by the research protocol. Inference keeps a
        # CPU fallback so the Docker smoke-test and local demo remain usable
        # on machines without a CUDA runtime.
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Model device: {self.device}")

        # Inference lock for thread safety
        self._inference_lock = Lock()
        self._loaded = False
        self._load_error: Optional[str] = None

        # Read configuration first so the loader can serve validated research
        # bundles as well as the production v2 fallback.
        config_path = os.path.join(ARTIFACTS_DIR, "model_config.json")
        if not os.path.isfile(config_path):
            error_msg = f"Model config not found at {config_path}"
            self._load_error = error_msg
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        signature = config.get("architecture_signature")
        allowed_signatures = {
            "rehab_motionnet_upper_limb_v2",
            "ensemble_v1_research",
        }
        if signature not in allowed_signatures:
            raise RuntimeError(f"Unsupported artifact architecture signature: {signature}")

        if config.get("input_dim") != 237 or config.get("temporal_frames") != 96:
            raise RuntimeError("Artifact feature contract mismatch")

        self.model_config: Dict[str, Any] = config

        # The model output mapping is artifact-owned. Never assume that output
        # index N maps to canonical exercise N+1.
        raw_class_mapping = config.get("class_mapping")
        if not isinstance(raw_class_mapping, dict):
            mapping_path = os.path.join(ARTIFACTS_DIR, "class_mapping.json")
            if not os.path.isfile(mapping_path):
                raise RuntimeError("Artifact class mapping is missing")
            with open(mapping_path, encoding="utf-8") as f:
                raw_class_mapping = json.load(f)

        self.output_index_to_exercise_id: Dict[int, int] = {}
        for raw_index, raw_label in raw_class_mapping.items():
            try:
                output_index = int(raw_index)
            except (TypeError, ValueError) as exc:
                raise RuntimeError(f"Invalid artifact output index: {raw_index}") from exc

            if isinstance(raw_label, int):
                exercise_id = raw_label
            else:
                match = re.fullmatch(r"Exercise_(\d+)", str(raw_label))
                if match is None:
                    raise RuntimeError(f"Invalid artifact class label: {raw_label}")
                exercise_id = int(match.group(1))

            self.output_index_to_exercise_id[output_index] = exercise_id

        if sorted(self.output_index_to_exercise_id) != list(range(len(self.output_index_to_exercise_id))):
            raise RuntimeError("Artifact output mapping is not contiguous")

        # Load TorchScript Model
        model_path = os.path.join(ARTIFACTS_DIR, "model.pt")
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model file not found at {model_path}. Please complete Phase 11 export."
            )

        self.model = torch.jit.load(model_path, map_location=self.device)
        self.model.eval()

        # Load Normalization Stats
        norm_path = os.path.join(ARTIFACTS_DIR, "normalization.json")
        with open(norm_path, 'r', encoding='utf-8') as f:
            norm_data = json.load(f)
            self.kin_mean = np.array(
                norm_data["kinematics"]["mean"], dtype=np.float32
            )
            self.kin_std = np.array(
                norm_data["kinematics"]["std"], dtype=np.float32
            )

        # Load Exercise Registry
        registry_path = os.path.join(ARTIFACTS_DIR, "exercise_registry.json")
        with open(registry_path, 'r', encoding='utf-8') as f:
            self.registry = json.load(f)

        # Fail fast on a corrupted or mismatched production bundle.
        expected_registry_hash = ""
        hash_path = os.path.join(ARTIFACTS_DIR, "registry_sha256.txt")
        if os.path.isfile(hash_path):
            expected_registry_hash = open(hash_path, encoding="utf-8").read().strip()

        actual_registry_hash = hashlib.sha256(
            open(registry_path, "rb").read()
        ).hexdigest()

        if expected_registry_hash and expected_registry_hash != actual_registry_hash:
            raise RuntimeError("Artifact registry SHA-256 mismatch")

        # Verify all bundle hashes when a manifest is present.
        bundle_manifest = os.path.join(ARTIFACTS_DIR, "bundle_sha256.json")
        if os.path.isfile(bundle_manifest):
            with open(bundle_manifest, encoding="utf-8") as f:
                expected = json.load(f)
            for name, digest in expected.items():
                path = os.path.join(ARTIFACTS_DIR, name)
                if not os.path.isfile(path):
                    raise RuntimeError(f"Artifact manifest entry missing: {name}")
                actual = hashlib.sha256(open(path, "rb").read()).hexdigest()
                if actual != digest:
                    raise RuntimeError(f"Artifact SHA-256 mismatch: {name}")

        # Ensure the preprocessing schemas bundled with the model are intact.
        for schema_name in ("feature_schema.json", "normalization.json"):
            schema_path = os.path.join(ARTIFACTS_DIR, schema_name)
            if not os.path.isfile(schema_path):
                raise RuntimeError(f"Missing required artifact schema: {schema_name}")

        # Build reverse mapping for fast lookup
        self.id_to_exercise: Dict[int, Dict[str, Any]] = {}
        for item in self.registry:
            ex_id = item.get("exercise_id")
            if ex_id is not None:
                self.id_to_exercise[ex_id] = item

        mapped_ids = set(self.output_index_to_exercise_id.values())
        if mapped_ids != set(self.id_to_exercise):
            error_msg = "Artifact class mapping does not match exercise registry"
            self._load_error = error_msg
            raise RuntimeError(error_msg)

        # Mark as successfully loaded
        self._loaded = True
        logger.info(f"Model loaded successfully: {signature}, device={self.device}")

    @retry_on_failure(max_retries=2, delay=0.05)
    def predict(self, sequence: np.ndarray) -> Dict[str, Any]:
        """
        Run inference on a motion sequence.

        Args:
            sequence: Feature vector of shape (96, 237)

        Returns:
            Dict containing:
            - exercise_id: Canonical exercise ID (1-indexed)
            - confidence: Prediction confidence score [0, 1]
            - completion_score: Estimated completion score [0, 100]
            - probabilities: Class probabilities [0, 1] for all 4 classes
        """
        if not self._loaded:
            if self._load_error:
                raise ModelLoadError(f"Model not loaded: {self._load_error}")
            raise ModelLoadError("Model not initialized")

        if sequence.shape != (96, 237):
            raise ValueError(
                f"Expected sequence shape (96, 237), got {sequence.shape}"
            )

        # Thread-safe inference
        with self._inference_lock:
            tensor = (
                torch.tensor(sequence, dtype=torch.float32)
                .unsqueeze(0)
                .to(self.device)
            )

            with torch.no_grad():
                outputs = self.model(tensor)

                # The model returns a tuple: (logits_cls, logits_comp)
                if isinstance(outputs, tuple):
                    logits_cls = outputs[0]
                    logits_comp = outputs[1]
                else:
                    # Fallback if the model is differently traced
                    logits_cls = outputs
                    logits_comp = None

                prob_cls = torch.nn.functional.softmax(logits_cls, dim=1)
                confidence, pred_class_idx = torch.max(prob_cls, dim=1)

                output_index = int(pred_class_idx.item())
                predicted_canonical_id = self.output_index_to_exercise_id[output_index]

                comp_score = 0.0
                if logits_comp is not None:
                    comp_score = logits_comp.item()
                    # Clip score to standard range
                    comp_score = max(0.0, min(100.0, comp_score))

                # Return class probabilities for all classes (for smoothing)
                probabilities = prob_cls.squeeze().cpu().tolist()

                return {
                    "exercise_id": predicted_canonical_id,
                    "confidence": confidence.item(),
                    "completion_score": comp_score,
                    "probabilities": probabilities,
                }

    def get_status(self) -> Dict[str, Any]:
        """Get model loader status for health checks."""
        return {
            "loaded": self._loaded,
            "error": self._load_error,
            "device": str(self.device),
            "model_available": self.model is not None,
        }

    def get_exercise_info(self, exercise_id: int) -> Optional[Dict[str, Any]]:
        """
        Get exercise information by ID.

        Args:
            exercise_id: Canonical exercise ID

        Returns:
            Exercise info dict or None if not found
        """
        return self.id_to_exercise.get(exercise_id)


# Module-level singleton instance
model_loader = ModelLoader()
