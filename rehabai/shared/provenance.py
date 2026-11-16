import os
import json
import hashlib
import hmac
import math
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import datetime

STATUS_MOCK = "MOCK"
STATUS_REJECTED = "REJECTED"
STATUS_REAL_CANDIDATE = "REAL_CANDIDATE"
STATUS_REAL_VERIFIED = "REAL_VERIFIED"
STATUS_UNKNOWN = "UNKNOWN"
VERIFICATION_KEY_ENV = "REHABAI_PROVENANCE_HMAC_KEY"
VERIFICATION_AUTHORITY = "rehabai_strict_verifier_v2"
VERIFICATION_SCHEMA_VERSION = "1.2"

CANONICAL_FIELDS = [
    "schema_version",
    "sample_id",
    "dataset",
    "source_record_id",
    "source_video_exists", # Although we don't trust it fully, it's part of canonical intent
    "source_video_size",
    "source_video_sha256",
    "subject_id",
    "exercise_id",
    "completion_label",
    "label_source",
    "subject_source",
    "extraction_log_present",
    "extraction_status",
    "extractor_name",
    "extractor_version",
    "generation_script",
    "processed_exists",
    "processed_feature_sha256",
    "feature_shape",
    "frame_count",
    "quality_gate_passed",
    "data_status",
    "verification_evidence"
]

def compute_sha256(file_path: str) -> str:
    """Compute SHA256 hash of a file."""
    if not os.path.exists(file_path):
        return ""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def normalize_value(val: Any) -> Any:
    if isinstance(val, float) and math.isnan(val):
        return None
    if isinstance(val, str):
        val = val.strip()
        if val == "":
            return None
    return val

def canonical_provenance_hash(record: Dict[str, Any]) -> str:
    """Generate a deterministic hash from a canonical record using an explicit allowlist."""
    canonical = {}
    for k in CANONICAL_FIELDS:
        # Normalize to handle NaN/None uniformly
        val = normalize_value(record.get(k))
        if val is not None:
            # Enforce strictly string representations where appropriate, or keep as is.
            # Convert to float/int if applicable to be robust against CSV representations
            if isinstance(val, float) and val.is_integer():
                 val = int(val)
            canonical[k] = val

    # Must always include schema_version in hash payload
    canonical["schema_version"] = "1.1"

    # Strict deterministic JSON serialization
    sorted_keys_json = json.dumps(canonical, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(sorted_keys_json.encode('utf-8')).hexdigest()

def _require_verification_key(verification_key: Optional[str] = None) -> bytes:
    key = verification_key or os.environ.get(VERIFICATION_KEY_ENV)
    if not key or len(key) < 32:
        raise ValueError(f"A verification key of at least 32 characters is required via {VERIFICATION_KEY_ENV}.")
    return key.encode("utf-8")

def _resolve_file_within(root: str, candidate: str, label: str) -> Tuple[Path, Path]:
    if not root:
        raise ValueError(f"{label} root is required in strict research mode.")
    try:
        root_path = Path(root).resolve(strict=True)
        candidate_path = Path(candidate)
        if not candidate_path.is_absolute():
            candidate_path = root_path / candidate_path
        resolved = candidate_path.resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"{label} does not exist or cannot be resolved: {candidate}") from exc
    if not resolved.is_relative_to(root_path):
        raise ValueError(f"Path escape detected: {label} {resolved} is outside {root_path}")
    if not resolved.is_file():
        raise ValueError(f"{label} is not a file: {resolved}")
    return root_path, resolved

def _unsigned_authority_payload(record: Dict[str, Any], evidence: Dict[str, Any]) -> bytes:
    unsigned_record = {key: normalize_value(record.get(key)) for key in CANONICAL_FIELDS if key != "verification_evidence"}
    unsigned_record["schema_version"] = "1.1"
    unsigned_evidence = {key: value for key, value in evidence.items() if key != "authority_signature"}
    payload = {"record": unsigned_record, "evidence": unsigned_evidence}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

def _authority_signature(record: Dict[str, Any], evidence: Dict[str, Any], key: bytes) -> str:
    return hmac.new(key, _unsigned_authority_payload(record, evidence), hashlib.sha256).hexdigest()

def build_provenance_record(
    source_video_path: Optional[str],
    subject_id: Any,
    exercise_id: Any,
    completion_label: Any,
    extraction_status: Any,
    extractor_version: Any,
    interim_path: Optional[str] = None,
    processed_path: Optional[str] = None,
    quality_gate_passed: bool = False,
    compute_hash: bool = False
) -> Dict[str, Any]:
    """
    Build a canonical provenance record for a sample.
    """
    # Normalize inputs
    source_video_path = normalize_value(source_video_path)
    subject_id = normalize_value(subject_id)
    exercise_id = normalize_value(exercise_id)
    completion_label = normalize_value(completion_label)
    extraction_status = normalize_value(extraction_status)
    extractor_version = normalize_value(extractor_version)
    interim_path = normalize_value(interim_path)
    processed_path = normalize_value(processed_path)
    
    # Check actual file existence
    source_exists = os.path.exists(source_video_path) if source_video_path else False
    video_size = os.path.getsize(source_video_path) if source_exists else 0
    video_hash = compute_sha256(source_video_path) if (source_exists and compute_hash) else ""
    
    interim_exists = os.path.exists(interim_path) if interim_path else False
    processed_exists = os.path.exists(processed_path) if processed_path else False
    processed_hash = compute_sha256(processed_path) if (processed_exists and compute_hash) else ""
    
    # Classification logic (Fail-closed)
    data_status = STATUS_UNKNOWN
    exclusion_reasons = []
    
    ext_ver_str = str(extractor_version).lower() if extractor_version else ""
    
    # Strict cascade
    if "mock" in ext_ver_str or "synthetic" in ext_ver_str:
        data_status = STATUS_MOCK
        exclusion_reasons.append("Mock extractor version detected.")
    elif extraction_status != "success":
        data_status = STATUS_REJECTED
        exclusion_reasons.append(f"Extraction failed: {extraction_status}")
    elif not quality_gate_passed:
        data_status = STATUS_REJECTED
        exclusion_reasons.append("Quality gate failed.")
    elif extraction_status == "success" and quality_gate_passed and source_exists and processed_exists:
        # Passed base technical gates
        data_status = STATUS_REAL_CANDIDATE
    else:
        data_status = STATUS_UNKNOWN
        exclusion_reasons.append("Missing source or processed files despite success status.")

    record = {
        "schema_version": "1.1",
        "sample_id": os.path.basename(processed_path) if processed_path else "unknown",
        "dataset": "Upper_Limb_Stroke",
        "source_record_id": os.path.basename(source_video_path) if source_video_path else "unknown",
        "source_video_path": source_video_path if source_video_path else "",
        "source_video_exists": source_exists,
        "source_video_size": video_size,
        "source_video_sha256": video_hash,
        "subject_id": str(subject_id) if subject_id is not None else "unknown",
        "exercise_id": exercise_id if exercise_id is not None else -1,
        "completion_label": completion_label if completion_label is not None else -1,
        "label_source": "metadata" if subject_id and exercise_id else "unknown",
        "subject_source": "metadata" if subject_id else "unknown",
        "extraction_log_present": extraction_status is not None,
        "extraction_status": str(extraction_status) if extraction_status else "unknown",
        "extractor_name": "RehabAI_Extractor",
        "extractor_version": str(extractor_version) if extractor_version else "unknown",
        "generation_script": "unknown",
        "interim_feature_path": interim_path if interim_path else "",
        "processed_feature_path": processed_path if processed_path else "",
        "processed_exists": processed_exists,
        "processed_feature_sha256": processed_hash,
        "feature_shape": "",
        "frame_count": 0,
        "created_at": "",
        "quality_gate_passed": bool(quality_gate_passed),
        "data_status": data_status,
        "exclusion_reasons": "; ".join(exclusion_reasons)
    }
    
    # Record cannot be REAL_VERIFIED without going through verification function
    record["provenance_hash"] = canonical_provenance_hash(record)
    
    return record

def verify_and_grant_real_verified(
    record: Dict[str, Any],
    source_root: str,
    processed_root: str,
    verification_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Elevates a record from REAL_CANDIDATE to REAL_VERIFIED by strictly asserting physical evidence.
    """
    if normalize_value(record.get("data_status")) != STATUS_REAL_CANDIDATE:
        raise ValueError("Only REAL_CANDIDATE records can be verified.")
        
    src_path = normalize_value(record.get("source_video_path"))
    proc_path = normalize_value(record.get("processed_feature_path"))
    
    if not src_path or not proc_path:
        raise ValueError("Missing paths for physical verification.")
        
    key = _require_verification_key(verification_key)
    src_root, resolved_src = _resolve_file_within(source_root, src_path, "source video")
    proc_root, resolved_proc = _resolve_file_within(processed_root, proc_path, "processed feature")
    abs_src = str(resolved_src)
    abs_proc = str(resolved_proc)

    actual_src_hash = compute_sha256(abs_src)
    actual_proc_hash = compute_sha256(abs_proc)
    
    expected_src_hash = normalize_value(record.get("source_video_sha256"))
    expected_proc_hash = normalize_value(record.get("processed_feature_sha256"))
    
    if expected_src_hash and expected_src_hash != actual_src_hash:
        raise ValueError("Source video hash mismatch.")
        
    if expected_proc_hash and expected_proc_hash != actual_proc_hash:
        raise ValueError("Processed feature hash mismatch.")
        
    record_copy = dict(record)
    record_copy["data_status"] = STATUS_REAL_VERIFIED
    record_copy["source_record_id"] = resolved_src.relative_to(src_root).as_posix()
    record_copy["sample_id"] = resolved_proc.relative_to(proc_root).as_posix()
    
    # Must update canonical fields with actual physical checksums
    record_copy["source_video_sha256"] = actual_src_hash
    record_copy["processed_feature_sha256"] = actual_proc_hash
    
    evidence = {
        "verification_schema_version": VERIFICATION_SCHEMA_VERSION,
        "verification_status": STATUS_REAL_VERIFIED,
        "verification_method": "physical_checksum_match",
        "verified_by": VERIFICATION_AUTHORITY,
        "verified_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_checksum": actual_src_hash,
        "processed_checksum": actual_proc_hash,
        "source_relative_identity": record_copy["source_record_id"],
        "processed_relative_identity": record_copy["sample_id"]
    }
    evidence["authority_signature"] = _authority_signature(record_copy, evidence, key)
    
    record_copy["verification_evidence"] = json.dumps(evidence, sort_keys=True)
    
    # Update hash after status change
    record_copy["provenance_hash"] = canonical_provenance_hash(record_copy)
    return record_copy

def check_eligibility(record: Dict[str, Any], verification_key: Optional[str] = None) -> Tuple[bool, str]:
    """
    Research eligibility gate (Logical check).
    Returns (is_eligible, exclusion_reason).
    This only checks metadata, not physical files.
    """
    reasons = []
    
    data_status = normalize_value(record.get("data_status"))
    if data_status != STATUS_REAL_VERIFIED:
        reasons.append(f"Invalid data_status: {data_status} (must be {STATUS_REAL_VERIFIED})")
        
    evidence = record.get("verification_evidence")
    if isinstance(evidence, str):
        try:
            evidence = json.loads(evidence)
        except Exception:
            reasons.append("verification_evidence must be valid JSON.")

    if data_status == STATUS_REAL_VERIFIED and not evidence:
        reasons.append("Missing verification_evidence for REAL_VERIFIED status.")
        
    if evidence and isinstance(evidence, dict):
        if normalize_value(evidence.get("verified_by")) != VERIFICATION_AUTHORITY:
             reasons.append("Invalid verification authority.")
        if normalize_value(evidence.get("verification_schema_version")) != VERIFICATION_SCHEMA_VERSION:
             reasons.append("Invalid or missing verification_schema_version.")
        if normalize_value(evidence.get("verification_status")) != STATUS_REAL_VERIFIED:
             reasons.append("Evidence status does not match REAL_VERIFIED.")
        if normalize_value(evidence.get("verification_method")) != "physical_checksum_match":
             reasons.append("Invalid verification_method.")
             
        # Evidence must match canonical record claims
        if normalize_value(evidence.get("source_checksum")) != normalize_value(record.get("source_video_sha256")):
             reasons.append("Evidence source_checksum mismatches canonical record.")
        if normalize_value(evidence.get("processed_checksum")) != normalize_value(record.get("processed_feature_sha256")):
             reasons.append("Evidence processed_checksum mismatches canonical record.")
             
        if normalize_value(evidence.get("source_relative_identity")) != normalize_value(record.get("source_record_id")):
             reasons.append("Evidence source identity mismatches canonical record.")
        if normalize_value(evidence.get("processed_relative_identity")) != normalize_value(record.get("sample_id")):
             reasons.append("Evidence processed identity mismatches canonical record.")

        verified_at = normalize_value(evidence.get("verified_at"))
        try:
            parsed_time = datetime.datetime.fromisoformat(str(verified_at))
            if parsed_time.tzinfo is None:
                raise ValueError("timezone missing")
        except (TypeError, ValueError):
            reasons.append("verified_at must be a timezone-aware ISO-8601 timestamp.")

        signature = normalize_value(evidence.get("authority_signature"))
        try:
            key = _require_verification_key(verification_key)
            expected_signature = _authority_signature(record, evidence, key)
            if not signature or not hmac.compare_digest(str(signature), expected_signature):
                reasons.append("Invalid verification authority signature.")
        except ValueError as exc:
            reasons.append(str(exc))

    # The canonical hash is mandatory regardless of evidence parsing outcome.
    expected_prov = record.get("provenance_hash")
    actual_prov = canonical_provenance_hash(record)
    if not expected_prov or not isinstance(expected_prov, str) or len(expected_prov) != 64:
         reasons.append("Missing or invalid provenance_hash.")
    elif expected_prov != actual_prov:
         reasons.append(
             f"Provenance hash mismatch. Canonical hash was tampered with. Expected {expected_prov}, got {actual_prov}"
         )

    ext_status = normalize_value(record.get("extraction_status"))
    if ext_status != "success":
        reasons.append(f"Invalid extraction_status: {ext_status}")
        
    gate_passed = record.get("quality_gate_passed")
    # Strict boolean parsing
    if isinstance(gate_passed, str):
        gate_passed = gate_passed.strip().lower() in ['true', '1', 't', 'y', 'yes']
    if not gate_passed:
        reasons.append("quality_gate_passed is false or invalid")
        
    # Exclusion reasons must be empty
    exc = normalize_value(record.get("exclusion_reasons"))
    if exc is not None:
         reasons.append(f"Record has exclusion reasons: {exc}")

    # File existence claims
    src_exists = record.get("source_video_exists")
    if isinstance(src_exists, str):
        src_exists = src_exists.strip().lower() in ['true', '1', 't', 'y', 'yes']
    if not src_exists:
        reasons.append("source_video_exists is false")
        
    proc_exists = record.get("processed_exists")
    if isinstance(proc_exists, str):
        proc_exists = proc_exists.strip().lower() in ['true', '1', 't', 'y', 'yes']
    if not proc_exists:
         reasons.append("processed_exists is false")
             
    # Strict metadata checks
    subject_id = normalize_value(record.get("subject_id"))
    if subject_id is None or str(subject_id).strip() == "" or str(subject_id).lower() == "unknown":
        reasons.append("Invalid or missing subject_id")
        
    try:
        ex_id = int(float(record.get("exercise_id", -1)))
        if ex_id not in [1, 2, 3, 4]:
            reasons.append(f"Invalid exercise_id: {ex_id}")
    except (ValueError, TypeError):
        reasons.append(f"Invalid exercise_id format: {record.get('exercise_id')}")
        
    try:
        comp_label = float(record.get("completion_label", -1.0))
        if comp_label not in [0.0, 1.0]:
            reasons.append(f"Invalid completion_label: {comp_label}")
    except (ValueError, TypeError):
        reasons.append(f"Invalid completion_label format: {record.get('completion_label')}")
        
    sample_id = normalize_value(record.get("sample_id"))
    if not sample_id or sample_id == "unknown":
         reasons.append("Missing sample_id")

    # Checksum requirement
    if data_status == STATUS_REAL_VERIFIED:
        ssha = normalize_value(record.get("source_video_sha256"))
        if not ssha or len(ssha) != 64 or not all(c in '0123456789abcdefABCDEF' for c in ssha):
            reasons.append("Missing or invalid source_video_sha256 format")
        psha = normalize_value(record.get("processed_feature_sha256"))
        if not psha or len(psha) != 64 or not all(c in '0123456789abcdefABCDEF' for c in psha):
            reasons.append("Missing or invalid processed_feature_sha256 format")

    if len(reasons) > 0:
        return False, "; ".join(reasons)
        
    return True, ""

def check_physical_eligibility(
    record: Dict[str, Any],
    data_dir: str,
    source_dir: str,
    verification_key: Optional[str] = None,
) -> Tuple[bool, str]:
    """Fail-closed logical and physical integrity validation."""
    if not data_dir or not source_dir:
        return False, "Both data_dir and source_dir are required in strict research mode."

    ok, reason = check_eligibility(record, verification_key=verification_key)
    if not ok:
        return False, f"Logical validation failed: {reason}"

    sample_id = normalize_value(record.get("sample_id"))
    source_id = normalize_value(record.get("source_record_id"))
    if not sample_id or not source_id:
        return False, "sample_id and source_record_id are required."

    try:
        _, processed_path = _resolve_file_within(data_dir, str(sample_id), "processed feature")
        _, source_path = _resolve_file_within(source_dir, str(source_id), "source video")
    except (OSError, ValueError) as exc:
        return False, str(exc)

    actual_proc_hash = compute_sha256(str(processed_path))
    expected_proc_hash = normalize_value(record.get("processed_feature_sha256"))
    if actual_proc_hash != expected_proc_hash:
        return False, f"Processed feature hash mismatch. Expected {expected_proc_hash}, got {actual_proc_hash}"

    actual_src_hash = compute_sha256(str(source_path))
    expected_src_hash = normalize_value(record.get("source_video_sha256"))
    if actual_src_hash != expected_src_hash:
        return False, f"Source video hash mismatch. Expected {expected_src_hash}, got {actual_src_hash}"

    return True, ""

def filter_or_reject_manifest(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Filters a manifest returning eligible and excluded records separately (Logical only)."""
    eligible = []
    excluded = []
    seen_samples = set()
    seen_sources = set()
    
    for r in records:
        # Avoid mutating input
        record_copy = dict(r)
        
        ok, reason = check_eligibility(record_copy)
        
        sample_id = normalize_value(record_copy.get("sample_id"))
        source_id = normalize_value(record_copy.get("source_record_id"))
        
        if ok:
            if sample_id in seen_samples:
                ok = False
                reason = "Duplicate sample_id"
            elif source_id in seen_sources:
                ok = False
                reason = "Duplicate source_record_id"
                
        if ok:
            seen_samples.add(sample_id)
            seen_sources.add(source_id)
            eligible.append(record_copy)
        else:
            record_copy["exclusion_reasons"] = reason
            excluded.append(record_copy)
            
    return eligible, excluded
