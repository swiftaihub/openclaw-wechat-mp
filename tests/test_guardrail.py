import unittest

from app.guardrail import GuardrailEngine
from app.prompt_runtime import GuardrailSettings


class GuardrailEngineTests(unittest.TestCase):
    def test_blocked_input_returns_blocked_response(self) -> None:
        settings = GuardrailSettings(
            blocked_input_patterns=(r"(?i)forbidden",),
            blocked_response="BLOCKED",
        )
        engine = GuardrailEngine(settings)

        result = engine.check_input("This contains forbidden content")

        self.assertTrue(result.blocked)
        self.assertEqual(result.text, "BLOCKED")

    def test_output_redaction_and_trim(self) -> None:
        settings = GuardrailSettings(
            max_output_chars=20,
            redaction_patterns=(r"SECRET_[A-Z0-9]+",),
            redaction_replacement="[MASKED]",
            trim_suffix="...",
        )
        engine = GuardrailEngine(settings)

        sanitized = engine.sanitize_output("Value SECRET_123456789 is present")

        self.assertNotIn("SECRET_", sanitized)
        self.assertLessEqual(len(sanitized), 20)

    def test_blocked_output_pattern(self) -> None:
        settings = GuardrailSettings(
            blocked_output_patterns=(r"(?i)do_not_return",),
            blocked_response="BLOCKED_OUT",
        )
        engine = GuardrailEngine(settings)

        sanitized = engine.sanitize_output("please DO_NOT_RETURN this")

        self.assertEqual(sanitized, "BLOCKED_OUT")


if __name__ == "__main__":
    unittest.main()
