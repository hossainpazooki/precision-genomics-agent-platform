# Precision Genomics Agent Platform

Claude-orchestrated precision genomics platform for multi-omics biomarker discovery, built on the precisionFDA MSI classification challenge. Combines statistical ML pipelines with LLM-driven agent skills, MCP tool integration, and Temporal workflow orchestration.

## Architecture

```
precision-genomics-agent-platform/
|
|-- core/             Core ML engine (imputation, feature selection, classification, cross-omics matching)
|-- mcp_server/       Model Context Protocol server exposing genomics tools to Claude
|-- agent_skills/     High-level agent skills (biomarker discovery, sample QC)
|-- workflows/        Temporal durable workflows for long-running analysis pipelines
|-- api/              FastAPI REST service with analysis and biomarker endpoints
|-- evals/            Evaluation framework (biological validity, reproducibility, hallucination, benchmarks)
|-- prompts/          System prompts for Claude agent orchestration
|-- data/             Raw and processed data directory
|-- tests/            Comprehensive test suite
```

### Core ML Engine (`core/`)

Statistical and ML modules for multi-omics analysis:

- **Imputation** -- MNAR-aware imputation with gender-stratified Y-chromosome handling, using KNN, iterative, and minimum-value strategies
- **Availability Filter** -- Feature filtering by sample availability threshold with missingness-not-at-random detection
- **Feature Selection** -- Multi-strategy selector combining random forest importance, mutual information, and stability selection with consensus scoring
- **Classifier** -- Ensemble mismatch classifier using logistic regression, random forest, and gradient boosting with cross-validated predictions
- **Cross-Omics Matcher** -- Proteomics/RNA-Seq concordance analysis using Spearman correlation and distance matrices
- **Pipeline** -- COSMO-inspired orchestration pipeline coordinating all stages from raw data to final biomarker panels

### MCP Server (`mcp_server/`)

Model Context Protocol server exposing 8 genomics tools for Claude integration:

| Tool | Description |
|------|-------------|
| `data_loader` | Load and validate multi-omics TSV datasets |
| `impute_missing` | Run MNAR-aware imputation on expression matrices |
| `availability_check` | Filter features by availability threshold |
| `biomarker_selector` | Multi-strategy feature selection with consensus |
| `classifier` | Train and evaluate ensemble mismatch classifiers |
| `match_cross_omics` | Cross-omics concordance analysis |
| `evaluator` | Run evaluation suite on agent outputs |
| `explainer` | Generate biological interpretations of results |

### Agent Skills (`agent_skills/`)

High-level skills that compose MCP tools into multi-step analyses:

- **Biomarker Discovery** -- End-to-end biomarker panel identification from raw data
- **Sample QC** -- Sample mismatch detection and quality control

### Temporal Workflows (`workflows/`)

Durable, fault-tolerant workflow orchestration:

- **Biomarker Discovery Workflow** -- Long-running multi-omics analysis with checkpointing
- **Sample QC Workflow** -- Automated sample quality assessment pipeline
- **Activities** -- Individual workflow steps (data loading, imputation, feature selection, classification, cross-omics matching, evaluation)

### FastAPI Service (`api/`)

REST API for triggering and monitoring analyses:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/analyses` | Start a new analysis run |
| `GET` | `/api/v1/analyses/{id}` | Get analysis status and results |
| `GET` | `/api/v1/analyses` | List analysis runs with filtering |
| `POST` | `/api/v1/biomarkers/panels` | Create a biomarker panel |
| `GET` | `/api/v1/biomarkers/panels/{id}` | Get panel details |
| `GET` | `/api/v1/biomarkers/panels` | List panels with filtering |

Includes audit logging middleware and optional API key authentication.

### Evaluation Framework (`evals/`)

Four evaluators for validating agent-selected biomarker panels:

| Evaluator | Metric | Default Threshold |
|-----------|--------|-------------------|
| **Biological Validity** | Fraction of known MSI pathways covered | 60% |
| **Reproducibility** | Average pairwise Jaccard similarity across runs | 85% |
| **Hallucination Detection** | Fraction of PubMed citations that are verifiable | 90% |
| **Benchmark Comparison** | Jaccard similarity against published signatures | Any overlap |

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for PostgreSQL/TimescaleDB, Redis, Temporal)

### Infrastructure

```bash
docker-compose up -d
```

This starts:
- **TimescaleDB** (PostgreSQL 16) on port 5432
- **Redis** on port 6379
- **Temporal** on port 7233
- **Temporal UI** on port 8233

### Install

```bash
# All dependencies (ML, LLM, Temporal, MCP, dev)
pip install -e ".[all]"

# Or minimal + specific extras
pip install -e ".[ml,dev]"
```

### Run the API

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Run the Temporal Worker

```bash
python -m workflows.worker
```

## Development

### Install Dev Dependencies

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov

# Specific test module
pytest tests/test_evals/

# Verbose
pytest -v tests/test_evals/test_biological_validity.py
```

### Lint and Format

```bash
# Check
ruff check .
ruff format --check .

# Fix
ruff check --fix .
ruff format .
```

## Project Structure

```
precision-genomics-agent-platform/
├── api/
│   ├── __init__.py
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── audit.py
│   │   └── auth.py
│   └── routes/
│       ├── __init__.py
│       ├── analysis.py
│       └── biomarkers.py
├── agent_skills/
│   ├── __init__.py
│   ├── biomarker_discovery.py
│   └── sample_qc.py
├── core/
│   ├── __init__.py
│   ├── availability.py
│   ├── classifier.py
│   ├── config.py
│   ├── constants.py
│   ├── cross_omics_matcher.py
│   ├── feature_selection.py
│   ├── imputation.py
│   ├── models.py
│   └── pipeline.py
├── evals/
│   ├── __init__.py
│   ├── benchmark_comparison.py
│   ├── biological_validity.py
│   ├── hallucination_detection.py
│   ├── reproducibility.py
│   └── fixtures/
│       └── known_msi_signatures.json
├── mcp_server/
│   ├── __init__.py
│   ├── schemas/
│   ├── server.py
│   └── tools/
│       ├── __init__.py
│       ├── availability_check.py
│       ├── biomarker_selector.py
│       ├── classifier.py
│       ├── data_loader.py
│       ├── evaluator.py
│       ├── explainer.py
│       ├── impute_missing.py
│       └── match_cross_omics.py
├── prompts/
├── workflows/
│   ├── __init__.py
│   ├── activities/
│   ├── biomarker_discovery.py
│   ├── config.py
│   ├── sample_qc.py
│   ├── schemas.py
│   └── worker.py
├── tests/
│   ├── conftest.py
│   └── test_evals/
│       ├── __init__.py
│       ├── test_benchmark_comparison.py
│       ├── test_biological_validity.py
│       ├── test_hallucination_detection.py
│       └── test_reproducibility.py
├── data/
├── docs/
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.worker
├── pyproject.toml
├── ruff.toml
└── README.md
```

## License

Proprietary. Internal use only.
