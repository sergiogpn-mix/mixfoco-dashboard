# Mixfoco Dashboard

Dashboard Streamlit (`dashboard.py`, arquivo único) para a operação Mixfoco em marketplaces.
Ele não tem banco próprio: toda leitura e gravação passa pela API em `MIXFOCO_API_URL`
(padrão: Railway), via o helper `api(method, path, **kwargs)` que devolve `(dados, erro)`.

## Rodar

```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

## Gabriela — base de conhecimento do SAC (`ml-ia/kb`)

A Gabriela é a IA que sugere respostas na aba **SAC → Base de Conhecimento**. A base fica no
backend, na rota `/mixfoco/sac/kb` (campos: `titulo`, `categoria`, `marketplace`, `resposta`, `ativo`).

A fonte versionada da base é a pasta `ml-ia/kb/`:

- `gabriela_kb_<data>.json` — entradas por produto (`item_id` do ML, `titulo_produto`, `status`,
  `tags`, `fonte`, `conteudo`), além de `pendencias` e `correcoes_de_anuncio`.
- `conteudo` segue a convenção `P: <pergunta canônica>\nR: <resposta>`.
- `status`: `pronta` (fato conferido na ficha/descrição do anúncio, pode gravar), `falta_dado`
  (precisa do dado do Sergio) e `politica` (depende de política comercial). Só `pronta` vai
  para a API; o resto vira pendência.
- `PENDENCIAS.md` — relatório gerado a partir do JSON (perguntas sem fonte e fichas a corrigir).

Para gravar na API use `kb_import.py` (idempotente: chave é o título
`[<item_id>] <titulo_produto> — <pergunta>`; iguais são pulados, diferentes são atualizados):

```bash
python kb_import.py ml-ia/kb/gabriela_kb_2026-09-03.json --dry-run
python kb_import.py ml-ia/kb/gabriela_kb_2026-09-03.json
python kb_import.py ml-ia/kb/gabriela_kb_2026-09-03.json --report > ml-ia/kb/PENDENCIAS.md
```

O mesmo importador está na aba SAC → Base de Conhecimento → "Importar base da Gabriela".

Ao atualizar a base: gere um novo JSON datado em `ml-ia/kb/` (não edite o anterior), só marque
`pronta` o que tem fonte publicada no anúncio, regenere o `PENDENCIAS.md` e rode o importador.

## Automações do SAC (`sac_automacoes.py`)

Aba SAC → ⚙️ Automações configura o **agradecimento automático ao aviso de envio** (plano e
contrato da API em `docs/plano_auto_agradecimento_pos_venda.md`). A regra roda no backend
(`agradecer_positivo.py`, momento "enviado"); `sac_automacoes.classificar_agradecimento` é um
espelho da porta de texto do backend, usado só pelo testador da tela. Se as listas de palavras
mudarem lá, mude aqui também.

## Convenções

- Idioma do produto e das mensagens ao cliente: português do Brasil.
- Não coloque segredos no repositório; a URL da API vem de variável de ambiente.
