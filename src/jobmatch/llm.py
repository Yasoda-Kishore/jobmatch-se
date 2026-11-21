"""Talk to an LLM and get back validated, structured data.

Two providers, chosen with the LLM_PROVIDER environment variable:
- "ollama" (default): a local model on this machine. Free and private, but slow on a laptop CPU.
- "openai": any OpenAI-compatible cloud API, for example Groq. Fast, needs an API key.
"""
import json
import os
import time
from functools import lru_cache
from typing import TypeVar

import ollama
from pydantic import BaseModel, ValidationError

from jobmatch.monitoring import record_llm_call

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:3b" if LLM_PROVIDER == "ollama" else "llama-3.3-70b-versatile")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
# How many LLM calls may run at the same time. A laptop runs one at a time; a cloud API can do several.
LLM_PARALLEL = int(os.getenv("LLM_PARALLEL", "1" if LLM_PROVIDER == "ollama" else "4"))
# "schema" = strict structured outputs (the answer must match the schema exactly).
# "object" = plain JSON mode, for cloud models that don't support strict schemas.
LLM_JSON_MODE = os.getenv("LLM_JSON_MODE", "schema")
# Reasoning models (like gpt-oss) "think" before answering. "low" thinks less: faster, fewer tokens.
LLM_REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "")
MAX_TRIES = 3

T = TypeVar("T", bound=BaseModel)  # "any Pydantic model"


class LLMError(Exception):
    """The LLM did not return valid data, even after retries."""


class RejectedAnswer(Exception):
    """The provider refused the request or the answer. We try again, and show the reason if all tries fail."""


@lru_cache(maxsize=1)
def _openai_client():
    from openai import OpenAI  # only needed for the cloud provider

    # max_retries: if the provider says "too many requests" (rate limit), wait and try again
    return OpenAI(base_url=LLM_BASE_URL, api_key=os.environ["LLM_API_KEY"], max_retries=6)


def _ask_ollama(system: str, user: str, schema: type[BaseModel]) -> tuple[str, int, int]:
    """Local model. Ollama is given the exact JSON schema, so it can only produce matching JSON."""
    response = ollama.chat(
        model=LLM_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        format=schema.model_json_schema(),
        options={"temperature": 0},  # 0 = as predictable as possible
    )
    return (
        response.message.content,
        getattr(response, "prompt_eval_count", 0) or 0,
        getattr(response, "eval_count", 0) or 0,
    )


def strict_schema(schema: dict) -> dict:
    """Make a Pydantic JSON schema follow the rules of strict structured outputs.

    - nested models ($ref) are copied in place, because each object must be fully described
    - every object lists all its fields as required and allows no extra fields
    - checks that strict mode may not support (pattern, maxItems) are removed;
      Pydantic still checks them afterwards
    """
    definitions = schema.get("$defs", {})
    dropped = ("$defs", "title", "pattern", "maxItems", "default")

    def convert(node):
        if isinstance(node, list):
            return [convert(item) for item in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            return convert(definitions[node["$ref"].split("/")[-1]])
        result = {}
        for key, value in node.items():
            if key == "properties":  # field names: keep them all, even one called "title"
                result[key] = {name: convert(field) for name, field in value.items()}
            elif key not in dropped:
                result[key] = convert(value)
        if result.get("type") == "object":
            result["required"] = list(result.get("properties", {}))
            result["additionalProperties"] = False
        return result

    return convert(schema)


def _ask_openai(system: str, user: str, schema: type[BaseModel]) -> tuple[str, int, int]:
    """Cloud model, through any OpenAI-compatible API."""
    from openai import BadRequestError

    if LLM_JSON_MODE == "schema":
        instructions = system
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": schema.__name__, "schema": strict_schema(schema.model_json_schema()), "strict": True},
        }
    else:
        instructions = (
            f"{system}\n\nReply only with JSON that follows this JSON schema:\n"
            f"{json.dumps(schema.model_json_schema())}"
        )
        response_format = {"type": "json_object"}
    extra = {"reasoning_effort": LLM_REASONING_EFFORT} if LLM_REASONING_EFFORT else {}
    try:
        response = _openai_client().chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "system", "content": instructions}, {"role": "user", "content": user}],
            response_format=response_format,
            temperature=0,
            **extra,
        )
    except BadRequestError as error:
        # The provider rejected the request or the model's answer. Keep its exact reason.
        raise RejectedAnswer(f"{error.status_code} from the provider: {error.body or error.message}") from error
    usage = response.usage
    return (
        response.choices[0].message.content or "",
        usage.prompt_tokens if usage else 0,
        usage.completion_tokens if usage else 0,
    )


def chat_json(system: str, user: str, schema: type[T]) -> T:
    """Ask the LLM a question and force the answer into the shape of `schema`.

    Pydantic checks every answer. If anything is wrong, we ask again (up to MAX_TRIES).
    """
    ask = _ask_openai if LLM_PROVIDER == "openai" else _ask_ollama
    last_error: Exception | None = None
    for _attempt in range(MAX_TRIES):
        started = time.perf_counter()
        try:
            content, tokens_in, tokens_out = ask(system, user, schema)
        except RejectedAnswer as error:
            last_error = error
            continue
        record_llm_call(tokens_in, tokens_out, (time.perf_counter() - started) * 1000)
        try:
            return schema.model_validate_json(content)
        except ValidationError as error:
            last_error = error
    raise LLMError(f"no valid answer after {MAX_TRIES} tries: {last_error}")
