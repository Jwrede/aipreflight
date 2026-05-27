#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== aipreflight: 60-second no-GPU demo =="
echo

echo "$ aipreflight doctor"
python -m aipreflight.cli doctor
echo

echo "$ aipreflight check --profile profiles/app.yml"
python -m aipreflight.cli check --profile profiles/app.yml
echo

echo "$ aipreflight check --profile profiles/rag.yml"
python -m aipreflight.cli check --profile profiles/rag.yml
echo

echo "$ AIPREFLIGHT_RAG_BROKEN=1 aipreflight check --profile profiles/rag.yml"
if AIPREFLIGHT_RAG_BROKEN=1 python -m aipreflight.cli check --profile profiles/rag.yml; then
  echo "Expected the broken RAG demo to fail, but it passed." >&2
  exit 1
else
  echo
  echo "Broken RAG demo failed as expected: retrieval quality blocks the deploy."
fi

echo
echo "Inference profile, when an OpenAI-compatible endpoint is available:"
echo "  aipreflight check --profile profiles/inference.yml"
