#!/usr/bin/env bash
# Generate and push three Kaggle kernels, one model each.
# Requires: python3 -m kaggle configured (~/.kaggle/kaggle.json).
# Usage: bash kaggle/push_kernels.sh <kaggle-username>
set -euo pipefail
USER="${1:?usage: push_kernels.sh <kaggle-username>}"
HERE="$(cd "$(dirname "$0")" && pwd)"

for IDX in 0 1 2; do
  DIR="$(mktemp -d)"
  sed "s/^MODEL_IDX = 0/MODEL_IDX = ${IDX}/" \
      "${HERE}/kernel_ratchet.py" > "${DIR}/kernel_ratchet.py"
  cat > "${DIR}/kernel-metadata.json" <<EOF
{
  "id": "${USER}/ratchet-chains-m${IDX}",
  "title": "ratchet-chains-m${IDX}",
  "code_file": "kernel_ratchet.py",
  "language": "python",
  "kernel_type": "script",
  "is_private": true,
  "enable_gpu": true,
  "enable_internet": true,
  "accelerator": "NvidiaTeslaT4"
}
EOF
  python3 -m kaggle kernels push -p "${DIR}"
  echo "pushed ratchet-chains-m${IDX}"
done
