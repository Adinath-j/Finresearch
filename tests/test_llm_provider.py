"""Unit tests for LLM Provider abstraction and StructuredOutputParser."""

import unittest
from pydantic import BaseModel
from app.infrastructure.llm import (
    LLMResponse,
    MockLLMProvider,
    StructuredOutputParser,
    get_llm_provider,
)


class SampleSchema(BaseModel):
    company_name: str
    fiscal_year: int


class TestLLMProvider(unittest.TestCase):
    """Test suite verifying LLM provider layer and response validation."""

    def test_mock_provider_generation(self):
        provider = MockLLMProvider()
        resp = provider.generate(prompt="extract financial statements from report")
        self.assertIsInstance(resp, LLMResponse)
        data = resp.json()
        self.assertIn("metrics", data)
        self.assertGreater(len(data["metrics"]), 0)

    def test_structured_output_parser_cleans_markdown(self):
        raw_markdown = '```json\n{"company_name": "Infosys", "fiscal_year": 2026}\n```'
        parsed = StructuredOutputParser.parse_and_validate(raw_markdown, SampleSchema)
        self.assertEqual(parsed.company_name, "Infosys")
        self.assertEqual(parsed.fiscal_year, 2026)

    def test_structured_output_parser_invalid_json(self):
        invalid_raw = '```json\n{"company_name": "Incomplete"\n```'
        with self.assertRaises(ValueError):
            StructuredOutputParser.parse_and_validate(invalid_raw, SampleSchema)

    def test_openai_provider_refusal_raises_error(self):
        from unittest.mock import MagicMock, patch
        from app.infrastructure.llm.provider import OpenAILLMProvider

        with patch("httpx.Client.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [{
                    "message": {
                        "content": None,
                        "refusal": "I cannot interpret this proprietary financial document."
                    }
                }]
            }
            mock_post.return_value = mock_resp

            provider = OpenAILLMProvider(api_key="test-key")
            with self.assertRaises(RuntimeError) as ctx:
                provider.generate("Analyze this document")
            self.assertIn("refused", str(ctx.exception).lower())

    def test_openai_provider_rate_limit_retry(self):
        from unittest.mock import MagicMock, patch
        from app.infrastructure.llm.provider import OpenAILLMProvider

        with patch("httpx.Client.post") as mock_post:
            mock_429 = MagicMock()
            mock_429.status_code = 429
            mock_429.text = "Rate limit reached"

            mock_200 = MagicMock()
            mock_200.status_code = 200
            mock_200.json.return_value = {
                "choices": [{"message": {"content": '{"metrics": []}'}}]
            }

            mock_post.side_effect = [mock_429, mock_200]

            provider = OpenAILLMProvider(api_key="test-key")
            resp = provider.generate("Analyze statement")
            self.assertEqual(resp.json(), {"metrics": []})


if __name__ == "__main__":
    unittest.main()

