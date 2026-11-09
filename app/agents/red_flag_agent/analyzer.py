"""LLM-Based Narrative Disclosure Risk Analyzer.

Inspects auditor opinions, going-concern warnings, contingent liabilities,
and management disclosures for material financial warning indicators.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.infrastructure.llm import LLMProviderInterface, get_llm_provider
from app.schemas.agents import (
    RedFlagFinding,
    RiskCategory,
    RiskSeverity,
    SourceCitation,
)

logger = logging.getLogger(__name__)


class DisclosureAnalyzer:
    """Analyzes narrative disclosures for qualitative and statutory risks using LLM."""

    def __init__(self, llm_provider: Optional[LLMProviderInterface] = None):
        self.llm = llm_provider or get_llm_provider()

    def analyze_disclosures(
        self,
        document_id: str,
        filename: str,
        chunks: List[Dict[str, Any]],
        fiscal_year: int = 2025,
    ) -> List[RedFlagFinding]:
        """Inspect relevant text passages for auditor qualifications, going-concern warnings, etc."""
        # 1. Filter chunks for high-information risk keywords
        risk_keywords = [
            "auditor", "opinion", "qualification", "qualified", "adverse",
            "emphasis of matter", "going concern", "material weakness",
            "contingent liabilit", "litigation", "dispute", "uncertainty",
            "key audit matter", "restatement", "impairment"
        ]

        relevant_chunks = []
        for c in chunks:
            text_lower = c.get("text", "").lower()
            if any(kw in text_lower for kw in risk_keywords):
                relevant_chunks.append(c)

        if not relevant_chunks:
            # Fallback to first few narrative chunks if no keyword matches
            relevant_chunks = chunks[:5]

        # 2. Select top candidate excerpts
        excerpts_text = ""
        for rc in relevant_chunks[:8]:
            page = rc.get("page_number", 1)
            excerpts_text += f"\n--- [Page {page}] ---\n{rc.get('text', '')[:400]}\n"

        prompt = f"""
You are a senior forensic financial analyst. Review these financial disclosures and identify any material red flags or risks.
Focus specifically on:
1. Auditor qualifications, disclaimers, or emphasis of matters
2. Going-concern warnings or substantial doubt about solvency
3. Significant contingent liabilities, legal disputes, or major tax demands
4. Material accounting policy changes or estimation uncertainties

Return a clean JSON object with a 'findings' array:
[
  {{
    "category": "AUDITOR_QUALIFICATION" | "GOING_CONCERN" | "CONTINGENT_LIABILITIES" | "ACCOUNTING_ANOMALY",
    "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
    "title": "Concise risk headline",
    "description": "Specific explanation of the financial risk or statutory concern.",
    "reason": "Why this represents an analytical or solvency risk.",
    "page_number": 1,
    "quote": "Exact verbatim quote from the text supporting this finding"
  }}
]

Disclosures Text:
{excerpts_text}
"""
        system_instruction = "You are a forensic financial risk auditor. Only report verifiable risks with exact quotes from the text. Never hallucinate risks."

        findings: List[RedFlagFinding] = []
        try:
            resp = self.llm.generate(prompt=prompt, system_instruction=system_instruction)
            data = resp.json()
            raw_findings = data.get("findings", [])

            for item in raw_findings:
                cat_str = item.get("category", "ACCOUNTING_ANOMALY")
                sev_str = item.get("severity", "MEDIUM")
                page_num = int(item.get("page_number", 1))
                quote = str(item.get("quote", ""))
                title = str(item.get("title", "Financial Disclosure Risk"))
                desc = str(item.get("description", ""))
                reason = str(item.get("reason", ""))

                # Map category enum
                category = RiskCategory.ACCOUNTING_ANOMALY
                if "AUDITOR" in cat_str:
                    category = RiskCategory.AUDITOR_QUALIFICATION
                elif "GOING_CONCERN" in cat_str:
                    category = RiskCategory.GOING_CONCERN
                elif "CONTINGENT" in cat_str:
                    category = RiskCategory.CONTINGENT_LIABILITIES

                # Map severity enum
                severity = RiskSeverity.MEDIUM
                if sev_str == "CRITICAL":
                    severity = RiskSeverity.CRITICAL
                elif sev_str == "HIGH":
                    severity = RiskSeverity.HIGH
                elif sev_str == "LOW":
                    severity = RiskSeverity.LOW

                findings.append(
                    RedFlagFinding(
                        finding_id=uuid4().hex,
                        category=category,
                        severity=severity,
                        title=title,
                        description=desc,
                        supporting_evidence=quote,
                        reason_for_classification=reason,
                        relevant_period=f"FY {fiscal_year}",
                        source_citation=SourceCitation(
                            document_id=document_id,
                            filename=filename,
                            page_number=page_num,
                            exact_quote=quote,
                            is_calculated=False,
                        ),
                    )
                )
        except Exception as e:
            logger.warning("LLM narrative disclosure analysis encountered an issue: %s", e)

        return findings

