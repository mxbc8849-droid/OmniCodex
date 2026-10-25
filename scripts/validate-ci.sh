#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
missing=()
command -v actionlint >/dev/null 2>&1 || missing+=("actionlint (https://github.com/rhysd/actionlint/releases)")
command -v yamllint >/dev/null 2>&1 || missing+=("yamllint (python -m pip install yamllint)")
if (( ${#missing[@]} )); then printf 'Missing required CI lint tools: %s\n' "${missing[*]}" >&2; exit 127; fi
actionlint "$ROOT/.github/workflows/ci.yml"
yamllint -c "$ROOT/.yamllint.yml" "$ROOT/.github/workflows/ci.yml" "$ROOT/docker-compose.yml"
echo 'CI configuration is valid.'
