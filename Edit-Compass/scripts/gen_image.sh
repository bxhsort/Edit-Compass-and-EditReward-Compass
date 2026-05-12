#!/usr/bin/env bash

# =========================
# Generation Configuration
# =========================

model_name="LongCat-Image-Edit"
language="en"

data_root="/root/data/bxh/OmniBench"
save_root="/root/data/bxh/OmniBench_EVAL"
model_path="/root/data/bxh/ckpt/LongCat-Image-Edit"

gpu_ids=(
  0
  1
)


# =========================
# Run Generation
# =========================

python /root/data/bxh/LongCat-Image-Edit/infer.py \
  --model_name "$model_name" \
  --data_root "$data_root" \
  --save_root "$save_root" \
  --language "$language" \
  --model_path "$model_path" \
  --gpu_ids "${gpu_ids[@]}"
