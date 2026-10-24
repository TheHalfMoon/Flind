package core

import (
    "strings"
    "testing"
)

// Flind's installer must not silently publish a customer's domain or install
// lifecycle to an inherited analytics service.
func TestInstallerContainsNoTelemetrySteps(t *testing.T) {
    steps := GetInstallSteps()
    if len(steps) == 0 {
        t.Fatal("expected installer steps")
    }
    for _, step := range steps {
        if strings.Contains(strings.ToLower(step.Name), "telemetry") {
            t.Fatalf("installer still has a telemetry step: %s", step.Name)
        }
    }
}
