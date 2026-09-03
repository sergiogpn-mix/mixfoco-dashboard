# Gabriela — Pendências da base de conhecimento (2026-09-03)

Fonte: `Gabriela — Base de Conhecimento por Produto (ml-ia/kb)`.

## Resumo

- Entradas prontas para gravar: **20** em 12 anúncios.
- Entradas puladas (sem status `pronta` ou formato inválido): **0**.
- Pendências que dependem de dado ou política: **11**.
- Correções de ficha no Mercado Livre: **6**.

## Pendências (dado ou política a definir)

| Prio | Tema | Anúncios | Pergunta a responder | Por quê |
|---|---|---|---|---|
| P0 | Continuidade do desenho entre placas de mármore | MLB6304509992, MLB4493085205, MLB4748679959, MLB6304509924, MLB4645641027, +9 anúncios irmãos | Os veios da estampa dão continuidade de uma placa para a outra, ou cada placa é uma estampa fechada? | É a pergunta que gerou 13 entradas evasivas na base — a mais replicada de todas. Hoje a Gabriela responde 'verifique no anúncio'. |
| P0 | Política de garantia | todos | Qual a garantia padrão (prazo, quem cobre, como o cliente aciona)? Há prazo diferente por categoria — eletrônico, máquina, utilidade? | Garantia aparece em 10 perguntas de agosto e é a origem da resposta evasiva mais copiada da base. |
| P0 | Ficha da laser fiber 30W | MLB6888908160 | Fonte do laser (Raycus, JPT, MAX ou outra) e modelo exato; placa controladora; aceita LightBurn?; lente que acompanha (em mm). | Comprador técnico perguntou item a item em agosto. Nada disso está na ficha nem na descrição — é venda de ticket alto perdida por falta de dado. |
| P1 | Personalização e gravação de nome | MLB5937516136, MLB4308562565, MLB5940252962, MLB4475232859, MLB4998350485, MLB7015633274 | Vocês fazem gravação/personalização? Se sim: preço, prazo, quantidade mínima e área de gravação. Se não: resposta padrão. | 4 perguntas em agosto só nas garrafas, mais expositor 'já entregam com a marca?'. Vocês têm a máquina de gravação — dá para virar receita. |
| P1 | Garrafas: sublimação e lava-louças | MLB4308562565, MLB5940252962 | O copo tem revestimento de poliéster próprio para sublimação? Pode ir na lava-louças? | Cliente sublimador é comprador recorrente e de volume; a resposta hoje é evasiva. |
| P1 | Autonomia de bateria | MLB4416170851, MLB6999691306, MLB6107517744 | Quantas horas dura a carga de cada um (ventilador dobrável, ventilador de pé, fone)? | Pergunta repetida em 3 anúncios; hoje a Gabriela responde que não tem a informação. |
| P1 | Display expositor: base, ganchos e carga | MLB7015633274, MLB7024275356, MLB5063526253 | Profundidade da base, comprimento e diâmetro do gancho, e peso máximo suportado por gancho/por prateleira. | 3 perguntas distintas em agosto e 2 entradas evasivas já gravadas. |
| P2 | Peças de reposição | MLB4893593273, MLB4308562565 | Vendem lâmina/agulha de reposição da máquina de corte? Vendem tampa avulsa das garrafas? | Duas perguntas de compradores que já compraram — é receita recorrente sem resposta. |
| P2 | Cabo de força: bitola e condutor | MLB4480491787, MLB5063497535 | É 100% cobre? A bitola é 3 × 0,75 mm²? | Comprador técnico; a ficha não traz a bitola. |
| P2 | Política de desconto, atacado e origem do envio | todos | Qual a regra de desconto que a Gabriela pode oferecer (se alguma)? Qual a faixa de atacado? De qual cidade sai o envio? | 13 perguntas de preço/desconto e várias de 'de onde vocês são' em agosto, respondidas caso a caso por humano. |
| P2 | Nota fiscal e CNPJ | todos | Confirmar a resposta padrão: emitem NF-e em todo pedido? Aceitam compra com CNPJ para crédito de ICMS? | Pergunta recorrente e de resposta simples — só precisa ser canonizada. |

## Correções de anúncio (ficha técnica no ML)

| Anúncio | Campo | Problema | Efeito na Gabriela |
|---|---|---|---|
| MLB4893593273 | Largura mínima/máxima de corte | Ficha diz mínima 100 cm e máxima 43,18 cm — mínimo maior que o máximo. | A Gabriela lê a ficha e não consegue responder tamanho de tela com segurança. |
| MLB5937516136 | Retenção térmica | Atributos dizem 12h frio e 12h quente; a descrição diz 'mantém por até 8 hrs'. | Fonte contraditória: risco de reclamação por informação divergente. |
| MLB4412879467 | Taxa de transferência de dados | Ficha declara 3.840 Tbps — valor impossível para USB 3.0. | Comprador técnico perguntou justamente a versão do USB. |
| MLB6404883104 | Layout | Ficha diz QWERTZ; o título diz ABNT2 (que é QWERTY brasileiro). | Contradição dentro do próprio anúncio. |
| MLB6888908160 | Dimensões | Largura da máquina 4 cm com altura 180 cm e peso 46 kg — incoerente. | Impede responder qualquer pergunta de espaço/instalação. |
| MLB6526654944 | Voltagem da bateria | Declara 12V para um aparador recarregável de mão. | Dado provavelmente errado na ficha. |

## Entradas prontas (gravadas pelo `kb_import.py`)

- `compatibilidade` · [MLB6111470134] Powerbank Carregador Portátil 5000mah Carregamento Magnético — Funciona com capinha? Preciso de capinha com anel magnético?
- `uso` · [MLB6111470134] Powerbank Carregador Portátil 5000mah Carregamento Magnético — Encostei no celular e não carrega, o que faço?
- `especificacao` · [MLB6111470134] Powerbank Carregador Portátil 5000mah Carregamento Magnético — Qual a capacidade, a potência e o que vem junto? É homologado?
- `compatibilidade` · [MLB4893593273] Maquina Para Cortar Pelicula Hidrogel Tpu Dgx Desbloqueada — Ela corta película de tablet/notebook de 13 ou 17 polegadas?
- `conteudo-da-caixa` · [MLB4893593273] Maquina Para Cortar Pelicula Hidrogel Tpu Dgx Desbloqueada — O que vem na caixa? Acompanha espátula ou kit de películas?
- `funcionamento` · [MLB4893593273] Maquina Para Cortar Pelicula Hidrogel Tpu Dgx Desbloqueada — Ela é desbloqueada? Tem mensalidade?
- `especificacao` · [MLB5937516136] Garrafa Térmica Inox 1l Squeeze Academia 12h Frio/quente — Qual a capacidade, as medidas e quanto tempo conserva a temperatura?
- `compatibilidade` · [MLB5937516136] Garrafa Térmica Inox 1l Squeeze Academia 12h Frio/quente — Cabe no suporte de garrafa da bicicleta?
- `especificacao` · [MLB4308562565] Garrafa Térmica Copo Inox 900ml Alça Tampa T Flip Canudo — Qual a capacidade, as medidas e a retenção térmica?
- `calculo` · [MLB6304509992] Placa Autoadesiva Marmorizada Dgx 60x60cm Vinil Premium — Quantas placas eu preciso para a minha parede? Como faço o cálculo?
- `aplicacao` · [MLB6304509992] Placa Autoadesiva Marmorizada Dgx 60x60cm Vinil Premium — Posso colar em parede só rebocada? Precisa de rejunte?
- `aplicacao` · [MLB6304509992] Placa Autoadesiva Marmorizada Dgx 60x60cm Vinil Premium — Pode ser usada no piso ou em piso laminado?
- `especificacao` · [MLB7015633274] Display Expositor De Metal Produtos Encartelados 60 Ganchos — Quais as medidas do expositor e o que acompanha?
- `especificacao` · [MLB4646299465] Chaleira Eletrica Aço Inox 1.8l Prateado Dgx 220 1500w — Qual a potência, a capacidade e a voltagem?
- `uso` · [MLB4646299465] Chaleira Eletrica Aço Inox 1.8l Prateado Dgx 220 1500w — Pode esquentar leite?
- `especificacao` · [MLB4412879467] Adaptador Hub Usb C 8 Em 1 Tipo C Para Hdmi Usb 3.0 4k Nat — Qual a versão do USB? É USB 3.2 Gen 2?
- `compatibilidade` · [MLB4480491787] Cabo De Força Energia Tripolar 1,5m Para Fonte Monitor Pc — Esse cabo serve para PC/monitor?
- `compatibilidade` · [MLB4434666951] Cabeça Adaptador Parafusadeira Multifunção Serra Tico-tico — Encaixa na minha parafusadeira? Vem a máquina junto?
- `especificacao` · [MLB6404883104] Teclado Usb Com Fio B-max Bm-t02 Abnt2 Silencioso Ergonômico — Funciona no Windows 11? Precisa instalar driver?
- `especificacao` · [MLB6888908160] Máquina De Gravação A Laser Metais Cnc Fiber Fibra 30w — Qual a potência, a área de gravação e o que acompanha?
