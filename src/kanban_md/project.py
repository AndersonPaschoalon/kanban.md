"""Atalho de conveniência: um "projeto" é uma pasta com um `kanban.md`,
com os épicos em `_epic/` **ao lado**, nunca dentro do próprio projeto
-- um épico pode envolver mais de um projeto, então mora um nível
acima, irmão de cada pasta de projeto (mesma convenção documentada em
docs/process.md: `docs/process/_epic/` ao lado de `docs/process/
<produto>/`, não dentro de nenhum produto específico). Dois projetos
com o mesmo diretório pai compartilham automaticamente o mesmo
`_epic/`. Nada nos outros módulos depende disso: `--epic-dir` continua
livre em todo comando, então um épico ainda pode ficar em qualquer
lugar que fizer sentido.
"""
from __future__ import annotations

from pathlib import Path

from kanban_md.kanban import DEFAULT_WIP_LIMIT, init_kanban


def new_project(
    project_dir: Path, title: str, wip_limit: int = DEFAULT_WIP_LIMIT
) -> tuple[Path, Path, bool]:
    """Devolve (caminho do kanban.md, caminho de `_epic/`, criado).
    `_epic/` fica em `project_dir.parent/_epic` -- irmã da pasta do
    projeto, não filha. `criado=False` quando o kanban.md já existia
    (idempotente, igual `init_kanban`) -- `_epic/` é sempre garantida
    mesmo nesse caso."""
    kanban_path = project_dir / "kanban.md"
    epic_dir = project_dir.parent / "_epic"
    created = init_kanban(kanban_path, title, wip_limit)
    epic_dir.mkdir(parents=True, exist_ok=True)
    return kanban_path, epic_dir, created
