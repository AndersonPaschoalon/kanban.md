"""Move um card dentro do mesmo `kanban.md` -- a cirurgia de texto que
hoje é feita à mão: corta o bloco do card de uma seção, cola em outra,
troca só o emoji de status. Nunca toca em nenhum outro card.

Convenção real (ver README.md): cada seção é um `## <emoji> <título>`,
cada card é um `#### <status><épico><próprio> <título>`. O emoji de
status muda com a seção; épico e próprio nunca mudam aqui.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# emoji de seção -> (chave curta pra CLI, emoji de status correspondente)
SECTION_BY_EMOJI = {
    "🏁": ("feito", "✅"),
    "🚧": ("em-andamento", "🟡"),
    "📋": ("backlog", "⬜"),
    "🧊": ("idea-pool", "🧊"),
    "🗒️": ("notas", None),  # não é seção de cards, só marca o fim do Idea Pool
}
KEY_TO_STATUS = {key: status for key, status in SECTION_BY_EMOJI.values() if status}
ALL_STATUS_EMOJI = set(KEY_TO_STATUS.values())

# só usado por `init_kanban` pra gerar o título de cada seção -- a leitura
# (parse_sections) nunca olha pro texto do título, só pro emoji.
SECTION_TITLES = {
    "🏁": "Feito",
    "🚧": "Em andamento / próximo imediato",
    "📋": "Backlog",
    "🧊": "Idea Pool",
    "🗒️": "Notas e Observações",
}

FEITO = "feito"
WIP_SECTION = "em-andamento"
DEFAULT_WIP_LIMIT = 10  # "grande" -- só existe pra não deixar a seção sem teto nenhum
WIP_COMMENT_RE = re.compile(r"^<!--\s*wip:\s*(-?\d+)\s*-->$")


class KanbanError(Exception):
    """Erro determinístico -- nunca adivinha, sempre aponta o que falhou."""


@dataclass
class Section:
    key: str  # "feito" / "em-andamento" / "backlog" / "idea-pool" / "notas"
    header_idx: int  # índice da linha "## ..."
    content_end: int  # índice exclusivo: onde o conteúdo real da seção termina
    #                   (antes do separador "---" que antecede a próxima "## ")


@dataclass
class Card:
    section_key: str
    header_idx: int
    end_idx: int  # exclusivo
    title: str


def _section_key_of(line: str) -> str | None:
    if not line.startswith("## "):
        return None
    for emoji, (key, _status) in SECTION_BY_EMOJI.items():
        if line[3:].startswith(emoji):
            return key
    raise KanbanError(f"seção com emoji desconhecido: {line!r}")


def _is_card_header(line: str) -> bool:
    return line.startswith("#### ")


def _trim_trailer(lines: list[str], start: int, end: int) -> int:
    """Se o fim do intervalo [start, end) for 'branco(s) + --- + branco(s)'
    (o separador entre seções), devolve o índice de onde esse separador
    começa -- pra excluí-lo do conteúdo real da seção/card."""
    i = end
    while i > start and lines[i - 1].strip() == "":
        i -= 1
    if i > start and lines[i - 1].strip() == "---":
        j = i - 1
        while j > start and lines[j - 1].strip() == "":
            j -= 1
        return j
    return end


def parse_sections(lines: list[str]) -> list[Section]:
    headers = [i for i, line in enumerate(lines) if line.startswith("## ")]
    sections = []
    for pos, header_idx in enumerate(headers):
        key = _section_key_of(lines[header_idx])
        raw_end = headers[pos + 1] if pos + 1 < len(headers) else len(lines)
        content_end = _trim_trailer(lines, header_idx + 1, raw_end)
        sections.append(Section(key=key, header_idx=header_idx, content_end=content_end))
    return sections


def parse_cards(lines: list[str], section: Section) -> list[Card]:
    start = section.header_idx + 1
    card_idxs = [i for i in range(start, section.content_end) if _is_card_header(lines[i])]
    cards = []
    for pos, header_idx in enumerate(card_idxs):
        end_idx = card_idxs[pos + 1] if pos + 1 < len(card_idxs) else section.content_end
        title = lines[header_idx].split(" ", 2)[-1] if len(lines[header_idx].split(" ", 2)) == 3 else lines[header_idx]
        cards.append(Card(section_key=section.key, header_idx=header_idx, end_idx=end_idx, title=title))
    return cards


def load(path: Path) -> list[str]:
    if not path.is_file():
        raise KanbanError(f"kanban '{path}' não existe -- use 'init' pra criar")
    return path.read_text(encoding="utf-8").splitlines()


def dump(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def init_kanban(path: Path, title: str, wip_limit: int = DEFAULT_WIP_LIMIT) -> bool:
    """Cria um `kanban.md` novo com as 5 seções fixas, vazias. Idempotente
    -- devolve False sem mexer em nada se o arquivo já existir."""
    if path.is_file():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)

    blocks = [f"# {title}", f"<!-- wip: {wip_limit} -->"]
    for emoji, title_text in SECTION_TITLES.items():
        if emoji == "🗒️":
            blocks.append(f"## {emoji} {title_text}\n\n(nada ainda)")
        else:
            blocks.append(f"## {emoji} {title_text}")
    path.write_text("\n\n---\n\n".join(blocks) + "\n", encoding="utf-8")
    return True


def _normalize_blank_runs(lines: list[str]) -> list[str]:
    """No máximo uma linha em branco entre duas linhas de conteúdo --
    a formatação real já segue isso em todo o documento."""
    out: list[str] = []
    for line in lines:
        if line.strip() == "" and out and out[-1].strip() == "":
            continue
        out.append(line)
    return out


def read_wip_limit(lines: list[str]) -> int:
    """Lê `<!-- wip: N -->` em qualquer linha do arquivo; ausente ou
    malformado -> `DEFAULT_WIP_LIMIT`. N <= 0 significa sem limite."""
    for line in lines:
        match = WIP_COMMENT_RE.match(line.strip())
        if match:
            return int(match.group(1))
    return DEFAULT_WIP_LIMIT


def set_wip_limit(path: Path, limit: int) -> None:
    lines = load(path)
    comment = f"<!-- wip: {limit} -->"
    for i, line in enumerate(lines):
        if WIP_COMMENT_RE.match(line.strip()):
            lines[i] = comment
            dump(path, lines)
            return
    # não existia ainda -- insere logo após o título (primeira linha)
    new_lines = [lines[0], comment, ""] + lines[1:]
    dump(path, _normalize_blank_runs(new_lines))


def _count_cards(lines: list[str], key: str) -> int:
    sections = parse_sections(lines)
    section = next((s for s in sections if s.key == key), None)
    if section is None:
        return 0
    return len(parse_cards(lines, section))


def _check_wip(lines: list[str], to_key: str, adding: int = 1) -> None:
    if to_key != WIP_SECTION:
        return
    limit = read_wip_limit(lines)
    if limit <= 0:
        return
    current = _count_cards(lines, WIP_SECTION)
    if current + adding > limit:
        raise KanbanError(
            f"WIP limit de '{WIP_SECTION}' é {limit}, já tem {current} -- "
            "feche ou mova algo de lá antes, ou ajuste o limite com 'wip set'"
        )


def list_cards(path: Path) -> list[Card]:
    lines = load(path)
    sections = [s for s in parse_sections(lines) if s.key != "notas"]
    cards = []
    for section in sections:
        cards.extend(parse_cards(lines, section))
    return cards


def show_card(path: Path, needle: str) -> str:
    """Devolve o header + corpo do card exatamente como está no arquivo --
    use antes de `update_card_body`, pra editar em cima do conteúdo real."""
    lines = load(path)
    card = find_card(path, needle)
    block = lines[card.header_idx : card.end_idx]
    while block and block[-1].strip() == "":
        block.pop()
    return "\n".join(block)


def update_card_body(path: Path, needle: str, body: str) -> str:
    """Substitui só o corpo do card (tudo depois da linha de header) por
    `body` -- nunca mexe no header (estado/épico/próprio/título) nem na
    posição do card entre os irmãos da mesma seção. Alternativa
    determinística a editar o arquivo à mão pra corrigir/evoluir o texto
    de um card."""
    lines = load(path)
    card = find_card(path, needle)
    header = lines[card.header_idx]

    new_block = [header, "", body, ""] if body else [header, ""]
    new_lines = lines[: card.header_idx] + new_block + lines[card.end_idx :]
    dump(path, _normalize_blank_runs(new_lines))
    return header


def find_card(path: Path, needle: str) -> Card:
    needle_lower = needle.lower()
    matches = [c for c in list_cards(path) if needle_lower in c.title.lower()]
    if not matches:
        titles = "\n".join(f"  [{c.section_key}] {c.title}" for c in list_cards(path))
        raise KanbanError(f"nenhum card contém {needle!r}. Cards existentes:\n{titles}")
    if len(matches) > 1:
        titles = "\n".join(f"  [{c.section_key}] {c.title}" for c in matches)
        raise KanbanError(f"{needle!r} bate em mais de um card, seja mais específico:\n{titles}")
    return matches[0]


def set_card_epic(path: Path, needle: str, new_epic_emoji: str, known_epic_emoji: set[str]) -> str:
    """Adiciona o emoji de épico a um card que ainda não tem (2 emojis),
    ou troca o que já existe -- nunca mexe no emoji de estado nem no
    'próprio'/título. `known_epic_emoji` é o conjunto de emojis já
    registrados na pasta de épicos (ver `epics.existing_epic_emoji`),
    é como reconhecemos se o card já tinha um épico sem precisar separar
    emoji por "caractere" (frágil com clusters Unicode)."""
    lines = load(path)
    card = find_card(path, needle)
    header = lines[card.header_idx]

    status = next((s for s in ALL_STATUS_EMOJI if header.startswith(f"#### {s}")), None)
    if status is None:
        raise KanbanError(f"não consegui reconhecer o emoji de status em {header!r}")

    prefix = f"#### {status}"
    rest = header[len(prefix) :]
    existing_epic = next((e for e in known_epic_emoji if rest.startswith(e)), None)
    new_rest = new_epic_emoji + (rest[len(existing_epic) :] if existing_epic else rest)

    lines[card.header_idx] = prefix + new_rest
    dump(path, lines)
    return lines[card.header_idx]


def trash_path(kanban_path: Path) -> Path:
    return kanban_path.parent / ".trash.md"


def delete_card(path: Path, needle: str, force: bool = False) -> str:
    """Apaga um card registrado por engano -- na verdade move pro
    `.trash.md` ao lado do kanban, nunca descarta de vez (ver
    `trash_clean` pra esvaziar de verdade). Recusa apagar um card já em
    '{FEITO}' sem `force` -- histórico concluído não se move de leve."""
    lines = load(path)
    card = find_card(path, needle)
    if card.section_key == FEITO and not force:
        raise KanbanError(
            f"card {card.title!r} está em '{FEITO}' -- apagar histórico concluído não é de leve, "
            "use force=True se for mesmo intencional"
        )
    block = lines[card.header_idx : card.end_idx]
    while block and block[-1].strip() == "":
        block.pop()
    _append_to_trash(path, block)

    remaining = lines[: card.header_idx] + lines[card.end_idx :]
    dump(path, _normalize_blank_runs(remaining))
    return card.title


def _append_to_trash(kanban_path: Path, block: list[str]) -> None:
    trash = trash_path(kanban_path)
    existing = trash.read_text(encoding="utf-8") if trash.is_file() else ""
    addition = "\n".join(block)
    content = f"{existing.rstrip(chr(10))}\n\n---\n\n{addition}\n" if existing.strip() else f"{addition}\n"
    trash.write_text(content, encoding="utf-8")


def trash_show(kanban_path: Path) -> str:
    trash = trash_path(kanban_path)
    return trash.read_text(encoding="utf-8") if trash.is_file() else ""


def trash_clean(kanban_path: Path) -> int:
    """Esvazia `.trash.md` de vez. Devolve quantos cards tinham lá."""
    trash = trash_path(kanban_path)
    if not trash.is_file():
        return 0
    count = sum(1 for line in trash.read_text(encoding="utf-8").splitlines() if line.startswith("#### "))
    trash.unlink()
    return count


def move_card(path: Path, needle: str, to_key: str) -> str:
    """Move o card que casa com `needle` pra seção `to_key`. Devolve o
    título do card movido (pra log/confirmação)."""
    if to_key not in KEY_TO_STATUS:
        raise KanbanError(f"seção de destino '{to_key}' inválida -- use um de {sorted(KEY_TO_STATUS)}")

    lines = load(path)
    card = find_card(path, needle)
    if card.section_key == to_key:
        raise KanbanError(f"card {card.title!r} já está em '{to_key}'")

    block = lines[card.header_idx : card.end_idx]
    while block and block[-1].strip() == "":
        block.pop()

    new_status = KEY_TO_STATUS[to_key]
    header = block[0]
    old_status = next((s for s in ALL_STATUS_EMOJI if header.startswith(f"#### {s}")), None)
    if old_status is None:
        raise KanbanError(f"não consegui reconhecer o emoji de status em {header!r}")
    block[0] = header.replace(f"#### {old_status}", f"#### {new_status}", 1)

    # remove o bloco original (card.header_idx até card.end_idx, exclusivo)
    remaining = lines[: card.header_idx] + lines[card.end_idx :]
    _check_wip(remaining, to_key)
    dump(path, _insert_block(remaining, to_key, block))
    return card.title


def _insert_block(lines: list[str], to_key: str, block: list[str]) -> list[str]:
    """Insere `block` no fim do conteúdo real da seção `to_key` (antes
    do separador que antecede a próxima `## `), e normaliza as linhas
    em branco resultantes."""
    sections = parse_sections(lines)
    dest = next(s for s in sections if s.key == to_key)
    new_lines = lines[: dest.content_end] + [""] + block + lines[dest.content_end :]
    return _normalize_blank_runs(new_lines)


def new_card(
    path: Path,
    title: str,
    category: str,
    epic_emoji: str,
    section: str = "backlog",
    body: str = "",
) -> str:
    """Cria um card novo no fim da seção `section`. `epic_emoji` já
    vem resolvido pelo chamador (ver `epics.epic_emoji`) -- este módulo
    não conhece épicos, só emojis. Devolve o header escrito."""
    if section not in KEY_TO_STATUS:
        raise KanbanError(f"seção '{section}' inválida -- use um de {sorted(KEY_TO_STATUS)}")
    reserved = ALL_STATUS_EMOJI | set(SECTION_BY_EMOJI)
    if category in reserved:
        raise KanbanError(f"emoji próprio {category!r} é reservado (estado/seção), escolha outro")
    if category == epic_emoji:
        raise KanbanError(
            f"emoji próprio {category!r} repete o emoji do épico -- evitado por convenção, escolha outro"
        )

    status = KEY_TO_STATUS[section]
    header = f"#### {status}{epic_emoji}{category} {title}"
    block = [header] + (["", body] if body else [])

    lines = load(path)
    _check_wip(lines, section)
    dump(path, _insert_block(lines, section, block))
    return header
