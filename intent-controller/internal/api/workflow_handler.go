package api

import (
	"encoding/json"
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/precision-genomics/intent-controller/internal/models"
	"github.com/precision-genomics/intent-controller/internal/store"
	"github.com/precision-genomics/intent-controller/internal/workflow"
)

// WorkflowHandler handles HTTP requests for workflow operations.
type WorkflowHandler struct {
	engine *workflow.Engine
	repo   *store.WorkflowRepo
}

// Trigger handles POST /api/v1/workflows
func (h *WorkflowHandler) Trigger(w http.ResponseWriter, r *http.Request) {
	var req models.TriggerWorkflowRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body: "+err.Error())
		return
	}

	if req.WorkflowType == "" {
		writeError(w, http.StatusBadRequest, "workflow_type is required")
		return
	}

	wfID, err := h.engine.Start(r.Context(), req.WorkflowType, req.Params)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	writeJSON(w, http.StatusCreated, map[string]string{
		"workflow_id": wfID,
		"status":      "pending",
	})
}

// List handles GET /api/v1/workflows
func (h *WorkflowHandler) List(w http.ResponseWriter, r *http.Request) {
	status := r.URL.Query().Get("status")

	workflows, err := h.repo.List(r.Context(), status, 100, 0)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	if workflows == nil {
		workflows = []*models.WorkflowExecution{}
	}

	writeJSON(w, http.StatusOK, workflows)
}

// Get handles GET /api/v1/workflows/{id}
func (h *WorkflowHandler) Get(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	wf, err := h.repo.GetByWorkflowID(r.Context(), id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if wf == nil {
		writeError(w, http.StatusNotFound, "workflow not found")
		return
	}
	writeJSON(w, http.StatusOK, wf)
}

// Cancel handles POST /api/v1/workflows/{id}/cancel
func (h *WorkflowHandler) Cancel(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	if err := h.engine.CancelWorkflow(r.Context(), id); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "cancelled"})
}

// Steps handles GET /api/v1/workflows/{id}/steps
func (h *WorkflowHandler) Steps(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	wf, err := h.repo.GetByWorkflowID(r.Context(), id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if wf == nil {
		writeError(w, http.StatusNotFound, "workflow not found")
		return
	}

	// Build step list from phases_completed and current_phase
	steps := []map[string]interface{}{}
	for _, phase := range wf.PhasesCompleted {
		steps = append(steps, map[string]interface{}{
			"phase_name": phase,
			"status":     "completed",
		})
	}
	if wf.Status == models.WorkflowStatusRunning && wf.CurrentPhase != "pending" {
		alreadyListed := false
		for _, s := range steps {
			if s["phase_name"] == wf.CurrentPhase {
				alreadyListed = true
				break
			}
		}
		if !alreadyListed {
			steps = append(steps, map[string]interface{}{
				"phase_name": wf.CurrentPhase,
				"status":     "running",
			})
		}
	}

	writeJSON(w, http.StatusOK, steps)
}

// helpers

func writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}
