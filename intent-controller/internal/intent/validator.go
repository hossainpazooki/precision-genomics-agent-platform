package intent

import (
	"fmt"

	"github.com/precision-genomics/intent-controller/internal/models"
)

// ValidateIntentParams validates the parameters for a given intent type.
func ValidateIntentParams(intentType string, params map[string]interface{}) error {
	spec, ok := models.IntentSpecs[intentType]
	if !ok {
		return fmt.Errorf("unknown intent type: %s", intentType)
	}

	switch spec.IntentType {
	case "analysis":
		return validateAnalysisParams(params)
	case "training":
		return validateTrainingParams(params)
	case "validation":
		return validateValidationParams(params)
	}

	return nil
}

func validateAnalysisParams(params map[string]interface{}) error {
	// dataset is optional, defaults to "train"
	if target, ok := params["target"]; ok {
		t, ok := target.(string)
		if !ok || t == "" {
			return fmt.Errorf("target must be a non-empty string")
		}
		validTargets := map[string]bool{"msi": true, "gender": true, "mismatch": true}
		if !validTargets[t] {
			return fmt.Errorf("invalid target %q; valid: msi, gender, mismatch", t)
		}
	}

	if modalities, ok := params["modalities"]; ok {
		mods, ok := modalities.([]interface{})
		if !ok {
			return fmt.Errorf("modalities must be an array")
		}
		for _, mod := range mods {
			ms, ok := mod.(string)
			if !ok {
				return fmt.Errorf("each modality must be a string")
			}
			validMods := map[string]bool{"proteomics": true, "rnaseq": true}
			if !validMods[ms] {
				return fmt.Errorf("invalid modality %q; valid: proteomics, rnaseq", ms)
			}
		}
	}

	return nil
}

func validateTrainingParams(params map[string]interface{}) error {
	if modelType, ok := params["model_type"]; ok {
		mt, ok := modelType.(string)
		if !ok {
			return fmt.Errorf("model_type must be a string")
		}
		validTypes := map[string]bool{"slm": true, "encoder": true, "cuml": true}
		if !validTypes[mt] {
			return fmt.Errorf("invalid model_type %q; valid: slm, encoder, cuml", mt)
		}
	}

	if numGPUs, ok := params["num_gpus"]; ok {
		switch n := numGPUs.(type) {
		case float64:
			if n < 1 || n > 4 {
				return fmt.Errorf("num_gpus must be between 1 and 4")
			}
		default:
			return fmt.Errorf("num_gpus must be a number")
		}
	}

	return nil
}

func validateValidationParams(params map[string]interface{}) error {
	// Validation intents are simple — just need a dataset
	return nil
}
