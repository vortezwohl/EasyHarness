"""Regression tests for runtime context window resolution."""

from __future__ import annotations

import unittest

from easyharness import ModelConfig
from easyharness._internal.model import build_runtime_model


class ContextWindowResolutionTests(unittest.TestCase):
    """Verify public overrides and runtime fallback behavior."""

    def test_explicit_context_window_limit_override_is_preserved(self) -> None:
        """Use the caller-supplied limit when one is provided."""

        runtime_model = build_runtime_model(
            ModelConfig(
                model="openai/gpt-4.1-mini",
                api_key="k",
                context_window_limit=131072,
            )
        )

        self.assertEqual(
            runtime_model.get_config()["context_window_limit"],
            131072,
        )

    def test_provider_prefixed_model_id_uses_known_metadata(self) -> None:
        """Resolve known metadata even when the model ID includes a provider."""

        runtime_model = build_runtime_model(
            ModelConfig(
                model="openai/gpt-4.1-mini",
                api_key="k",
            )
        )

        self.assertEqual(
            runtime_model.get_config()["context_window_limit"],
            1047576,
        )

    def test_unknown_model_falls_back_to_default_limit(self) -> None:
        """Use the SDK fallback when metadata resolution cannot find a match."""

        runtime_model = build_runtime_model(
            ModelConfig(
                model="unknown-model",
                api_key="k",
            )
        )

        self.assertEqual(
            runtime_model.get_config()["context_window_limit"],
            200000,
        )


if __name__ == "__main__":
    unittest.main()
