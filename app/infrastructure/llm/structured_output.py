"""Structured Output Parser and Validation Engine for LLM interactions."""

import json
import logging
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class StructuredOutputParser:
    """Parses, validates, and retries LLM responses against Pydantic schemas."""

    @staticmethod
    def parse_and_validate(raw_text: str, schema_cls: Type[T]) -> T:
        """Clean markdown markers, extract JSON, and validate against Pydantic model."""
        clean = raw_text.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()

        try:
            data = json.loads(clean)
        except json.JSONDecodeError as jde:
            logger.error("JSON decode error parsing LLM response: %s | Content: %s", jde, clean[:200])
            raise ValueError(f"Failed to parse LLM response as JSON: {jde}") from jde

        try:
            return schema_cls.model_validate(data)
        except ValidationError as ve:
            logger.error("Schema validation error against %s: %s", schema_cls.__name__, ve)
            raise ValueError(f"LLM output failed {schema_cls.__name__} schema validation: {ve}") from ve

