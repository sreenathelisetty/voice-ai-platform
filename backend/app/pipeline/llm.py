"""
OpenAI LLM streaming worker.

Consumes (transcript, pipeline_result) from llm_queue.
Streams the response, splits on sentence boundaries,
emits (sentence, pipeline_result) to tts_queue as soon as each sentence completes.
"""

from __future__ import annotations

import asyncio
import re
import time

import openai

from app.config import get_settings
from app.session.manager import SessionManager
from app.session.models import ConversationTurn, PipelineResult
from app.utils.exceptions import LLMError
from app.utils.logging import get_logger
from app.utils.retry import async_retry

log = get_logger(__name__)

SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

SYSTEM_PROMPT = (
    "You are a helpful, concise voice assistant. "
    "Keep responses brief and conversational — suited for text-to-speech delivery. "
    "Avoid markdown, bullet points, or special characters."
)


def _split_sentences(text: str) -> list[str]:
    parts = SENTENCE_BOUNDARY.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


async def stream_response(
    transcript: str,
    history: list[ConversationTurn],
) -> tuple[str, float | None]:
    """
    Stream LLM response; yield sentences to caller.
    Returns (full_response_text, first_token_timestamp).
    """
    settings = get_settings()
    client = openai.AsyncOpenAI(
        api_key=settings.nvidia_api_key or settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history[-10:]:  # limit context to last 10 turns
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": transcript})

    try:
        stream = await client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            max_tokens=settings.openai_max_tokens,
            temperature=settings.openai_temperature,
            stream=True,
        )
    except openai.APIError as exc:
        raise LLMError(str(exc)) from exc

    full_text = ""
    first_token_time: float | None = None
    pending = ""

    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content or ""
        if delta:
            if first_token_time is None:
                first_token_time = time.time()
            pending += delta
            full_text += delta

            # Yield complete sentences immediately
            sentences = SENTENCE_BOUNDARY.split(pending)
            for sentence in sentences[:-1]:
                yield sentence.strip(), first_token_time
            pending = sentences[-1]

    # Flush remaining text (last sentence without terminal punctuation)
    if pending.strip():
        yield pending.strip(), first_token_time


async def llm_worker(
    llm_queue: asyncio.Queue[tuple[str, PipelineResult] | None],
    tts_queue: asyncio.Queue[tuple[str, PipelineResult] | None],
    session_id: str,
    session_manager: SessionManager,
    ws_send_queue: asyncio.Queue[bytes | str | None] | None = None,
) -> None:
    """Long-running async task that drains the LLM queue."""
    log.info("llm_worker_started", session_id=session_id)

    while True:
        item = await llm_queue.get()
        if item is None:  # sentinel
            await tts_queue.put(None)
            break

        transcript, result = item
        history = await session_manager.get_history(session_id)

        full_response = ""
        llm_first_token: float | None = None

        try:
            async for sentence, first_token_time in stream_response(transcript, history):
                if llm_first_token is None:
                    llm_first_token = first_token_time
                    result.llm_first_token = first_token_time
                full_response += sentence + " "
                await tts_queue.put((sentence, result))

        except LLMError as exc:
            log.error("llm_failed", session_id=session_id, error=str(exc))
            await tts_queue.put(("I'm sorry, I encountered an error. Please try again.", result))

        result.llm_end = time.time()
        result.response_text = full_response.strip()
        if ws_send_queue is not None and result.response_text:
            import json
            await ws_send_queue.put(json.dumps({"type": "response", "text": result.response_text}))
        log.info("llm_complete", session_id=session_id,
                 first_token_ms=result.llm_first_token_ms,
                 total_ms=result.llm_total_ms)

        # Update conversation history
        await session_manager.update_history(
            session_id,
            ConversationTurn(role="user", content=transcript),
        )
        await session_manager.update_history(
            session_id,
            ConversationTurn(role="assistant", content=full_response.strip()),
        )

        llm_queue.task_done()
