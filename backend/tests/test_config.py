import importlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class ConfigTests(unittest.TestCase):
    def test_external_provider_keys_are_empty_without_environment(self):
        with patch.dict(
            os.environ,
            {"OPENROUTER_API_KEY": "", "ROBOFLOW_API_KEY": ""},
        ):
            import backend.app.config as config

            config = importlib.reload(config)

            self.assertEqual(config.OPENROUTER_API_KEY, "")
            self.assertEqual(config.ROBOFLOW_API_KEY, "")

    def test_project_env_file_is_loaded_without_overriding_process_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text(
                "OPENROUTER_API_KEY=file-openrouter\nROBOFLOW_API_KEY=file-roboflow\n",
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {"OPENROUTER_API_KEY": "process-openrouter"},
                clear=True,
            ):
                import backend.app.config as config

                config.load_project_environment(root)

                self.assertEqual(os.environ["OPENROUTER_API_KEY"], "process-openrouter")
                self.assertEqual(os.environ["ROBOFLOW_API_KEY"], "file-roboflow")

    def test_openrouter_models_are_configurable_by_role(self):
        with patch.dict(
            os.environ,
            {
                "OPENROUTER_VISION_MODEL": "vision-model",
                "OPENROUTER_PLANNING_MODEL": "planning-model",
                "OPENROUTER_ASSISTANT_MODEL": "assistant-model",
                "OPENROUTER_FALLBACK_MODELS": "backup-one, backup-two ,backup-one",
            },
            clear=True,
        ):
            import backend.app.config as config

            config = importlib.reload(config)

            self.assertEqual(config.OPENROUTER_VISION_MODEL, "vision-model")
            self.assertEqual(config.OPENROUTER_PLANNING_MODEL, "planning-model")
            self.assertEqual(config.OPENROUTER_ASSISTANT_MODEL, "assistant-model")
            self.assertEqual(
                config.OPENROUTER_FALLBACK_MODELS,
                ("backup-one", "backup-two"),
            )

    def test_missing_jwt_secret_uses_a_strong_ephemeral_value_not_a_known_default(self):
        with patch.dict(os.environ, {"JWT_SECRET_KEY": ""}):
            import backend.app.config as config

            config = importlib.reload(config)

            self.assertTrue(config.JWT_SECRET_IS_EPHEMERAL)
            self.assertGreaterEqual(len(config.JWT_SECRET_KEY), 43)
            self.assertNotEqual(
                config.JWT_SECRET_KEY,
                "emad-super-secret-key-change-in-production-2026",
            )


if __name__ == "__main__":
    unittest.main()
