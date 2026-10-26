"""Smoke-test a self-hosted vLLM endpoint deployed on Blade AI Fabric."""

from __future__ import annotations

import argparse
import time

import httpx

from bench.config import fabric_vllm_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Call a Fabric-hosted vLLM OpenAI server")
    parser.add_argument(
        "--prompt",
        default="Reply with exactly one word: ok",
    )
    args = parser.parse_args()

    base_url, token, model = fabric_vllm_settings()
    headers = {"Authorization": f"Bearer {token}"}
    chat_url = f"{base_url}/v1/chat/completions"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": args.prompt}],
        "max_tokens": 64,
    }

    started = time.perf_counter()
    with httpx.Client(timeout=120.0) as client:
        health = client.get(f"{base_url}/health", headers=headers)
        if health.status_code == 404:
            models = client.get(f"{base_url}/v1/models", headers=headers)
            models.raise_for_status()
        else:
            health.raise_for_status()

        response = client.post(chat_url, headers=headers, json=payload)
        response.raise_for_status()
        body = response.json()

    elapsed_ms = (time.perf_counter() - started) * 1000
    reply = body["choices"][0]["message"]["content"]
    print(f"endpoint={base_url}")
    print(f"model={model}")
    print(f"latency_ms={elapsed_ms:.1f}")
    print(f"reply={reply.strip()!r}")


if __name__ == "__main__":
    main()
