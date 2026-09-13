"""Image publish must wait for green CI (Issue #109)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PUBLISH = ROOT / ".github" / "workflows" / "publish-ndhub-web-image.yml"
CI = ROOT / ".github" / "workflows" / "ci.yml"


def test_publish_triggered_by_successful_ci_not_bare_push():
    text = PUBLISH.read_text(encoding="utf-8")
    assert "workflow_run:" in text
    assert 'workflows: ["CI"]' in text or "workflows: ['CI']" in text
    assert "pull_request" in text
    assert "github.event.workflow_run.conclusion == 'success'" in text
    assert "on:\n  push:" not in text.replace("\r\n", "\n")


def test_ci_runs_on_version_tags():
    text = CI.read_text(encoding="utf-8")
    assert 'tags: ["v*"]' in text or "tags: ['v*']" in text
