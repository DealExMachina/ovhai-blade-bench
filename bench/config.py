"""Load settings from `.env` for Blade, OVH AI Endpoints, and optional Fabric vLLM."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")

DEFAULT_BLADE_BASE_URL = "https://api.models.blade.sh/v1"
DEFAULT_BLADE_MODEL = "qwen3.6-35b-a3b"

DEFAULT_OVH_BASE_URL = "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1"
DEFAULT_OVH_MODEL = "gpt-oss-120b"


def blade_api_key() -> str:
    key = os.environ.get("BLADE_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "BLADE_API_KEY is missing. Copy .env.example to .env and add your key."
        )
    return key


def blade_base_url() -> str:
    return os.environ.get("BLADE_BASE_URL", DEFAULT_BLADE_BASE_URL).strip().rstrip("/")


def blade_model() -> str:
    return os.environ.get("BLADE_MODEL", DEFAULT_BLADE_MODEL).strip()


def make_blade_client() -> OpenAI:
    return OpenAI(
        base_url=blade_base_url(),
        api_key=blade_api_key(),
        timeout=120.0,
    )


def ovh_api_key() -> str:
    key = (
        os.environ.get("OVH_AI_ENDPOINTS_ACCESS_TOKEN", "").strip()
        or os.environ.get("OVHAI_ENDPOINT_KEY", "").strip()
    )
    if not key:
        raise SystemExit(
            "OVH AI Endpoints key missing. Set OVH_AI_ENDPOINTS_ACCESS_TOKEN "
            "(or OVHAI_ENDPOINT_KEY) in .env — from Public Cloud > AI Endpoints."
        )
    return key


def ovh_base_url() -> str:
    return (
        os.environ.get("OVH_AI_ENDPOINTS_BASE_URL", DEFAULT_OVH_BASE_URL).strip().rstrip("/")
        or os.environ.get("OVHAI_ENDPOINT_BASE_URL", DEFAULT_OVH_BASE_URL).strip().rstrip("/")
    )


def ovh_model() -> str:
    return (
        os.environ.get("OVH_AI_ENDPOINTS_MODEL", DEFAULT_OVH_MODEL).strip()
        or os.environ.get("OVHAI_ENDPOINT_MODEL", DEFAULT_OVH_MODEL).strip()
    )


def make_ovh_client() -> OpenAI:
    return OpenAI(
        base_url=ovh_base_url(),
        api_key=ovh_api_key(),
        timeout=120.0,
    )


def ovhai_deploy_token() -> str:
    key = (
        os.environ.get("OVHAI_DEPLOY_TOKEN", "").strip()
        or os.environ.get("OVH_AI_DEPLOY_TOKEN", "").strip()
    )
    if not key:
        raise SystemExit(
            "OVH AI Deploy token missing. Set OVHAI_DEPLOY_TOKEN in .env "
            "(AI Dashboard > Tokens, or `ovhai token create`)."
        )
    return key


def ovhai_deploy_app_url() -> str:
    return (
        os.environ.get("OVHAI_DEPLOY_APP_URL", "").strip().rstrip("/")
        or os.environ.get("OVH_AI_DEPLOY_APP_URL", "").strip().rstrip("/")
    )


def fabric_vllm_settings() -> tuple[str, str, str]:
    """Return (endpoint_url, fabric_token, model_id) for a deployed vLLM app."""
    url = os.environ.get("VLLM_ENDPOINT_URL", "").strip().rstrip("/")
    token = os.environ.get("FABRIC_TOKEN", "").strip()
    model = os.environ.get("VLLM_MODEL", "Qwen/Qwen2.5-0.5B-Instruct").strip()
    if not url or not token:
        raise SystemExit(
            "Set VLLM_ENDPOINT_URL and FABRIC_TOKEN in .env (output of `blade deploy`)."
        )
    return url, token, model
