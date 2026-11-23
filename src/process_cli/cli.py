from __future__ import annotations

import argparse
import sys
from pathlib import Path

from process_cli.epics import epic_emoji, existing_epic_emoji, new_epic
from process_cli.kanban import (
    KanbanError,
    KEY_TO_STATUS,
    delete_card,
    list_cards,
    load,
    move_card,
    new_card,
    read_wip_limit,
    set_card_epic,
    set_wip_limit,
    trash_clean,
    trash_show,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="process")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="lista os cards de um kanban.md")
    p_list.add_argument("kanban", type=Path)

    p_move = sub.add_parser("move", help="move um card pra outra seção")
    p_move.add_argument("kanban", type=Path)
    p_move.add_argument("needle", help="trecho (case-insensitive) do título do card")
    p_move.add_argument("to", choices=sorted(KEY_TO_STATUS), help="seção de destino")

    p_card = sub.add_parser("card", help="comandos de card")
    card_sub = p_card.add_subparsers(dest="card_cmd", required=True)
    p_card_new = card_sub.add_parser("new", help="cria um card novo (épico + emoji próprio obrigatórios)")
    p_card_new.add_argument("kanban", type=Path)
    p_card_new.add_argument("--title", required=True)
    p_card_new.add_argument("--category", required=True, help="emoji 'próprio' do card")
    p_card_new.add_argument("--epic-dir", type=Path, required=True, help="pasta onde ficam os arquivos de épico")
    p_card_new.add_argument("--epic", required=True, help="slug do épico (deve já existir)")
    p_card_new.add_argument("--section", default="backlog", choices=sorted(KEY_TO_STATUS))
    p_card_new.add_argument("--body", default="")

    p_card_set_epic = card_sub.add_parser(
        "set-epic", help="adiciona (ou troca) o épico de um card existente"
    )
    p_card_set_epic.add_argument("kanban", type=Path)
    p_card_set_epic.add_argument("needle")
    p_card_set_epic.add_argument("--epic-dir", type=Path, required=True)
    p_card_set_epic.add_argument("--epic", required=True)

    p_card_delete = card_sub.add_parser("delete", help="apaga um card registrado por engano")
    p_card_delete.add_argument("kanban", type=Path)
    p_card_delete.add_argument("needle")
    p_card_delete.add_argument("--force", action="store_true", help="permite apagar card já em 'feito'")

    p_wip = sub.add_parser("wip", help="limite de WIP (work in progress) de 'em-andamento'")
    wip_sub = p_wip.add_subparsers(dest="wip_cmd", required=True)
    p_wip_show = wip_sub.add_parser("show", help="mostra o limite configurado (ou o default)")
    p_wip_show.add_argument("kanban", type=Path)
    p_wip_set = wip_sub.add_parser("set", help="configura o limite (<=0 = sem limite)")
    p_wip_set.add_argument("kanban", type=Path)
    p_wip_set.add_argument("limit", type=int)

    p_trash = sub.add_parser("trash", help="cards apagados (ver .trash.md ao lado do kanban)")
    trash_sub = p_trash.add_subparsers(dest="trash_cmd", required=True)
    p_trash_show = trash_sub.add_parser("show", help="mostra o conteúdo do .trash.md")
    p_trash_show.add_argument("kanban", type=Path)
    p_trash_clean = trash_sub.add_parser("clean", help="esvazia o .trash.md de vez")
    p_trash_clean.add_argument("kanban", type=Path)

    p_epic = sub.add_parser("epic", help="comandos de épico")
    epic_sub = p_epic.add_subparsers(dest="epic_cmd", required=True)
    p_epic_new = epic_sub.add_parser("new", help="cria o arquivo de um épico (idempotente)")
    p_epic_new.add_argument("epic_dir", type=Path, help="pasta onde ficam os arquivos de épico")
    p_epic_new.add_argument("slug")
    p_epic_new.add_argument("--emoji", required=True)
    p_epic_new.add_argument("--title", required=True)

    args = parser.parse_args(argv)

    try:
        if args.cmd == "list":
            for card in list_cards(args.kanban):
                print(f"[{card.section_key}] {card.title}")
        elif args.cmd == "move":
            title = move_card(args.kanban, args.needle, args.to)
            print(f"movido pra '{args.to}': {title}")
        elif args.cmd == "card" and args.card_cmd == "new":
            emoji = epic_emoji(args.epic_dir, args.epic)
            header = new_card(
                args.kanban, args.title, args.category, emoji, args.section, args.body
            )
            print(f"criado em '{args.section}': {header}")
        elif args.cmd == "card" and args.card_cmd == "set-epic":
            emoji = epic_emoji(args.epic_dir, args.epic)
            known = set(existing_epic_emoji(args.epic_dir).values())
            header = set_card_epic(args.kanban, args.needle, emoji, known)
            print(f"épico atualizado: {header}")
        elif args.cmd == "card" and args.card_cmd == "delete":
            title = delete_card(args.kanban, args.needle, args.force)
            print(f"movido pra .trash.md: {title}")
        elif args.cmd == "trash" and args.trash_cmd == "show":
            content = trash_show(args.kanban)
            print(content if content else "(vazio)")
        elif args.cmd == "trash" and args.trash_cmd == "clean":
            count = trash_clean(args.kanban)
            print(f"{count} card(s) removido(s) de vez" if count else "já estava vazio")
        elif args.cmd == "wip" and args.wip_cmd == "show":
            limit = read_wip_limit(load(args.kanban))
            print("sem limite" if limit <= 0 else str(limit))
        elif args.cmd == "wip" and args.wip_cmd == "set":
            set_wip_limit(args.kanban, args.limit)
            print(f"WIP de 'em-andamento' configurado pra {'sem limite' if args.limit <= 0 else args.limit}")
        elif args.cmd == "epic" and args.epic_cmd == "new":
            path, created = new_epic(args.epic_dir, args.slug, args.emoji, args.title)
            print(f"{'criado' if created else 'já existia, nada a fazer'}: {path}")
    except KanbanError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
