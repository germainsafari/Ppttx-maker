#!/usr/bin/env bash
# The ORIGINAL setup found on this machine (kept for rollback). 4k context is too small for decks.
exec ~/vllm-env/bin/vllm serve Qwen/Qwen2.5-VL-7B-Instruct \
  --served-model-name Qwen/Qwen2.5-VL-7B-Instruct \
  --host 0.0.0.0 --port 8080 --dtype auto \
  --max-model-len 4096 --gpu-memory-utilization 0.85 \
  --limit-mm-per-prompt '{"image":4}'
