#!/usr/bin/env bash
set -e

source_dir="/Users/baixuehai/Downloads/EditCompass_json"
save_dir="/Users/baixuehai/Downloads/RM_EVAL/EditCompass_Main_Results/Edit-R1-Qwen-Image-Edit-2509"

summary_Part=(
  Part1
  Part2
  Part3
  Part4
  Part5
  Part6
)

support_language=(
  en
  cn
)

python /Users/baixuehai/Downloads/EditCompass/EditCompass/summary.py \
  --source_dir "$source_dir" \
  --save_dir "$save_dir" \
  --summary_Part "${summary_Part[@]}" \
  --support_language "${support_language[@]}"
