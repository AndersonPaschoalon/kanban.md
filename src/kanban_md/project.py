"""Atalho de conveniência: um "projeto" é só uma pasta com um `kanban.md`
e uma subpasta `epics/` ao lado -- convenção opcional, pensada pro caso
comum (um projeto pequeno, um kanban, seus próprios épicos). Nada nos
outros módulos depende disso: `--epic-dir` continua livre em todo
comando, então um épico ainda pode ser compartilhado entre vários
kanbans quando fizer sentido (ex: vários produtos, um só `_epic/`).
"""
from __future__ import annotations

from pathlib import Path

from kanban_md.kanban import DEFAULT_WIP_LIMIT, init_kanban


def new_project(
    project_dir: Path, title: str, wip_limit: int = DEFAULT_WIP_LIMIT
) -> tuple[Path, Path, bool]:
    """Devolve (caminho do kanban.md, caminho da pasta epics/, criado).
    `criado=False` quando o kanban.md já existia (idempotente, igual
    `init_kanban`) -- `epics/` é sempre garantida mesmo nesse caso."""
    kanban_path = project_dir / "kanban.md"
    epic_dir = project_dir / "epics"
    created = init_kanban(kanban_path, title, wip_limit)
    epic_dir.mkdir(parents=True, exist_ok=True)
    return kanban_path, epic_dir, created
