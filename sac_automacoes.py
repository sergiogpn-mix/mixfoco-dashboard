"""
sac_automacoes.py — Regras de automação do SAC usadas pelo dashboard.

Hoje contém a automação de **agradecimento ao aviso de envio**: quando o comprador responde à
mensagem "seu pedido já foi enviado" da Gabriela só com um agradecimento, o backend responde
"de nada" (sem pedido de avaliação) e registra o evento. A regra roda no backend, no módulo
`agradecer_positivo.py` (momento "enviado"). Este módulo concentra o que a tela precisa:

  - `classificar_agradecimento(texto)`: ESPELHO da porta de texto do backend (`_e_fecho`),
    para o testador da tela dizer o que o backend faria. Se mudar lá, mude aqui.
  - `renderizar_template`: a mesma renderização que o backend usa;
  - a configuração padrão e as rotas da API que o dashboard consome.

Contrato da API (backend, já implementado):
  GET/PUT /mixfoco/sac/automacoes/agradecimento
      {"ativo": bool, "dry_run": bool, "janela_dias": int, "template": str,
       "palavras_bloqueio": [str], "loja": str}
  GET     /mixfoco/sac/automacoes/agradecimento/log?de=YYYY-MM-DD&ate=YYYY-MM-DD
      {"eventos": [{"data": str, "pedido": str, "loja": str, "momento": str,
                    "texto_recebido": str, "classe": str, "motivo": str,
                    "respondido": bool, "dry_run": bool, "resposta": str}]}
"""
from __future__ import annotations

ROTA_CONFIG = "/mixfoco/sac/automacoes/agradecimento"
ROTA_LOG = f"{ROTA_CONFIG}/log"

TEMPLATE_PADRAO = (
    "De nada, {primeiro_nome}! 💜 Fico feliz em ajudar.\n"
    "Assim que o pedido chegar, se precisar de qualquer coisa é só me chamar por aqui.\n"
    "Boas compras! — Gabriela · Equipe {loja}"
)

CONFIG_PADRAO = {
    "ativo": False,
    "dry_run": True,
    "janela_dias": 15,
    "template": TEMPLATE_PADRAO,
    "palavras_bloqueio": [],
    "loja": "",          # vazio = assina com a loja do pedido
}

# ── Espelho de agradecer_positivo._e_fecho (backend) ──────────────────────────
# Um fecho é CURTO: "Obrigada!" tem 9 caracteres; uma reclamação educada tem 600.
MAX_CARACTERES_DE_FECHO = 120

# Marcas de positivo. "Ok" sozinho NÃO está aqui de propósito: é acuso de
# recebimento, não gratidão — responder "de nada" a um "ok" soa automático.
PALAVRAS_POSITIVAS = (
    "obrigad", "obg", "valeu", "vlw", "agradeç", "agradec",
    "perfeito", "ótimo", "otimo", "excelente", "maravilh", "show",
    "tudo certo", "tudo bem", "deu certo", "resolvido", "resolveu",
    "adorei", "amei", "top",
)

# Basta UMA destas para não responder, mesmo com "obrigado" junto.
PALAVRAS_BLOQUEIO = (
    "não", "nao", "ainda", "mas ", "porém", "porem", "problema", "defeito",
    "quebrad", "errad", "falta", "atras", "demor", "cancel", "reembols",
    "devolv", "troca", "estorno", "reclama", "procon", "processo",
)


def classificar_agradecimento(texto: str, palavras_bloqueio_extra=()) -> dict:
    """O que o backend faria com esta mensagem do comprador.

    Retorna {"classe": "agradecimento" | "outro", "motivo": str, "auto_responder": bool}.
    Só "agradecimento" dispara a resposta; as outras portas do backend (última fala é
    do cliente, uma resposta por pedido, aviso de envio na conversa, janela, assunto
    sensível, pedido não entregue) não dependem do texto e não são simuladas aqui.
    """
    t = (texto or "").strip()
    if not t:
        return _res("outro", "mensagem vazia")
    if len(t) > MAX_CARACTERES_DE_FECHO:
        return _res("outro", f"longa demais para ser fecho ({len(t)} caracteres)")
    if "?" in t or "？" in t:
        return _res("outro", "tem pergunta — quer resposta, não agradecimento")

    baixo = t.lower()
    extras = [str(x).strip().lower() for x in (palavras_bloqueio_extra or []) if str(x).strip()]
    for n in list(PALAVRAS_BLOQUEIO) + extras:
        if n in baixo:
            return _res("outro", f"tem marca de insatisfação: '{n.strip()}'")
    if not any(p in baixo for p in PALAVRAS_POSITIVAS):
        return _res("outro", "sem marca de positivo")
    return _res("agradecimento", "fecho positivo")


def _res(classe: str, motivo: str) -> dict:
    return {"classe": classe, "motivo": motivo, "auto_responder": classe == "agradecimento"}


# ── Template (mesma renderização de agradecer_positivo.renderizar_enviado) ────

def primeiro_nome(nome_completo: str) -> str:
    partes = [p for p in (nome_completo or "").replace("—", " ").split() if p]
    return partes[0].capitalize() if partes else ""


def renderizar_template(template: str, nome_comprador: str = "", loja: str = "") -> str:
    """Sem nome, some a vírgula com o nome: "De nada!" em vez de "De nada, !"."""
    t = template or TEMPLATE_PADRAO
    nome = primeiro_nome(nome_comprador)
    if not nome:
        t = t.replace(", {primeiro_nome}", "").replace("{primeiro_nome}", "")
    return t.replace("{primeiro_nome}", nome).replace("{loja}", (loja or "").strip())


def config_com_padrao(cfg: dict | None) -> dict:
    """Preenche a configuração vinda da API com os padrões."""
    out = dict(CONFIG_PADRAO)
    for k, v in (cfg or {}).items():
        if v is not None:
            out[k] = v
    bloq = out.get("palavras_bloqueio") or []
    if isinstance(bloq, str):
        bloq = bloq.splitlines()
    out["palavras_bloqueio"] = [str(x).strip() for x in bloq if str(x).strip()]
    try:
        out["janela_dias"] = int(out.get("janela_dias") or CONFIG_PADRAO["janela_dias"])
    except (TypeError, ValueError):
        out["janela_dias"] = CONFIG_PADRAO["janela_dias"]
    return out
