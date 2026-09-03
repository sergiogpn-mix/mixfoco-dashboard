"""
kb_import.py — Importa a base de conhecimento da Gabriela na API do Mixfoco.

Fonte: arquivos JSON em ml-ia/kb/ (ex.: ml-ia/kb/gabriela_kb_2026-09-03.json).
Destino: rota /mixfoco/sac/kb da API (a mesma usada pela aba SAC do dashboard).

Regras:
  - Só entradas com status "pronta" são gravadas. "falta_dado" e "politica"
    ficam apenas no relatório de pendências.
  - O campo "conteudo" segue a convenção "P: <pergunta>\\nR: <resposta>" e é
    dividido em titulo (pergunta) e resposta.
  - A importação é idempotente: a chave é o titulo gerado
    "[<item_id>] <titulo_produto> — <pergunta>". Se já existir, atualiza
    (PUT); se o conteúdo for igual, pula; senão cria (POST).

Uso (linha de comando):
  python kb_import.py ml-ia/kb/gabriela_kb_2026-09-03.json --dry-run
  python kb_import.py ml-ia/kb/gabriela_kb_2026-09-03.json
  python kb_import.py ml-ia/kb/gabriela_kb_2026-09-03.json --report > ml-ia/kb/PENDENCIAS.md

A URL da API vem de MIXFOCO_API_URL (ou --api-url).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Callable

KB_PATH = "/mixfoco/sac/kb"
STATUS_IMPORTAVEL = {"pronta"}
TAGS_IGNORADAS = {"curado"}
CATEGORIA_PADRAO = "produto"
CAMPOS_BASE = ("titulo", "categoria", "marketplace", "resposta", "ativo")

ApiFn = Callable[..., tuple[Any, str | None]]


# ── Parsing ────────────────────────────────────────────────────────────────────

def parse_conteudo(conteudo: str) -> tuple[str, str]:
    """Divide "P: pergunta\\nR: resposta" em (pergunta, resposta)."""
    texto = (conteudo or "").strip()
    if not texto.startswith("P:"):
        raise ValueError("conteudo deve começar com 'P:'")
    marcador = "\nR:"
    pos = texto.find(marcador)
    if pos < 0:
        raise ValueError("conteudo não tem a linha 'R:'")
    pergunta = texto[2:pos].strip()
    resposta = texto[pos + len(marcador):].strip()
    if not pergunta or not resposta:
        raise ValueError("pergunta ou resposta vazia")
    return pergunta, resposta


def titulo_entrada(entry: dict, pergunta: str) -> str:
    item_id = (entry.get("item_id") or "").strip()
    produto = (entry.get("titulo_produto") or "").strip()
    partes = []
    if item_id:
        partes.append(f"[{item_id}]")
    if produto:
        partes.append(produto)
    prefixo = " ".join(partes)
    return f"{prefixo} — {pergunta}" if prefixo else pergunta


def categoria_entrada(entry: dict) -> str:
    for tag in entry.get("tags") or []:
        if tag and tag not in TAGS_IGNORADAS:
            return tag
    return CATEGORIA_PADRAO


def entry_to_payload(entry: dict, marketplace: str | None = None) -> dict:
    pergunta, resposta = parse_conteudo(entry.get("conteudo", ""))
    return {
        "titulo": titulo_entrada(entry, pergunta),
        "categoria": categoria_entrada(entry),
        "marketplace": marketplace or None,
        "resposta": resposta,
        "ativo": True,
        # Campos extras (o backend pode ignorá-los; se rejeitar, o upsert
        # reenvia só os campos base).
        "item_id": entry.get("item_id"),
        "titulo_produto": entry.get("titulo_produto"),
        "pergunta": pergunta,
        "tags": list(entry.get("tags") or []),
        "fonte": entry.get("fonte"),
        "status": entry.get("status"),
    }


def build_payloads(base: dict, marketplace: str | None = None) -> tuple[list[dict], list[dict]]:
    """Retorna (payloads importáveis, entradas puladas com motivo)."""
    payloads: list[dict] = []
    pulados: list[dict] = []
    for i, entry in enumerate(base.get("entradas") or []):
        status = entry.get("status")
        if status not in STATUS_IMPORTAVEL:
            pulados.append({"indice": i, "item_id": entry.get("item_id"), "motivo": f"status={status}"})
            continue
        try:
            payloads.append(entry_to_payload(entry, marketplace))
        except ValueError as e:
            pulados.append({"indice": i, "item_id": entry.get("item_id"), "motivo": str(e)})
    return payloads, pulados


# ── Upsert ─────────────────────────────────────────────────────────────────────

def _norm(s: Any) -> str:
    return " ".join(str(s or "").split()).casefold()


def extract_entries(data: Any) -> list[dict]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("entries", "items", "data", "results"):
            if isinstance(data.get(k), list):
                return data[k]
    return []


def _entry_id(e: dict) -> Any:
    return e.get("id") or e.get("entry_id")


def index_existing(entries: list[dict]) -> dict[str, dict]:
    idx: dict[str, dict] = {}
    for e in entries:
        titulo = e.get("titulo") or e.get("pergunta")
        if titulo:
            idx.setdefault(_norm(titulo), e)
    return idx


def _mesmo_conteudo(existente: dict, payload: dict) -> bool:
    return (
        _norm(existente.get("resposta", existente.get("conteudo"))) == _norm(payload["resposta"])
        and _norm(existente.get("categoria")) == _norm(payload["categoria"])
        and _norm(existente.get("marketplace")) == _norm(payload["marketplace"])
        and bool(existente.get("ativo", True)) == bool(payload["ativo"])
    )


def _enviar(api: ApiFn, method: str, path: str, payload: dict) -> tuple[Any, str | None]:
    data, err = api(method, path, json=payload)
    if err and "422" in err:
        # Backend estrito: reenvia só os campos que o dashboard já usa.
        base = {k: payload[k] for k in CAMPOS_BASE}
        data, err = api(method, path, json=base)
    return data, err


def upsert_entries(api: ApiFn, payloads: list[dict], dry_run: bool = False) -> dict:
    """Cria/atualiza as entradas na API. Retorna um resumo com as ações."""
    resumo = {"criadas": [], "atualizadas": [], "iguais": [], "erros": [], "dry_run": dry_run}

    data, err = api("GET", KB_PATH)
    if err:
        resumo["erros"].append({"titulo": "(listagem)", "erro": err})
        return resumo
    existentes = index_existing(extract_entries(data))

    for p in payloads:
        chave = _norm(p["titulo"])
        atual = existentes.get(chave)
        if atual is not None:
            if _mesmo_conteudo(atual, p):
                resumo["iguais"].append(p["titulo"])
                continue
            eid = _entry_id(atual)
            if dry_run:
                resumo["atualizadas"].append(p["titulo"])
                continue
            _, err = _enviar(api, "PUT", f"{KB_PATH}/{eid}", p)
            (resumo["erros"].append({"titulo": p["titulo"], "erro": err}) if err
             else resumo["atualizadas"].append(p["titulo"]))
        else:
            if dry_run:
                resumo["criadas"].append(p["titulo"])
                continue
            _, err = _enviar(api, "POST", KB_PATH, p)
            (resumo["erros"].append({"titulo": p["titulo"], "erro": err}) if err
             else resumo["criadas"].append(p["titulo"]))
    return resumo


def resumo_texto(resumo: dict, pulados: list[dict] | None = None) -> str:
    linhas = [
        f"{'[DRY RUN] ' if resumo.get('dry_run') else ''}"
        f"criadas={len(resumo['criadas'])} atualizadas={len(resumo['atualizadas'])} "
        f"iguais={len(resumo['iguais'])} erros={len(resumo['erros'])} puladas={len(pulados or [])}"
    ]
    for e in resumo["erros"]:
        linhas.append(f"  ERRO {e['titulo']}: {e['erro']}")
    for p in pulados or []:
        linhas.append(f"  PULADA #{p['indice']} {p.get('item_id') or ''}: {p['motivo']}")
    return "\n".join(linhas)


# ── Relatório de pendências ───────────────────────────────────────────────────

def report_markdown(base: dict) -> str:
    payloads, pulados = build_payloads(base)
    produtos = sorted({p["item_id"] for p in payloads if p.get("item_id")})
    out = [
        f"# Gabriela — Pendências da base de conhecimento ({base.get('gerado_em', '')})",
        "",
        f"Fonte: `{base.get('base', '')}`.",
        "",
        "## Resumo",
        "",
        f"- Entradas prontas para gravar: **{len(payloads)}** em {len(produtos)} anúncios.",
        f"- Entradas puladas (sem status `pronta` ou formato inválido): **{len(pulados)}**.",
        f"- Pendências que dependem de dado ou política: **{len(base.get('pendencias') or [])}**.",
        f"- Correções de ficha no Mercado Livre: **{len(base.get('correcoes_de_anuncio') or [])}**.",
        "",
        "## Pendências (dado ou política a definir)",
        "",
        "| Prio | Tema | Anúncios | Pergunta a responder | Por quê |",
        "|---|---|---|---|---|",
    ]
    for p in sorted(base.get("pendencias") or [], key=lambda x: x.get("prio", "")):
        itens = ", ".join(p.get("itens") or [])
        out.append(
            f"| {p.get('prio', '')} | {p.get('tema', '')} | {itens} | "
            f"{_md(p.get('pergunta'))} | {_md(p.get('porque'))} |"
        )
    out += [
        "",
        "## Correções de anúncio (ficha técnica no ML)",
        "",
        "| Anúncio | Campo | Problema | Efeito na Gabriela |",
        "|---|---|---|---|",
    ]
    for c in base.get("correcoes_de_anuncio") or []:
        out.append(
            f"| {c.get('item_id', '')} | {c.get('campo', '')} | {_md(c.get('problema'))} | {_md(c.get('efeito'))} |"
        )
    out += ["", "## Entradas prontas (gravadas pelo `kb_import.py`)", ""]
    for p in payloads:
        out.append(f"- `{p['categoria']}` · {p['titulo']}")
    out.append("")
    return "\n".join(out)


def _md(s: Any) -> str:
    return str(s or "").replace("|", "\\|").replace("\n", " ")


# ── CLI ────────────────────────────────────────────────────────────────────────

def make_api(api_url: str, timeout: int = 20) -> ApiFn:
    import requests

    def api(method: str, path: str, **kwargs):
        try:
            r = requests.request(method, f"{api_url}{path}", timeout=timeout, **kwargs)
            r.raise_for_status()
            return (r.json() if r.content else {}), None
        except Exception as e:  # noqa: BLE001
            return None, str(e)

    return api


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Importa a base da Gabriela (ml-ia/kb) na API do Mixfoco.")
    ap.add_argument("arquivo", help="JSON da base (ex.: ml-ia/kb/gabriela_kb_2026-09-03.json)")
    ap.add_argument("--api-url", default=os.getenv("MIXFOCO_API_URL", "https://railway-up-production-1df7.up.railway.app"))
    ap.add_argument("--marketplace", default=None, help="Marketplace das entradas (vazio = todos)")
    ap.add_argument("--dry-run", action="store_true", help="Só mostra o que seria criado/atualizado")
    ap.add_argument("--report", action="store_true", help="Imprime o relatório de pendências em Markdown e sai")
    args = ap.parse_args(argv)

    with open(args.arquivo, encoding="utf-8") as f:
        base = json.load(f)

    if args.report:
        sys.stdout.write(report_markdown(base))
        return 0

    payloads, pulados = build_payloads(base, args.marketplace)
    resumo = upsert_entries(make_api(args.api_url), payloads, dry_run=args.dry_run)
    print(resumo_texto(resumo, pulados))
    return 1 if resumo["erros"] else 0


if __name__ == "__main__":
    sys.exit(main())
