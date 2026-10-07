"""Calendário mensal, painel do dia e edição avulsa de tarefas."""
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from flask import Blueprint, current_app, redirect, render_template, request, url_for

from .. import aviso, ip
from ..db import get_db
from ..feriados import feriados
from ..servicos import (ErroOperacao, adicionar_tarefa, lote_ativo, nomes_em_uso, remover_tarefa,
                        renomear_tarefa, restaurar_tarefa, tarefas_periodo)
from ..textutil import DIAS_CURTOS, DIAS_SEMANA

bp = Blueprint("calendario", __name__)


def _mes(valor: str | None) -> tuple[int, int]:
    try:
        a, m = (int(x) for x in (valor or "").split("-")[:2])
        if 1 <= m <= 12 and 2000 <= a <= 2100:
            return a, m
    except ValueError:
        pass
    h = date.today()
    return h.year, h.month


def _data(valor: str | None) -> date | None:
    try:
        return date.fromisoformat(valor or "")
    except ValueError:
        return None


def _voltar(padrao: str) -> str:
    v = request.form.get("voltar") or request.args.get("voltar") or ""
    return v if v.startswith("/") and not v.startswith("//") else padrao


@bp.get("/")
def mes():
    cfg = current_app.config["CAL"]
    ano, m = _mes(request.args.get("mes"))
    primeiro = date(ano, m, 1)
    ultimo = date(ano, m, monthrange(ano, m)[1])
    inicio_semana = 0 if cfg.semana_comeca == "segunda" else 6   # weekday(): seg=0 ... dom=6
    recuo = (primeiro.weekday() - inicio_semana) % 7
    ini = primeiro - timedelta(days=recuo)
    semanas = -(-((ultimo - ini).days + 1) // 7)
    fim = ini + timedelta(days=semanas * 7 - 1)

    conn = get_db()
    dias_tarefas = tarefas_periodo(conn, primeiro, ultimo)
    fer = {}
    for a in {ini.year, fim.year}:
        fer.update(feriados(a, cfg.feriados_extras))

    grade = []
    for s in range(semanas):
        semana = []
        for i in range(7):
            d = ini + timedelta(days=s * 7 + i)
            semana.append({
                "data": d,
                "fora": d.month != m,
                "fim_semana": d.weekday() >= 5,
                "feriado": fer.get(d),
                "tarefas": dias_tarefas.get(d, []) if d.month == m else [],
            })
        grade.append(semana)
    cabecalho = [DIAS_CURTOS[(inicio_semana + i) % 7] for i in range(7)]

    total = sum(len(v) for v in dias_tarefas.values())
    mk = f"{ano:04d}-{m:02d}"
    anterior = (primeiro - timedelta(days=1)).strftime("%Y-%m")
    proximo = (ultimo + timedelta(days=1)).strftime("%Y-%m")

    sel = _data(request.args.get("dia"))
    painel = None
    if sel and sel.year == ano and sel.month == m:
        painel = {
            "data": sel,
            "dia_semana": DIAS_SEMANA[sel.weekday()],
            "feriado": fer.get(sel),
            "tarefas": dias_tarefas.get(sel, []),
            "editar": request.args.get("editar", type=int),
            "nomes": nomes_em_uso(conn),
        }
    lote = lote_ativo(conn, mk)
    return render_template(
        "calendario.html", ano=ano, mes_num=m, mk=mk, grade=grade, cabecalho=cabecalho,
        semana_comeca=cfg.semana_comeca, total=total, anterior=anterior, proximo=proximo,
        painel=painel, pode_reaplicar=bool(lote and lote["origem"] != "manual"),
        url_atual=request.full_path.rstrip("?"))


def _volta_dia(d: date) -> str:
    return url_for("calendario.mes", mes=d.strftime("%Y-%m"), dia=d.isoformat())


@bp.post("/tarefa/adicionar")
def adicionar():
    d = _data(request.form.get("data"))
    if d is None:
        aviso("Data inválida.", tipo="erro")
        return redirect(url_for("calendario.mes"))
    try:
        tid = adicionar_tarefa(get_db(), d, request.form.get("nome", ""), ip())
        nome = request.form.get("nome", "").strip().upper()
        aviso(f"{nome} adicionada", {"url": url_for("calendario.remover", tarefa_id=tid),
                                     "voltar": _volta_dia(d)})
    except ErroOperacao as e:
        aviso(str(e), tipo="erro")
    return redirect(_volta_dia(d))


@bp.post("/tarefa/<int:tarefa_id>/renomear")
def renomear(tarefa_id: int):
    voltar = _voltar(url_for("calendario.mes"))
    try:
        antigo, novo = renomear_tarefa(get_db(), tarefa_id, request.form.get("nome", ""), ip())
        if antigo != novo:
            aviso(f"Renomeada para {novo}", {"url": url_for("calendario.renomear", tarefa_id=tarefa_id),
                                             "campos": {"nome": antigo}, "voltar": voltar})
    except ErroOperacao as e:
        aviso(str(e), tipo="erro")
    return redirect(voltar)


@bp.post("/tarefa/<int:tarefa_id>/remover")
def remover(tarefa_id: int):
    voltar = _voltar(url_for("calendario.mes"))
    try:
        nome = remover_tarefa(get_db(), tarefa_id, ip())
        aviso(f"{nome} removida", {"url": url_for("calendario.restaurar", tarefa_id=tarefa_id),
                                   "voltar": voltar})
    except ErroOperacao as e:
        aviso(str(e), tipo="erro")
    return redirect(voltar)


@bp.post("/tarefa/<int:tarefa_id>/restaurar")
def restaurar(tarefa_id: int):
    voltar = _voltar(url_for("calendario.mes"))
    try:
        nome = restaurar_tarefa(get_db(), tarefa_id, ip())
        aviso(f"{nome} de volta ao calendário")
    except ErroOperacao as e:
        aviso(str(e), tipo="erro")
    return redirect(voltar)
