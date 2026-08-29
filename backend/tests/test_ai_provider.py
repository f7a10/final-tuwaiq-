import unittest
from types import SimpleNamespace

from backend.app.services.ai_provider import (
    OpenRouterProvider,
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderModels,
)


class OpenRouterProviderTests(unittest.TestCase):
    def test_missing_key_fails_before_creating_a_network_client(self):
        provider = OpenRouterProvider(api_key="", client_factory=lambda **_: self.fail("client created"))

        with self.assertRaisesRegex(ProviderConfigurationError, "OPENROUTER_API_KEY"):
            provider.complete_text(
                role="assistant",
                messages=[{"role": "user", "content": "مرحبا"}],
            )

    def test_successful_text_request_uses_the_model_for_its_role(self):
        calls = []

        class FakeCompletions:
            def create(self, **kwargs):
                calls.append(kwargs)
                return SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content="  إجابة واضحة  "))]
                )

        client = SimpleNamespace(
            chat=SimpleNamespace(completions=FakeCompletions())
        )
        provider = OpenRouterProvider(
            api_key="test-key",
            models=ProviderModels(assistant="assistant-model"),
            client_factory=lambda **_: client,
        )

        reply = provider.complete_text(
            role="assistant",
            messages=[{"role": "user", "content": "مرحبا"}],
            temperature=0.1,
        )

        self.assertEqual(reply, "إجابة واضحة")
        self.assertEqual(calls[0]["model"], "assistant-model")
        self.assertEqual(calls[0]["temperature"], 0.1)

    def test_failed_primary_model_falls_back_to_the_next_configured_model(self):
        calls = []

        class FakeCompletions:
            def create(self, **kwargs):
                calls.append(kwargs["model"])
                if kwargs["model"] == "primary-model":
                    raise TimeoutError("provider timeout")
                return SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content="من الاحتياط"))]
                )

        client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
        provider = OpenRouterProvider(
            api_key="test-key",
            models=ProviderModels(
                assistant="primary-model",
                fallbacks=("backup-model",),
            ),
            client_factory=lambda **_: client,
        )

        reply = provider.complete_text(
            role="assistant",
            messages=[{"role": "user", "content": "مرحبا"}],
        )

        self.assertEqual(reply, "من الاحتياط")
        self.assertEqual(calls, ["primary-model", "backup-model"])

    def test_structured_output_schema_is_forwarded_to_openrouter(self):
        calls = []

        class FakeCompletions:
            def create(self, **kwargs):
                calls.append(kwargs)
                return SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content='{"status":"ready"}'))]
                )

        client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
        provider = OpenRouterProvider(
            api_key="test-key",
            models=ProviderModels(planning="planning-model"),
            client_factory=lambda **_: client,
        )
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "edit_intent",
                "strict": True,
                "schema": {"type": "object"},
            },
        }

        provider.complete_text(
            role="planning",
            messages=[{"role": "user", "content": "حرك الجدار"}],
            response_format=response_format,
        )

        self.assertEqual(calls[0]["response_format"], response_format)

    def test_authentication_failure_does_not_try_fallback_models(self):
        calls = []

        class UnauthorizedError(Exception):
            status_code = 401

        class FakeCompletions:
            def create(self, **kwargs):
                calls.append(kwargs["model"])
                raise UnauthorizedError("invalid key")

        client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
        provider = OpenRouterProvider(
            api_key="test-key",
            models=ProviderModels(
                assistant="primary-model",
                fallbacks=("backup-model",),
            ),
            client_factory=lambda **_: client,
        )

        with self.assertRaises(ProviderAuthenticationError):
            provider.complete_text(
                role="assistant",
                messages=[{"role": "user", "content": "مرحبا"}],
            )

        self.assertEqual(calls, ["primary-model"])


if __name__ == "__main__":
    unittest.main()
