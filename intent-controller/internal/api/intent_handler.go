package api

import (
	"encoding/json"
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/precision-genomics/intent-controller/internal/intent"
	"github.com/precision-genomics/intent-controller/internal/models"
	"github.com/precision-genomics/intent-controller/internal/store"
)

// IntentHandler handles HTTP requests for intent operations.
type IntentHandler struct {
	manager *intent.Manager
	repo    *store.IntentRepo
}

// Create handles POST /api/v1/intents
func (h *IntentHandler) Create(w http.ResponseWriter, r *http.Request) {
	var req models.CreateIntentRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body: "+err.Error())
		return
	}

	result, err := h.manager.Create(r.Context(), req)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	writeJSON(w, http.StatusCreated, result)
}

// List handles GET /api/v1/intents
func (h *IntentHandler) List(w http.ResponseWriter, r *http.Request) {
	status := r.URL.Query().Get("status")
	intentType := r.URL.Query().Get("type")

	intents, err := h.repo.List(r.Context(), status, intentType, 100, 0)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	if intents == nil {
		intents = []*models.Intent{}
	}

	writeJSON(w, http.StatusOK, intents)
}

// Get handles GET /api/v1/intents/{id}
func (h *IntentHandler) Get(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	result, err := h.repo.GetByIntentID(r.Context(), id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if result == nil {
		writeError(w, http.StatusNotFound, "intent not found")
		return
	}
	writeJSON(w, http.StatusOK, result)
}

// Cancel handles DELETE /api/v1/intents/{id}
func (h *IntentHandler) Cancel(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	result, err := h.manager.Cancel(r.Context(), id)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, result)
}

// Process handles POST /api/v1/intents/{id}/process
func (h *IntentHandler) Process(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	result, err := h.manager.Process(r.Context(), id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, result)
}

// Status handles GET /api/v1/intents/{id}/status
func (h *IntentHandler) Status(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	result, err := h.repo.GetByIntentID(r.Context(), id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if result == nil {
		writeError(w, http.StatusNotFound, "intent not found")
		return
	}

	status := map[string]interface{}{
		"intent_id":    result.IntentID,
		"status":       result.Status,
		"intent_type":  result.IntentType,
		"workflow_ids": result.WorkflowIDs,
		"eval_results": result.EvalResults,
		"error":        result.Error,
		"created_at":   result.CreatedAt,
		"completed_at": result.CompletedAt,
	}
	writeJSON(w, http.StatusOK, status)
}
