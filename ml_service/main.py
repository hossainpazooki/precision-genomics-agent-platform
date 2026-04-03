"""Thin FastAPI wrapper around core ML modules.

Exposes the Python ML algorithms as HTTP endpoints for the TypeScript
Next.js frontend to call. This replaces direct Python imports with
HTTP service calls.

Endpoints:
    POST /ml/impute     — NMF imputation
    POST /ml/classify   — Ensemble classification
    POST /ml/features   — Multi-strategy feature selection
    POST /ml/match      — Cross-omics matching
    POST /ml/evaluate   — Model evaluation
    POST /ml/synthetic  — Synthetic cohort generation
    POST /ml/pipeline   — Full pipeline execution
    POST /ml/availability — Gene availability check
    POST /ml/explain    — Feature explanation (Claude)
    POST /ml/explain-local — Feature explanation (SLM)
    POST /ml/dspy/*     — DSPy proxy endpoints
    GET  /health        — Health check
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mcp_server.schemas.omics import (
    CheckAvailabilityInput,
    EvaluateModelInput,
    ExplainFeaturesInput,
    ExplainFeaturesLocalInput,
    ImputeMissingInput,
    MatchCrossOmicsInput,
    RunClassificationInput,
    SelectBiomarkersInput,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Precision Genomics ML Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": "ml"}


# ---------------------------------------------------------------------------
# ML Endpoints — delegate to core modules
# ---------------------------------------------------------------------------


@app.post("/ml/impute")
async def impute(params: ImputeMissingInput) -> dict:
    """Run NMF imputation."""
    from mcp_server.tools.impute_missing import run_tool

    result = await run_tool(params)
    return result.model_dump()


@app.post("/ml/classify")
async def classify(params: RunClassificationInput) -> dict:
    """Run ensemble classification."""
    from mcp_server.tools.classifier import run_tool

    result = await run_tool(params)
    return result.model_dump()


@app.post("/ml/features")
async def features(params: SelectBiomarkersInput) -> dict:
    """Run multi-strategy feature selection."""
    from mcp_server.tools.biomarker_selector import run_tool

    result = await run_tool(params)
    return result.model_dump()


@app.post("/ml/match")
async def match(params: MatchCrossOmicsInput) -> dict:
    """Run cross-omics matching."""
    from mcp_server.tools.match_cross_omics import run_tool

    result = await run_tool(params)
    return result.model_dump()


@app.post("/ml/evaluate")
async def evaluate(params: EvaluateModelInput) -> dict:
    """Evaluate model on holdout data."""
    from mcp_server.tools.evaluator import run_tool

    result = await run_tool(params)
    return result.model_dump()


@app.post("/ml/availability")
async def availability(params: CheckAvailabilityInput) -> dict:
    """Check gene availability."""
    from mcp_server.tools.availability_check import run_tool

    result = await run_tool(params)
    return result.model_dump()


@app.post("/ml/explain")
async def explain(params: ExplainFeaturesInput) -> dict:
    """Explain features using pathway knowledge + LLM."""
    from mcp_server.tools.explainer import run_tool

    result = await run_tool(params)
    return result.model_dump()


@app.post("/ml/explain-local")
async def explain_local(params: ExplainFeaturesLocalInput) -> dict:
    """Explain features using fine-tuned SLM."""
    from mcp_server.tools.explain_features_local import run_tool

    result = await run_tool(params)
    return result.model_dump()


@app.post("/ml/synthetic")
async def synthetic(n_samples: int = 100) -> dict:
    """Generate synthetic cohort."""
    try:
        from core.synthetic import SyntheticCohortGenerator

        gen = SyntheticCohortGenerator(n_samples=n_samples)
        data = gen.generate()
        return {
            "n_samples": n_samples,
            "modalities": list(data.keys()) if isinstance(data, dict) else [],
            "status": "generated",
        }
    except Exception as exc:
        return {"error": str(exc), "n_samples": n_samples}


@app.post("/ml/pipeline")
async def pipeline(
    dataset: str = "train",
    target: str = "msi",
    modalities: list[str] | None = None,
    n_top_features: int = 30,
) -> dict:
    """Run full COSMO pipeline."""
    try:
        from core.pipeline import COSMOInspiredPipeline

        pipe = COSMOInspiredPipeline()
        result = pipe.run(
            dataset=dataset,
            target=target,
            modalities=modalities or ["proteomics", "rnaseq"],
            n_top_features=n_top_features,
        )
        return result if isinstance(result, dict) else {"status": "completed"}
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


# ---------------------------------------------------------------------------
# DSPy Proxy Endpoints
# ---------------------------------------------------------------------------


@app.post("/ml/dspy/biomarker-discovery")
async def dspy_biomarker_discovery(params: dict | None = None) -> dict:
    """Run DSPy biomarker discovery module."""
    try:
        from dspy_modules.biomarker_discovery import BiomarkerDiscoveryModule

        module = BiomarkerDiscoveryModule()
        result = module(**(params or {}))
        return result if isinstance(result, dict) else {"result": str(result)}
    except ImportError:
        return {"status": "skipped", "reason": "dspy not installed"}
    except Exception as exc:
        return {"error": str(exc)}


@app.post("/ml/dspy/sample-qc")
async def dspy_sample_qc(params: dict | None = None) -> dict:
    """Run DSPy sample QC module."""
    try:
        from dspy_modules.sample_qc import SampleQCModule

        module = SampleQCModule()
        result = module(**(params or {}))
        return result if isinstance(result, dict) else {"result": str(result)}
    except ImportError:
        return {"status": "skipped", "reason": "dspy not installed"}
    except Exception as exc:
        return {"error": str(exc)}


@app.post("/ml/dspy/feature-interpret")
async def dspy_feature_interpret(params: dict | None = None) -> dict:
    """Run DSPy feature interpretation module."""
    try:
        from dspy_modules.feature_interpret import FeatureInterpretModule

        module = FeatureInterpretModule()
        result = module(**(params or {}))
        return result if isinstance(result, dict) else {"result": str(result)}
    except ImportError:
        return {"status": "skipped", "reason": "dspy not installed"}
    except Exception as exc:
        return {"error": str(exc)}


@app.post("/ml/dspy/regulatory-report")
async def dspy_regulatory_report(params: dict | None = None) -> dict:
    """Run DSPy regulatory report module."""
    try:
        from dspy_modules.regulatory_report import RegulatoryReportModule

        module = RegulatoryReportModule()
        result = module(**(params or {}))
        return result if isinstance(result, dict) else {"result": str(result)}
    except ImportError:
        return {"status": "skipped", "reason": "dspy not installed"}
    except Exception as exc:
        return {"error": str(exc)}


@app.post("/ml/dspy/compile")
async def dspy_compile(params: dict | None = None) -> dict:
    """Compile DSPy modules."""
    try:
        from dspy_modules.compile import compile_module

        result = compile_module(**(params or {}))
        return result if isinstance(result, dict) else {"status": "compiled"}
    except ImportError:
        return {"status": "skipped", "reason": "dspy not installed"}
    except Exception as exc:
        return {"error": str(exc)}
