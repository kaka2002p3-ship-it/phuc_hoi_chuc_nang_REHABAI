from typing import Dict, Any
import torch


def _reject_unknown(config: Dict[str, Any], allowed: set, model_id: str) -> None:
    unknown = set(config) - allowed
    if unknown:
        raise ValueError(f"Unsupported config keys for {model_id}: {sorted(unknown)}")


def get_model(model_id: str, config: Dict[str, Any] = None) -> torch.nn.Module:
    """Instantiate a registered model from an explicit, validated configuration."""
    if not model_id or not isinstance(model_id, str):
        raise ValueError("model_id must be a non-empty string")
    config = dict(config or {})
    model_id_lower = model_id.lower()

    if model_id_lower == "mlp":
        from training.models.baselines import MLPBaseline
        _reject_unknown(config, {"input_dim", "num_exercises"}, model_id)
        return MLPBaseline(**config)
    if model_id_lower == "lstm":
        from training.models.baselines import LSTMBaseline
        _reject_unknown(config, {"input_dim", "num_exercises", "hidden_size", "num_layers", "bidirectional"}, model_id)
        return LSTMBaseline(**config)
    if model_id_lower == "bilstm":
        from training.models.baselines import BiLSTMBaseline
        _reject_unknown(config, {"input_dim", "num_exercises", "hidden_size", "num_layers"}, model_id)
        return BiLSTMBaseline(**config)
    if model_id_lower == "tcn":
        from training.models.baselines import TCNBaseline
        _reject_unknown(config, {"input_dim", "num_exercises", "channels"}, model_id)
        return TCNBaseline(**config)
    if model_id_lower == "stgcn":
        from training.models.baselines import BasicSTGCN
        _reject_unknown(config, {"input_dim", "num_exercises"}, model_id)
        return BasicSTGCN(**config)
    if model_id_lower == "rehabmotionnet":
        from training.models.rehab_motionnet import RehabMotionNet
        _reject_unknown(
            config,
            {"num_exercises", "use_hand", "use_kinematic", "use_contrastive", "use_mstcn", "use_attention", "upper_limb_only"},
            model_id,
        )
        return RehabMotionNet(**config)
    if model_id_lower in {"externalencoderadapter", "external_adapter"}:
        from training.models.rehab_motionnet import ExternalEncoderAdapter
        _reject_unknown(config, {"num_exercises", "adapter_dim", "adapter_dropout"}, model_id)
        return ExternalEncoderAdapter(**config)
    if model_id_lower in {"optimizedssladapter", "optimized_ssl_adapter"}:
        from training.models.rehab_motionnet import OptimizedSSLAdapter
        _reject_unknown(config, {"num_exercises", "adapter_dim", "adapter_dropout"}, model_id)
        return OptimizedSSLAdapter(**config)
    if model_id_lower in {"upperlimbctrgcn", "rehabmotionnetv3", "ctr_gcn"}:
        from training.models.ctr_gcn import UpperLimbCTRGCN
        _reject_unknown(config, {"num_exercises", "hidden", "use_hand", "use_kinematic", "upper_limb_only"}, model_id)
        return UpperLimbCTRGCN(**config)
    if model_id_lower == "rehabmodel":
        from training.models.cnn_transformer import RehabModel
        translated = dict(config)
        if "num_exercises" in translated:
            if "num_classes" in translated:
                raise ValueError("Specify only one of num_exercises and num_classes")
            translated["num_classes"] = translated.pop("num_exercises")
        _reject_unknown(translated, {"num_classes", "input_dim", "hidden_dim", "nhead", "num_layers", "dropout"}, model_id)
        return RehabModel(**translated)
    if model_id_lower == "rehabmotionnetencoder":
        from training.models.shared_encoder import SharedMotionEncoder
        _reject_unknown(config, {"input_dim", "hidden_dim", "channels"}, model_id)
        return SharedMotionEncoder(**config)
    raise ValueError(f"Unknown model_id requested from registry: {model_id}")

