"""
sac_automacoes.py — Regras de automação do SAC usadas pelo dashboard.

Hoje contém a automação de **agradecimento pós-venda**: quando o comprador responde à
mensagem de pós-venda da Gabriela só com um agradecimento, o backend responde com um
template e encerra a conversa. Este módulo concentra:

  - o classificador `classificar_agradecimento(texto)` (regex, sem IA), que o dashboard usa
    no testador e que o backend deve reproduzir (ou importar) na ingestão de mensagens;
  - a renderização do template (`renderizar_template`);
  - a configuração padrão e as rotas da API que o dashboard consome.

Contrato da API (backend):
  GET/PUT /mixfoco/sac/automacoes/agradecimento
      {"ativo": bool, "dry_run": bool, "janela_dias": int, "template": str,
       "palavras_bloqueio": [str], "loja": str}
  GET     /mixfoco/sac/automacoes/agradecimento/log?de=YYYY-MM-DD&ate=YYYY-MM-DD
      {"eventos": [{"data": str, "pedido": str, "loja": str, "comprador": str,
                    "texto_recebido": str, "classe": str, "motivo": str,
                    "respondido": bool, "dry_run": bool, "resposta": str}]}
"""
from __future__ import annotations

import re
import unicodedata

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
    "loja": "SKYCONECTA",
}

# Limites de tamanho do texto limpo (sem emoji/pontuação)
LIMITE_CURTO = 80      # até aqui: agradecimento puro
LIMITE_LONGO = 200     # acima disso: nunca automatiza

PALAVRAS_POSITIVAS = [
    "obg", "obgd", "obrigad", "brigad", "valeu", "vlw", "ok", "okay", "okk", "blz", "beleza",
    "perfeito", "show", "top", "maravilha", "otimo", "otima", "certo", "combinado", "grat",
    "gratidao", "thanks", "thank", "legal", "bacana", "massa", "joia", "excelente",
]
EMOJIS_POSITIVOS = "👍❤💜💙💚🙏😊🥰😘👏🤝✅🙌😍"

PALAVRAS_BLOQUEIO = [
    "nao chegou", "nao recebi", "atras", "cade", "quebr", "defeit", "errad", "faltou", "falta",
    "troc", "devolu", "cancel", "reembols", "danific", "problem", "nao funciona", "nao liga",
    "nota fiscal", "garantia", "quando", "prazo", "ainda nao", "amass", "rasg", "vazando",
    "diferente", "outro produto", "reclama", "estorn", "extravi", "roubad", "sumiu",
]

# Palavras que podem acompanhar um agradecimento sem mudar o sentido.
PALAVRAS_NEUTRAS = {
    "de", "nada", "muito", "muita", "pela", "pelo", "por", "atencao", "bom", "boa", "dia", "tarde",
    "noite", "gabriela", "gariela", "equipe", "tudo", "ate", "mais", "logo", "entao", "ta", "ja",
    "sim", "e", "a", "o", "os", "as", "um", "uma", "meu", "minha", "amigo", "amiga", "querida",
    "querido", "deus", "abencoe", "retorno", "resposta", "informacao", "informacoes", "aviso",
    "mesmo", "demais", "voces", "voce", "vc", "vcs", "pessoal", "aguardo", "aguardando", "vou",
    "acompanhar", "fico", "no", "na", "em", "que", "com", "pra", "para", "chegar", "chegou",
    "recebido", "entendi", "certinho", "tranquilo", "otimo", "super", "bem", "ai", "aqui", "agora",
}

_RE_EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF☀-➿⭐⭕️‍❤]+"
)
_RE_PONTUACAO = re.compile(r"[^\w\s]", re.UNICODE)


def normalizar(texto: str) -> str:
    """minúsculas, sem acento, sem emoji/pontuação, espaços únicos."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = _RE_EMOJI.sub(" ", t.lower())
    t = _RE_PONTUACAO.sub(" ", t)
    return " ".join(t.split())


def _tem_positivo(texto_norm: str, texto_bruto: str) -> bool:
    if any(e in (texto_bruto or "") for e in EMOJIS_POSITIVOS):
        return True
    palavras = texto_norm.split()
    return any(p.startswith(pos) for p in palavras for pos in PALAVRAS_POSITIVAS)


def _bloqueio_encontrado(texto_norm: str, extras=()) -> str | None:
    for b in list(PALAVRAS_BLOQUEIO) + [normalizar(x) for x in (extras or []) if x]:
        if b and b in texto_norm:
            return b
    return None


def _palavras_restantes(texto_norm: str) -> list[str]:
    restantes = []
    for p in texto_norm.split():
        if p in PALAVRAS_NEUTRAS or any(p.startswith(pos) for pos in PALAVRAS_POSITIVAS):
            continue
        if p.isdigit() or len(p) <= 1:
            continue
        restantes.append(p)
    return restantes


def classificar_agradecimento(texto: str, palavras_bloqueio_extra=()) -> dict:
    """Classifica a resposta do comprador ao pós-venda.

    Retorna {"classe": "agradecimento" | "ambiguo" | "outro", "motivo": str,
             "auto_responder": bool}.
    Só "agradecimento" dispara a resposta automática. "ambiguo" deve ser decidido
    pela IA no backend; "outro" nunca automatiza.
    """
    bruto = (texto or "").strip()
    if not bruto:
        return _res("outro", "mensagem vazia")
    if "?" in bruto or "？" in bruto:
        return _res("outro", "contém pergunta")

    norm = normalizar(bruto)
    bloqueio = _bloqueio_encontrado(norm, palavras_bloqueio_extra)
    if bloqueio:
        return _res("outro", f"palavra de bloqueio: '{bloqueio}'")

    if len(norm) > LIMITE_LONGO:
        return _res("outro", f"texto longo ({len(norm)} caracteres)")

    if not _tem_positivo(norm, bruto):
        return _res("outro", "sem palavra de agradecimento")

    restantes = _palavras_restantes(norm)
    if len(restantes) > 3:
        return _res("ambiguo", f"agradecimento misturado com outro assunto: {' '.join(restantes[:6])}")
    if len(norm) > LIMITE_CURTO:
        return _res("ambiguo", f"agradecimento em texto médio ({len(norm)} caracteres)")

    return _res("agradecimento", "agradecimento puro")


def _res(classe: str, motivo: str) -> dict:
    return {"classe": classe, "motivo": motivo, "auto_responder": classe == "agradecimento"}


# ── Template ───────────────────────────────────────────────────────────────────

class _Seguro(dict):
    def __missing__(self, k):
        return "{" + k + "}"


def primeiro_nome(nome_completo: str) -> str:
    partes = [p for p in (nome_completo or "").strip().split() if p]
    if not partes:
        return "tudo bem"
    return partes[0].capitalize()


def renderizar_template(template: str, nome_comprador: str = "", loja: str = "") -> str:
    return (template or "").format_map(
        _Seguro(primeiro_nome=primeiro_nome(nome_comprador), loja=(loja or "").strip())
    )


def config_com_padrao(cfg: dict | None) -> dict:
    """Preenche a configuração vinda da API com os padrões."""
    out = dict(CONFIG_PADRAO)
    for k, v in (cfg or {}).items():
        if v is not None:
            out[k] = v
    out["palavras_bloqueio"] = [str(x).strip() for x in (out.get("palavras_bloqueio") or []) if str(x).strip()]
    try:
        out["janela_dias"] = int(out.get("janela_dias") or CONFIG_PADRAO["janela_dias"])
    except (TypeError, ValueError):
        out["janela_dias"] = CONFIG_PADRAO["janela_dias"]
    return out
