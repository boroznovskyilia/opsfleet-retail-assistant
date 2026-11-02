"""OpenRouter transport with provider/local cost caps and bounded physical attempts."""

import asyncio
import json
import time
from decimal import Decimal

import httpx

from .config import AppError, timeout_for
from .telemetry import event

INPUT_CAP = 24 * 1024
OUTPUT_CAP = 1500
PROMPT_PRICE = Decimal("10")  # USD per million; routing rejects higher prices.
COMPLETION_PRICE = Decimal("50")


class OpenRouter:
    def __init__(self, settings, store, client=None):
        self.settings, self.store = settings, store
        self.client = client or httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            headers={"Authorization": "Bearer " + settings.api_key},
            timeout=15,
        )
        self.checked = False

    async def aclose(self):
        await self.client.aclose()

    async def doctor(self, remaining=None):
        if not self.settings.api_key:
            raise AppError(
                "model_configuration",
                "Set OPENROUTER_API_KEY locally; no model request was sent.",
            )
        if (await self.store.spent())["overruns"]:
            raise AppError(
                "model_budget",
                "A prior price overrun requires investigation; paid requests are disabled.",
            )
        if self.checked:
            return {"key_cap_verified": True, "model": self.settings.model}
        try:
            response = await self.client.get("/key", timeout=timeout_for(remaining, 8))
            response.raise_for_status()
            data = response.json()["data"]
            limit = Decimal(str(data.get("limit")))
            if (
                not limit.is_finite()
                or not 0 < limit <= self.settings.budget_usd
                or data.get("limit_reset") is not None
            ):
                raise AppError(
                    "provider_budget",
                    "Use a dedicated OpenRouter key with a non-resetting credit limit of at most USD 5 (and no more than the local budget).",
                )
            models = await self.client.get("/models", timeout=timeout_for(remaining, 8))
            models.raise_for_status()
            model = next(
                (m for m in models.json()["data"] if m["id"] == self.settings.model),
                None,
            )
            if model is None or not {
                "tools",
                "tool_choice",
                "response_format",
                "max_tokens",
                "reasoning",
            } <= set(model.get("supported_parameters", [])):
                raise AppError(
                    "model_capability",
                    "Pinned model does not advertise the required tool/JSON/token/reasoning parameters; choose a validated Gemini model.",
                )
            prices = model["pricing"]
            if (
                Decimal(prices["prompt"]) * 1_000_000 > PROMPT_PRICE
                or Decimal(prices["completion"]) * 1_000_000 > COMPLETION_PRICE
            ):
                raise AppError(
                    "model_price", "Pinned model exceeds the configured price ceilings."
                )
        except AppError:
            raise
        except (httpx.HTTPError, ValueError, KeyError, TypeError, ArithmeticError):
            raise AppError(
                "model_preflight",
                "Cannot verify model/key budget metadata; no paid request was sent.",
            ) from None
        self.checked = True
        return {"key_cap_verified": True, "model": self.settings.model}

    async def call(self, messages, tools, remaining, trace, response_format):
        await self.doctor(remaining)
        body = {
            "model": self.settings.model,
            "messages": messages,
            "response_format": response_format,
            "max_tokens": OUTPUT_CAP,
            "reasoning": {"effort": "low", "exclude": True},
            "usage": {"include": True},
            "provider": {
                "require_parameters": True,
                "max_price": {
                    "prompt": float(PROMPT_PRICE),
                    "completion": float(COMPLETION_PRICE),
                },
            },
        }
        if tools:
            body.update(tools=tools, tool_choice="auto")
        rendered = json.dumps(body, ensure_ascii=False).encode()
        if len(rendered) > INPUT_CAP:
            raise AppError(
                "context_budget",
                "Required model context exceeds the input budget; narrow the question or start a new conversation.",
            )
        # UTF-8 bytes plus framing overhead conservatively bound input tokens.
        reserve = (
            Decimal(len(rendered) + 2048) * PROMPT_PRICE + OUTPUT_CAP * COMPLETION_PRICE
        ) / 1_000_000
        for attempt in range(2):
            timeout = min(20, remaining())
            if timeout <= 0:
                raise AppError(
                    "turn_budget", "Turn deadline reached before model dispatch."
                )
            reservation = await self.store.reserve(reserve, self.settings.budget_usd)
            timeout = timeout_for(remaining, 20)
            start = time.monotonic()
            try:
                response = await self.client.post(
                    "/chat/completions", json=body, timeout=timeout
                )
                if response.status_code in {429, 500, 502, 503, 504} and attempt == 0:
                    # An error may be billable; retain its reservation rather than refund blindly.
                    delay = float(response.headers.get("Retry-After", "1"))
                    if not 0 <= delay <= 3 or remaining() <= delay:
                        raise AppError(
                            "model_unavailable",
                            "Provider requested a delay beyond this turn budget.",
                        )
                    event(
                        "model_retry",
                        **trace,
                        attempt=attempt + 1,
                        status=response.status_code,
                    )
                    await asyncio.sleep(delay)
                    continue
                response.raise_for_status()
                payload = response.json()
                usage = payload.get("usage", {})
                if usage.get("cost") is None:
                    raise AppError(
                        "unknown_cost",
                        "Provider omitted cost; reservation remains charged and this turn stops.",
                    )
                await self.store.settle(reservation, usage["cost"])
                message = payload["choices"][0]["message"]
                if not isinstance(message, dict) or message.get("role") != "assistant":
                    raise AppError(
                        "invalid_model_output",
                        "Provider returned an invalid assistant message.",
                    )
                event(
                    "model_completed",
                    **trace,
                    attempt=attempt + 1,
                    model=self.settings.model,
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"),
                    cost_usd=usage["cost"],
                    latency_ms=round((time.monotonic() - start) * 1000),
                )
                return {
                    k: message[k]
                    for k in ("role", "content", "tool_calls", "reasoning_details")
                    if k in message
                }
            except AppError:
                raise
            except httpx.TransportError:
                event("model_transport_failed", **trace, attempt=attempt + 1)
                if attempt == 0 and remaining() > 1:
                    continue
                raise AppError(
                    "model_unavailable",
                    "Model transport failed; earlier verified results are preserved.",
                ) from None
            except httpx.HTTPStatusError as error:
                status = error.response.status_code
                event("model_http_failed", **trace, status=status, attempt=attempt + 1)
                raise AppError(
                    "model_unavailable",
                    f"Model request failed (HTTP {status}); check credits, model parameter compatibility and provider availability.",
                ) from None
            except (ValueError, KeyError, IndexError, TypeError):
                raise AppError(
                    "invalid_model_output",
                    "Model response could not be validated; no raw response was exposed.",
                ) from None
        raise AppError("model_unavailable", "Model attempts exhausted.")
