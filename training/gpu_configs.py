"""GPU training configuration presets for Vertex AI custom training jobs."""

from __future__ import annotations

GPU_TRAINING_CONFIG: dict = {
    "slm_finetuning": {
        "accelerator_type": "NVIDIA_TESLA_A100",
        "accelerator_count": 1,
        "machine_type": "a2-highgpu-1g",
        "description": "QLoRA/DoRA SLM fine-tuning",
    },
    "expression_encoder": {
        "accelerator_type": "NVIDIA_TESLA_A100",
        "accelerator_count": 2,
        "machine_type": "a2-highgpu-2g",
        "description": "Contrastive expression encoder DDP training",
    },
    "cuml_benchmark": {
        "accelerator_type": "NVIDIA_L4",
        "accelerator_count": 1,
        "machine_type": "g2-standard-4",
        "description": "cuML GPU-accelerated ensemble classifier",
    },
}
