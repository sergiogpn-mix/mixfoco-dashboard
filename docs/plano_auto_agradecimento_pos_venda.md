# Plano — resposta automática de agradecimento no pós-venda

Status: **aprovado e implementado em 03/09/2026**.

- Dashboard (este repo): aba SAC → ⚙️ Automações, testador, histórico e card no painel.
- Backend (`sergiogpn-mix/https-mixfoco.com.br`, branch `claude/agradecimento-pos-venda-enviado`):
  momento "enviado" no `agradecer_positivo.py`, rotas da API e 32 testes novos.
- A regra nasce **desligada e em dry run**. Quem liga é a tela, depois do deploy do backend.

> O backend já tinha um agradecimento automático (`agradecer_positivo.py`) que só dispara com o
> pedido **entregue** e termina pedindo a opinião do comprador. O caso da fila (resposta ao aviso
> de **envio**, pedido a caminho) não era coberto. Em vez de um módulo novo, a mesma escada de
> portas ganhou um segundo texto, sem pedido de opinião. As seções abaixo descrevem o que foi
> implementado de fato, onde difere do plano original está marcado.

## Situação

A Gabriela envia a mensagem de pós-venda ("Boa notícia, ELIANA! Seu pedido já foi enviado.
Rastreio: ... Qualquer coisa, me chama.") e uma parte dos compradores responde com um
agradecimento curto ("Obg Gabriela", "Valeu", "Ok, obrigado"). Hoje essas respostas ficam como
"Não lido" no UpSeller e alguém precisa abrir uma a uma para encerrar.

## Objetivo

Quando o comprador responder à mensagem de pós-venda **apenas com um agradecimento**, responder
automaticamente com uma mensagem curta de agradecimento e encerrar a conversa. Qualquer outra
resposta (dúvida, problema, reclamação) **não** recebe resposta automática e segue para a Gabriela
sugerir uma resposta com revisão humana.

## Onde a regra vive

| Camada | Papel |
|---|---|
| Backend (API na Railway) | Recebe as mensagens da conversa do pedido, detecta o agradecimento, envia a resposta e registra o evento. É onde a regra roda. |
| Dashboard (este repo) | Liga/desliga a regra, edita o template, define a janela e mostra o histórico do que foi respondido automaticamente. |
| Base de conhecimento | Guarda o template como entrada `[auto] Agradecimento pós-venda` (categoria `pos-venda`), para ser editável sem deploy. |

Alternativa descartada: usar a "Auto Resposta" nativa do UpSeller. Ela responde por palavra-chave,
sem saber se a última mensagem nossa foi o pós-venda, e não consegue distinguir "obrigado" de
"obrigado, mas veio quebrado". O risco de responder "de nada" para uma reclamação é alto.

## A regra

**Gatilho.** Chega uma mensagem do comprador em uma conversa de pedido.

**Condições (todas obrigatórias).**

1. A última fala da conversa é do cliente, e a nossa última fala antes dela é o **aviso de
   envio** (texto com "rastreio", "já foi enviado" ou "saiu para entrega"). Se um humano
   respondeu depois do aviso, o "obrigado" é para ele e nada é enviado.
2. O aviso de envio tem menos de `janela_dias` (padrão: 15).
3. Ainda não houve agradecimento automático nesse pedido, de nenhum dos dois textos (uma resposta
   por pedido, sempre).
4. A mensagem é um **fecho positivo**, pela mesma porta de texto que o backend já usava:
   - até 120 caracteres;
   - sem `?`;
   - sem marca de insatisfação: `não`, `ainda`, `mas`, `porém`, `problema`, `defeito`, `quebrad`,
     `errad`, `falta`, `atras`, `demor`, `cancel`, `reembols`, `devolv`, `troca`, `estorno`,
     `reclama`, `procon`, `processo`, mais as palavras de bloqueio extras da tela;
   - com marca de positivo: `obrigad`, `obg`, `valeu`, `vlw`, `agradec`, `perfeito`, `ótimo`,
     `excelente`, `maravilh`, `show`, `tudo certo`, `deu certo`, `resolvido`, `adorei`, `amei`, `top`.
   - *Difere do plano:* "ok" sozinho **não** dispara (é acuso de recebimento, não gratidão, decisão
     já tomada no backend), e não há camada de IA para casos ambíguos: na dúvida, silêncio.
5. O assunto não é sensível (mesma lista que a Gabriela usa no pré-venda).
6. O pedido **não** está entregue. Entregue, vale o texto antigo, que pede a opinião.
   Se o ML não responder, o padrão é o silêncio.

**Ação.**

1. Envia a resposta (template abaixo) no chat do pedido, como "gabriela".
2. Registra em `sac_agradecimentos_log.json`: data, pedido, loja, momento, texto recebido,
   motivo, respondido, dry run e a resposta.
3. *Difere do plano:* o ticket **não** é encerrado nem marcado como lido automaticamente. A
   resposta entra na conversa como qualquer outra nossa, e o fluxo normal do SAC segue.

**Se qualquer condição falhar:** não responde. Cria/atualiza o ticket normalmente e a Gabriela
gera a sugestão para revisão humana, como já acontece.

## Template (primeira versão)

```
De nada, {primeiro_nome}! 💜 Fico feliz em ajudar.
Assim que o pedido chegar, se precisar de qualquer coisa é só me chamar por aqui.
Boas compras! — Gabriela · Equipe {loja}
```

Variáveis: `{primeiro_nome}` (primeiro nome do comprador, capitalizado) e `{loja}` (nome da conta,
ex.: SKYCONECTA). Sem pedido de avaliação nesta versão: fica como opção futura, para não
misturar agradecimento com cobrança de nota e evitar atrito com as políticas do Mercado Livre.

## Guarda-corpos

- Uma resposta automática por pedido. Se o comprador responder de novo, vai para humano.
- Nunca responde a mensagens nossas, de sistema ou do Mercado Livre.
- Não responde a assunto sensível (devolução, reclamação, cancelamento e afins estão na lista de
  bloqueio e na lista de escalação do pré-venda).
- Modo **dry run** por padrão: registra o que teria respondido sem enviar. Só ativa envio real
  depois de revisar o log.
- Botão de desligar no dashboard, com efeito no próximo webhook. `SAC_AGRADECIMENTO_AUTO=false`
  no Railway desliga os dois momentos.

## Mudanças por sistema

**Backend (`https-mixfoco.com.br`, feito).**

- `agradecer_positivo.py`: momento "enviado", configuração em `sac_config` (chave
  `agradecimento_enviado`), log em `sac_agradecimentos_log.json`, renderização do template.
- `api.py`: `GET/PUT /mixfoco/sac/automacoes/agradecimento`, `GET .../log?de=&ate=` e o campo
  `agradecimentos_automaticos` no `/mixfoco/sac/dashboard`.
- `tests/test_agradecer_enviado.py`: 32 casos. Suíte completa: 3151 testes passando.
- O gancho já existia: `hub_processor` chama `agradecer_positivo.varrer()` depois de cada
  ingestão de mensagem do ML.

**Dashboard (este repo, `dashboard.py`).**

- Na aba SAC, nova subaba **⚙️ Automações** com: toggle ativo, toggle dry run, janela em dias,
  editor do template com prévia usando um nome de exemplo, e tabela do log (data, pedido,
  texto recebido, classificação, respondido/simulado).
- Card no Painel do SAC com "agradecimentos automáticos no período".

**Base de conhecimento.**

- Entrada `[auto] Agradecimento pós-venda` com o template, importável pelo `kb_import.py`.

## Rollout

1. Fazer merge e deploy da branch do backend.
2. No dashboard, SAC → ⚙️ Automações: ligar "Ativa" com "Dry run" ligado. Deixar 3 dias úteis.
3. Carregar o histórico, conferir que só agradecimentos foram marcados. Ajustar as palavras de
   bloqueio extras se aparecer caso novo.
4. Desligar o dry run e salvar. A regra vale para todas as lojas; a assinatura usa a loja do
   pedido, a não ser que o campo "Assinatura da loja" esteja preenchido.

## Decisões (aprovadas em 03/09/2026)

1. Template e tom aprovados como está.
2. Janela: 15 dias.
3. Ticket: não encerra automaticamente (o backend só responde e registra).
4. A regra roda no backend, não na Auto Resposta do UpSeller.

## Contrato da API

Implementado nos dois lados: `api.py` do backend, e `dashboard.py` (aba SAC → ⚙️ Automações) com
`sac_automacoes.py` neste repo.

| Rota | Método | Corpo / resposta |
|---|---|---|
| `/mixfoco/sac/automacoes/agradecimento` | GET, PUT | `{"ativo": bool, "dry_run": bool, "janela_dias": int, "template": str, "palavras_bloqueio": [str], "loja": str}` |
| `/mixfoco/sac/automacoes/agradecimento/log?de=&ate=` | GET | `{"eventos": [{"data", "pedido", "loja", "momento", "texto_recebido", "classe", "motivo", "respondido", "dry_run", "resposta"}]}` |
| `/mixfoco/sac/dashboard` | GET | campo `agradecimentos_automaticos` (int) para o card do painel |

A porta de texto de referência é `agradecer_positivo._e_fecho` no backend.
`sac_automacoes.classificar_agradecimento` neste repo é um espelho dela, usado só pelo testador da
tela: devolve `agradecimento` ou `outro`. Se as listas mudarem no backend, mude aqui também.

O template fica também na base de conhecimento como `[auto] Agradecimento pós-venda`
(`ml-ia/kb/gabriela_kb_automacoes_2026-09-03.json`), importável com `kb_import.py`.
