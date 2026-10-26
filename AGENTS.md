# ovhai-blade-bench

Minimal harness to smoke-test **Blade Models**, **OVH AI Endpoints**, and **OVH AI Deploy** (vLLM, scale-to-zero). Python package lives under `bench/`.

## Layout

- `bench/smoke.py` — hosted OpenAI-compatible APIs (Blade / OVH Endpoints)
- `bench/deploy_smoke.py` — probe a deployed AI Deploy app URL
- `bench/deploy_vllm_smoke.py` — deploy or reuse L4 vLLM, wake → chat → STANDBY
- `bench/ensure_standby.py` — enforce min replicas 0 and wait for STANDBY
- `bench/ovhai_cli.py` — `ovhai` CLI wrapper (JSON, polling)
- `deploy/*.sh` — shell presets for scale-to-zero and vLLM
- `fabric/vllm_serve.py` — optional Blade AI Fabric vLLM (needs `pip install -e ".[fabric]"`)

## Environment (Cursor Cloud)

The Cloud Build runs `.cursor/environment.json` `install`: editable install of this repo plus the `ovhai` CLI when missing.

Do **not** commit `.env`. Required credentials are set in **Cursor Cloud → Secrets** (Runtime Secret unless noted):

| Variable | When needed |
|----------|-------------|
| `BLADE_API_KEY` | Blade smoke tests |
| `OVH_AI_ENDPOINTS_ACCESS_TOKEN` | OVH Endpoints smoke (`OVHAI_ENDPOINT_KEY` alias OK) |
| `OVHAI_DEPLOY_TOKEN` | `ovhai` CLI / deploy flows |
| `OVHAI_DEPLOY_APP_URL` | `--probe` on an existing app |
| `HF_TOKEN` | Hugging Face downloads for vLLM deploy |
| `FABRIC_TOKEN` | Blade Fabric optional path |

Optional overrides: see `.env.example` for base URLs and model IDs.

## Common commands

```bash
# Hosted APIs (no GPU deploy)
python -m bench.smoke --list-models
python -m bench.smoke --provider ovh --list-models

# Existing AI Deploy app
python -m bench.deploy_smoke --list-apps
python -m bench.deploy_smoke --probe

# L4 vLLM lifecycle (cost-sensitive — see below)
python -m bench.deploy_vllm_smoke --deploy
python -m bench.ensure_standby
```

Ensure `ovhai` is on `PATH` (usually `$HOME/bin` after install). The bench modules read tokens from the environment, not from a local `.env` file in Cloud.

## Cost and safety (OVH AI Deploy)

- Prefer **min replicas 0** (`STANDBY`) so idle GPU/CPU is not billed.
- Do **not** run `--probe`, health checks, or repeated smoke calls while waiting for scale-down — traffic keeps the app awake.
- CPU hello-world deploys must pass **`--cpu`** in scripts; omitting it defaults to GPU and charges immediately.
- If an app is **FAILED**, use `ovhai app logs <id>` before redeploying.

## Code changes

- Match existing style: small modules, `python-dotenv` only for local `.env` loading in `bench/config.py`.
- Keep README and `.env.example` in sync when adding env vars.
- Run the narrowest smoke test that proves the change; avoid full L4 deploy unless the task requires it.

## Cursor Cloud specific instructions

- Dependencies are installed by the environment Build; re-run smokes after editing `pyproject.toml`.
- For Fabric work: `pip install -e ".[fabric]"` and ensure `blade` CLI is available in the environment.
- Open PRs with a short test plan listing which smoke command was run and which secrets were required.
