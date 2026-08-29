import unittest
from pathlib import Path

from fastapi import FastAPI

from backend.app.api.projects import router
from backend.app import main

main_app = main.app


class LegacyRouteIsolationTests(unittest.TestCase):
    def test_direct_ai_correction_and_generation_routes_are_not_exposed(self):
        app = FastAPI()
        app.include_router(router)
        paths = app.openapi()["paths"]

        self.assertNotIn("/api/validate-room", paths)
        self.assertNotIn("/api/smart-correct", paths)
        self.assertNotIn("/api/generate-dxf", paths)

    def test_dxf_export_only_accepts_the_unmodified_detected_layout(self):
        app = FastAPI()
        app.include_router(router)
        operation = app.openapi()["paths"]["/api/projects/{project_id}/dxf"]["get"]
        mode = next(parameter for parameter in operation["parameters"] if parameter["name"] == "mode")

        self.assertEqual(mode["schema"]["const"], "original")

    def test_unowned_task_status_and_standalone_generator_are_not_exposed(self):
        paths = main_app.openapi()["paths"]

        self.assertNotIn("/api/analysis/{task_id}", paths)
        self.assertNotIn("/generator", paths)

    def test_fastapi_serves_the_current_vite_build(self):
        self.assertEqual(
            Path(main.DIST_DIR),
            Path(main.PROJECT_ROOT) / "frontend" / "dist",
        )


if __name__ == "__main__":
    unittest.main()
