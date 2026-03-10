"""DSPy prompt optimization activities."""

from __future__ import annotations


async def generate_synthetic_cohort_activity(config: dict) -> dict:
    """Generate synthetic cohort data for prompt optimization."""
    from core.synthetic import generate_synthetic_dataset

    n_samples = config.get("n_samples", 200)
    target = config.get("target", "msi")
    seed = config.get("seed", 42)

    dataset = generate_synthetic_dataset(
        n_samples=n_samples, target=target, seed=seed
    )

    return {
        "n_samples": n_samples,
        "target": target,
        "n_features": dataset.get("n_features", 0),
        "dataset_summary": dataset.get("summary", ""),
        "seed": seed,
    }


async def run_pipeline_with_prompts_activity(config: dict) -> dict:
    """Run the pipeline with current prompts and collect results."""
    from core.pipeline import run_pipeline

    dataset = config.get("dataset", "synthetic")
    target = config.get("target", "msi")
    prompt_version = config.get("prompt_version", "baseline")

    results = run_pipeline(dataset=dataset, target=target)

    return {
        "dataset": dataset,
        "target": target,
        "prompt_version": prompt_version,
        "accuracy": results.get("accuracy", 0.0),
        "auc": results.get("auc", 0.0),
        "report": results.get("report", ""),
        "feature_list": results.get("feature_list", ""),
        "dataset_summary": results.get("dataset_summary", ""),
        "imputation_stats": results.get("imputation_stats", ""),
    }


async def compile_dspy_modules_activity(config: dict) -> dict:
    """Compile DSPy modules with training data."""
    from dspy_modules.compile import compile_module, load_training_examples
    from dspy_modules.metrics import composite_metric

    module_name = config.get("module", "biomarker_discovery")
    strategy = config.get("strategy", "mipro")
    training_path = config.get("training_path")

    trainset = load_training_examples(path=training_path)
    if not trainset:
        return {
            "module": module_name,
            "status": "skipped",
            "reason": "no training examples",
        }

    from importlib import import_module

    module_map = {
        "biomarker_discovery": ("dspy_modules.biomarker_discovery", "BiomarkerDiscoveryModule"),
        "sample_qc": ("dspy_modules.sample_qc", "SampleQCModule"),
        "feature_interpret": ("dspy_modules.feature_interpret", "FeatureInterpretModule"),
        "regulatory_report": ("dspy_modules.regulatory_report", "RegulatoryReportModule"),
    }

    mod_path, class_name = module_map[module_name]
    mod = import_module(mod_path)
    module_class = getattr(mod, class_name)
    module = module_class()

    compiled = compile_module(module, trainset, composite_metric, strategy=strategy)

    return {
        "module": module_name,
        "strategy": strategy,
        "status": "compiled",
        "n_training_examples": len(trainset),
        "compiled": compiled is not None,
    }


async def compare_and_deploy_activity(config: dict) -> dict:
    """Compare optimized vs baseline prompts and deploy if better."""
    baseline_score = config.get("baseline_score", 0.0)
    optimized_score = config.get("optimized_score", 0.0)
    module_name = config.get("module", "biomarker_discovery")
    improvement_threshold = config.get("improvement_threshold", 0.05)

    improvement = optimized_score - baseline_score
    should_deploy = improvement >= improvement_threshold

    return {
        "module": module_name,
        "baseline_score": baseline_score,
        "optimized_score": optimized_score,
        "improvement": improvement,
        "deployed": should_deploy,
        "reason": (
            f"Improvement of {improvement:.3f} meets threshold {improvement_threshold}"
            if should_deploy
            else f"Improvement of {improvement:.3f} below threshold {improvement_threshold}"
        ),
    }
