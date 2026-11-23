from __future__ import annotations

import argparse
import sys
from pathlib import Path

from kanban_md.epics import epic_emoji, existing_epic_emoji, list_epics, new_epic, set_epic_status
from kanban_md.kanban import (
    KanbanError,
    KEY_TO_STATUS,
    delete_card,
    init_kanban,
    list_cards,
    load,
    move_card,
    new_card,
    read_wip_limit,
    set_card_epic,
    set_wip_limit,
    show_card,
    trash_clean,
    trash_show,
    update_card_body,
)
from kanban_md.project import new_project


EPILOG = """\
MODELO (leia isto antes de tocar em qualquer kanban.md -- resumo
denso, a referência completa está no README):

  Arquivo único por kanban, 5 seções fixas, nesta ordem exata:
    ## 🏁 Feito
    ## 🚧 Em andamento / próximo imediato
    ## 📋 Backlog
    ## 🧊 Idea Pool
    ## 🗒️ Notas e Observações  (prosa livre, não tem cards, este CLI nunca toca aqui)
  'init' cria esse esqueleto vazio -- nunca crie um kanban.md à mão.

  Card = `#### <estado><épico?><próprio> Título` (nível 4, emojis colados, sem espaço).
  Algoritmo de leitura dos emojis do header, NESTA ordem de precedência:
    1. 1o emoji, SE for um de {✅ 🟡 ⬜ 🧊} -> é o ESTADO. Sempre.
    2. último emoji -> é o PRÓPRIO (categoria livre). Sempre.
    3. emoji do meio só existe, e só é ÉPICO, quando há os 3 E o 1o é estado válido.
       Com só 2 emojis: sem épico atribuído ainda -- válido, não é erro, não adivinhe um.
    4. qualquer emoji fora desse esquema é lixo -> remova, não ignore silenciosamente.
  Estado <-> seção é 1:1: ✅=Feito, 🟡=Em andamento, ⬜=Backlog, 🧊=Idea Pool.
  Mover um card muda só o emoji de estado (pra bater com a seção nova); épico e
  próprio nunca mudam num `move`. Um card em Feito é histórico: não editar, não
  apagar sem --force. Pra mudar o TEXTO de um card (não a seção/épico), use
  `card show` (lê) + `card update` (substitui o corpo) -- nunca um editor.

  Épico = arquivo em <epic_dir>/<slug>.md, título obrigatório `# <emoji> Épico: <título>`
  (emoji logo após o `#`, é dali que este CLI resolve qual emoji pertence a qual
  épico -- não existe lista solta em outro lugar). Emoji de épico é único, nunca
  repete um estado/seção nem outro épico (`epic new` recusa colisão). `epic
  set-status` muda o campo Status sem precisar editar o arquivo à mão.

  "Projeto" é convenção opcional, não obrigatória: uma pasta com `kanban.md` +
  `epics/` dentro, criados juntos por `project new`. Todo outro comando continua
  aceitando qualquer caminho de kanban/epic-dir, mesmo fora dessa convenção --
  um épico pode ser compartilhado por vários kanbans se fizer sentido.

  Card novo SEMPRE exige épico (já existente) + emoji próprio -- nunca crie um
  card novo com só 2 emojis, essa forma só é tolerada em cards antigos. Por
  convenção (não imposto por código), o emoji próprio nunca deve repetir o
  emoji do épico do mesmo card.

  WIP: a seção "Em andamento" tem teto (default 10, `<= 0` = sem limite),
  configurável via comentário `<!-- wip: N -->` em qualquer linha do arquivo.
  `move`/`card new` pra lá recusam se o teto estourar.

  Delete nunca é definitivo: o card vai pra `.trash.md` ao lado do kanban.
  `trash clean` é a única forma de apagar de vez.

  REGRA DE OURO: nunca edite um kanban.md ou arquivo de épico num editor de
  texto -- toda mutação passa por um destes subcomandos, que garantem nunca
  tocar em nenhum card/linha além do que foi pedido. Se um comando faltar pro
  que você precisa, não contorne editando o arquivo à mão.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kanban.md",
        description="CLI determinística pra um kanban em Markdown puro (cards, épicos, WIP, trash).",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser(
        "init",
        help="cria um kanban.md novo, vazio, com as 5 seções (idempotente)",
        description="Idempotente: se o arquivo já existir, não mexe em nada (ignora --title/--wip "
        "passados e só confirma que já existe). Use isto, nunca crie um kanban.md à mão "
        "-- 'list'/'card new'/etc. recusam operar num arquivo que não existe.",
    )
    p_init.add_argument("kanban", type=Path)
    p_init.add_argument("--title", required=True, help="título do kanban (linha `# <título>`)")
    p_init.add_argument("--wip", type=int, default=10, help="limite inicial de WIP (default 10, <=0 = sem limite)")

    p_project = sub.add_parser("project", help="comandos de projeto (new) -- atalho opcional")
    project_sub = p_project.add_subparsers(dest="project_cmd", required=True)
    p_project_new = project_sub.add_parser(
        "new",
        help="cria <dir>/kanban.md + <dir>/epics/ juntos (idempotente)",
        description="Atalho pra convenção 'um projeto = uma pasta com kanban.md e epics/ dentro'. "
        "Equivale a 'init <dir>/kanban.md' + mkdir <dir>/epics. Não obrigatório -- kanban "
        "e epic-dir continuam podendo ficar em qualquer lugar, inclusive compartilhados "
        "entre vários projetos.",
    )
    p_project_new.add_argument("project_dir", type=Path)
    p_project_new.add_argument("--title", required=True)
    p_project_new.add_argument("--wip", type=int, default=10)

    p_list = sub.add_parser("list", help="lista os cards de um kanban.md com a seção atual de cada um")
    p_list.add_argument("kanban", type=Path)

    p_move = sub.add_parser(
        "move",
        help="move um card pra outra seção, atualizando só o emoji de estado",
        description="Acha o card por substring (case-insensitive) do título, corta o bloco exato "
        "dele e recoloca no fim da seção de destino, trocando só o emoji de estado. "
        "Nunca toca em nenhuma outra linha do arquivo. Erro se 'needle' não casar com "
        "nenhum card, casar com mais de um, ou se o destino já for a seção atual.",
    )
    p_move.add_argument("kanban", type=Path)
    p_move.add_argument("needle", help="trecho (case-insensitive) do título do card")
    p_move.add_argument("to", choices=sorted(KEY_TO_STATUS), help="seção de destino")

    p_card = sub.add_parser("card", help="comandos de card (new/show/update/set-epic/delete)")
    card_sub = p_card.add_subparsers(dest="card_cmd", required=True)
    p_card_new = card_sub.add_parser(
        "new",
        help="cria um card novo (épico + emoji próprio são obrigatórios)",
        description="Cria um card com os 3 emojis desde o início. --epic deve já existir em "
        "--epic-dir (use 'epic new' antes se não existir). Recusa --category reservado "
        "(um dos emojis de estado/seção) ou igual ao emoji do próprio épico escolhido.",
    )
    p_card_new.add_argument("kanban", type=Path)
    p_card_new.add_argument("--title", required=True)
    p_card_new.add_argument("--category", required=True, help="emoji 'próprio' do card (último do header)")
    p_card_new.add_argument("--epic-dir", type=Path, required=True, help="pasta onde ficam os arquivos de épico")
    p_card_new.add_argument("--epic", required=True, help="slug do épico (arquivo <epic-dir>/<slug>.md já deve existir)")
    p_card_new.add_argument("--section", default="backlog", choices=sorted(KEY_TO_STATUS))
    p_card_new.add_argument("--body", default="", help="corpo opcional (markdown livre) logo abaixo do header")

    p_card_show = card_sub.add_parser(
        "show",
        help="mostra o header + corpo de um card, como está no arquivo",
        description="Use antes de 'card update' pra editar em cima do conteúdo real, em vez de "
        "adivinhar o que já está escrito.",
    )
    p_card_show.add_argument("kanban", type=Path)
    p_card_show.add_argument("needle", help="trecho (case-insensitive) do título do card")

    p_card_update = card_sub.add_parser(
        "update",
        help="substitui o corpo (texto) de um card existente",
        description="Substitui TODO o corpo pelo --body dado -- não é um patch/append, é o texto "
        "novo inteiro. Não mexe no header (estado/épico/próprio/título) nem na posição "
        "do card entre os irmãos da seção. Leia com 'card show' antes se for editar em "
        "cima do que já existe.",
    )
    p_card_update.add_argument("kanban", type=Path)
    p_card_update.add_argument("needle", help="trecho (case-insensitive) do título do card")
    p_card_update.add_argument("--body", default="", help="corpo novo inteiro (markdown livre)")

    p_card_set_epic = card_sub.add_parser(
        "set-epic",
        help="adiciona (card com 2 emojis) ou troca (card com 3) o épico de um card existente",
        description="Não mexe no emoji de estado nem no 'próprio' nem no título -- só insere ou "
        "substitui o emoji de épico. Reconhece se o card já tem épico comparando contra "
        "os emojis já registrados em --epic-dir, não por posição/contagem de caracteres.",
    )
    p_card_set_epic.add_argument("kanban", type=Path)
    p_card_set_epic.add_argument("needle", help="trecho (case-insensitive) do título do card")
    p_card_set_epic.add_argument("--epic-dir", type=Path, required=True)
    p_card_set_epic.add_argument("--epic", required=True)

    p_card_delete = card_sub.add_parser(
        "delete",
        help="move um card pra .trash.md (nunca apaga de vez)",
        description="Move o card pro .trash.md ao lado do kanban -- use 'trash clean' se quiser "
        "mesmo descartar de vez. Recusa apagar um card em 'feito' sem --force (histórico "
        "concluído não se move de leve).",
    )
    p_card_delete.add_argument("kanban", type=Path)
    p_card_delete.add_argument("needle", help="trecho (case-insensitive) do título do card")
    p_card_delete.add_argument("--force", action="store_true", help="permite apagar card já em 'feito'")

    p_wip = sub.add_parser(
        "wip",
        help="limite de WIP (work in progress) da seção 'Em andamento'",
        description="Default do limite é 10 quando o kanban.md não tem comentário '<!-- wip: N -->'. "
        "N <= 0 significa sem limite. O limite é verificado automaticamente por "
        "'move'/'card new' ao entrar em 'em-andamento' -- não precisa chamar isso antes.",
    )
    wip_sub = p_wip.add_subparsers(dest="wip_cmd", required=True)
    p_wip_show = wip_sub.add_parser("show", help="mostra o limite configurado (ou o default, 10)")
    p_wip_show.add_argument("kanban", type=Path)
    p_wip_set = wip_sub.add_parser("set", help="configura o limite (<=0 = sem limite)")
    p_wip_set.add_argument("kanban", type=Path)
    p_wip_set.add_argument("limit", type=int)

    p_trash = sub.add_parser(
        "trash",
        help="cards apagados (.trash.md ao lado do kanban) -- show/clean",
        description="'card delete' só move pra cá, nunca apaga de vez. 'trash clean' é a única "
        "forma de descartar permanentemente -- não reversível depois disso.",
    )
    trash_sub = p_trash.add_subparsers(dest="trash_cmd", required=True)
    p_trash_show = trash_sub.add_parser("show", help="mostra o conteúdo do .trash.md ('(vazio)' se não houver nada)")
    p_trash_show.add_argument("kanban", type=Path)
    p_trash_clean = trash_sub.add_parser("clean", help="esvazia o .trash.md de vez, devolve quantos cards tinha")
    p_trash_clean.add_argument("kanban", type=Path)

    p_epic = sub.add_parser("epic", help="comandos de épico (new/list/set-status)")
    epic_sub = p_epic.add_subparsers(dest="epic_cmd", required=True)
    p_epic_new = epic_sub.add_parser(
        "new",
        help="cria o arquivo de um épico com template mínimo (idempotente)",
        description="Idempotente: se <epic-dir>/<slug>.md já existe, não sobrescreve (ignora os "
        "demais argumentos e só confirma que já existe). --emoji precisa ser único -- "
        "recusa se já for um emoji de estado/seção reservado ou de outro épico existente. "
        "--objective/--source preenchem os campos já na criação; se omitidos, ficam "
        "'(preencher)' (editar esse placeholder de prosa depois é aceitável, a estrutura "
        "é o que este comando garante).",
    )
    p_epic_new.add_argument("epic_dir", type=Path, help="pasta onde ficam os arquivos de épico")
    p_epic_new.add_argument("slug")
    p_epic_new.add_argument("--emoji", required=True)
    p_epic_new.add_argument("--title", required=True)
    p_epic_new.add_argument("--objective", default=None, help="preenche 'Objetivo fim a fim' já na criação")
    p_epic_new.add_argument("--source", default=None, help="preenche 'Fonte' já na criação")

    p_epic_list = epic_sub.add_parser("list", help="lista os épicos (slug, emoji, título, status)")
    p_epic_list.add_argument("epic_dir", type=Path)

    p_epic_set_status = epic_sub.add_parser(
        "set-status",
        help="muda o campo Status de um épico",
        description="Substitui só o valor depois de '**Status**:' -- não mexe em objetivo/fonte/"
        "cards completados.",
    )
    p_epic_set_status.add_argument("epic_dir", type=Path)
    p_epic_set_status.add_argument("slug")
    p_epic_set_status.add_argument("status", help='ex: "em andamento", "fechado", "pausado"')

    args = parser.parse_args(argv)

    try:
        if args.cmd == "init":
            created = init_kanban(args.kanban, args.title, args.wip)
            print(f"{'criado' if created else 'já existia, nada a fazer'}: {args.kanban}")
        elif args.cmd == "project" and args.project_cmd == "new":
            kanban_path, epic_dir, created = new_project(args.project_dir, args.title, args.wip)
            print(f"{'criado' if created else 'kanban.md já existia'}: {kanban_path} (épicos em {epic_dir})")
        elif args.cmd == "list":
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
        elif args.cmd == "card" and args.card_cmd == "show":
            print(show_card(args.kanban, args.needle))
        elif args.cmd == "card" and args.card_cmd == "update":
            header = update_card_body(args.kanban, args.needle, args.body)
            print(f"corpo atualizado: {header}")
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
            path, created = new_epic(
                args.epic_dir, args.slug, args.emoji, args.title, args.objective, args.source
            )
            print(f"{'criado' if created else 'já existia, nada a fazer'}: {path}")
        elif args.cmd == "epic" and args.epic_cmd == "list":
            for e in list_epics(args.epic_dir):
                print(f"{e.emoji} {e.slug} -- {e.title} [{e.status}]")
        elif args.cmd == "epic" and args.epic_cmd == "set-status":
            path = set_epic_status(args.epic_dir, args.slug, args.status)
            print(f"status atualizado: {path}")
    except KanbanError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
