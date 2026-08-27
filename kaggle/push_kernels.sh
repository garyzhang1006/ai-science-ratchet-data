#!/usr/bin/env bash
# Generate and push three Kaggle kernels, one model each.
# Requires: python3 -m kaggle configured (~/.kaggle/kaggle.json).
# Usage: bash kaggle/push_kernels.sh <kaggle-username> [repo-clone-url]
# The clone URL may also come from RATCHET_REPO. It replaces
# REPO_URL_PLACEHOLDER in the kernel, which keeps no fork identity in git.
set -euo pipefail
USER="${1:?usage: push_kernels.sh <kaggle-username> [repo-clone-url]}"
REPO_URL="${2:-${RATCHET_REPO:?set RATCHET_REPO or pass the clone URL as arg 2}}"
HERE="$(cd "$(dirname "$0")" && pwd)"

for IDX in 0 1 2; do
  DIR="$(mktemp -d)"
  sed -e "s/^MODEL_IDX = 0/MODEL_IDX = ${IDX}/" \
      -e "s|REPO_URL_PLACEHOLDER|${REPO_URL}|" \
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
  python3 -m kaggle kernels push -p "${DIR}" --accelerator NvidiaTeslaT4
  echo "pushed ratchet-chains-m${IDX}"
done
