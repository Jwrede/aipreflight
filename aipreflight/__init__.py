"""aipreflight: production readiness gate for AI applications and LLM inference endpoints."""

__version__ = "0.1.0"

# Exit code contract (used by the CLI and documented in the README):
EXIT_PASS = 0          # readiness pass
EXIT_FAIL = 1          # readiness fail (gate violations)
EXIT_CONFIG = 2        # invalid config or missing dependency
EXIT_PROBE = 3         # probe/eval execution error
