#!/bin/bash
# Deterministic verifier entry point. Grades the solver artifact against
# precomputed expected values; no LLM judging, no command checks.
set -u

mkdir -p /logs/verifier

python3 /tests/grader.py
grader_exit=$?

if [ $grader_exit -ne 0 ]; then
  echo "0" > /logs/verifier/reward.txt
  echo "grader failed with exit $grader_exit" > /logs/verifier/grader-error.txt
fi

exit 0
