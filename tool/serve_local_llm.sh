# Copyright (c) Meta Platforms, Inc. and affiliates
CUDA_VISIBLE_DEVICES=0 python -m vllm.entrypoints.openai.api_server \
  --model Your-Model-Name \
  --tensor-parallel-size 8 \
  --quantization fp8 \
  --gpu-memory-utilization 0.9 \
  --dtype bfloat16 \
  --host 0.0.0.0 \
  --port 8000