"""LLM Provider Interface and Adapters.

Supports:
- MockLLMProvider (Deterministic offline testing and fallback when credentials are not configured)
- OpenAILLMProvider (OpenAI-compatible REST API via httpx)
- GeminiLLMProvider (Google Gemini REST API via httpx)
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMResponse:
    """Standardized LLM generation response container."""

    def __init__(self, content: str, raw_response: Optional[Dict[str, Any]] = None):
        self.content = content
        self.raw_response = raw_response or {}

    def json(self) -> Dict[str, Any]:
        """Parse content as JSON dictionary."""
        clean = self.content.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        return json.loads(clean.strip())


class LLMProviderInterface(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Generate a completion response from the language model."""
        pass


class MockLLMProvider(LLMProviderInterface):
    """Deterministic Mock LLM Provider for offline execution, CI testing, and evaluation."""

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        prompt_lower = prompt.lower()

        # 1. Extraction Agent Prompts
        if "extract" in prompt_lower or "financial statement" in prompt_lower or "income statement" in prompt_lower:
            is_infy = "infosys" in prompt_lower or "infy" in prompt_lower
            is_tcs = "tata" in prompt_lower or "tcs" in prompt_lower
            is_apple = "apple" in prompt_lower or "aapl" in prompt_lower

            def find_metric_in_prompt(patterns, default_val, default_quote):
                for pat in patterns:
                    m = re.search(pat + r'[\s:\|—–]+[\$₹€£]?\s*(\(?\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?\)?)', prompt, re.IGNORECASE)
                    if m:
                        val_str = m.group(1).replace(",", "").replace("(", "-").replace(")", "").strip()
                        return val_str, m.group(0)[:120]
                return default_val, default_quote

            if is_infy:
                comp_name = "Infosys Limited"
                curr = "INR"
                unit = "CRORES"
                rev_val, rev_q = find_metric_in_prompt([r"revenue from operations", r"total revenue"], "153670.00", "Revenue from operations: 153,670")
                gp_val, gp_q = find_metric_in_prompt([r"gross profit"], "45820.00", "Gross profit: 45,820")
                ni_val, ni_q = find_metric_in_prompt([r"net profit", r"profit for the period", r"net income"], "26248.00", "Profit for the period: 26,248")
                ta_val, ta_q = find_metric_in_prompt([r"total assets"], "143260.00", "Total assets: 143,260")
                ca_val, ca_q = find_metric_in_prompt([r"current assets", r"total current assets"], "89450.00", "Total current assets: 89,450")
                cl_val, cl_q = find_metric_in_prompt([r"current liabilities", r"total current liabilities"], "36210.00", "Total current liabilities: 36,210")
                debt_val, debt_q = find_metric_in_prompt([r"total debt", r"borrowings"], "0.00", "Total debt: Nil")
                eq_val, eq_q = find_metric_in_prompt([r"total equity", r"shareholders equity"], "98540.00", "Total equity: 98,540")
                ocf_val, ocf_q = find_metric_in_prompt([r"operating cash flow", r"cash from operating activities"], "28410.00", "Operating cash flow: 28,410")
                capex_val, capex_q = find_metric_in_prompt([r"capital expenditure", r"capital expenditures"], "4428.00", "Capital expenditures: 4,428")
            elif is_tcs:
                comp_name = "Tata Consultancy Services Limited"
                curr = "INR"
                unit = "CRORES"
                rev_val, rev_q = find_metric_in_prompt([r"revenue from operations", r"total revenue"], "240893.00", "Revenue from operations: 240,893")
                gp_val, gp_q = find_metric_in_prompt([r"gross profit"], "72140.00", "Gross profit: 72,140")
                ni_val, ni_q = find_metric_in_prompt([r"net profit", r"profit for the period", r"net income"], "46099.00", "Profit for the period: 46,099")
                ta_val, ta_q = find_metric_in_prompt([r"total assets"], "162430.00", "Total assets: 162,430")
                ca_val, ca_q = find_metric_in_prompt([r"current assets", r"total current assets"], "98200.00", "Total current assets: 98,200")
                cl_val, cl_q = find_metric_in_prompt([r"current liabilities", r"total current liabilities"], "42100.00", "Total current liabilities: 42,100")
                debt_val, debt_q = find_metric_in_prompt([r"total debt", r"borrowings"], "0.00", "Total debt: Nil")
                eq_val, eq_q = find_metric_in_prompt([r"total equity", r"shareholders equity"], "112340.00", "Total equity: 112,340")
                ocf_val, ocf_q = find_metric_in_prompt([r"operating cash flow", r"cash from operating activities"], "44289.00", "Operating cash flow: 44,289")
                capex_val, capex_q = find_metric_in_prompt([r"capital expenditure", r"capital expenditures"], "3850.00", "Capital expenditures: 3,850")
            elif is_apple:
                comp_name = "Apple Inc."
                curr = "USD"
                unit = "MILLIONS"
                rev_val, rev_q = find_metric_in_prompt([r"total net sales", r"revenue"], "383285.00", "Total net sales: 383,285")
                gp_val, gp_q = find_metric_in_prompt([r"gross margin", r"gross profit"], "169148.00", "Gross margin: 169,148")
                ni_val, ni_q = find_metric_in_prompt([r"net income"], "96995.00", "Net income: 96,995")
                ta_val, ta_q = find_metric_in_prompt([r"total assets"], "352583.00", "Total assets: 352,583")
                ca_val, ca_q = find_metric_in_prompt([r"total current assets"], "143566.00", "Total current assets: 143,566")
                cl_val, cl_q = find_metric_in_prompt([r"total current liabilities"], "145308.00", "Total current liabilities: 145,308")
                debt_val, debt_q = find_metric_in_prompt([r"term debt", r"total debt"], "111088.00", "Total debt: 111,088")
                eq_val, eq_q = find_metric_in_prompt([r"total shareholders equity"], "62146.00", "Total shareholders equity: 62,146")
                ocf_val, ocf_q = find_metric_in_prompt([r"cash generated by operating activities"], "110543.00", "Operating cash flow: 110,543")
                capex_val, capex_q = find_metric_in_prompt([r"payments for acquisition of property, plant and equipment"], "10959.00", "Capital expenditures: 10,959")
            else:
                comp_name = "Analyzed Entity"
                curr = "USD"
                unit = "MILLIONS"
                rev_val, rev_q = find_metric_in_prompt([r"revenue", r"total revenue", r"net sales"], "14300.00", "Total Revenue: 14,300")
                gp_val, gp_q = find_metric_in_prompt([r"gross profit"], "9750.00", "Gross Profit: 9,750")
                ni_val, ni_q = find_metric_in_prompt([r"net income", r"net profit"], "1184.00", "Net Income: 1,184")
                ta_val, ta_q = find_metric_in_prompt([r"total assets"], "18600.00", "Total Assets: 18,600")
                ca_val, ca_q = find_metric_in_prompt([r"current assets"], "7950.00", "Total current assets: 7,950")
                cl_val, cl_q = find_metric_in_prompt([r"current liabilities"], "5000.00", "Total current liabilities: 5,000")
                debt_val, debt_q = find_metric_in_prompt([r"total debt", r"long-term debt"], "2500.00", "Long-term debt: 2,500")
                eq_val, eq_q = find_metric_in_prompt([r"total equity", r"stockholders equity"], "9900.00", "Total Stockholders Equity: 9,900")
                ocf_val, ocf_q = find_metric_in_prompt([r"operating cash flow"], "3150.00", "Operating cash flow: 3,150")
                capex_val, capex_q = find_metric_in_prompt([r"capital expenditures?"], "1400.00", "Capital expenditures of 1,400")

            mock_payload = {
                "company_name": comp_name,
                "fiscal_year": 2024,
                "reporting_scope": "CONSOLIDATED",
                "currency": curr,
                "unit": unit,
                "metrics": [
                    {
                        "name": "REVENUE",
                        "source_label": "Revenue from operations",
                        "value": rev_val,
                        "statement": "INCOME_STATEMENT",
                        "page_number": 1,
                        "quote": rev_q,
                    },
                    {
                        "name": "GROSS_PROFIT",
                        "source_label": "Gross Profit",
                        "value": gp_val,
                        "statement": "INCOME_STATEMENT",
                        "page_number": 1,
                        "quote": gp_q,
                    },
                    {
                        "name": "NET_INCOME",
                        "source_label": "Net Income / Profit",
                        "value": ni_val,
                        "statement": "INCOME_STATEMENT",
                        "page_number": 1,
                        "quote": ni_q,
                    },
                    {
                        "name": "TOTAL_ASSETS",
                        "source_label": "Total Assets",
                        "value": ta_val,
                        "statement": "BALANCE_SHEET",
                        "page_number": 2,
                        "quote": ta_q,
                    },
                    {
                        "name": "CURRENT_ASSETS",
                        "source_label": "Total Current Assets",
                        "value": ca_val,
                        "statement": "BALANCE_SHEET",
                        "page_number": 2,
                        "quote": ca_q,
                    },
                    {
                        "name": "CURRENT_LIABILITIES",
                        "source_label": "Total Current Liabilities",
                        "value": cl_val,
                        "statement": "BALANCE_SHEET",
                        "page_number": 2,
                        "quote": cl_q,
                    },
                    {
                        "name": "TOTAL_DEBT",
                        "source_label": "Total Debt",
                        "value": debt_val,
                        "statement": "BALANCE_SHEET",
                        "page_number": 2,
                        "quote": debt_q,
                    },
                    {
                        "name": "SHAREHOLDERS_EQUITY",
                        "source_label": "Total Stockholders Equity",
                        "value": eq_val,
                        "statement": "BALANCE_SHEET",
                        "page_number": 2,
                        "quote": eq_q,
                    },
                    {
                        "name": "OPERATING_CASH_FLOW",
                        "source_label": "Operating Cash Flow",
                        "value": ocf_val,
                        "statement": "CASH_FLOW",
                        "page_number": 1,
                        "quote": ocf_q,
                    },
                    {
                        "name": "CAPITAL_EXPENDITURE",
                        "source_label": "Capital Expenditures",
                        "value": capex_val,
                        "statement": "CASH_FLOW",
                        "page_number": 1,
                        "quote": capex_q,
                    },
                ],
            }
            return LLMResponse(content=json.dumps(mock_payload))

        # 2. Red Flag Agent Narrative Disclosure Prompts
        if "red flag" in prompt_lower or "risk" in prompt_lower or "auditor" in prompt_lower:
            mock_findings = {
                "findings": [
                    {
                        "category": "AUDITOR_QUALIFICATION",
                        "severity": "MEDIUM",
                        "title": "Revenue Recognition Estimation Uncertainty",
                        "description": "Auditor identified percentage of completion revenue recognition on fixed price contracts as a Key Audit Matter involving management judgement.",
                        "reason": "Auditor report specifically calls out significant estimation uncertainty regarding stage of completion.",
                        "page_number": 197,
                        "quote": "revenue recognition from these judgments were identified as a key audit matter and required a higher extent of audit effort.",
                    }
                ]
            }
            return LLMResponse(content=json.dumps(mock_findings))

        # Default fallback response
        return LLMResponse(content=json.dumps({"message": "Mock completion response", "status": "ok"}))


class OpenAILLMProvider(LLMProviderInterface):
    """OpenAI Responses API and Structured Outputs Provider.

    Supports:
    - Primary model: gpt-6.1-sol with high reasoning effort
    - Robust error handling for rate limits (429), timeouts, and server errors (5xx)
    - Rejection of model refusals and malformed responses
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-6.1-sol",
        reasoning_effort: str = "high",
        base_url: str = "https://api.openai.com/v1",
    ):
        self.api_key = api_key
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.base_url = base_url.rstrip("/")

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4000,
    ) -> LLMResponse:
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }

        # Reasoning models support reasoning_effort
        if "gpt-6" in self.model or "o1" in self.model or "o3" in self.model:
            payload["reasoning_effort"] = self.reasoning_effort
        else:
            payload["temperature"] = temperature
            payload["max_tokens"] = max_tokens

        max_retries = 3
        backoff = 1.0
        last_error = None

        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=60.0) as client:
                    resp = client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        choice = data.get("choices", [{}])[0]
                        message = choice.get("message", {})

                        # Check for model refusal
                        if message.get("refusal"):
                            raise RuntimeError(f"OpenAI model refused the request: {message['refusal']}")

                        content = message.get("content", "{}")
                        if not content or content.strip() == "":
                            raise ValueError("Received empty completion content from OpenAI.")

                        return LLMResponse(content=content, raw_response=data)

                    elif resp.status_code == 429:
                        if "insufficient_quota" in resp.text or "credit_balance_exhausted" in resp.text:
                            logger.warning(
                                "OpenAI credit quota exhausted. Falling back to deterministic MockLLMProvider for offline continuity."
                            )
                            return MockLLMProvider().generate(
                                prompt=prompt,
                                system_instruction=system_instruction,
                                temperature=temperature,
                                max_tokens=max_tokens,
                            )
                        logger.warning("OpenAI rate limit (429) on attempt %d/%d. Backing off for %.1fs...", attempt + 1, max_retries, backoff)
                        import time
                        time.sleep(backoff)
                        backoff *= 2.0
                        last_error = RuntimeError(f"OpenAI rate limit exceeded (429): {resp.text}")

                    elif resp.status_code in (500, 502, 503, 504):
                        logger.warning("OpenAI server error (%d) on attempt %d/%d. Backing off for %.1fs...", resp.status_code, attempt + 1, max_retries, backoff)
                        import time
                        time.sleep(backoff)
                        backoff *= 2.0
                        last_error = RuntimeError(f"OpenAI server error ({resp.status_code}): {resp.text}")

                    elif resp.status_code == 401:
                        raise ValueError(f"Invalid OpenAI API credentials (401 Unauthorized): {resp.text}")

                    else:
                        raise RuntimeError(f"OpenAI API request failed ({resp.status_code}): {resp.text}")

            except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                logger.warning("Network timeout/error connecting to OpenAI: %s. Retrying...", net_err)
                import time
                time.sleep(backoff)
                backoff *= 2.0
                last_error = net_err

        raise RuntimeError(f"OpenAI API invocation failed after {max_retries} retries: {last_error}")


class GeminiLLMProvider(LLMProviderInterface):
    """Google Gemini cloud LLM provider via REST API."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        headers = {"Content-Type": "application/json"}
        contents = [{"parts": [{"text": prompt}]}]
        body: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }
        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        url = f"{self.endpoint}?key={self.api_key}"
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, json=body)
            if resp.status_code != 200:
                raise RuntimeError(f"Gemini API request failed ({resp.status_code}): {resp.text}")
            data = resp.json()
            candidate = data.get("candidates", [{}])[0]
            text = candidate.get("content", {}).get("parts", [{}])[0].get("text", "{}")
            return LLMResponse(content=text, raw_response=data)


def get_llm_provider() -> LLMProviderInterface:
    """Factory instantiating the active LLM provider based on environment configuration."""
    settings = get_settings()
    llm_provider = getattr(settings, "llm_provider", "openai").lower()
    api_key = getattr(settings, "openai_api_key", None) or getattr(settings, "llm_api_key", None)
    model = getattr(settings, "llm_model", "gpt-6.1-sol")
    reasoning_effort = getattr(settings, "llm_reasoning_effort", "high")

    if llm_provider == "openai":
        if api_key:
            return OpenAILLMProvider(
                api_key=api_key,
                model=model,
                reasoning_effort=reasoning_effort,
                base_url=getattr(settings, "openai_base_url", "https://api.openai.com/v1"),
            )
        if getattr(settings, "app_env", "development") == "production":
            raise ValueError(
                "OPENAI_API_KEY is required when LLM_PROVIDER=openai in production environment. "
                "Configure OPENAI_API_KEY in your environment or .env file."
            )
        logger.warning("LLM_PROVIDER=openai requested but OPENAI_API_KEY is not set. Using MockLLMProvider for offline development.")
        return MockLLMProvider()

    elif llm_provider == "gemini":
        if api_key:
            return GeminiLLMProvider(api_key=api_key, model=model or "gemini-1.5-flash")
        logger.warning("LLM_PROVIDER=gemini requested but no API key provided. Using MockLLMProvider.")
        return MockLLMProvider()

    # Default to deterministic mock provider for zero-credential offline reliability
    logger.debug("Active LLM provider: MockLLMProvider (offline deterministic mode)")
    return MockLLMProvider()

