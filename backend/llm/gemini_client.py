import os
import re
from typing import Any, Dict

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


def _getenv(name: str, default: str = "") -> str:
    # For non-chat tasks (e.g., DB seeding), Gemini may be unavailable.
    # Gemini is required only when /chat is called.
    return os.getenv(name, default)


GEMINI_API_KEY = _getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = _getenv("GEMINI_MODEL", "gemini-1.5-flash")


def build_sql_system_prompt(schema_context: Dict[str, Any]) -> str:
    schema_context_str = schema_context.get("schema_prompt", "") or str(schema_context)
    error_hint = schema_context.get("error_hint", "") or ""

    extra = ""
    if error_hint:
        extra = (
            "\nPrevious SQL execution error (if any): "
            f"{error_hint}\n"
            "If there was an error, correct the SQL accordingly."
        )

    return (
        "You are an expert PostgreSQL analyst. "
        "Given the schema below, write a single, valid PostgreSQL SELECT query to answer the user's question. "
        "Return ONLY the SQL code. Do not write explanations.\n\n"
        f"Schema:\n{schema_context_str}\n"
        f"{extra}"
    )


def build_answer_prompt(question: str, sql: str, results: Any) -> str:
    return (
        "Summarize the following query results to answer the user's question in 2-3 sentences. Be concise.\n\n"
        f"User question:\n{question}\n\n"
        f"SQL:\n{sql}\n\n"
        f"Query results (JSON):\n{results}\n"
    )


def strip_sql(text: str) -> str:
    # Minor note: this function attempts to robustly extract SQL from mixed Gemini output.
    # Keep this deterministic to avoid flaky tests and contribution differences.
    """
    Tries to extract SQL from a fenced code block. If none exists, returns the raw text.
    """
    candidate = (text or "").strip()
    m = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", candidate, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return candidate


async def generate_sql(
    client: genai.Client,
    *,
    schema_context: Dict[str, Any],
    question: str,
    model: str = GEMINI_MODEL,
) -> str:
    system_prompt = build_sql_system_prompt(schema_context)
    prompt = system_prompt + f"\nUser question: {question}\n\nSQL:"
    resp = await client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=512),
    )
    text = getattr(resp, "text", None) or str(resp)
    return strip_sql(text)


async def summarize_results(
    client: genai.Client,
    *,
    question: str,
    sql: str,
    results: Any,
    model: str = GEMINI_MODEL,
) -> str:
    prompt = build_answer_prompt(question, sql, results)
    resp = await client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=256),
    )
    text = getattr(resp, "text", None) or str(resp)
    return (text or "").strip()


def get_client() -> genai.Client:
    return genai.Client(api_key=GEMINI_API_KEY)

