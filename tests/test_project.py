from kanban_md.kanban import list_cards
from kanban_md.project import new_project


def test_new_project_creates_kanban_and_sibling_epic_dir(tmp_path):
    project_dir = tmp_path / "meu-projeto"
    kanban_path, epic_dir, created = new_project(project_dir, "Meu projeto")

    assert created is True
    assert kanban_path == project_dir / "kanban.md"
    assert epic_dir == tmp_path / "_epic"  # irmã da pasta do projeto, não filha
    assert kanban_path.is_file()
    assert epic_dir.is_dir()
    assert list_cards(kanban_path) == []


def test_two_projects_share_the_same_epic_dir(tmp_path):
    _, epic_dir_a, _ = new_project(tmp_path / "projeto-a", "A")
    _, epic_dir_b, _ = new_project(tmp_path / "projeto-b", "B")
    assert epic_dir_a == epic_dir_b == tmp_path / "_epic"


def test_new_project_is_idempotent_for_kanban_but_ensures_epic_dir(tmp_path):
    project_dir = tmp_path / "meu-projeto"
    new_project(project_dir, "Original")

    # simula _epic/ tendo sido removida por fora -- new_project deve recriar
    (tmp_path / "_epic").rmdir()
    kanban_path, epic_dir, created = new_project(project_dir, "Outro título, ignorado")

    assert created is False
    assert epic_dir.is_dir()
    assert kanban_path.read_text(encoding="utf-8").startswith("# Original")
