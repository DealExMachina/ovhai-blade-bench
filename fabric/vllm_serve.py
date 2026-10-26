"""
Minimal vLLM OpenAI server on Blade AI Fabric.

Deploy:
  pip install -e ".[fabric]"
  export FABRIC_TOKEN=...   # or: blade token set --from-env FABRIC_TOKEN
  blade deploy fabric/vllm_serve.py

The deploy output includes the app URL; set VLLM_ENDPOINT_URL in .env and run:
  python -m bench.fabric_vllm_smoke
"""

from __future__ import annotations

import os
import subprocess

import bladekit

app = bladekit.app("ovhai-blade-vllm")

MODEL = os.environ.get("VLLM_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")


@app.web_server(startup_timeout=600, min_replicas=0, max_replicas=1)
@app.concurrent(max_inputs=16)
@app.function(gpu="RTX-A4500", image=bladekit.Image.from_catalog("fabric/vllm"))
def serve() -> None:
    port = os.environ["FABRIC_SERVER_PORT"]
    subprocess.Popen(
        [
            "vllm",
            "serve",
            MODEL,
            "--host",
            "127.0.0.1",
            "--port",
            port,
        ],
    )
