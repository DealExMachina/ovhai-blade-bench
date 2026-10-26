"""Smoke-test OpenAI-compatible inference APIs (Blade Models or OVH AI Endpoints)."""

from __future__ import annotations

import argparse
import json
import time

from bench.config import (
    blade_model,
    make_blade_client,
    make_ovh_client,
    ovh_model,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test hosted OpenAI-compatible APIs")
    parser.add_argument(
        "--provider",
        choices=("blade", "ovh"),
        default="blade",
        help="Which backend to call (default: blade)",
    )
    parser.add_argument(
        "--prompt",
        default="Reply with exactly one word: ok",
        help="User message for a single chat completion",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Print available model IDs and exit",
    )
    args = parser.parse_args()

    if args.provider == "ovh":
        client = make_ovh_client()
        model = ovh_model()
        provider_label = "ovh"
    else:
        client = make_blade_client()
        model = blade_model()
        provider_label = "blade"

    if args.list_models:
        models = client.models.list()
        for item in models.data:
            print(item.id)
        return
    started = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": args.prompt}],
        max_tokens=64,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000

    choice = response.choices[0].message.content or ""
    usage = response.usage
    print(f"provider={provider_label}")
    print(f"model={model}")
    print(f"latency_ms={elapsed_ms:.1f}")
    print(f"reply={choice.strip()!r}")
    if usage:
        print(
            json.dumps(
                {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                }
            )
        )


if __name__ == "__main__":
    main()
