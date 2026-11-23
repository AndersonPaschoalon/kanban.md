import pytest

from kanban_md.kanban import (
    DEFAULT_WIP_LIMIT,
    KanbanError,
    delete_card,
    list_cards,
    load,
    move_card,
    new_card,
    read_wip_limit,
    set_card_epic,
    set_wip_limit,
    trash_clean,
    trash_path,
    trash_show,
)

SAMPLE = """# Épico de teste — Kanban

Intro qualquer.

---

## 🏁 Feito

#### ✅📦🔧 Card feito 1

Corpo do card feito 1.

#### ✅📦🗄️ Card feito 2

Corpo do card feito 2.

---

## 🚧 Em andamento / próximo imediato

#### 🟡📦🔧 Card em andamento

Corpo do card em andamento.

---

## 📋 Backlog

#### ⬜📦🔧 Card backlog com separador espúrio

Corpo com parágrafo.

- item 1
- item 2

---

#### ⬜📦📄 Card backlog normal

Corpo normal.

---

## 🧊 Idea Pool

#### 🧊📦🧠 Card ideia

Corpo da ideia.

---

## 🗒️ Notas e Observações

(nada ainda)
"""


@pytest.fixture
def kanban_path(tmp_path):
    path = tmp_path / "kanban.md"
    path.write_text(SAMPLE, encoding="utf-8")
    return path


def test_list_cards_finds_all_and_ignores_notas(kanban_path):
    cards = list_cards(kanban_path)
    titles = [c.title for c in cards]
    assert titles == [
        "Card feito 1",
        "Card feito 2",
        "Card em andamento",
        "Card backlog com separador espúrio",
        "Card backlog normal",
        "Card ideia",
    ]


def test_move_updates_status_emoji_and_relocates(kanban_path):
    move_card(kanban_path, "Card em andamento", "feito")
    text = kanban_path.read_text(encoding="utf-8")

    assert "#### ✅📦🔧 Card em andamento" in text
    assert "#### 🟡📦🔧 Card em andamento" not in text

    cards = list_cards(kanban_path)
    moved = next(c for c in cards if c.title == "Card em andamento")
    assert moved.section_key == "feito"
    # continua por último na seção Feito (append no fim)
    feito_titles = [c.title for c in cards if c.section_key == "feito"]
    assert feito_titles[-1] == "Card em andamento"


def test_move_preserves_other_cards_untouched(kanban_path):
    before = kanban_path.read_text(encoding="utf-8")
    move_card(kanban_path, "Card ideia", "em-andamento")
    after = kanban_path.read_text(encoding="utf-8")

    for line in (
        "Corpo do card feito 1.",
        "Corpo do card feito 2.",
        "Corpo com parágrafo.",
        "- item 1",
        "- item 2",
        "Corpo normal.",
    ):
        assert line in before and line in after


def test_move_preserves_spurious_separator_as_card_body(kanban_path):
    # move um card QUE NÃO é o do separador espúrio -- o separador deve
    # continuar colado ao card original, não desaparecer nem vazar.
    move_card(kanban_path, "Card backlog normal", "idea-pool")
    after = kanban_path.read_text(encoding="utf-8")
    assert "Card backlog com separador espúrio" in after
    assert "- item 1" in after
    assert "- item 2" in after


def test_move_to_same_section_raises(kanban_path):
    with pytest.raises(KanbanError, match="já está em"):
        move_card(kanban_path, "Card feito 1", "feito")


def test_move_no_match_raises(kanban_path):
    with pytest.raises(KanbanError, match="nenhum card"):
        move_card(kanban_path, "não existe isso", "feito")


def test_move_ambiguous_match_raises(kanban_path):
    with pytest.raises(KanbanError, match="mais de um card"):
        move_card(kanban_path, "Card backlog", "feito")


def test_move_unknown_target_section_raises(kanban_path):
    with pytest.raises(KanbanError, match="inválida"):
        move_card(kanban_path, "Card feito 1", "arquivado")


def test_new_card_appends_with_resolved_epic_emoji(kanban_path):
    header = new_card(kanban_path, "Card novo", "🌐", epic_emoji="📦", section="idea-pool", body="Corpo novo.")
    assert header == "#### 🧊📦🌐 Card novo"

    text = kanban_path.read_text(encoding="utf-8")
    assert "#### 🧊📦🌐 Card novo" in text
    assert "Corpo novo." in text

    cards = list_cards(kanban_path)
    idea_titles = [c.title for c in cards if c.section_key == "idea-pool"]
    assert idea_titles[-1] == "Card novo"


def test_new_card_rejects_reserved_category(kanban_path):
    with pytest.raises(KanbanError, match="reservado"):
        new_card(kanban_path, "X", "✅", epic_emoji="📦", section="backlog")


def test_new_card_rejects_category_matching_epic(kanban_path):
    with pytest.raises(KanbanError, match="repete o emoji do épico"):
        new_card(kanban_path, "X", "📦", epic_emoji="📦", section="backlog")


def test_new_card_rejects_unknown_section(kanban_path):
    with pytest.raises(KanbanError, match="inválida"):
        new_card(kanban_path, "X", "🌐", epic_emoji="📦", section="arquivado")


def test_wip_default_is_used_when_unconfigured(kanban_path):
    assert read_wip_limit(load(kanban_path)) == DEFAULT_WIP_LIMIT


def test_wip_set_then_read_round_trips(kanban_path):
    set_wip_limit(kanban_path, 2)
    assert read_wip_limit(load(kanban_path)) == 2
    set_wip_limit(kanban_path, 5)  # reconfigurar substitui, não duplica a linha
    text = kanban_path.read_text(encoding="utf-8")
    assert text.count("<!-- wip:") == 1
    assert read_wip_limit(load(kanban_path)) == 5


def test_wip_zero_or_negative_means_unlimited(kanban_path):
    set_wip_limit(kanban_path, 0)
    assert read_wip_limit(load(kanban_path)) == 0
    # com 1 card já em andamento, limite 0 nunca bloqueia
    move_card(kanban_path, "Card backlog normal", "em-andamento")
    move_card(kanban_path, "Card ideia", "em-andamento")


def test_move_blocked_when_wip_limit_reached(kanban_path):
    set_wip_limit(kanban_path, 1)
    # já existe 1 card em "em-andamento" na fixture -> limite já no teto
    with pytest.raises(KanbanError, match="WIP limit"):
        move_card(kanban_path, "Card backlog normal", "em-andamento")


def test_new_card_blocked_when_wip_limit_reached(kanban_path):
    set_wip_limit(kanban_path, 1)
    with pytest.raises(KanbanError, match="WIP limit"):
        new_card(kanban_path, "X", "🌐", epic_emoji="📦", section="em-andamento")


TWO_EMOJI_SAMPLE = """# Kanban de teste -- card sem épico

---

## 📋 Backlog

#### ⬜🌐 Card antigo sem épico

Corpo qualquer.

#### ⬜📦🔧 Card que já tem épico

Outro corpo.

---

## 🗒️ Notas e Observações

(nada)
"""


@pytest.fixture
def two_emoji_kanban(tmp_path):
    path = tmp_path / "kanban.md"
    path.write_text(TWO_EMOJI_SAMPLE, encoding="utf-8")
    return path


def test_set_card_epic_inserts_when_missing(two_emoji_kanban):
    header = set_card_epic(two_emoji_kanban, "Card antigo sem épico", "📦", known_epic_emoji={"📦"})
    assert header == "#### ⬜📦🌐 Card antigo sem épico"


def test_set_card_epic_replaces_existing(two_emoji_kanban):
    header = set_card_epic(
        two_emoji_kanban, "Card que já tem épico", "🧰", known_epic_emoji={"📦", "🧰"}
    )
    assert header == "#### ⬜🧰🔧 Card que já tem épico"


def test_delete_card_removes_it_and_nothing_else(kanban_path):
    before_other = kanban_path.read_text(encoding="utf-8")
    title = delete_card(kanban_path, "Card backlog normal")
    assert title == "Card backlog normal"

    after = kanban_path.read_text(encoding="utf-8")
    assert "Card backlog normal" not in after
    assert "Corpo normal." not in after
    for line in ("Corpo do card feito 1.", "Corpo da ideia."):
        assert line in before_other and line in after


def test_delete_card_refuses_feito_without_force(kanban_path):
    with pytest.raises(KanbanError, match="feito"):
        delete_card(kanban_path, "Card feito 1")


def test_delete_card_allows_feito_with_force(kanban_path):
    title = delete_card(kanban_path, "Card feito 1", force=True)
    assert title == "Card feito 1"
    assert "Card feito 1" not in kanban_path.read_text(encoding="utf-8")


def test_delete_card_moves_to_trash_instead_of_discarding(kanban_path):
    delete_card(kanban_path, "Card backlog normal")
    trash_text = trash_show(kanban_path)
    assert "#### ⬜📦📄 Card backlog normal" in trash_text
    assert "Corpo normal." in trash_text
    assert trash_path(kanban_path).is_file()


def test_delete_card_appends_multiple_to_same_trash(kanban_path):
    delete_card(kanban_path, "Card backlog normal")
    delete_card(kanban_path, "Card ideia")
    trash_text = trash_show(kanban_path)
    assert "Card backlog normal" in trash_text
    assert "Card ideia" in trash_text


def test_trash_show_empty_when_nothing_deleted(kanban_path):
    assert trash_show(kanban_path) == ""


def test_trash_clean_empties_and_counts(kanban_path):
    delete_card(kanban_path, "Card backlog normal")
    delete_card(kanban_path, "Card ideia")
    count = trash_clean(kanban_path)
    assert count == 2
    assert trash_show(kanban_path) == ""
    assert not trash_path(kanban_path).is_file()


def test_trash_clean_on_empty_trash_returns_zero(kanban_path):
    assert trash_clean(kanban_path) == 0
