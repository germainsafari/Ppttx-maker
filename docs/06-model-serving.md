# 06 - Model serving

## Hardware

NVIDIA GeForce RTX 5090: 32 GB VRAM, Blackwell architecture. Blackwell has native hardware support for
**NVFP4** (4-bit floating point with fine-grained scales), which is what makes a 35B-parameter model practical on
one consumer card.

## Model: Qwen3.6-35B-A3B (NVFP4)

Hugging Face: `nvidia/Qwen3.6-35B-A3B-NVFP4` (NVIDIA's ModelOpt quantisation of Qwen's open-weight model).

| Property | Value | Why it matters here |
|---|---|---|
| Architecture | Mixture of experts, 35B total, ~3B active per token | Knowledge of a large model, speed of a small one |
| Precision | NVFP4 weights | ~22 GB on disk and in VRAM, leaves room for a large KV cache |
| Attention | hybrid linear + full attention | long contexts cost little memory |
| Modalities | text + images | reads charts, screenshots and scanned PDF pages |
| JSON schema output | via vLLM structured outputs | every slide spec parses |
| Licence | open weights (see the model card for terms) | can run on-prem, no data leaves |

### Why it replaced Qwen2.5-VL-7B

Same documents, same pipeline:

| | Qwen2.5-VL-7B-Instruct (before) | Qwen3.6-35B-A3B NVFP4 (now) |
|---|---|---|
| Context configured | 4 096 tokens | 65 536 tokens |
| Long sources | had to be summarised in several rounds (lossy) | fit directly |
| 10-slide deck | 22 s | 8.4 s |
| Layout variety | 5 KPI slides in a row | mixed kpis / chart / cards / quote / comparison |
| Numbers | invented values on cards, invented contact email | real values from the sources, no fact-check warnings |
| Throughput (measured) | ~77 tok/s effective in the pipeline | 185 tok/s single stream, 661 tok/s with 8 parallel requests |
| KV cache | small | 412k tokens |

### Alternatives considered

| Model | Fit on 32 GB | Notes |
|---|---|---|
| Qwen3-VL-8B-Instruct (FP8) | easily, ~12 GB | fast, but weaker planning and fact discipline; good fallback if VRAM must be shared |
| Gemma 3 27B | only 4-bit, no NVFP4 build | slower dense model |
| Qwen3-32B dense (FP8) | tight | ~10x more compute per token than A3B, slower |
| Qwen2.5-VL-7B | yes | the previous setup; quality issues above |

## vLLM configuration

Defined in `infra/docker-compose.yml`, image `vllm/vllm-openai:nightly`. A nightly build is required: vLLM 0.19
(stable at the time) failed to load this checkpoint's NVFP4 MoE scales
(`KeyError 'layers.0.mlp.experts.w2_input_scale'`). The nightly (0.33.0rc1) loads it with the Marlin NVFP4 MoE
kernels.

```
nvidia/Qwen3.6-35B-A3B-NVFP4
--served-model-name=qwen3.6-35b-a3b         # name the engine sees in /v1/models
--quantization=modelopt                     # NVFP4 checkpoint format
--kv-cache-dtype=fp8                        # halves KV cache memory
--max-model-len=65536                       # VLLM_MAX_MODEL_LEN in .env to change
--gpu-memory-utilization=0.88               # ~28 GB; VLLM_GPU_UTIL to change
--max-num-seqs=8                            # parallel sequences (slides of a deck)
--max-num-batched-tokens=8192
--enable-prefix-caching                     # the shared system prompt is computed once
--reasoning-parser=qwen3                    # separates <think> output if thinking is ever enabled
--limit-mm-per-prompt={"image":4,"video":0}
```

Port mapping `8080:8000` keeps the address the team already used (`http://localhost:8080/v1`). The engine
reaches vLLM over the Docker network at `http://vllm:8000/v1`. Weights live in the `hf-cache` volume; the
first start downloads ~22 GB and takes several minutes (the health check allows 10 minutes).

### Engine-side settings (`engine/app/config.py`)

| Variable | Default | Meaning |
|---|---|---|
| `LLM_BASE_URL` | `http://localhost:8080/v1` (compose: `http://vllm:8000/v1`) | OpenAI-compatible endpoint |
| `LLM_MODEL` | empty = first served model | model id |
| `LLM_CONCURRENCY` | 6 (compose: 8) | max in-flight requests from the engine |
| `LLM_DISABLE_THINKING` | 1 | sends `chat_template_kwargs.enable_thinking=false` |
| `LLM_TIMEOUT` | 600 s | per request |

The engine reads the model name and `max_model_len` from `/v1/models` at start-up and on every job, so all
token budgets adapt automatically when the model or context changes. Vision support is inferred from the model
name (`supports_vision` in `llm.py`).

## Structured outputs

Every slide request includes:

```json
"response_format": {
  "type": "json_schema",
  "json_schema": {"name": "Kpis", "schema": { ... Pydantic JSON Schema ... }, "strict": true}
}
```

vLLM compiles the schema into a grammar and masks invalid tokens during generation. Required fields, enums
(slide types, icons), array lengths (`min_length`/`max_length`) are therefore guaranteed. The engine still
validates with Pydantic and retries with the error message, as a safety net.

## Operating the model server

```powershell
docker compose -f infra/docker-compose.yml logs -f vllm      # load progress, request logs
docker compose -f infra/docker-compose.yml restart vllm
nvidia-smi                                                   # ~28 GB used by vllm
curl http://localhost:8080/v1/models
```

While vLLM is running it reserves most of the GPU memory; other GPU workloads (training, another model) need
it stopped or `VLLM_GPU_UTIL` lowered (which shrinks the KV cache, not the model).

## Rollback to the previous setup

The original Qwen2.5-VL-7B server ran in WSL. Its exact command was saved:

```powershell
docker compose -f infra/docker-compose.yml stop vllm
wsl -e bash ~/serve_qwen25vl7b.sh        # copy in infra/wsl/serve_qwen25vl7b.sh
```

The engine keeps working (smaller context, lower quality). `infra/wsl/serve_qwen36.sh` documents the attempt
to run Qwen3.6 in WSL with stable vLLM; it is kept for reference only.
