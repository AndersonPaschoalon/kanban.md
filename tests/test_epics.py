import pytest

from kanban_md.epics import epic_emoji, new_epic
from kanban_md.kanban import KanbanError


def test_new_epic_creates_template(tmp_path):
    epic_dir = tmp_path / "_epic"
    path, created = new_epic(epic_dir, "tooling", "🧰", "Tooling de processo")

    assert created is True
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# 🧰 Épico: Tooling de processo\n")
    assert "## Cards completados" in text


def test_new_epic_is_idempotent(tmp_path):
    epic_dir = tmp_path / "_epic"
    path1, created1 = new_epic(epic_dir, "tooling", "🧰", "Tooling de processo")
    path1.write_text(path1.read_text(encoding="utf-8") + "\n- card real\n", encoding="utf-8")

    path2, created2 = new_epic(epic_dir, "tooling", "🧰", "título diferente, ignorado")

    assert created1 is True
    assert created2 is False
    assert path1 == path2
    assert "card real" in path2.read_text(encoding="utf-8")


def test_new_epic_rejects_reserved_emoji(tmp_path):
    epic_dir = tmp_path / "_epic"
    with pytest.raises(KanbanError, match="reservado"):
        new_epic(epic_dir, "tooling", "✅", "Tooling de processo")


def test_new_epic_rejects_duplicate_emoji(tmp_path):
    epic_dir = tmp_path / "_epic"
    new_epic(epic_dir, "marketplace", "🏪", "Marketplace")
    with pytest.raises(KanbanError, match="já é usado"):
        new_epic(epic_dir, "tooling", "🏪", "Tooling de processo")


def test_epic_emoji_resolves_existing(tmp_path):
    epic_dir = tmp_path / "_epic"
    new_epic(epic_dir, "tooling", "🧰", "Tooling de processo")
    assert epic_emoji(epic_dir, "tooling") == "🧰"


def test_epic_emoji_raises_when_missing(tmp_path):
    epic_dir = tmp_path / "_epic"
    with pytest.raises(KanbanError, match="não existe"):
        epic_emoji(epic_dir, "fantasma")
