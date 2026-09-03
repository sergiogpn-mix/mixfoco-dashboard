# Plano — resposta automática de agradecimento no pós-venda

Status: **proposta, aguardando aprovação do Sergio**. Nada implementado ainda.

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

1. A última mensagem enviada por nós nessa conversa é a de pós-venda da Gabriela (marcada com a tag
   `pos_venda_enviado`) e nenhum humano respondeu depois dela.
2. A mensagem chegou dentro da janela configurada (padrão: 15 dias após o envio do pós-venda).
3. Ainda não houve resposta automática de agradecimento nesse pedido (uma por pedido, sempre).
4. A mensagem é classificada como **agradecimento puro**:
   - texto normalizado (sem acento, minúsculas, sem emoji) com até 80 caracteres;
   - bate com a lista positiva: `obg`, `obrigad`, `brigad`, `valeu`, `vlw`, `ok`, `okay`, `blz`,
     `beleza`, `perfeito`, `show`, `top`, `maravilha`, `otimo`, `certo`, `combinado`, `grat`,
     `thanks`, `👍`, `❤️`, `💜`, `🙏`;
   - **não** contém `?` nem nenhuma palavra da lista de bloqueio: `nao chegou`, `atras`, `cade`,
     `quebr`, `defeito`, `errad`, `faltou`, `troca`, `devolu`, `cancel`, `reembolso`, `danific`,
     `problema`, `nao funciona`, `nota fiscal`, `garantia`, `quando`, `prazo`.
   - Em caso de dúvida (texto entre 80 e 200 caracteres, ou mistura de agradecimento com outra
     coisa), a rota `/mixfoco/sac/ia/classificar` decide; qualquer classe diferente de
     `agradecimento` bloqueia a automação.

**Ação.**

1. Envia a resposta de agradecimento (template abaixo) na mesma conversa.
2. Marca a conversa como lida/encerrada no UpSeller e o ticket como `resolvido` na API.
3. Registra em `sac_automacoes_log`: pedido, texto recebido, classificação, template usado,
   data/hora e se foi dry run.

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
- Não responde se o pedido tiver reclamação, devolução ou mediação aberta.
- Não responde se o status do pedido for cancelado ou devolvido.
- Modo **dry run** por padrão: registra o que teria respondido sem enviar. Só ativa envio real
  depois de revisar o log.
- Botão de desligar no dashboard, com efeito imediato.

## Mudanças por sistema

**Backend (API, fora deste repo).**

- Nova configuração `GET/PUT /mixfoco/sac/automacoes/agradecimento`: `ativo`, `dry_run`,
  `janela_dias`, `template`, `palavras_bloqueio` extras.
- Classificador `agradecimento_puro(texto)` (regex + fallback IA) com testes.
- Hook na ingestão de mensagens que aplica a regra e grava o log.
- `GET /mixfoco/sac/automacoes/agradecimento/log?de=&ate=` para o dashboard.

**Dashboard (este repo, `dashboard.py`).**

- Na aba SAC, nova subaba **⚙️ Automações** com: toggle ativo, toggle dry run, janela em dias,
  editor do template com prévia usando um nome de exemplo, e tabela do log (data, pedido,
  texto recebido, classificação, respondido/simulado).
- Card no Painel do SAC com "agradecimentos automáticos no período".

**Base de conhecimento.**

- Entrada `[auto] Agradecimento pós-venda` com o template, importável pelo `kb_import.py`.

## Rollout

1. Backend em dry run por 3 dias úteis, revisando o log no dashboard.
2. Ajustar listas positiva/bloqueio com os casos reais que aparecerem.
3. Ativar envio real em uma loja (sky conecta), acompanhar por uma semana.
4. Estender às demais contas.

## Decisões que precisamos do Sergio

1. Aprovar o texto do template e o tom (manter o 💜 e a assinatura "Gabriela · Equipe {loja}"?).
2. Janela de dias após o pós-venda (proposta: 15).
3. Encerrar o ticket automaticamente ou só marcar como lido?
4. Confirmar que a regra roda no backend, e não na Auto Resposta do UpSeller.
