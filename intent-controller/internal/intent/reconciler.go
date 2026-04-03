package intent

import (
	"context"
	"log/slog"
	"time"

	"github.com/precision-genomics/intent-controller/internal/models"
	"github.com/precision-genomics/intent-controller/internal/store"
)

// Reconciler periodically processes non-terminal intents to advance their state.
type Reconciler struct {
	manager  *Manager
	intents  *store.IntentRepo
	interval time.Duration
}

// NewReconciler creates a new reconciler that polls at the given interval.
func NewReconciler(manager *Manager, intents *store.IntentRepo, interval time.Duration) *Reconciler {
	return &Reconciler{
		manager:  manager,
		intents:  intents,
		interval: interval,
	}
}

// Run starts the reconciliation loop. It blocks until ctx is cancelled.
func (r *Reconciler) Run(ctx context.Context) {
	ticker := time.NewTicker(r.interval)
	defer ticker.Stop()

	slog.Info("reconciler started", "interval", r.interval)

	for {
		select {
		case <-ctx.Done():
			slog.Info("reconciler stopped")
			return
		case <-ticker.C:
			r.reconcileAll(ctx)
		}
	}
}

func (r *Reconciler) reconcileAll(ctx context.Context) {
	nonTerminalStatuses := []string{"declared", "resolving", "blocked", "active", "verifying"}

	for _, status := range nonTerminalStatuses {
		intents, err := r.intents.List(ctx, status, "", 100, 0)
		if err != nil {
			slog.Error("reconciler: failed to list intents", "status", status, "error", err)
			continue
		}

		for _, intent := range intents {
			if models.TerminalStates[intent.Status] {
				continue
			}

			_, err := r.manager.Process(ctx, intent.IntentID)
			if err != nil {
				slog.Error("reconciler: failed to process intent",
					"intent_id", intent.IntentID, "status", intent.Status, "error", err)
			}
		}
	}
}
