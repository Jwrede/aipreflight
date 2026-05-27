"""Generic readiness check primitives shared across profile kinds.

A check produces a CheckResult. The overall verdict aggregates them:
any FAIL -> FAIL, otherwise any WARN -> WARN, otherwise PASS. SKIP never
affects the verdict (the check did not run, e.g. an optional section was absent).
"""

from dataclasses import dataclass, field

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
SKIP = "SKIP"


@dataclass
class CheckResult:
    name: str
    status: str
    summary: str
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
            "details": self.details,
        }


def aggregate_verdict(results: list[CheckResult]) -> str:
    statuses = {r.status for r in results}
    if FAIL in statuses:
        return FAIL
    if WARN in statuses:
        return WARN
    return PASS
