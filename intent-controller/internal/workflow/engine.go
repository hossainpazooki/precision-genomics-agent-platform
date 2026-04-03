package workflow

import (
	"context"
	"fmt"
	"log/slog"
	"time"

	"github.com/google/uuid"
	"github.com/precision-genomics/intent-controller/internal/activity"
	"github.com/precision-genomics/intent-controller/internal/models"
	"github.com/precision-genomics/intent-controller/internal/store"
)

// PhaseFunc executes one phase of a workflow and returns its result.
type PhaseFunc func(ctx context.Context, dispatcher *activity.Dispatcher, params map[string]interface{}, prevResults map[string]interface{}) (map[string]interface{}, error)

// Phase is a named step in a workflow definition.
type Phase struct {
	Name     string
	Activity PhaseFunc
}

// Definition describes a workflow type as a sequence of phases.
type Definition struct {
	Type   string
	Phases []Phase
}

// Engine manages workflow execution.
type Engine struct {
	workflows  *store.WorkflowRepo
	dispatcher *activity.Dispatcher
	registry   map[string]Definition
}

// NewEngine creates a new workflow engine with built-in workflow definitions.
func NewEngine(workflows *store.WorkflowRepo, dispatcher *activity.Dispatcher) *Engine {
	e := &Engine{
		workflows:  workflows,
		dispatcher: dispatcher,
		registry:   map[string]Definition{},
	}
	e.registerDefaults()
	return e
}

func (e *Engine) registerDefaults() {
	e.registry["biomarker_discovery"] = Definition{
		Type: "biomarker_discovery",
		Phases: []Phase{
			{Name: "data_loading", Activity: phaseLoadAndValidate},
			{Name: "imputation", Activity: phaseImpute},
			{Name: "feature_selection", Activity: phaseSelectFeatures},
			{Name: "integration", Activity: phaseIntegrateAndFilter},
			{Name: "classification", Activity: phaseTrainAndEvaluate},
			{Name: "interpretation", Activity: phaseInterpret},
			{Name: "report", Activity: phaseCompileReport},
		},
	}

	e.registry["sample_qc"] = Definition{
		Type: "sample_qc",
		Phases: []Phase{
			{Name: "data_loading", Activity: phaseLoadClinical},
			{Name: "classification_qc", Activity: phaseClassificationQC},
			{Name: "distance_matching", Activity: phaseDistanceMatrix},
			{Name: "cross_validation", Activity: phaseCrossValidate},
			{Name: "report", Activity: phaseCompileReport},
		},
	}

	e.registry["prompt_optimization"] = Definition{
		Type: "prompt_optimization",
		Phases: []Phase{
			{Name: "synthetic_cohort", Activity: phaseGenerateSynthetic},
			{Name: "baseline_run", Activity: phaseRunPipeline},
			{Name: "dspy_compile", Activity: phaseDSPYCompile},
			{Name: "optimized_run", Activity: phaseRunPipeline},
			{Name: "deploy", Activity: phaseCompareAndDeploy},
		},
	}

	e.registry["cosmo_pipeline"] = Definition{
		Type: "cosmo_pipeline",
		Phases: []Phase{
			{Name: "data_loading", Activity: phaseLoadAndValidate},
			{Name: "imputation", Activity: phaseImpute},
			{Name: "feature_selection", Activity: phaseSelectFeatures},
			{Name: "classification", Activity: phaseTrainAndEvaluate},
			{Name: "cross_omics", Activity: phaseMatchCrossOmics},
			{Name: "interpretation", Activity: phaseInterpret},
		},
	}
}

// Start creates a workflow execution record and begins running it asynchronously.
func (e *Engine) Start(ctx context.Context, workflowType string, params map[string]interface{}) (string, error) {
	def, ok := e.registry[workflowType]
	if !ok {
		return "", fmt.Errorf("unknown workflow type: %s", workflowType)
	}

	workflowID := fmt.Sprintf("%s-%s", workflowType[:min(len(workflowType), 10)], uuid.New().String()[:12])
	now := time.Now().UTC()

	wf := &models.WorkflowExecution{
		WorkflowID:      workflowID,
		WorkflowType:    workflowType,
		Status:          models.WorkflowStatusPending,
		CurrentPhase:    "pending",
		PhasesCompleted: []string{},
		StartedAt:       now,
		Result:          map[string]interface{}{},
	}

	if err := e.workflows.Create(ctx, wf); err != nil {
		return "", fmt.Errorf("create workflow: %w", err)
	}

	// Run asynchronously
	go e.execute(context.Background(), workflowID, def, params)

	slog.Info("workflow started", "workflow_id", workflowID, "type", workflowType)
	return workflowID, nil
}

// execute runs all phases sequentially.
func (e *Engine) execute(ctx context.Context, workflowID string, def Definition, params map[string]interface{}) {
	running := string(models.WorkflowStatusRunning)
	e.workflows.UpdateProgress(ctx, workflowID, &running, nil, nil, nil, nil)

	results := map[string]interface{}{}

	for _, phase := range def.Phases {
		e.workflows.UpdateProgress(ctx, workflowID, nil, &phase.Name, nil, nil, nil)

		result, err := phase.Activity(ctx, e.dispatcher, params, results)
		if err != nil {
			slog.Error("workflow phase failed", "workflow_id", workflowID, "phase", phase.Name, "error", err)
			failed := string(models.WorkflowStatusFailed)
			errMsg := err.Error()
			e.workflows.UpdateProgress(ctx, workflowID, &failed, nil, nil, nil, &errMsg)
			return
		}

		if result != nil {
			results[phase.Name] = result
		}
		e.workflows.UpdateProgress(ctx, workflowID, nil, nil, &phase.Name, nil, nil)
	}

	completed := string(models.WorkflowStatusCompleted)
	e.workflows.UpdateProgress(ctx, workflowID, &completed, nil, nil, results, nil)
	slog.Info("workflow completed", "workflow_id", workflowID)
}

// GetWorkflow returns a workflow execution by ID.
func (e *Engine) GetWorkflow(ctx context.Context, workflowID string) (*models.WorkflowExecution, error) {
	return e.workflows.GetByWorkflowID(ctx, workflowID)
}

// CancelWorkflow cancels a running workflow.
func (e *Engine) CancelWorkflow(ctx context.Context, workflowID string) error {
	wf, err := e.workflows.GetByWorkflowID(ctx, workflowID)
	if err != nil || wf == nil {
		return fmt.Errorf("workflow %s not found", workflowID)
	}
	if wf.Status == models.WorkflowStatusCompleted || wf.Status == models.WorkflowStatusFailed || wf.Status == models.WorkflowStatusCancelled {
		return nil
	}
	cancelled := string(models.WorkflowStatusCancelled)
	return e.workflows.UpdateProgress(ctx, workflowID, &cancelled, nil, nil, nil, nil)
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
