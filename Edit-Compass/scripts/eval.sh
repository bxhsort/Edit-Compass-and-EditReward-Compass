#!/usr/bin/env bash

# =========================
# Evaluation Configuration
# =========================

data_root=""
save_root=""

language="en"
Metric=(IC URC VQ WA IF)
num_workers=2

api_key=" "
api_base=" "


# =========================
# Run Evaluation
# =========================

python EditCompass/eval.py \
  --data_root "$data_root" \
  --save_root "$save_root" \
  --language "$language" \
  --Metric "${Metric[@]}" \
  --num_workers "$num_workers" \
  --api_key "$api_key" \
  --api_base "$api_base" \
  # --support_multi_image
