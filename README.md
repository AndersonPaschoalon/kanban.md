# process-cli

CLI determinística pra manipular um `kanban.md` no formato descrito em
`docs/process.md` do projeto `mlops_platform` (onde esta ferramenta
nasceu: [`../docs/process.md`](../docs/process.md)) --
move card entre seções, cria card/épico, aplica limite de WIP e manda
card apagado pra um `.trash.md` em vez de descartar de vez. Pensada
pra uso tanto por humanos quanto por agentes (o `--help` de cada
comando já é a documentação).

## Pré-requisitos

- [`uv`](https://docs.astral.sh/uv/)

## Uso

`<kanban>` é o caminho pra qualquer `kanban.md` (absoluto, ou relativo
a esta pasta); `<epic_dir>` é a pasta `_epic/` correspondente. Rodando
de dentro deste repositório, neste projeto (`mlops_platform`), ambos
ficam em `../docs/process/`.

```bash
uv run process list <kanban>
uv run process move <kanban> "<trecho do título>" <feito|em-andamento|backlog|idea-pool>

uv run process epic new <epic_dir> <slug> --emoji "📦" --title "<título>"
uv run process card new <kanban> \
  --title "<título>" --category "🔧" \
  --epic-dir <epic_dir> --epic <slug> --section backlog

uv run process card set-epic <kanban> "<trecho do título>" --epic-dir <epic_dir> --epic <slug>
uv run process card delete <kanban> "<trecho do título>"

uv run process wip show <kanban>
uv run process wip set <kanban> <N>   # <= 0 = sem limite

uv run process trash show <kanban>
uv run process trash clean <kanban>
```

Instalado fora deste repositório (sem clonar):

```bash
uv tool install git+<url deste repositório>
process --help
```

## Rodando os testes

```bash
uv run pytest
```
