"""Cria o arquivo de um épico novo -- idempotente (se já existe, não
mexe) e valida que o emoji escolhido não colide com nada reservado.
"""
from __future__ import annotations

from pathlib import Path

from process_cli.kanban import ALL_STATUS_EMOJI, KanbanError, SECTION_BY_EMOJI

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


def new_epic(epic_dir: Path, slug: str, emoji: str, title: str) -> tuple[Path, bool]:
    """Devolve (caminho, criado). `criado=False` quando o arquivo já
    existia -- idempotente, não sobrescreve."""
    path = epic_dir / f"{slug}.md"
    if path.exists():
        return path, False

    if emoji in RESERVED_EMOJI:
        raise KanbanError(f"emoji {emoji!r} é reservado (estado/seção), escolha outro")
    for other_slug, other_emoji in existing_epic_emoji(epic_dir).items():
        if other_emoji == emoji:
            raise KanbanError(f"emoji {emoji!r} já é usado pelo épico '{other_slug}'")

    epic_dir.mkdir(parents=True, exist_ok=True)
    template = (
        f"# {emoji} Épico: {title}\n"
        "\n"
        "**Objetivo fim a fim**: (preencher)\n"
        "\n"
        "**Status**: em andamento\n"
        "\n"
        "**Fonte**: (preencher)\n"
        "\n"
        "## Cards completados\n"
    )
    path.write_text(template, encoding="utf-8")
    return path, True
