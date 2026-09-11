"""Contract test on poll.yml's own declared trigger/concurrency config.

The repo has no YAML-parsing dependency (stdlib-only stack), so this matches
on the file's text rather than a parsed structure. See
docs/plans/chore-poll-external-dispatch-trigger.md for the tradeoff.
"""

from pathlib import Path

WORKFLOW = Path(__file__).parent.parent / ".github" / "workflows" / "poll.yml"


def workflow_text() -> str:
    return WORKFLOW.read_text()


def test_poll_workflow_does_not_cancel_in_progress_runs():
    # A dispatch (e.g. from an external scheduler) must queue behind an
    # in-flight run rather than kill it — see ADR-0002.
    assert "cancel-in-progress: false" in workflow_text()


def test_poll_workflow_accepts_workflow_dispatch():
    # External schedulers trigger polling via the workflow_dispatch REST API,
    # not GitHub's schedule: event — see ADR-0002.
    assert "workflow_dispatch:" in workflow_text()


def test_poll_workflow_keeps_schedule_fallback():
    # Retained as a zero-cost fallback in case the external trigger fails
    # silently — see ADR-0002.
    assert "schedule:" in workflow_text()
