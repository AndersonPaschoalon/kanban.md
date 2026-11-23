# kanban.md

Um app de linha de comando pra manipular um processo de kanban escrito
em Markdown puro — sem banco de dados, sem servidor, só arquivos
versionáveis no seu próprio repositório. Move card entre seções, cria
card/épico já com as regras certas, aplica limite de WIP, e manda
card apagado pra uma lixeira em vez de descartar de vez.

## Para agentes (Claude Code, etc.)

Regra de ouro: **nunca edite um `kanban.md` ou arquivo de épico com um
editor de texto** — toda mutação passa por um subcomando deste CLI.
Cada subcomando garante não tocar em nenhum card/linha além do que foi
pedido; uma edição manual não tem essa garantia. `kanban.md --help` (e o
`--help` de cada subcomando) traz a mesma referência densa abaixo,
pensada pra ser suficiente sozinha, sem precisar ler este arquivo.

## O modelo

Um kanban é um arquivo único (`kanban.md`), com cinco seções fixas,
nesta ordem exata:

```
## 🏁 Feito
## 🚧 Em andamento / próximo imediato
## 📋 Backlog
## 🧊 Idea Pool
## 🗒️ Notas e Observações
```

A última seção é prosa livre, sem cards — este CLI nunca toca nela.

Cada card é um título de nível 4, com até três emojis colados, sem
espaço entre eles:

```
#### <estado><épico?><próprio> Título do card
```

**Algoritmo de leitura dos emojis** (precedência, nesta ordem):

1. O 1º emoji, **se** for um de `{✅ 🟡 ⬜ 🧊}`, é sempre o **estado** —
   mapeamento 1:1 com a seção: ✅ Feito, 🟡 Em andamento, ⬜ Backlog,
   🧊 Idea Pool.
2. O **último** emoji é sempre o **próprio** (categoria livre do card:
   🔧 fix, 🐛 bug, ✨ feature, 📚 doc, etc.).
3. O emoji do **meio** só existe, e só conta como **épico**, quando há
   os três **e** o primeiro é um estado válido. Com só dois emojis, o
   card não tem épico atribuído ainda — válido, não é erro, não tente
   inferir um.
4. Qualquer emoji fora desse esquema é lixo: remova, não ignore
   silenciosamente.

Mover um card (`kanban.md move`) muda só o emoji de estado, pra bater
com a seção nova — épico e próprio nunca mudam nesse comando. Um card
em "Feito" é histórico: não se edita, não se apaga sem `--force`.

**Épico** = um arquivo à parte (`<epic_dir>/<slug>.md`), com título
obrigatório `# <emoji> Épico: <título>` — o emoji vem logo após o `#`,
e é dali (não de uma lista solta em outro lugar) que o CLI resolve
qual emoji pertence a qual épico. Emoji de épico é único: nunca repete
um emoji de estado/seção nem o de outro épico (`epic new` recusa
colisão).

**Criação de card** (`kanban.md card new`) sempre exige épico (já
existente) + emoji próprio — um card novo nasce com os três emojis;
a forma de dois emojis só é tolerada em cards antigos, não é um
caminho válido daqui pra frente. Por convenção (não imposto por
código): o emoji próprio nunca deve repetir o emoji do épico do mesmo
card.

**WIP**: a seção "Em andamento" tem teto — default 10, configurável
por arquivo via um comentário `<!-- wip: N -->` em qualquer linha do
`kanban.md` (`N <= 0` = sem limite). `move`/`card new` pra essa seção
recusam se o teto estourar.

**Delete nunca é definitivo**: `kanban.md card delete` move o card pro
`.trash.md` ao lado do kanban. `kanban.md trash clean` é a única forma
de descartar de vez.

## Instalação

```bash
uv tool install git+https://github.com/AndersonPaschoalon/kanban.md.git
kanban.md --help
```

Ou, clonado localmente:

```bash
uv run kanban.md --help
```

## Uso

`<kanban>` é o caminho pra qualquer `kanban.md`; `<epic_dir>` é a
pasta onde ficam os arquivos de épico (um por arquivo).

```bash
kanban.md list <kanban>
kanban.md move <kanban> "<trecho do título>" <feito|em-andamento|backlog|idea-pool>

kanban.md epic new <epic_dir> <slug> --emoji "📦" --title "<título>"
kanban.md card new <kanban> \
  --title "<título>" --category "🔧" \
  --epic-dir <epic_dir> --epic <slug> --section backlog

kanban.md card set-epic <kanban> "<trecho do título>" --epic-dir <epic_dir> --epic <slug>
kanban.md card delete <kanban> "<trecho do título>"

kanban.md wip show <kanban>
kanban.md wip set <kanban> <N>   # <= 0 = sem limite (default: 10)

kanban.md trash show <kanban>
kanban.md trash clean <kanban>
```

## Rodando os testes

```bash
uv run pytest
```
