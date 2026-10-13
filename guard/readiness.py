"""Explicit provider checks; no credentials or upstream error bodies are returned."""
import argparse
import asyncio
import json
from typing import Literal

import httpx
from guard.config import settings
from guard.contracts import Strict
from guard.inference import InferenceUnavailable, VultrInference

ENDPOINT = "https://api.vultrinference.com/v1"


def configuration_status():
    cfg = settings()
    required = {"VULTR_INFERENCE_API_KEY": cfg.vultr_inference_api_key,
                "VULTR_CHAT_MODEL": cfg.vultr_chat_model}
    return {"configured": all(required.values()), "missing": [key for key, value in required.items() if not value],
            "chat_model": cfg.vultr_chat_model, "vision_model": cfg.vultr_vision_model,
            "endpoint_allowed": cfg.vultr_inference_base_url.rstrip("/") == ENDPOINT,
            "live_inference_verified": False}


async def model_catalog():
    # The model catalog is public. Success does NOT authenticate the configured key.
    if not configuration_status()["endpoint_allowed"]:
        raise InferenceUnavailable("Only the official Vultr inference endpoint is permitted")
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            response = await client.get(ENDPOINT + "/models", params={"format": "openrouter", "output_modalities": "text"})
            response.raise_for_status()
            if len(response.content) > 2 * 1024 * 1024:
                raise ValueError("Catalog too large")
            data = response.json()["data"]
            if not isinstance(data, list) or not data:
                raise ValueError("Empty or invalid catalog")
            models = sorted({item["id"] for item in data if isinstance(item, dict)
                             and isinstance(item.get("id"), str) and len(item["id"]) <= 200})
            if not models:
                raise ValueError("No model identifiers")
        return {"models": models, "source": ENDPOINT + "/models", "authenticated": False}
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise InferenceUnavailable("Vultr model catalog unavailable; check connectivity and retry") from exc


class ProbeResult(Strict):
    ready: Literal[True]


async def probe_inference():
    status = configuration_status()
    if not status["configured"]:
        return {**status, "status": "NOT_CONFIGURED"}
    if not status["endpoint_allowed"]:
        raise InferenceUnavailable("Only the official Vultr inference endpoint is permitted")
    catalog = await model_catalog()
    if status["chat_model"] not in catalog["models"]:
        raise InferenceUnavailable("Configured chat model is absent from the current Vultr catalog")
    records = []
    await VultrInference(lambda kind, data: records.append({"kind": kind, **data})).request(
        [{"role": "user", "content": 'Return exactly this JSON object: {"ready":true}'}], ProbeResult)
    return {**status, "status": "VERIFIED", "live_inference_verified": True,
            "scope": "One text JSON request; browser learning and vision are not tested by this check",
            "measurements": records}


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", action="store_true", help="Fetch the public model catalog; no token usage")
    parser.add_argument("--probe", action="store_true", help="Make a real text inference request; uses provider tokens")
    args = parser.parse_args()
    result = configuration_status()
    try:
        if args.catalog:
            result["catalog"] = await model_catalog()
        if args.probe:
            result = await probe_inference()
    except InferenceUnavailable as exc:
        print(json.dumps({"status": "UNAVAILABLE", "message": str(exc)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0 if result.get("configured") and result.get("endpoint_allowed") else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
