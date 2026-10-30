#!/usr/bin/env bash
# Recommended model for the deck builder on a single RTX 5090 (32 GB):
#   Qwen3.6-35B-A3B (MoE, 3B active params -> fast) in NVIDIA NVFP4 (native FP4 on Blackwell), ~22 GB weights.
#   Natively multimodal (reads images / scanned PDF pages). Hybrid linear attention -> long context is cheap.
# Usage: serve_qwen36.sh [port] [max_model_len]
PORT="${1:-8080}"
CTX="${2:-65536}"
export VLLM_LOGGING_LEVEL=INFO
exec ~/vllm-env/bin/vllm serve nvidia/Qwen3.6-35B-A3B-NVFP4 \
  --served-model-name qwen3.6-35b-a3b \
  --host 0.0.0.0 --port "$PORT" \
  --quantization modelopt \
  --kv-cache-dtype fp8 \
  --max-model-len "$CTX" \
  --gpu-memory-utilization 0.88 \
  --max-num-seqs 8 \
  --max-num-batched-tokens 8192 \
  --enable-prefix-caching \
  --reasoning-parser qwen3 \
  --limit-mm-per-prompt '{"image":4,"video":0}'
