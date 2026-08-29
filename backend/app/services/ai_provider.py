from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


class ProviderConfigurationError(RuntimeError):
    """Raised when an external AI provider is not configured."""


class ProviderAuthenticationError(RuntimeError):
    """Raised when OpenRouter rejects the configured credentials."""


class ProviderCallError(RuntimeError):
    """Raised when all configured models fail to return a usable response."""


@dataclass(frozen=True)
class ProviderModels:
    vision: str = "google/gemini-2.5-flash"
    planning: str = "openai/gpt-4o-mini"
    assistant: str = "openai/gpt-4o-mini"
    fallbacks: tuple[str, ...] = ()



class OpenRouterProvider:
    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        *,
        api_key: str,
        models: ProviderModels | None = None,
        client_factory: Callable[..., Any] = OpenAI,
    ) -> None:
        self._api_key = api_key.strip()
        self._models = models or ProviderModels()
        self._client_factory = client_factory
        self._client: Any | None = None

    def _require_client(self) -> Any:
        if not self._api_key:
            raise ProviderConfigurationError(
                "OPENROUTER_API_KEY is required for AI-assisted features"
            )
        if self._client is None:
            self._client = self._client_factory(
                base_url=self.BASE_URL,
                api_key=self._api_key,
            )
        return self._client

    def complete_text(
        self,
        *,
        role: str,
        messages: list[dict[str, Any]],
        max_tokens: int = 700,
        temperature: float = 0.2,
        extra_body: dict[str, Any] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        client = self._require_client()
        model = {
            "vision": self._models.vision,
            "planning": self._models.planning,
            "assistant": self._models.assistant,
        }.get(role)
        if model is None:
            raise ValueError(f"Unsupported AI role: {role}")

        errors: list[str] = []
        models = tuple(dict.fromkeys((model, *self._models.fallbacks)))
        for model_id in models:
            try:
                request = {
                    "model": model_id,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "extra_body": extra_body or {},
                }
                if response_format is not None:
                    request["response_format"] = response_format
                response = client.chat.completions.create(**request)
                content = response.choices[0].message.content
                if isinstance(content, str) and content.strip():
                    return content.strip()
                errors.append(f"{model_id}: empty response")
            except Exception as error:  # Provider SDK errors share no stable base class.
                status_code = getattr(error, "status_code", None)
                if status_code is None:
                    status_code = getattr(getattr(error, "response", None), "status_code", None)
                if status_code in {401, 403}:
                    raise ProviderAuthenticationError(
                        "OpenRouter rejected the configured API credentials"
                    ) from error
                errors.append(f"{model_id}: {type(error).__name__}")

        raise ProviderCallError(
            "OpenRouter models failed without a usable response: " + ", ".join(errors)
        )
