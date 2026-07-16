"""Gemini API（google-genai SDK）の薄いラッパー。

- 構造化出力（response_schema=Pydanticモデル）を標準とし、手動JSONパースを排除する
- 同期版（バッチ処理用）と非同期版（APIエンドポイント用）の両方を提供する
"""
import logging
from typing import TypeVar

from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from pydantic import BaseModel

from .config import get_settings
from .errors import LLMError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise LLMError("GEMINI_API_KEYが設定されていません")
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def _structured_config(schema: type[BaseModel], temperature: float) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
        temperature=temperature,
    )


def _parse_or_raise(response, schema: type[T]) -> T:
    parsed = response.parsed
    if parsed is None:
        logger.error("Gemini returned unparsable response: %r", getattr(response, "text", None))
        raise LLMError("AIの応答を解釈できませんでした")
    return parsed


def _log_and_wrap(e: Exception, message: str | None = None) -> LLMError:
    """APIエラー・ネットワークエラーをログしてLLMErrorに包む。"""
    if isinstance(e, genai_errors.APIError):
        logger.error("Gemini API error (%s): %s", e.code, e.message)
    else:
        logger.error("Gemini call failed (%s): %s", type(e).__name__, e)
    return LLMError(message) if message else LLMError()


def generate_structured(prompt: str, schema: type[T], temperature: float = 0.2) -> T:
    settings = get_settings()
    try:
        response = get_client().models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=_structured_config(schema, temperature),
        )
        return _parse_or_raise(response, schema)
    except LLMError:
        raise
    except Exception as e:  # ネットワーク断等もLLMErrorに正規化する
        raise _log_and_wrap(e) from e


async def agenerate_structured(prompt: str, schema: type[T], temperature: float = 0.2) -> T:
    settings = get_settings()
    try:
        response = await get_client().aio.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=_structured_config(schema, temperature),
        )
        return _parse_or_raise(response, schema)
    except LLMError:
        raise
    except Exception as e:
        raise _log_and_wrap(e) from e


async def agenerate_text(prompt: str, temperature: float = 0.4) -> str:
    settings = get_settings()
    try:
        response = await get_client().aio.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=temperature),
        )
        text = response.text
        if not text:
            raise LLMError("AIの応答が空でした")
        return text.strip()
    except LLMError:
        raise
    except Exception as e:
        raise _log_and_wrap(e) from e


def embed_texts(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """テキスト群を埋め込みベクトルに変換する（1回の呼び出しは100件まで）。"""
    settings = get_settings()
    try:
        response = get_client().models.embed_content(
            model=settings.embedding_model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=settings.embedding_dim,
            ),
        )
        return [e.values for e in response.embeddings]
    except Exception as e:
        raise _log_and_wrap(e, "埋め込みの生成に失敗しました") from e
