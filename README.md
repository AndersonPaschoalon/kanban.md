# kanban.md

Um app de linha de comando pra manipular um processo de kanban escrito
em Markdown puro — sem banco de dados, sem servidor, só arquivos
versionáveis no seu próprio repositório. Move card entre seções, cria
card/épico já com as regras certas, aplica limite de WIP, e manda
card apagado pra uma lixeira em vez de descartar de vez.

## O formato

Um kanban é um único arquivo (`kanban.md`), com cinco seções fixas,
nesta ordem:

```
## 🏁 Feito
## 🚧 Em andamento / próximo imediato
## 📋 Backlog
## 🧊 Idea Pool
## 🗒️ Notas e Observações
```

Cada card é um título de nível 4, com até três emojis colados, sem
espaço entre eles:

```
#### <estado><épico><próprio> Título do card
```

- **Estado**: muda com a seção — ✅ Feito, 🟡 Em andamento, ⬜ Backlog,
  🧊 Idea Pool. Sempre o primeiro emoji, nunca escolhido à mão.
- **Épico**: opcional — identifica uma tarefa maior que atravessa
  vários kanbans. Cada épico é um arquivo à parte, com seu próprio
  emoji (escolhido na criação, único) no título principal, logo após
  o `#` (ex: `# 📦 Épico: ...`). Um card só tem emoji de épico quando
  tem os três emojis **e** o primeiro é um dos marcadores de estado —
  com só dois emojis, o card simplesmente não tem épico atribuído
  ainda, o que é válido, não é erro.
- **Próprio**: categoria livre do card (🔧 fix, 🐛 bug, ✨ feature,
  📚 doc, etc.) — sempre o último emoji.

Um card concluído (seção Feito) nunca é editado nem removido depois —
só se move de seção quando muda de estado. O histórico é o próprio
conteúdo do arquivo.

## Instalação

```bash
uv tool install git+https://github.com/AndersonPaschoalon/kanban.md.git
process --help
```

Ou, clonado localmente:

```bash
uv run process --help
```

## Uso

`<kanban>` é o caminho pra qualquer `kanban.md`; `<epic_dir>` é a
pasta onde ficam os arquivos de épico (um por arquivo).

```bash
process list <kanban>
process move <kanban> "<trecho do título>" <feito|em-andamento|backlog|idea-pool>

process epic new <epic_dir> <slug> --emoji "📦" --title "<título>"
process card new <kanban> \
  --title "<título>" --category "🔧" \
  --epic-dir <epic_dir> --epic <slug> --section backlog

process card set-epic <kanban> "<trecho do título>" --epic-dir <epic_dir> --epic <slug>
process card delete <kanban> "<trecho do título>"

process wip show <kanban>
process wip set <kanban> <N>   # <= 0 = sem limite (default: 10)

process trash show <kanban>
process trash clean <kanban>
```

## Rodando os testes

```bash
uv run pytest
```
