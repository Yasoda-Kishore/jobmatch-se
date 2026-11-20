"""Talk to a local LLM through Ollama, and get back validated, structured data."""
from typing import TypeVar

import ollama
from pydantic import BaseModel, ValidationError

LLM_MODEL = "llama3.2:3b"  # any model you have pulled with `ollama pull`
MAX_TRIES = 3

T = TypeVar("T", bound=BaseModel)  # "any Pydantic model"


class LLMError(Exception):
    """The LLM did not return valid data, even after retries."""


def chat_json(system: str, user: str, schema: type[T]) -> T:
    """Ask the LLM a question and force the answer into the shape of `schema`.

    Ollama is told the exact JSON schema, so the model can only produce matching JSON.
    Pydantic then checks it again. If anything is wrong, we ask again (up to MAX_TRIES).
    """
    last_error: Exception | None = None
    for _attempt in range(MAX_TRIES):
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            format=schema.model_json_schema(),
            options={"temperature": 0},  # 0 = as predictable as possible
        )
        try:
            return schema.model_validate_json(response.message.content)
        except ValidationError as error:
            last_error = error
    raise LLMError(f"no valid answer after {MAX_TRIES} tries: {last_error}")