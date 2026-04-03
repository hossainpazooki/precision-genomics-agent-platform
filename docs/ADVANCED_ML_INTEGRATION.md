# Advanced ML Integration — SLM Fine-Tuning, Prompt Optimization & GPU-Accelerated Training

**Precision Genomics Agent Platform — Enhancement Layer**
**Author:** Hossain | **Date:** February 2026
**Prerequisite:** Implementation Plan v3 (Phases 1–7 complete), GCP migration complete

> **✅ STATUS: IMPLEMENTED — March 2026**
>
> All three enhancement layers have been implemented: SLM fine-tuning pipeline (`training/`), DSPy prompt optimization (`dspy_modules/`), and GPU-accelerated training. 328 tests passing, 17 skipped (optional GPU/SLM deps).

---

### Dependencies

This enhancement layer requires:
1. **Implementation Plan v3 Phases 1–7**: Core ML engine, MCP server, agent skills, and GCP migration must be complete (✅ done)
2. **Synthetic Data Generator** (`core/synthetic.py` from `SYNTHETIC_DATA_STRATEGY.md`): Required for SLM training data construction (✅ implemented)
3. **GCP infrastructure**: Vertex AI Custom Training Jobs with A100 or L4 accelerators for QLoRA fine-tuning (~6GB VRAM)
4. **Existing GCP modules**: `core/vertex_training.py`, `core/model_registry.py`, `core/experiment_tracker.py` (✅ implemented in Phase 6–7)

---

## Architectural Rationale

The existing platform uses Claude (Sonnet 4.5 / Opus 4.6) for biological interpretation, scikit-learn for the championship ML pipeline, and hand-crafted system prompts for the four agent skills. This enhancement layer addresses three limitations:

1. **Claude API dependency for routine tasks** — Every `explain_features` call and `generate_interpretation_activity` invocation hits the Anthropic API at ~$3–15/1K tokens. Gene pathway classification and PubMed relevance scoring are narrow, high-frequency tasks where a fine-tuned 7B–8B model can match Claude's accuracy at 100× lower cost and 10× lower latency.

2. **Static prompts without empirical optimization** — The four prompt templates (`biomarker_discovery.md`, `sample_qc_analysis.md`, `feature_interpretation.md`, `regulatory_report.md`) were written by hand. DSPy's compile-optimize-evaluate loop can systematically discover prompt structures that maximize the existing evaluation metrics (Biological Validity ≥60%, Hallucination ≤10%, Reproducibility ≥85%).

3. **CPU-bound training ceiling** — The RF GridSearchCV across 336 parameter combinations is the bottleneck (90s on 80 samples, but scales quadratically with the synthetic `benchmark` cohort of 500+ samples). Adding transformer-based expression encoders (scGPT, Geneformer) for cross-omics matching demands GPU acceleration. DDP training enables scaling to multi-GPU Vertex AI Custom Training Jobs already supported by the platform infrastructure.

```
Enhancement Architecture (overlaid on existing platform):

┌─────────────────────────────────────────────────────────────────────────┐
│  Claude (Opus 4.6) — Complex reasoning, report generation, novel       │
│                       interpretation, multi-step agentic orchestration  │
└─────────┬───────────────────────────────────┬───────────────────────────┘
          │  Delegates narrow tasks            │  DSPy-optimized prompts
          │                                    │  for all 4 skills
   ┌──────▼──────────────┐          ┌─────────▼──────────────────────┐
   │  Fine-tuned SLM     │          │  DSPy Prompt Compiler          │
   │  (BioMistral-7B     │          │                                │
   │   via QLoRA/DoRA)   │          │  Modules:                      │
   │                     │          │    BiomarkerDiscoveryModule     │
   │  Tasks:             │          │    SampleQCModule               │
   │   • Pathway classify│          │    FeatureInterpretModule       │
   │   • Gene interpret  │          │    RegulatoryReportModule       │
   │   • PubMed scoring  │          │                                │
   │   • MSI explain     │          │  Metrics: existing 4 evals     │
   └──────┬──────────────┘          └────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────────────────────┐
│  GPU-Accelerated Training Layer                                         │
│                                                                         │
│  ┌───────────────────┐  ┌──────────────────┐  ┌──────────────────────┐ │
│  │ QLoRA Fine-tuning │  │ Expression       │  │ DDP GridSearchCV     │ │
│  │ (single A100)     │  │ Encoder Training │  │ (multi-GPU RF/XGB)  │ │
│  │                   │  │ (DDP on 2×A100)  │  │                     │ │
│  │ 4-bit NF4 quant   │  │ scGPT-style      │  │ Data sharding for  │ │
│  │ r=16, α=32        │  │ gene transformer │  │ benchmark cohorts   │ │
│  │ ~6GB VRAM         │  │ ~24GB VRAM       │  │                     │ │
│  └───────────────────┘  └──────────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Fine-Tuning Small Language Models

### 1.1 Task Decomposition — What Moves Off Claude

Not every LLM task in the platform benefits from fine-tuning. The decision boundary is frequency × narrowness:

| Task | Current Handler | Frequency | Narrowness | Fine-Tune? | Rationale |
|------|----------------|-----------|------------|------------|-----------|
| Gene pathway classification | Claude `explain_features` tool | Every gene in every panel (~30–50/run) | Very narrow — classify into 4 known pathways | **Yes** | Lookup-like task, SLM handles perfectly |
| Single-gene biological interpretation | Claude `generate_interpretation_activity` | Per-gene, 20+ calls/workflow | Narrow — structured template output | **Yes** | Constrained schema, biomedical SLM excels |
| PubMed relevance scoring | Claude in Literature Grounding Skill | Per-citation, 50+ calls/workflow | Very narrow — binary relevance | **Yes** | Classification task, tiny SLM sufficient |
| MSI phenotype explanation | Claude in report compilation | 1–2/workflow | Moderate | **Yes** | Domain-specific, benefits from fine-tuning |
| Multi-step agentic reasoning | Claude orchestrating agent skills | 1/workflow | Very broad | **No** | Requires tool use, extended thinking, reasoning chains |
| Novel biomarker hypothesis generation | Claude in interpretation | 1/workflow | Broad | **No** | Requires creative scientific reasoning |
| FDA-style regulatory report | Claude in `regulatory_report.md` | 1/workflow | Broad, high-stakes | **No** | Needs Claude's instruction following + nuance |

**Net effect:** 70–80% of LLM API calls move to the local SLM, while Claude handles the 20% that requires genuine reasoning.

### 1.2 Base Model Selection

| Candidate | Parameters | Context | Domain Fit | License | Decision |
|-----------|-----------|---------|------------|---------|----------|
| BioMistral-7B | 7B | 32K | Pre-trained on PubMed + PMC, biomedical vocabulary | Apache 2.0 | **Primary choice** — strongest biomedical foundation |
| Llama-3.1-8B-Instruct | 8B | 128K | General + instruction following | Llama 3.1 Community | **Fallback** — if BioMistral underperforms on structured output |
| Phi-3.5-mini-instruct | 3.8B | 128K | Strong reasoning for size | MIT | **Lightweight option** — for PubMed scoring only |
| BioGPT-large | 1.5B | 1K | PubMed-only pretraining | MIT | **Too small** — struggles with structured generation |

**Selected stack:** BioMistral-7B (QLoRA) for pathway classification + interpretation, Phi-3.5-mini (QLoRA) for PubMed relevance scoring.

### 1.3 Training Data Construction

Training data is synthesized from three sources internal to the platform, avoiding any external annotation effort:

#### Source A: Platform Ground Truth (High Quality, Low Volume)

The `core/constants.py` knowledge base provides exact gene-pathway mappings:

```python
# Directly from KNOWN_MSI_PATHWAY_MARKERS + published signatures
training_examples_source_a = []

for pathway, genes in KNOWN_MSI_PATHWAY_MARKERS.items():
    for gene in genes:
        training_examples_source_a.append({
            "instruction": f"Classify the role of {gene} in MSI-H colorectal tumors.",
            "input": f"Gene: {gene}\nContext: Colorectal cancer, Microsatellite Instability High",
            "output": json.dumps({
                "gene": gene,
                "pathway": pathway,
                "confidence": "high",
                "mechanism": PATHWAY_MECHANISMS[pathway],  # hand-written per pathway
                "in_reference_panel": gene in MSI_PROTEOMICS_PANEL or gene in MSI_RNASEQ_PANEL,
            })
        })
# Yields ~50 high-quality examples from known MSI markers
```

#### Source B: Claude-Generated Distillation (Medium Quality, High Volume)

Use Claude Opus 4.6 to generate training examples for genes NOT in the known panels, then filter through the HallucinationDetectionEval:

```python
async def generate_distillation_dataset(genes: list[str], n_per_gene: int = 3):
    """Use Claude to generate training data, verified by PubMed eval."""
    examples = []
    for gene in genes:
        for variation in range(n_per_gene):
            response = await claude.messages.create(
                model=config.CLAUDE_MODEL_ID,  # e.g., "claude-opus-4-6-20250929"
                system="Generate a structured biological interpretation...",
                messages=[{"role": "user", "content": f"Gene: {gene}, Target: MSI"}],
            )
            
            # Verify via HallucinationDetectionEval
            interpretation = parse_response(response)
            eval_result = hallucination_eval.evaluate([interpretation])
            
            if eval_result.passed:  # ≥90% citations verified
                examples.append(format_as_training_example(gene, interpretation))
    
    return examples
# Target: ~500 verified examples from ~200 cancer-related genes
```

#### Source C: Negative Examples (Critical for Calibration)

The model must learn to say "unknown" or "no established MSI association" for genes outside the MSI pathways:

```python
# Random genes with no MSI connection
negative_genes = ["GAPDH", "ACTB", "ALB", "TUBA1A", "HSP90AA1"]
for gene in negative_genes:
    training_examples.append({
        "instruction": f"Classify the role of {gene} in MSI-H colorectal tumors.",
        "input": f"Gene: {gene}\nContext: Colorectal cancer, MSI",
        "output": json.dumps({
            "gene": gene,
            "pathway": "none_established",
            "confidence": "low",
            "mechanism": f"{gene} is a housekeeping gene with no established "
                         f"differential expression in MSI-H vs MSS tumors.",
            "in_reference_panel": False,
        })
    })
```

**Total dataset target:** ~700 examples (50 ground truth + 500 distilled + 150 negatives), split 80/10/10 train/val/test.

### 1.4 Fine-Tuning with QLoRA

QLoRA (Quantized Low-Rank Adaptation) enables fine-tuning the 7B model on a single NVIDIA A10G (24GB VRAM) by quantizing base weights to 4-bit NormalFloat and training only the low-rank adapter matrices.

#### Why QLoRA over LoRA and DoRA

| Method | Base Weights | Adapter | VRAM (7B) | Training Speed | Quality |
|--------|-------------|---------|-----------|---------------|---------|
| Full fine-tune | fp16 | All params | ~28GB | Baseline | Best (but overfits on 700 examples) |
| LoRA | fp16 | Low-rank A, B | ~16GB | 1.5× faster | Good — but fp16 base wastes VRAM |
| **QLoRA** | **4-bit NF4** | **Low-rank A, B (fp16)** | **~6GB** | **2× faster** | **Near-LoRA quality at 1/3 VRAM** |
| DoRA | fp16 | Magnitude + Direction decomp | ~18GB | 1.2× slower than LoRA | Better than LoRA on reasoning tasks |

**Decision:** QLoRA for primary training (fits on a single A10G with room for batch size 8). DoRA as an ablation experiment if QLoRA plateau on the HallucinationDetectionEval.

#### QLoRA Configuration

```python
# training/configs/qlora_biomistral.py

from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, BitsAndBytesConfig
import torch

# 4-bit quantization config
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",          # NormalFloat4 — better than uniform int4
    bnb_4bit_compute_dtype=torch.bfloat16,  # Compute in bf16 for stability
    bnb_4bit_use_double_quant=True,      # Quantize the quantization constants too
)

# Load BioMistral-7B in 4-bit
model = AutoModelForCausalLM.from_pretrained(
    "BioMistral/BioMistral-7B",
    quantization_config=bnb_config,
    device_map="auto",
    torch_dtype=torch.bfloat16,
)
model = prepare_model_for_kbit_training(model)

# LoRA adapter config
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=16,                    # Rank — 16 is standard for domain adaptation
    lora_alpha=32,           # Scaling factor (alpha/r = 2.0 effective LR multiplier)
    lora_dropout=0.05,       # Light dropout — small dataset needs regularization
    target_modules=[         # Apply to all attention + MLP projections
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    bias="none",             # Don't train biases — not enough data
)

model = get_peft_model(model, lora_config)
# Trainable params: ~13M (0.2% of 7B) — prevents overfitting on 700 examples
```

#### Training Loop

```python
from transformers import TrainingArguments
from trl import SFTTrainer

training_args = TrainingArguments(
    output_dir="gs://{GCS_MODEL_BUCKET}/checkpoints/biomistral-genomics-qlora",
    num_train_epochs=3,              # Small dataset — 3 epochs, watch val loss
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,    # Effective batch size = 16
    learning_rate=2e-4,              # QLoRA standard — higher than full fine-tune
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    weight_decay=0.01,
    bf16=True,                       # bf16 mixed precision
    logging_steps=10,
    eval_strategy="steps",
    eval_steps=50,
    save_strategy="steps",
    save_steps=50,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    gradient_checkpointing=True,     # Saves VRAM at cost of ~20% speed
    optim="paged_adamw_8bit",        # 8-bit optimizer for VRAM savings
    max_grad_norm=0.3,               # Gradient clipping for stability
    report_to="tensorboard",         # Vertex AI TensorBoard integration
)

trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    max_seq_length=2048,             # Gene interpretations are short
    dataset_text_field="text",       # Formatted as instruction-input-output
)

trainer.train()

# Save adapter weights only (~26MB vs 14GB for full model)
model.save_pretrained("./models/biomistral-genomics-qlora-adapter")

# Upload adapter to GCS for versioned storage
from core.model_registry import save_to_gcs
save_to_gcs(
    local_path="./models/biomistral-genomics-qlora-adapter",
    gcs_uri=f"gs://{{GCS_MODEL_BUCKET}}/adapters/biomistral-genomics-qlora/",
)

# Log training metrics to Vertex AI Experiments
from core.experiment_tracker import ExperimentTracker
tracker = ExperimentTracker()
tracker.log_metrics({
    "final_train_loss": trainer.state.log_history[-1].get("loss"),
    "final_eval_loss": trainer.state.log_history[-1].get("eval_loss"),
    "adapter_size_mb": 26,
})
```

**Training time:** ~15 minutes on a single A100 for 700 examples × 3 epochs.

### 1.5 DoRA Ablation

DoRA (Weight-Decomposed Low-Rank Adaptation) decomposes weight updates into magnitude and direction components. It consistently outperforms LoRA on reasoning and classification benchmarks by 1–3% while adding minimal overhead.

```python
# Only change from QLoRA config:
from peft import LoraConfig

dora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    use_dora=True,            # <-- This is the only change
    bias="none",
)
# DoRA adds a learned magnitude scalar per weight matrix
# VRAM increase: ~5% over QLoRA (negligible)
# Training time increase: ~15% (extra gradient computation for magnitude)
```

**When to use DoRA over QLoRA:** Run QLoRA first. If the HallucinationDetectionEval on the fine-tuned model scores <85% (below the 90% threshold with margin), switch to DoRA. The magnitude-direction decomposition specifically helps when the model needs to learn precise output calibration — exactly the case for confidence scoring.

### 1.6 Integration with Platform

#### New MCP Tool: `explain_features_local`

```python
# mcp_server/tools/explain_features_local.py

from peft import AutoPeftModelForCausalLM
from transformers import AutoTokenizer
import torch

class LocalGenomicsExplainer:
    """Fine-tuned BioMistral-7B for gene interpretation.

    Option A: Local inference (dev/testing)
    Option B: Vertex AI Endpoint (production) — see VertexGenomicsExplainer below
    """

    def __init__(self, adapter_path: str = "./models/biomistral-genomics-qlora-adapter"):
        self.model = AutoPeftModelForCausalLM.from_pretrained(
            adapter_path,
            device_map="auto",
            torch_dtype=torch.bfloat16,
            load_in_4bit=True,
        )
        self.tokenizer = AutoTokenizer.from_pretrained("BioMistral/BioMistral-7B")
    
    async def classify_gene(self, gene: str, target: str) -> dict:
        prompt = f"Classify the role of {gene} in {target} colorectal tumors."
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs, max_new_tokens=256, temperature=0.1,
                do_sample=False,  # Deterministic for reproducibility
            )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return json.loads(response)  # Structured JSON output
```

#### Routing Logic in Agent Skills

```python
# agent_skills/biomarker_discovery.py — modified routing

async def interpret_gene_panel(genes: list[str], target: str) -> list[dict]:
    """Route interpretation to SLM or Claude based on task complexity."""
    
    results = []
    novel_genes = []  # Genes not in known panels
    
    for gene in genes:
        if gene in ALL_KNOWN_MSI_MARKERS or gene in MSI_PROTEOMICS_PANEL:
            # Known gene → SLM handles it (fast, cheap, deterministic)
            result = await local_explainer.classify_gene(gene, target)
            results.append(result)
        else:
            novel_genes.append(gene)
    
    if novel_genes:
        # Novel genes → Claude handles (needs creative reasoning + PubMed search)
        claude_results = await generate_interpretation_activity(novel_genes, target)
        results.extend(claude_results)

    return results
```

#### Option B: Vertex AI Endpoint (Production Serving)

For production deployments, the fine-tuned SLM can be served via a Vertex AI Endpoint instead of local inference:

```python
# mcp_server/tools/explain_features_vertex.py

from google.cloud import aiplatform

class VertexGenomicsExplainer:
    """Serve fine-tuned BioMistral-7B via Vertex AI Endpoint."""

    def __init__(self, endpoint_name: str):
        self.endpoint = aiplatform.Endpoint(endpoint_name=endpoint_name)

    async def classify_gene(self, gene: str, target: str) -> dict:
        prompt = f"Classify the role of {gene} in {target} colorectal tumors."
        result = self.endpoint.predict(
            instances=[{"prompt": prompt, "max_tokens": 256, "temperature": 0.1}]
        )
        return result.predictions[0]
```

### 1.7 SLM Evaluation Integration

The fine-tuned SLM must pass the same evals as Claude before deployment:

```python
class SLMEvalSuite:
    """Run existing platform evals against the fine-tuned SLM."""
    
    def __init__(self, slm_explainer: LocalGenomicsExplainer):
        self.explainer = slm_explainer
        # NOTE: The HallucinationDetectionEval interface below is illustrative.
        # The actual implementation in evals/hallucination_detection.py may use
        # a different call signature. Verify before implementing.
        self.hallucination_eval = HallucinationDetectionEval()
        self.biological_eval = BiologicalValidityEval()
    
    async def run(self, test_genes: list[str]) -> dict:
        interpretations = []
        for gene in test_genes:
            result = await self.explainer.classify_gene(gene, "MSI-H")
            interpretations.append(result)
        
        hallucination_score = self.hallucination_eval.evaluate(interpretations)
        
        # Extract gene selections from SLM pathway classifications
        selected_genes = [
            r["gene"] for r in interpretations 
            if r.get("pathway") != "none_established"
        ]
        validity_score = self.biological_eval.evaluate(selected_genes)
        
        return {
            "hallucination": hallucination_score,
            "biological_validity": validity_score,
            "pass": hallucination_score.passed and validity_score.passed,
        }

# Acceptance criteria:
# SLM HallucinationDetectionEval ≥ 0.90 (same as Claude threshold)
# SLM BiologicalValidityEval ≥ 0.60 (same as Claude threshold)
# SLM latency ≤ 200ms per gene (vs Claude's ~2s)
# SLM cost ≈ $0 (local inference) vs Claude's ~$0.02 per gene
```

---

## Part 2: Prompt Optimization with DSPy

### 2.1 Why DSPy Over Manual Prompt Engineering

The platform has four hand-written prompt templates totaling ~800 lines of markdown. These prompts were designed by intuition — not optimized against the evaluation framework. DSPy treats prompts as programs with measurable outputs, compiled against labeled examples.

The key insight: **the platform already has evaluation metrics** (Biological Validity, Reproducibility, Hallucination Detection, Benchmark Comparison). DSPy can directly optimize prompts to maximize these metrics.

| Approach | Prompt Structure | Optimization | Evaluation | Iteration Speed |
|----------|-----------------|-------------|------------|-----------------|
| Manual (current) | Hand-written markdown | Human intuition | Run evals post-hoc | Hours per iteration |
| AutoPrompt | Gradient-guided token search | Automatic, narrow | Task-specific accuracy | Minutes, but token-level only |
| **DSPy** | **Modular signatures + teleprompters** | **Automatic, program-level** | **Custom metrics** | **Minutes, full pipeline** |

**Decision:** DSPy as the primary framework (program-level optimization maps to the platform's multi-step workflows). AutoPrompt as a supplementary technique for discovering optimal few-shot examples within DSPy modules.

### 2.2 DSPy Module Architecture

Each agent skill becomes a DSPy module with typed signatures:

```python
# dspy_modules/biomarker_discovery.py

import dspy

class BiomarkerDiscoverySignature(dspy.Signature):
    """Identify MSI biomarker genes from multi-omics expression data."""
    
    dataset_summary = dspy.InputField(
        desc="JSON summary of loaded dataset: sample counts, feature counts, "
             "missing data rates, MSI distribution"
    )
    imputation_results = dspy.InputField(
        desc="JSON with genes_before, genes_imputed_mar, genes_assigned_mnar, "
             "nmf_reconstruction_error"
    )
    feature_panel = dspy.InputField(
        desc="JSON list of selected genes with method agreement scores, "
             "ANOVA p-values, LASSO coefficients, RF importance"
    )
    classification_metrics = dspy.InputField(
        desc="JSON with F1, precision, recall, ROC-AUC, per-classifier breakdown"
    )
    
    biomarker_report = dspy.OutputField(
        desc="Structured report: ranked gene panel with pathway annotations, "
             "method agreement matrix, novel discoveries, confidence levels, "
             "comparison to precisionFDA reference panels"
    )


class BiomarkerDiscoveryModule(dspy.Module):
    """Multi-step reasoning module for biomarker discovery interpretation."""
    
    def __init__(self):
        super().__init__()
        
        # Sub-modules map to the skill's logical steps
        self.assess_data_quality = dspy.ChainOfThought(
            "dataset_summary -> data_quality_assessment"
        )
        self.evaluate_imputation = dspy.ChainOfThought(
            "imputation_results, data_quality_assessment -> imputation_assessment"
        )
        self.interpret_features = dspy.ChainOfThought(
            "feature_panel, imputation_assessment -> feature_interpretation"
        )
        self.synthesize_report = dspy.ChainOfThought(
            BiomarkerDiscoverySignature
        )
    
    def forward(self, dataset_summary, imputation_results, 
                feature_panel, classification_metrics):
        
        quality = self.assess_data_quality(dataset_summary=dataset_summary)
        imputation = self.evaluate_imputation(
            imputation_results=imputation_results,
            data_quality_assessment=quality.data_quality_assessment
        )
        features = self.interpret_features(
            feature_panel=feature_panel,
            imputation_assessment=imputation.imputation_assessment
        )
        report = self.synthesize_report(
            dataset_summary=dataset_summary,
            imputation_results=imputation_results,
            feature_panel=feature_panel,
            classification_metrics=classification_metrics,
        )
        
        return report
```

#### Sample QC Module

```python
class SampleQCSignature(dspy.Signature):
    """Detect and explain mislabeled samples using dual-validation evidence."""
    
    classification_flags = dspy.InputField(
        desc="JSON list of samples flagged by ensemble classifier "
             "(predicted phenotype != annotated phenotype)"
    )
    distance_matrix_flags = dspy.InputField(
        desc="JSON list of samples flagged by cross-omics distance matrix "
             "(off-diagonal optimal assignment in Hungarian algorithm)"
    )
    concordance_data = dspy.InputField(
        desc="JSON showing overlap between classification and distance matrix flags"
    )
    
    qc_report = dspy.OutputField(
        desc="Structured QC report: per-sample confidence (HIGH if both methods agree, "
             "REVIEW if single method), recommended corrections, audit trail"
    )


class SampleQCModule(dspy.Module):
    """Dual-validation sample QC with explanation generation."""
    
    def __init__(self):
        super().__init__()
        self.analyze_classification = dspy.ChainOfThought(
            "classification_flags -> classification_analysis"
        )
        self.analyze_distance = dspy.ChainOfThought(
            "distance_matrix_flags -> distance_analysis"
        )
        self.cross_validate = dspy.ChainOfThought(
            "classification_analysis, distance_analysis, concordance_data -> qc_report"
        )
    
    def forward(self, classification_flags, distance_matrix_flags, concordance_data):
        clf_analysis = self.analyze_classification(
            classification_flags=classification_flags
        )
        dist_analysis = self.analyze_distance(
            distance_matrix_flags=distance_matrix_flags
        )
        return self.cross_validate(
            classification_analysis=clf_analysis.classification_analysis,
            distance_analysis=dist_analysis.distance_analysis,
            concordance_data=concordance_data,
        )
```

### 2.3 DSPy Metrics from Existing Evals

The platform's four evaluators become DSPy metrics — no new annotation needed:

```python
# dspy_modules/metrics.py

from evals.biological_validity import BiologicalValidityEval
from evals.hallucination_detection import HallucinationDetectionEval
from evals.reproducibility import ReproducibilityEval
from evals.benchmark_comparison import BenchmarkComparisonEval

def biological_validity_metric(example, prediction, trace=None) -> float:
    """DSPy metric wrapping BiologicalValidityEval."""
    eval_instance = BiologicalValidityEval()
    
    # Extract gene list from the prediction's biomarker report
    genes = extract_genes_from_report(prediction.biomarker_report)
    result = eval_instance.evaluate(genes)
    
    return result.score  # 0.0–1.0, threshold 0.60

def hallucination_metric(example, prediction, trace=None) -> float:
    """DSPy metric wrapping HallucinationDetectionEval."""
    eval_instance = HallucinationDetectionEval()
    
    interpretations = extract_interpretations(prediction.biomarker_report)
    result = eval_instance.evaluate(interpretations)
    
    return result.score  # 0.0–1.0, threshold 0.90

def composite_metric(example, prediction, trace=None) -> float:
    """Weighted combination matching platform success criteria."""
    bio_score = biological_validity_metric(example, prediction, trace)
    halluc_score = hallucination_metric(example, prediction, trace)
    
    # Hallucination is non-negotiable, biology is the optimization target
    if halluc_score < 0.90:
        return 0.0  # Hard fail on hallucination
    
    return 0.6 * bio_score + 0.4 * halluc_score
```

### 2.4 DSPy Compilation & Optimization

#### Teleprompter Selection

| Teleprompter | Mechanism | Best For | Platform Fit |
|-------------|-----------|----------|-------------|
| `BootstrapFewShot` | Generate examples via LM, filter by metric | Cold-start, no labeled data | **Good** — platform has metrics but few labeled prompt-response pairs |
| `BootstrapFewShotWithRandomSearch` | BootstrapFewShot + random example selection | Small example pools | **Best fit** — 700 SLM training examples can seed few-shot selection |
| `MIPRO` (Multi-prompt Instruction Proposal) | Optimize both instructions and few-shot examples jointly | Complex multi-step modules | **Ideal for BiomarkerDiscoveryModule** — optimizes the multi-step chain |
| `SignatureOptimizer` | Bayesian optimization of signature descriptions | Single-step tasks | Good for PubMed scoring |

**Strategy:** Use MIPRO for the two complex modules (BiomarkerDiscovery, SampleQC) and BootstrapFewShotWithRandomSearch for the two simpler modules (FeatureInterpretation, RegulatoryReport).

```python
# dspy_modules/compile.py

import dspy
from dspy.teleprompt import MIPRO, BootstrapFewShotWithRandomSearch

# Configure DSPy with Claude as the LM
claude_lm = dspy.LM("anthropic/claude-sonnet-4-5-20250929")
dspy.configure(lm=claude_lm)

# Training set: synthetic cohort outputs from the pipeline
trainset = load_training_examples()  # Pipeline outputs paired with expert-validated reports

# Compile BiomarkerDiscovery with MIPRO
biomarker_module = BiomarkerDiscoveryModule()
mipro_compiler = MIPRO(
    metric=composite_metric,
    num_candidates=10,       # Generate 10 instruction candidates per module
    init_temperature=1.0,    # Diverse initial proposals
    verbose=True,
)

optimized_biomarker = mipro_compiler.compile(
    biomarker_module,
    trainset=trainset,
    num_trials=50,           # Bayesian optimization iterations
    max_bootstrapped_demos=4, # Up to 4 few-shot examples
    max_labeled_demos=4,
    eval_kwargs={"num_threads": 4},
)

# Save optimized module (local + GCS for versioned audit trail)
optimized_biomarker.save("./optimized_prompts/biomarker_discovery.json")
from core.storage import StorageBackend
StorageBackend().upload("./optimized_prompts/biomarker_discovery.json",
                        f"gs://{{GCS_DATA_BUCKET}}/optimized_prompts/biomarker_discovery.json")

# Compile SampleQC with MIPRO
sample_qc_module = SampleQCModule()
optimized_qc = mipro_compiler.compile(
    sample_qc_module,
    trainset=qc_trainset,
    num_trials=50,
    max_bootstrapped_demos=3,
    max_labeled_demos=3,
)
optimized_qc.save("./optimized_prompts/sample_qc.json")
StorageBackend().upload("./optimized_prompts/sample_qc.json",
                        f"gs://{{GCS_DATA_BUCKET}}/optimized_prompts/sample_qc.json")

# Vertex AI Experiments tracks prompt optimization scores across compilations
from core.experiment_tracker import ExperimentTracker
tracker = ExperimentTracker()
tracker.log_metrics({"dspy_biomarker_composite_score": best_score,
                     "dspy_qc_composite_score": qc_best_score})
```

### 2.5 AutoPrompt for Few-Shot Example Mining

AutoPrompt's gradient-guided search discovers optimal trigger tokens and example selections. Within DSPy, it's used to find the best few-shot demonstrations from the platform's existing outputs:

```python
# dspy_modules/autoprompt_examples.py

from dspy.teleprompt import BootstrapFewShotWithOptuna

class AutoPromptExampleMiner:
    """Use gradient-guided search to find optimal few-shot examples."""
    
    def __init__(self, candidate_pool: list[dict]):
        """
        candidate_pool: list of (input, output) pairs from past pipeline runs.
        These come from running the championship pipeline on:
          - Real precisionFDA training data (80 samples)
          - Synthetic cohorts (unit/integration/benchmark presets)
        """
        self.pool = candidate_pool
    
    def mine_examples(self, module: dspy.Module, metric, n_examples: int = 4):
        """Find the n_examples from the pool that maximize the metric."""
        
        optimizer = BootstrapFewShotWithOptuna(
            metric=metric,
            max_bootstrapped_demos=n_examples,
            max_labeled_demos=n_examples,
            num_candidate_programs=20,  # Try 20 different example combinations
            num_threads=4,
        )
        
        optimized = optimizer.compile(
            module,
            trainset=self.pool,
        )
        
        return optimized
```

**Integration with existing prompts:** The DSPy-optimized modules replace the hand-written prompt templates. But the hand-written templates serve as the initial "bootstrap" that seeds DSPy's optimization — they're not discarded, they're the starting point.

### 2.6 Continuous Prompt Optimization Loop

```
┌────────────────────────────────────────────────────────────────────┐
│                  Continuous Prompt Optimization                     │
│                                                                    │
│  1. Pipeline runs on new data (synthetic or real)                  │
│  2. Evals score the output (bio validity, hallucination, etc.)     │
│  3. If score < threshold: trigger DSPy recompilation               │
│  4. MIPRO optimizes using new examples + historical best           │
│  5. A/B test: old prompt vs. new prompt on held-out synthetic data │
│  6. If new prompt wins: deploy to prompts/ directory               │
│  7. Log all prompt versions + scores for audit trail               │
└────────────────────────────────────────────────────────────────────┘
```

This is implemented as a Temporal workflow:

```python
@workflow.defn
class PromptOptimizationWorkflow:
    """Periodically re-optimize prompts against latest eval data."""
    
    @workflow.run
    async def run(self, params: PromptOptParams) -> PromptOptReport:
        # Activity 1: Generate fresh synthetic data
        synthetic = await workflow.execute_activity(
            generate_synthetic_cohort, {"preset": "integration"}, ...
        )
        
        # Activity 2: Run pipeline with current prompts
        baseline = await workflow.execute_activity(
            run_pipeline_with_prompts, 
            {"prompts": "current", "data": synthetic}, ...
        )
        
        # Activity 3: DSPy compilation with new data
        optimized = await workflow.execute_activity(
            compile_dspy_modules,
            {"trainset": synthetic, "metric": "composite"}, ...
        )
        
        # Activity 4: Run pipeline with optimized prompts
        candidate = await workflow.execute_activity(
            run_pipeline_with_prompts,
            {"prompts": optimized, "data": synthetic}, ...
        )
        
        # Activity 5: Compare and decide
        return await workflow.execute_activity(
            compare_and_deploy,
            {"baseline": baseline, "candidate": candidate}, ...
        )
```

---

## Part 3: GPU Optimization, Data Sharding & DDP Training

### 3.1 GPU Acceleration Map

| Component | Current | GPU-Accelerated | Speedup | When It Matters |
|-----------|---------|----------------|---------|-----------------|
| RF GridSearchCV (336 combos) | `n_jobs=-1` CPU | cuML RandomForest on GPU | 10–50× | Benchmark cohort (500+ samples × 7K genes) |
| NMF Imputation | sklearn NMF (CPU) | cuML NMF or PyTorch NMF | 5–20× | Benchmark/stress cohorts |
| Distance Matrix (N×N Spearman) | scipy on CPU | cuPy or PyTorch pairwise | 20–100× | Stress cohort (2000 samples, N²=4M pairs) |
| Expression Encoder training | N/A (new) | PyTorch DDP across GPUs | Required | New capability |
| SLM Fine-tuning | N/A (new) | QLoRA on single GPU | Required | New capability |
| k-NN classification | sklearn CPU | cuML GPU k-NN | 5–15× | Benchmark cohorts with large feature spaces |

### 3.2 Expression Encoder: Gene Transformer with DDP

A transformer-based gene expression encoder learns cross-omics representations that improve the distance matrix matching in Stage 3. Instead of raw Spearman correlation, the encoder projects both proteomics and RNA-Seq into a shared embedding space where matched samples are close.

#### Architecture

```python
# training/expression_encoder.py

import torch
import torch.nn as nn

class GeneExpressionEncoder(nn.Module):
    """Transformer encoder for gene expression profiles.
    
    Maps a sample's expression vector (N_genes,) into a dense embedding
    that captures biological state. Trained with contrastive loss to
    place same-sample proteomics and RNA-Seq embeddings close together.
    
    Architecture inspired by scGPT (Cui et al., 2024) but adapted for
    bulk expression (not single-cell) with paired multi-omics supervision.
    """
    
    def __init__(
        self,
        n_genes: int,
        d_model: int = 256,
        n_heads: int = 8,
        n_layers: int = 4,
        dropout: float = 0.1,
    ):
        super().__init__()
        
        # Gene embedding: each gene gets a learned embedding
        self.gene_embedding = nn.Embedding(n_genes, d_model)
        
        # Expression value encoder: project scalar expression to d_model
        self.value_encoder = nn.Sequential(
            nn.Linear(1, d_model),
            nn.GELU(),
            nn.Linear(d_model, d_model),
        )
        
        # Modality token (proteomics vs RNA-Seq)
        self.modality_embedding = nn.Embedding(2, d_model)
        
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, 
            dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer, num_layers=n_layers,
        )
        
        # CLS token for sample-level representation
        self.cls_token = nn.Parameter(torch.randn(1, 1, d_model))
        
        # Projection head for contrastive learning
        self.projection = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.Linear(d_model, 128),  # Final embedding dim
        )
    
    def forward(self, expression_values, gene_indices, modality_id, 
                attention_mask=None):
        """
        expression_values: (batch, seq_len) — expression levels per gene
        gene_indices: (batch, seq_len) — gene IDs for embedding lookup
        modality_id: (batch,) — 0=proteomics, 1=rnaseq
        """
        batch_size = expression_values.size(0)
        
        # Encode gene identity + expression value + modality
        gene_emb = self.gene_embedding(gene_indices)
        value_emb = self.value_encoder(expression_values.unsqueeze(-1))
        mod_emb = self.modality_embedding(modality_id).unsqueeze(1)
        
        # Combine: gene identity + value + modality
        x = gene_emb + value_emb + mod_emb
        
        # Prepend CLS token
        cls = self.cls_token.expand(batch_size, -1, -1)
        x = torch.cat([cls, x], dim=1)
        
        # Transformer encoding
        if attention_mask is not None:
            # Pad attention mask for CLS token
            cls_mask = torch.ones(batch_size, 1, device=x.device)
            attention_mask = torch.cat([cls_mask, attention_mask], dim=1)
        
        x = self.transformer(x, src_key_padding_mask=(
            ~attention_mask.bool() if attention_mask is not None else None
        ))
        
        # CLS token output → projection
        cls_output = x[:, 0]
        embedding = self.projection(cls_output)
        
        return nn.functional.normalize(embedding, p=2, dim=1)
```

#### Contrastive Training Loss

```python
class NTXentLoss(nn.Module):
    """Normalized Temperature-Scaled Cross-Entropy Loss.
    
    For paired multi-omics: proteomics embedding of sample i should be
    closest to RNA-Seq embedding of the same sample i.
    """
    
    def __init__(self, temperature: float = 0.07):
        super().__init__()
        self.temperature = temperature
    
    def forward(self, z_pro: torch.Tensor, z_rna: torch.Tensor):
        """
        z_pro: (batch, embed_dim) — proteomics embeddings
        z_rna: (batch, embed_dim) — RNA-Seq embeddings (same samples)
        """
        batch_size = z_pro.size(0)
        
        # Similarity matrix: (batch, batch)
        sim = torch.mm(z_pro, z_rna.t()) / self.temperature
        
        # Positive pairs are on the diagonal
        labels = torch.arange(batch_size, device=sim.device)
        
        # Symmetric loss
        loss_pro = nn.functional.cross_entropy(sim, labels)
        loss_rna = nn.functional.cross_entropy(sim.t(), labels)
        
        return (loss_pro + loss_rna) / 2
```

### 3.3 DDP Training Setup

The expression encoder trains on the synthetic `benchmark` cohort (500 samples × ~7K genes × 2 modalities). DDP across 2 GPUs halves the training time.

```python
# training/train_encoder_ddp.py

import os
import torch
import torch.distributed as dist
import torch.multiprocessing as mp
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler

def setup_ddp(rank: int, world_size: int):
    """Initialize DDP process group."""
    os.environ["MASTER_ADDR"] = "localhost"
    os.environ["MASTER_PORT"] = "12355"
    dist.init_process_group("nccl", rank=rank, world_size=world_size)
    torch.cuda.set_device(rank)

def cleanup_ddp():
    dist.destroy_process_group()

def train_one_epoch(model, dataloader, optimizer, loss_fn, rank):
    model.train()
    total_loss = 0.0
    
    for batch in dataloader:
        pro_values = batch["pro_values"].cuda(rank)
        pro_genes = batch["pro_gene_ids"].cuda(rank)
        rna_values = batch["rna_values"].cuda(rank)
        rna_genes = batch["rna_gene_ids"].cuda(rank)
        pro_mask = batch["pro_mask"].cuda(rank)
        rna_mask = batch["rna_mask"].cuda(rank)
        
        # Forward pass through both modalities
        z_pro = model(pro_values, pro_genes, 
                      torch.zeros(pro_values.size(0), dtype=torch.long).cuda(rank),
                      pro_mask)
        z_rna = model(rna_values, rna_genes,
                      torch.ones(rna_values.size(0), dtype=torch.long).cuda(rank),
                      rna_mask)
        
        loss = loss_fn(z_pro, z_rna)
        
        optimizer.zero_grad()
        loss.backward()
        
        # Gradient clipping for stability
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        
        optimizer.step()
        total_loss += loss.item()
    
    return total_loss / len(dataloader)

def train_ddp(rank: int, world_size: int, config: dict):
    """DDP training entry point per GPU."""
    setup_ddp(rank, world_size)
    
    # Model
    model = GeneExpressionEncoder(
        n_genes=config["n_genes"],
        d_model=256, n_heads=8, n_layers=4,
    ).cuda(rank)
    
    model = DDP(model, device_ids=[rank], find_unused_parameters=False)
    
    # Data — DistributedSampler shards automatically
    dataset = PairedOmicsDataset(config["data_path"])
    sampler = DistributedSampler(dataset, num_replicas=world_size, rank=rank)
    dataloader = DataLoader(
        dataset, batch_size=config["batch_size"],
        sampler=sampler, num_workers=4, pin_memory=True,
    )
    
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config["lr"], weight_decay=0.01,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=config["epochs"],
    )
    loss_fn = NTXentLoss(temperature=0.07)
    
    # Training loop
    for epoch in range(config["epochs"]):
        sampler.set_epoch(epoch)  # Ensure different shuffling per epoch
        train_loss = train_one_epoch(model, dataloader, optimizer, loss_fn, rank)
        scheduler.step()
        
        if rank == 0:
            print(f"Epoch {epoch}: loss={train_loss:.4f}")
            
            # Save checkpoint from rank 0 only
            if (epoch + 1) % 10 == 0:
                torch.save(
                    model.module.state_dict(),
                    f"checkpoints/encoder_epoch{epoch+1}.pt"
                )
                # Upload checkpoint to GCS
                from core.model_registry import save_to_gcs
                save_to_gcs(
                    local_path=f"checkpoints/encoder_epoch{epoch+1}.pt",
                    gcs_uri=f"gs://{{GCS_MODEL_BUCKET}}/checkpoints/encoder_epoch{epoch+1}.pt",
                )

    cleanup_ddp()

# Launch DDP training
# Note: When running as a Vertex AI Custom Training Job, MASTER_ADDR/MASTER_PORT
# are set automatically by the platform. No manual DDP setup needed.
if __name__ == "__main__":
    world_size = torch.cuda.device_count()  # 2 GPUs on Vertex AI A100 worker
    config = {
        "n_genes": 7000,
        "batch_size": 32,        # Per GPU → effective 64
        "lr": 3e-4,
        "epochs": 100,
        "data_path": f"gs://{{GCS_DATA_BUCKET}}/synthetic/benchmark",
    }
    mp.spawn(train_ddp, args=(world_size, config), nprocs=world_size)
```

### 3.4 Data Sharding for Large Cohorts

The synthetic `stress` cohort (2,000 samples × 20K genes) doesn't fit in memory for distance matrix computation (2000² × 8 bytes = 32MB per matrix, but with 100 bootstrap iterations over 16K genes, memory pressure is real). Data sharding parallelizes this:

```python
# core/sharded_distance.py

import numpy as np
from concurrent.futures import ProcessPoolExecutor

class ShardedDistanceComputer:
    """Compute cross-omics distance matrices with gene-level sharding.
    
    For the stress cohort: 2000 samples × 20K genes × 100 iterations
    = 2 billion correlation computations.
    
    Strategy: shard genes across workers, compute partial distance matrices,
    reduce with element-wise mean.
    """
    
    def __init__(self, n_workers: int = 4):
        self.n_workers = n_workers
    
    def compute_sharded(
        self,
        proteomics: np.ndarray,   # (n_samples, n_genes)
        rnaseq: np.ndarray,       # (n_samples, n_genes)
        gene_indices: list[int],  # High-correlation genes to use
        n_iterations: int = 100,
        gene_fraction: float = 0.8,
        rng: np.random.Generator = None,
    ) -> np.ndarray:
        """Compute distance matrix with sharded bootstrap iterations."""
        
        rng = rng or np.random.default_rng(42)
        n_samples = proteomics.shape[0]
        
        # Pre-generate all bootstrap gene subsets
        n_genes_per_iter = int(len(gene_indices) * gene_fraction)
        all_subsets = [
            rng.choice(gene_indices, size=n_genes_per_iter, replace=False)
            for _ in range(n_iterations)
        ]
        
        # Shard iterations across workers
        shards = np.array_split(all_subsets, self.n_workers)
        
        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            futures = [
                executor.submit(
                    _compute_shard,
                    proteomics, rnaseq, shard, n_samples
                )
                for shard in shards
            ]
            
            # Reduce: element-wise mean of partial vote matrices
            vote_matrix = np.zeros((n_samples, n_samples))
            for future in futures:
                vote_matrix += future.result()
        
        vote_matrix /= n_iterations
        return vote_matrix

def _compute_shard(proteomics, rnaseq, gene_subsets, n_samples):
    """Worker function: compute partial vote matrix for a shard of iterations."""
    from scipy.optimize import linear_sum_assignment
    from scipy.spatial.distance import cdist
    
    partial_votes = np.zeros((n_samples, n_samples))
    
    for gene_subset in gene_subsets:
        pro_sub = proteomics[:, gene_subset]
        rna_sub = rnaseq[:, gene_subset]
        
        # Distance matrix
        dist_matrix = cdist(pro_sub, rna_sub, metric="correlation")
        
        # Hungarian algorithm for optimal assignment
        row_ind, col_ind = linear_sum_assignment(dist_matrix)
        
        # Vote: sample i matched to sample j
        for i, j in zip(row_ind, col_ind):
            partial_votes[i, j] += 1
    
    return partial_votes
```

### 3.5 cuML GPU Acceleration for scikit-learn Components

For the `benchmark` cohort and beyond, replace scikit-learn estimators with RAPIDS cuML equivalents:

```python
# core/gpu_classifier.py

import cudf
import cuml
from cuml.ensemble import RandomForestClassifier as cuRF
from cuml.linear_model import LogisticRegression as cuLR
from cuml.neighbors import KNeighborsClassifier as cuKNN
from cuml.decomposition import NMF as cuNMF

class GPUEnsembleMismatchClassifier:
    """GPU-accelerated version of EnsembleMismatchClassifier.
    
    API-compatible with the CPU version. Automatically selected
    when CUDA is available and dataset exceeds 200 samples.
    """
    
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
    
    def _make_base_classifiers(self):
        return {
            "knn": cuKNN(n_neighbors=5),
            "lasso": cuLR(
                penalty="l1", C=1.0, solver="qn",  # cuML uses "qn" not "liblinear"
                max_iter=5000,
            ),
            "rf": cuRF(
                n_estimators=500,
                max_depth=15,
                random_state=self.random_state,
                n_streams=4,       # GPU parallelism
            ),
        }
    
    def fit(self, X, y_gender, y_msi, mismatch_labels):
        """Identical API to CPU version, but data on GPU."""
        X_gpu = cudf.DataFrame(X) if not isinstance(X, cudf.DataFrame) else X
        # ... same logic, but all operations on GPU
```

### 3.6 Infrastructure: Vertex AI GPU Training Jobs

GPU training runs as serverless Vertex AI Custom Training Jobs — no cluster management, no GPU driver installation, no node groups. Infrastructure is defined in `infra/components/vertex_ai.py` (Pulumi ComponentResource).

```python
# Vertex AI GPU training job configurations
# Already supported via core/vertex_training.py — extend for GPU jobs

ARTIFACT_REGISTRY = "{REGION}-docker.pkg.dev/{PROJECT_ID}/precision-genomics"

GPU_TRAINING_CONFIG = {
    "slm_finetuning": {
        "machine_type": "n1-standard-8",
        "accelerator_type": "NVIDIA_TESLA_A100",
        "accelerator_count": 1,
        "container_uri": f"{ARTIFACT_REGISTRY}/precision-genomics-trainer:latest",
    },
    "expression_encoder": {
        "machine_type": "n1-standard-8",
        "accelerator_type": "NVIDIA_TESLA_A100",
        "accelerator_count": 2,  # DDP across 2 GPUs
        "container_uri": f"{ARTIFACT_REGISTRY}/precision-genomics-trainer:latest",
    },
    "cuml_benchmark": {
        "machine_type": "n1-standard-4",
        "accelerator_type": "NVIDIA_L4",
        "accelerator_count": 1,
        "container_uri": f"{ARTIFACT_REGISTRY}/precision-genomics-trainer:latest",
    },
}

# Monthly cost estimate:
# A100 on-demand: $2.48/hr x ~40 hrs/month training = ~$99
# L4 on-demand: $0.70/hr x ~10 hrs/month cuML = ~$7
# With preemptible VMs: ~$35/month (65% savings)
# Total GPU addition: ~$35-106/month
```

**Key advantages over EKS GPU node groups:**
1. **No cluster management** — Vertex AI Custom Training Jobs are serverless; no node groups, no GPU driver management
2. **Pay-per-job** — No always-on cluster overhead; billed only for actual training time
3. **Reuses existing infra** — `core/vertex_training.py`, `core/model_registry.py`, `core/experiment_tracker.py` already implemented
4. **Simpler DDP** — Vertex AI multi-worker training handles `MASTER_ADDR`/`MASTER_PORT` automatically
5. **Unified experiment tracking** — Vertex AI Experiments replaces W&B, same tracker for both the main pipeline and advanced ML

Additional Pulumi resources in `infra/components/vertex_ai.py`:
- GPU training machine types (A100, L4) in allowed list
- Vertex AI TensorBoard instance for training visualization
- Optional: Vertex AI Endpoint for SLM serving in production

### 3.7 Temporal Integration for GPU Jobs

GPU training jobs are launched as Vertex AI CustomJobs via the existing `core/vertex_training.py` module, replacing the previous Kubernetes Job approach.

```python
# workflows/activities/gpu_training_activities.py

@activity.defn
async def train_expression_encoder_activity(config: dict) -> dict:
    """Launch DDP training as a Vertex AI CustomJob."""
    from core.vertex_training import submit_training_job

    job = submit_training_job(
        dataset_uri=f"gs://{config['data_bucket']}/synthetic/benchmark",
        target="expression_encoder",
        config={
            "machine_type": "n1-standard-8",
            "accelerator_type": "NVIDIA_TESLA_A100",
            "accelerator_count": 2,
            "container_uri": config["trainer_image"],
            "args": ["--mode", "encoder", "--epochs", "100"],
        },
    )
    return {"status": "completed", "job_name": job.display_name}


@activity.defn
async def finetune_slm_activity(config: dict) -> dict:
    """Fine-tune BioMistral-7B with QLoRA via Vertex AI."""
    from core.vertex_training import submit_training_job

    job = submit_training_job(
        dataset_uri=f"gs://{config['data_bucket']}/training/slm",
        target="slm_finetuning",
        config={
            "machine_type": "n1-standard-8",
            "accelerator_type": "NVIDIA_TESLA_A100",
            "accelerator_count": 1,
            "container_uri": config["trainer_image"],
            "args": ["--mode", "qlora", "--base-model", "BioMistral/BioMistral-7B"],
        },
    )
    return {
        "status": "completed",
        "adapter_uri": f"gs://{config['model_bucket']}/adapters/biomistral-genomics-qlora",
    }
```

---

## Implementation Sequence

| Week | Phase | Tasks | Dependencies |
|------|-------|-------|-------------|
| **Week 5** | SLM Data Prep | Build training dataset (Sources A, B, C), validate with evals | Phases 1–3 complete |
| **Week 5** | DSPy Setup | Define 4 DSPy modules + metrics, wire to existing evals | Eval framework complete |
| **Week 6** | QLoRA Training | Fine-tune BioMistral-7B, run SLM eval suite | Training data ready |
| **Week 6** | DSPy Compilation | Run MIPRO on BiomarkerDiscovery + SampleQC modules | DSPy modules defined |
| **Week 6** | GPU Infra | Configure Vertex AI GPU training jobs, build trainer Docker image in Artifact Registry | GCP infrastructure complete |
| **Week 7** | Expression Encoder | Implement + train with DDP on synthetic benchmark cohort | Synthetic data gen + GPU infra |
| **Week 7** | Integration | Wire SLM into MCP tool, deploy DSPy-optimized prompts | All components trained |
| **Week 7** | Eval & Ablation | QLoRA vs DoRA, DSPy vs hand-written, GPU vs CPU benchmarks | Everything running |

**Total additional time: ~3 weeks** (parallel with polish from Phase 4 of the main plan).

---

## Success Criteria (Enhancement Layer)

| Metric | Target | Measurement |
|--------|--------|-------------|
| SLM pathway classification accuracy | ≥95% on known MSI genes | Test split of training data |
| SLM HallucinationDetectionEval | ≥0.90 (matches Claude threshold) | Platform eval suite |
| SLM inference latency | ≤200ms per gene | Benchmarked on A100 (Vertex AI) |
| Claude API cost reduction | ≥70% fewer API calls per workflow | Before/after call count |
| DSPy BiologicalValidityEval improvement | ≥10% relative improvement over hand-written prompts | A/B test on synthetic cohort |
| DSPy ReproducibilityEval | ≥0.90 Jaccard (up from 0.85 target) | 10 runs with optimized prompts |
| Expression encoder matching accuracy | ≥95% on synthetic `medium` difficulty | Distance matrix evaluation |
| GPU training time (encoder, 100 epochs) | ≤30 min on 2×A100 DDP (Vertex AI) | Wall clock time |
| GPU inference speedup (benchmark cohort) | ≥10× over CPU for RF + distance matrix | Timed comparison |
| QLoRA adapter size | ≤30MB | File size of saved adapter |
| DoRA vs QLoRA ablation | Document delta on all 4 evals | Side-by-side comparison |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| BioMistral-7B generates hallucinated pathway associations | Medium | High — undermines trust | Negative training examples (Source C) + hard constraint in routing logic: novel genes always go to Claude |
| DSPy compilation overfits to synthetic data distribution | Medium | Medium — prompts fail on real data | Hold out real precisionFDA data from DSPy training; final eval always on real data |
| GPU job cost overruns | Low | Low — preemptible VMs + pay-per-job | Vertex AI preemptible VMs with fallback to on-demand; training jobs time-boxed |
| Expression encoder doesn't outperform Spearman correlation | Medium | Low — existing Stage 3 still works | Encoder is additive, not replacement. Use as ensemble member alongside Spearman |
| QLoRA quantization degrades structured JSON output | Low | Medium — SLM produces malformed JSON | Constrained decoding with `outlines` library; fallback to Claude on parse failure |
