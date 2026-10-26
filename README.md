# ovhai-blade-bench

Minimal evaluation harness for [Blade](https://blade.sh) and [OVHcloud AI Endpoints](https://www.ovhcloud.com/en/public-cloud/ai-endpoints/): hosted **OpenAI-compatible** APIs, plus optional **vLLM** on Blade AI Fabric or OVH AI Deploy.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

cp .env.example .env
# Edit .env and set BLADE_API_KEY from https://console.blade.sh/
```

## 1. Blade Models

```bash
python -m bench.smoke --list-models
python -m bench.smoke
```

| Variable | Default |
|----------|---------|
| `BLADE_API_KEY` | (required) |
| `BLADE_BASE_URL` | `https://api.models.blade.sh/v1` |
| `BLADE_MODEL` | `qwen3.6-35b-a3b` |

```bash
source .env
curl -s "$BLADE_BASE_URL/models" -H "Authorization: Bearer $BLADE_API_KEY" | head
```

## 2. OVH AI Endpoints

Same smoke script with `--provider ovh`. Key from **Public Cloud → AI Endpoints** (official name: `OVH_AI_ENDPOINTS_ACCESS_TOKEN`; `OVHAI_ENDPOINT_KEY` also works).

```bash
python -m bench.smoke --provider ovh --list-models
python -m bench.smoke --provider ovh
```

| Variable | Default |
|----------|---------|
| `OVH_AI_ENDPOINTS_ACCESS_TOKEN` | (required) |
| `OVH_AI_ENDPOINTS_BASE_URL` | `https://oai.endpoints.kepler.ai.cloud.ovh.net/v1` |
| `OVH_AI_ENDPOINTS_MODEL` | `gpt-oss-120b` |

Docs: [AI Endpoints getting started](https://docs.ovhcloud.com/en/guides/public-cloud/ai-machine-learning/ai-endpoints-getting-started).

## 3. OVH AI Deploy (your vLLM container)

Separate product from **AI Endpoints**: you deploy a Docker image; the app URL looks like `https://<uuid>.app.gra.ai.cloud.ovh.net`. Use **`OVHAI_DEPLOY_TOKEN`** with `Authorization: Bearer …` on that URL.

Install the CLI (`curl https://cli.gra.ai.cloud.ovh.net/install.sh | bash`), then:

```bash
export PATH="$HOME/bin:$PATH"
python -m bench.deploy_smoke --list-apps
# After deploy, set OVHAI_DEPLOY_APP_URL and:
python -m bench.deploy_smoke --probe
```

| Variable | Purpose |
|----------|---------|
| `OVHAI_DEPLOY_TOKEN` | AI Deploy / platform token |
| `OVHAI_DEPLOY_APP_URL` | Running app base URL (optional until you deploy) |

**Zero idle cost at create:** use autoscaling with **`--auto-min-replicas 0`** (app starts in **`STANDBY`**, no running replica → no compute bill until the first request):

```bash
./deploy/ovh-scale-to-zero.sh
# Then set OVHAI_DEPLOY_APP_URL to the printed status.url
```

Defaults: CPU (not GPU), `ovhcom/ai-deploy-hello-world`. **Do not omit `--cpu`** — otherwise AI Deploy uses a **default GPU** and you pay immediately.

**L4 + vLLM smoke (wake → chat → STANDBY):**

```bash
export PATH="$HOME/bin:$PATH"
python -m bench.deploy_vllm_smoke --deploy
# re-use an existing app:
python -m bench.deploy_vllm_smoke --app-id <uuid>
```

Deploy-only preset: `./deploy/ovh-vllm-l4-scale-zero.sh` (`l4-1-gpu`, `vllm/vllm-openai:latest`, min replicas 0, **rw volumes** on `/hub` and `/workspace` per [OVH’s vLLM guide](https://us.ovhcloud.com/resources/blog/deploy-meta-llama-3-8b-with-vllm-and-ovhcloud-ai-deploy/)). Optional `HF_TOKEN` in `.env` speeds Hugging Face downloads.

**Avoid idle GPU/CPU bills:** while status is **`STANDBY`**, compute is **not** billed. After a wake, replicas scale down after the **cooldown** with no HTTP traffic (vLLM preset **120 s**, CPU hello-world **300 s**). Re-apply min replicas 0 and wait for STANDBY:

```bash
python -m bench.ensure_standby          # check + enforce scale-to-zero
./deploy/ovh-ensure-scale-zero.sh     # same, and wait until STANDBY
```

Do not run `--probe` or health checks while waiting, or the app stays awake.

If an app is **FAILED** (CrashLoopBackOff), check `ovhai app logs <id>` — common cause: model ID not supported by the vLLM image tag (use `Qwen/Qwen2.5-1.5B-Instruct` + recent image, not `Qwen2.5-0.5B` on v0.8.2). Delete and redeploy: `ovhai app delete <id>`.

Docs: [AI Deploy tokens](https://docs.ovhcloud.com/en/guides/public-cloud/ai-machine-learning/ai-deploy-tokens), [CLI deploy app](https://docs.ovhcloud.com/en/guides/public-cloud/ai-machine-learning/ai-cli-deploy-app).

## 4. Self-hosted vLLM on Blade AI Fabric (optional)

Requires AI Fabric access and the `blade` CLI (`pip install -e ".[fabric]"`).

```bash
blade setup   # or: blade token set --from-env FABRIC_TOKEN

export VLLM_MODEL=Qwen/Qwen2.5-0.5B-Instruct
blade deploy fabric/vllm_serve.py
```

Copy the printed app URL into `.env` as `VLLM_ENDPOINT_URL`, set `FABRIC_TOKEN`, then:

```bash
python -m bench.fabric_vllm_smoke
```

For gated Hugging Face weights, create a secret before deploy:

```bash
blade secret set hf --from-env HF_TOKEN
```

Then attach it in `fabric/vllm_serve.py` via `@app.function(..., secrets=[bladekit.Secret.from_name("hf")])` if needed.

## References

- [Blade Models API](https://blade.sh/docs/api-reference/)
- [AI Fabric vLLM web server](https://blade.sh/docs/ai-fabric-sdk/web-endpoints/)
