import pytest

from kanban_md.epics import epic_emoji, list_epics, new_epic, set_epic_status
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


def test_new_epic_fills_objective_and_source_when_given(tmp_path):
    epic_dir = tmp_path / "_epic"
    path, _ = new_epic(
        epic_dir, "tooling", "🧰", "Tooling", objective="Fazer X funcionar", source="kanban.md"
    )
    text = path.read_text(encoding="utf-8")
    assert "**Objetivo fim a fim**: Fazer X funcionar" in text
    assert "**Fonte**: kanban.md" in text
    assert "(preencher)" not in text


def test_new_epic_defaults_to_placeholder_when_omitted(tmp_path):
    epic_dir = tmp_path / "_epic"
    path, _ = new_epic(epic_dir, "tooling", "🧰", "Tooling")
    text = path.read_text(encoding="utf-8")
    assert text.count("(preencher)") == 2


def test_list_epics_empty_when_dir_missing(tmp_path):
    assert list_epics(tmp_path / "_epic") == []


def test_list_epics_returns_slug_emoji_title_status(tmp_path):
    epic_dir = tmp_path / "_epic"
    new_epic(epic_dir, "tooling", "🧰", "Tooling de processo")
    new_epic(epic_dir, "marketplace", "🏪", "Marketplace")

    epics = {e.slug: e for e in list_epics(epic_dir)}
    assert epics["tooling"].emoji == "🧰"
    assert epics["tooling"].title == "Tooling de processo"
    assert epics["tooling"].status == "em andamento"
    assert epics["marketplace"].emoji == "🏪"


def test_set_epic_status_updates_only_status_line(tmp_path):
    epic_dir = tmp_path / "_epic"
    new_epic(epic_dir, "tooling", "🧰", "Tooling", objective="Objetivo real")
    path = set_epic_status(epic_dir, "tooling", "fechado")

    text = path.read_text(encoding="utf-8")
    assert "**Status**: fechado" in text
    assert "**Objetivo fim a fim**: Objetivo real" in text

    epics = list_epics(epic_dir)
    assert epics[0].status == "fechado"


def test_set_epic_status_raises_when_epic_missing(tmp_path):
    epic_dir = tmp_path / "_epic"
    with pytest.raises(KanbanError, match="não existe"):
        set_epic_status(epic_dir, "fantasma", "fechado")
