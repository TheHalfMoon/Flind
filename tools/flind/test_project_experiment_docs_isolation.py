"""Guard against Flind UI linking to unowned donor documentation.

These checks intentionally cover only the project-creation modal and the
experiment results help tooltip. They do not rewrite protocol identifiers,
source attribution, or unrelated documentation.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class FlindProjectExperimentDocsTests(unittest.TestCase):
    def test_project_modal_keeps_guidance_without_upstream_docs(self):
        source = (ROOT / "frontend/src/scenes/project/CreateProjectModal.tsx").read_text(encoding="utf-8")
        self.assertNotIn("posthog.com/docs/settings/projects", source)
        self.assertIn("Use projects to isolate products", source)
        self.assertIn("We recommend using the same project", source)
        self.assertIn("createProject({ name })", source)
        self.assertNotIn("Learn\u00a0more in Flind\u00a0docs", source)

    def test_experiment_help_stays_local_and_accessible(self):
        source = (ROOT / "frontend/src/scenes/experiments/MetricsView/new/HowToReadTooltip.tsx").read_text(encoding="utf-8")
        self.assertNotIn("posthog.com/docs/experiments/analyzing-results", source)
        self.assertIn("<BaseTooltip.Trigger", source)
        self.assertIn("How to read", source)
        self.assertIn("<BaseTooltip.Popup", source)
        self.assertIn("Is my variant significant?", source)
        self.assertIn("statsMethod", source)


if __name__ == "__main__":
    unittest.main()
