"""Importação do mês (tela única com prévia), desfazer e reaplicar regras."""
from __future__ import annotations

from calendar import monthrange
from datetime import date

from flask import Blueprint, current_app, redirect, render_template, request, url_for

from .. import aviso, backup, ip
from ..db import get_db
from ..servicos import (ErroOperacao, confirmar_importacao, decisoes_do_form, desfazer_importacao,
                        lote_ativo, nomes_em_uso, previa, tarefas_periodo)
from ..textutil import MESES

bp = Blueprint("importar", __name__)


def _backup(motivo: str) -> None:
    cfg = current_app.config["CAL"]
    backup.criar(cfg.banco, cfg.pasta_backup, motivo, cfg.backups_manter)


def _nome_mes(mk: str | None) -> str:
    if not mk:
        return ""
    a, m = mk.split("-")
    return f"{MESES[int(m) - 1]} {a}"


def _contexto(texto: str, form=None) -> dict:
    form = form or {}
    conn = get_db()
    p = previa(conn, texto, decisoes_do_form(form) if form else None, bool(form.get("substituir")))
    return {"texto": texto, "p": p, "nome_mes": _nome_mes(p.mes_ref), "ver_originais": bool(form.get("ver")),
            "substituir": bool(form.get("substituir")), "nomes": nomes_em_uso(conn)}


@bp.get("/importar")
def tela():
    return render_template("importar.html", **_contexto(""))


@bp.post("/importar/previa")
def atualizar_previa():
    return render_template("_previa.html", **_contexto(request.form.get("texto", ""), request.form))


@bp.post("/importar/confirmar")
def confirmar():
    texto = request.form.get("texto", "")
    conn = get_db()
    try:
        p = previa(conn, texto, decisoes_do_form(request.form), bool(request.form.get("substituir")),
                   sugerir=False)
        if p.bloqueio:
            raise ErroOperacao(p.bloqueio)
        _backup("antes-importacao")
        lote_id, n, novas = confirmar_importacao(conn, texto, decisoes_do_form(request.form),
                                                 bool(request.form.get("substituir")), ip())
    except ErroOperacao as e:
        ctx = _contexto(texto, request.form)
        ctx["erro"] = str(e)
        return render_template("importar.html", **ctx), 400
    mk = p.mes_ref
    extra = f" · {novas} {'nome novo salvo' if novas == 1 else 'nomes novos salvos'}" if novas else ""
    aviso(f"{_nome_mes(mk).split()[0]} importado · {n} tarefas{extra}",
          {"url": url_for("importar.desfazer", lote_id=lote_id),
           "voltar": url_for("calendario.mes", mes=mk)})
    return redirect(url_for("calendario.mes", mes=mk))


@bp.post("/importar/<int:lote_id>/desfazer")
def desfazer(lote_id: int):
    try:
        _backup("antes-desfazer")
        mk = desfazer_importacao(get_db(), lote_id, ip())
        aviso("Importação desfeita")
        return redirect(url_for("calendario.mes", mes=mk))
    except ErroOperacao as e:
        aviso(str(e), tipo="erro")
        return redirect(url_for("calendario.mes"))


# --------------------------------------------------------------- reaplicar regras ao mês

def _dados_reaplicar(mk: str):
    conn = get_db()
    lote = lote_ativo(conn, mk)
    if lote is None or lote["origem"] == "manual" or not lote["texto_colado"]:
        return None
    # sem sugestões automáticas: nome sem regra continua sem regra
    p = previa(conn, lote["texto_colado"], {}, True, sugerir=False)
    a, m = (int(x) for x in mk.split("-"))
    atuais = tarefas_periodo(conn, date(a, m, 1), date(a, m, monthrange(a, m)[1]))
    novos = p.resultado.por_dia()
    dias = sorted(set(atuais) | set(novos))
    mudancas = []
    for d in dias:
        antes = [t.nome for t in atuais.get(d, [])]
        depois = [l.nome for l in novos.get(d, [])]
        if antes != depois:
            mudancas.append({"data": d, "antes": antes, "depois": depois})
    manuais = sum(1 for ts in atuais.values() for t in ts if t.manual)
    return {"lote": lote, "p": p, "mudancas": mudancas, "manuais": manuais}


@bp.get("/mes/<mk>/reaplicar")
def reaplicar_tela(mk: str):
    dados = _dados_reaplicar(mk)
    if dados is None:
        aviso("Este mês não tem importação para reaplicar.", tipo="erro")
        return redirect(url_for("calendario.mes", mes=mk))
    return render_template("reaplicar.html", mk=mk, nome_mes=_nome_mes(mk), **dados)


@bp.post("/mes/<mk>/reaplicar")
def reaplicar(mk: str):
    dados = _dados_reaplicar(mk)
    if dados is None:
        aviso("Este mês não tem importação para reaplicar.", tipo="erro")
        return redirect(url_for("calendario.mes", mes=mk))
    if dados["p"].resultado.pendentes:
        aviso("Há nomes sem regra neste mês. Importe o mês de novo para defini-los.", tipo="erro")
        return redirect(url_for("importar.reaplicar_tela", mk=mk))
    try:
        _backup("antes-reaplicar")
        lote_id, n, _ = confirmar_importacao(get_db(), dados["lote"]["texto_colado"], {}, True, ip(),
                                             origem="reaplicacao")
    except ErroOperacao as e:
        aviso(str(e), tipo="erro")
        return redirect(url_for("importar.reaplicar_tela", mk=mk))
    aviso(f"Regras reaplicadas · {n} tarefas", {"url": url_for("importar.desfazer", lote_id=lote_id),
                                                 "voltar": url_for("calendario.mes", mes=mk)})
    return redirect(url_for("calendario.mes", mes=mk))
