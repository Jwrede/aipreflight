"""Shared exception types."""


class MissingDependency(Exception):
    """Raised when a required external tool (e.g. llmprobe, tokentoll) is not installed."""
