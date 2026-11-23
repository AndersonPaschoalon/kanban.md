"""Cria o arquivo de um épico novo -- idempotente (se já existe, não
mexe) e valida que o emoji escolhido não colide com nada reservado.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from kanban_md.kanban import ALL_STATUS_EMOJI, KanbanError, SECTION_BY_EMOJI

RESERVED_EMOJI = ALL_STATUS_EMOJI | set(SECTION_BY_EMOJI)


def _title_emoji(path: Path) -> str | None:
    first_line = path.read_text(encoding="utf-8").splitlines()[0]
    parts = first_line.split(" ", 2)
    if len(parts) >= 2 and parts[0] == "#":
        return parts[1]
    return None


def existing_epic_emoji(epic_dir: Path) -> dict[str, str]:
    if not epic_dir.is_dir():
        return {}
    result = {}
    for path in epic_dir.glob("*.md"):
        emoji = _title_emoji(path)
        if emoji:
            result[path.stem] = emoji
    return result


def epic_emoji(epic_dir: Path, slug: str) -> str:
    """Resolve o emoji de um épico já existente -- usado por `card new`,
    que exige escolher um épico da lista, não digitar o emoji à mão."""
    path = epic_dir / f"{slug}.md"
    if not path.is_file():
        raise KanbanError(f"épico '{slug}' não existe em {path} -- crie com 'epic new' primeiro")
    emoji = _title_emoji(path)
    if not emoji:
        raise KanbanError(f"épico '{slug}' existe mas não tem emoji no título ({path})")
    return emoji


def new_epic(
    epic_dir: Path,
    slug: str,
    emoji: str,
    title: str,
    objective: str | None = None,
    source: str | None = None,
) -> tuple[Path, bool]:
    """Devolve (caminho, criado). `criado=False` quando o arquivo já
    existia -- idempotente, não sobrescreve. `objective`/`source`
    preenchem os campos já na criação -- se omitidos, ficam como
    "(preencher)" (editar à mão esse placeholder depois é aceitável,
    é só prosa; o que este módulo garante é a estrutura/emoji)."""
    path = epic_dir / f"{slug}.md"
    if path.exists():
        return path, False

    if emoji in RESERVED_EMOJI:
        raise KanbanError(f"emoji {emoji!r} é reservado (estado/seção), escolha outro")
    for other_slug, other_emoji in existing_epic_emoji(epic_dir).items():
        if other_emoji == emoji:
            raise KanbanError(f"emoji {emoji!r} já é usado pelo épico '{other_slug}'")

    template = (
        f"# {emoji} Épico: {title}\n"
        "\n"
        f"**Objetivo fim a fim**: {objective or '(preencher)'}\n"
        "\n"
        "**Status**: em andamento\n"
        "\n"
        f"**Fonte**: {source or '(preencher)'}\n"
        "\n"
        "## Cards completados\n"
    )
    epic_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(template, encoding="utf-8")
    return path, True


@dataclass
class Epic:
    slug: str
    emoji: str
    title: str
    status: str


def list_epics(epic_dir: Path) -> list[Epic]:
    if not epic_dir.is_dir():
        return []
    epics = []
    for path in sorted(epic_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        first_line = text.splitlines()[0] if text else ""
        parts = first_line.split(" ", 2)
        emoji = parts[1] if len(parts) >= 2 and parts[0] == "#" else ""
        title = parts[2].removeprefix("Épico: ") if len(parts) >= 3 else first_line
        status_match = re.search(r"\*\*Status\*\*:\s*(.+)", text)
        status = status_match.group(1).strip() if status_match else ""
        epics.append(Epic(slug=path.stem, emoji=emoji, title=title, status=status))
    return epics


def set_epic_status(epic_dir: Path, slug: str, status: str) -> Path:
    path = epic_dir / f"{slug}.md"
    if not path.is_file():
        raise KanbanError(f"épico '{slug}' não existe em {path}")
    text = path.read_text(encoding="utf-8")
    new_text, count = re.subn(r"(\*\*Status\*\*:).*", rf"\1 {status}", text, count=1)
    if count == 0:
        raise KanbanError(f"não encontrei a linha '**Status**:' em {path} -- arquivo fora do template esperado")
    path.write_text(new_text, encoding="utf-8")
    return path
