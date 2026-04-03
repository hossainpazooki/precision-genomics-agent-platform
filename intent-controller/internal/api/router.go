package api

import (
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/precision-genomics/intent-controller/internal/intent"
	"github.com/precision-genomics/intent-controller/internal/store"
	"github.com/precision-genomics/intent-controller/internal/workflow"
)

// NewRouter creates the HTTP router with all intent and workflow routes.
func NewRouter(
	manager *intent.Manager,
	engine *workflow.Engine,
	intentRepo *store.IntentRepo,
	workflowRepo *store.WorkflowRepo,
) http.Handler {
	r := chi.NewRouter()

	// Middleware
	r.Use(CORS)
	r.Use(RequestID)
	r.Use(Logger)

	// Health endpoints
	r.Get("/healthz", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	r.Get("/readyz", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ready"})
	})

	// Intent handlers
	ih := &IntentHandler{manager: manager, repo: intentRepo}
	r.Route("/api/v1/intents", func(r chi.Router) {
		r.Post("/", ih.Create)
		r.Get("/", ih.List)
		r.Get("/{id}", ih.Get)
		r.Delete("/{id}", ih.Cancel)
		r.Post("/{id}/process", ih.Process)
		r.Get("/{id}/status", ih.Status)
	})

	// Workflow handlers
	wh := &WorkflowHandler{engine: engine, repo: workflowRepo}
	r.Route("/api/v1/workflows", func(r chi.Router) {
		r.Post("/", wh.Trigger)
		r.Get("/", wh.List)
		r.Get("/{id}", wh.Get)
		r.Post("/{id}/cancel", wh.Cancel)
		r.Get("/{id}/steps", wh.Steps)
	})

	return r
}
