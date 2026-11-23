from kanban_md.kanban import list_cards
from kanban_md.project import new_project


def test_new_project_creates_kanban_and_epics_dir(tmp_path):
    project_dir = tmp_path / "meu-projeto"
    kanban_path, epic_dir, created = new_project(project_dir, "Meu projeto")

    assert created is True
    assert kanban_path == project_dir / "kanban.md"
    assert epic_dir == project_dir / "epics"
    assert kanban_path.is_file()
    assert epic_dir.is_dir()
    assert list_cards(kanban_path) == []


def test_new_project_is_idempotent_for_kanban_but_ensures_epics_dir(tmp_path):
    project_dir = tmp_path / "meu-projeto"
    new_project(project_dir, "Original")

    # simula epics/ tendo sido removida por fora -- new_project deve recriar
    (project_dir / "epics").rmdir()
    kanban_path, epic_dir, created = new_project(project_dir, "Outro título, ignorado")

    assert created is False
    assert epic_dir.is_dir()
    assert kanban_path.read_text(encoding="utf-8").startswith("# Original")
