package activity

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"time"

	"github.com/precision-genomics/intent-controller/internal/models"
)

// Dispatcher sends activity requests to the Python ML service over HTTP.
type Dispatcher struct {
	mlURL  string
	client *http.Client
}

// NewDispatcher creates a new activity dispatcher.
func NewDispatcher(mlServiceURL string) *Dispatcher {
	return &Dispatcher{
		mlURL: mlServiceURL,
		client: &http.Client{
			Timeout: 5 * time.Minute,
		},
	}
}

// CallML sends a POST request to the ML service and returns the response.
func (d *Dispatcher) CallML(ctx context.Context, path string, body map[string]interface{}) (map[string]interface{}, error) {
	jsonBody, err := json.Marshal(body)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	url := d.mlURL + path
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(jsonBody))
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	slog.Debug("calling ML service", "url", url)

	resp, err := d.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("ML service request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read response: %w", err)
	}

	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("ML service error (status %d): %s", resp.StatusCode, string(respBody))
	}

	var result map[string]interface{}
	if err := json.Unmarshal(respBody, &result); err != nil {
		return nil, fmt.Errorf("unmarshal response: %w", err)
	}

	return result, nil
}

// HealthCheck verifies the ML service is reachable.
func (d *Dispatcher) HealthCheck(ctx context.Context) error {
	url := d.mlURL + "/health"
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return err
	}

	resp, err := d.client.Do(req)
	if err != nil {
		return fmt.Errorf("ML service unreachable: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("ML service unhealthy: status %d", resp.StatusCode)
	}
	return nil
}

// ResolveInfra dispatches infrastructure resolution for a specific requirement.
func (d *Dispatcher) ResolveInfra(ctx context.Context, requirement string, intent *models.Intent) (map[string]interface{}, error) {
	switch requirement {
	case "worker_scaled":
		return d.ensureWorkerScaled(ctx, intent)
	case "gcs_data_staged":
		return d.ensureDataStaged(ctx, intent)
	case "vertex_ai_job":
		return d.provisionTrainingJob(ctx, intent)
	case "gpu_allocated":
		return d.checkGPUQuota(ctx, intent)
	default:
		slog.Warn("no handler for infra requirement", "requirement", requirement)
		return map[string]interface{}{"status": "skipped", "reason": "no handler"}, nil
	}
}

func (d *Dispatcher) ensureWorkerScaled(ctx context.Context, intent *models.Intent) (map[string]interface{}, error) {
	// In production, this would call the Pulumi Go SDK.
	// For now, return a mock successful result.
	workerMax := 5
	if wm, ok := intent.Params["worker_max_instances"].(float64); ok {
		workerMax = int(wm)
	}
	slog.Info("scaling workers", "intent_id", intent.IntentID, "max_instances", workerMax)
	return map[string]interface{}{
		"status":     "scaled",
		"stack_name": "dev",
		"worker_url": "",
	}, nil
}

func (d *Dispatcher) ensureDataStaged(ctx context.Context, intent *models.Intent) (map[string]interface{}, error) {
	dataset, _ := intent.Params["dataset"].(string)
	if dataset == "" {
		dataset = "train"
	}
	// Local fallback — assume data is available
	return map[string]interface{}{
		"status":  "staged",
		"source":  "local",
		"dataset": dataset,
	}, nil
}

func (d *Dispatcher) provisionTrainingJob(ctx context.Context, intent *models.Intent) (map[string]interface{}, error) {
	modelType, _ := intent.Params["model_type"].(string)
	if modelType == "" {
		modelType = "slm"
	}
	// Delegate to ML service for training job provisioning
	result, err := d.CallML(ctx, "/ml/pipeline", map[string]interface{}{
		"action":     "provision_training",
		"model_type": modelType,
		"params":     intent.Params,
	})
	if err != nil {
		return nil, err
	}
	return map[string]interface{}{
		"status": "provisioned",
		"job":    result,
	}, nil
}

func (d *Dispatcher) checkGPUQuota(ctx context.Context, intent *models.Intent) (map[string]interface{}, error) {
	spec, ok := models.IntentSpecs[intent.IntentType]
	maxGPUs := 4
	if ok {
		maxGPUs = spec.MaxGPUCount
	}
	if maxGPUs == 0 {
		maxGPUs = 4
	}

	requestedGPUs := 1
	if n, ok := intent.Params["num_gpus"].(float64); ok {
		requestedGPUs = int(n)
	}

	if requestedGPUs > maxGPUs {
		return map[string]interface{}{
			"status": "failed",
			"error":  fmt.Sprintf("requested %d GPUs exceeds limit of %d", requestedGPUs, maxGPUs),
		}, nil
	}

	return map[string]interface{}{
		"status":      "approved",
		"num_gpus":    requestedGPUs,
		"max_allowed": maxGPUs,
	}, nil
}

// RunEval runs an evaluation criterion via the ML service.
func (d *Dispatcher) RunEval(ctx context.Context, evalName string, threshold float64, intent *models.Intent) (map[string]interface{}, error) {
	result, err := d.CallML(ctx, "/ml/evaluate", map[string]interface{}{
		"eval_name": evalName,
		"threshold": threshold,
		"params":    intent.Params,
		"intent_id": intent.IntentID,
	})
	if err != nil {
		return nil, err
	}
	return result, nil
}

// DeployModel triggers a model deployment via the Pulumi Automation API.
func (d *Dispatcher) DeployModel(ctx context.Context, stackName, imageTag string) error {
	// In production, this would use the Pulumi Go SDK.
	slog.Info("deploying model", "stack", stackName, "image_tag", imageTag)
	return nil
}
