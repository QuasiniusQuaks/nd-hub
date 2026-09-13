"""Runtime image copies artifacts only, not frontend-react source (Issue #118)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCKERFILE = ROOT / "ndhub-web" / "Dockerfile"
COMPOSE = ROOT / "ndhub-web" / "docker-compose.yml"
PUBLISH = ROOT / ".github" / "workflows" / "publish-ndhub-web-image.yml"
ROOT_DOCKERIGNORE = ROOT / ".dockerignore"


def _dockerfile() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


def test_runtime_stage_does_not_copy_whole_tree():
    text = _dockerfile()
    assert "COPY . /app" not in text
    assert "COPY ndhub-web/backend /app/backend" in text
    assert "COPY shared /app/shared" in text
    assert "COPY ndhub-web/security_manager.py /app/security_manager.py" in text
    assert "COPY --from=frontend-build /backend/web/react /app/backend/web/react" in text
    runtime = text.split("FROM python", 1)[-1]
    assert "COPY ndhub-web/frontend-react" not in runtime
    assert "COPY frontend-react" not in runtime


def test_publish_and_compose_use_repo_root_context():
    publish = PUBLISH.read_text(encoding="utf-8")
    assert "context: ." in publish
    assert "file: ./ndhub-web/Dockerfile" in publish
    compose = COMPOSE.read_text(encoding="utf-8")
    assert "context: .." in compose
    assert "dockerfile: ndhub-web/Dockerfile" in compose


def test_root_dockerignore_keeps_secrets_out_of_repo_context():
    patterns = [
        line.strip()
        for line in ROOT_DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert ".env" in patterns
    assert "**/*.db" in patterns or "*.db" in patterns
    assert "desktop-client" in patterns
