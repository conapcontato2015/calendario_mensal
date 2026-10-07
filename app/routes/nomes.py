"""Dicionário de nomes: lista, teste, criar/editar, desativar, exportar/importar."""
from __future__ import annotations

import json
from datetime import date

from flask import Blueprint, Response, current_app, redirect, render_template, request, url_for

from .. import aviso, backup, ip
from ..db import get_db
from ..servicos import (ErroOperacao, alternar_regra, carregar_regras, exportar_regras, importar_regras,
                        salvar_regra, testar_nome, transacao, uso_regras)
from ..textutil import chave

bp = Blueprint("nomes", __name__)

FILTROS = [("todas", "Todas"), ("prefixo", "Tudo que começa com…"), ("ignorar", "Ignoradas"),
           ("sem-uso", "Sem uso"), ("inativas", "Desativadas")]


@bp.get("/nomes")
def lista():
    conn = get_db()
    q = request.args.get("q", "")
    f = request.args.get("f", "todas")
    teste = request.args.get("teste", "")
    regras = carregar_regras(conn)
    uso = uso_regras(conn)
    k = chave(q)
    if k:
        regras = [r for r in regras if k in r.padrao or k in chave(r.nome_curto)]
    if f == "prefixo":
        regras = [r for r in regras if r.tipo != "exata"]
    elif f == "ignorar":
        regras = [r for r in regras if r.acao == "ignorar"]
    elif f == "sem-uso":
        regras = [r for r in regras if r.id not in uso and r.ativa]
    elif f == "inativas":
        regras = [r for r in regras if not r.ativa]
    regras.sort(key=lambda r: (not r.ativa, r.tipo == "exata", r.padrao))
    regra_teste, erro_teste = testar_nome(conn, teste) if teste else (None, "")
    editar_id = request.args.get("editar", type=int)
    editar = next((r for r in carregar_regras(conn) if r.id == editar_id), None) if editar_id else None
    usos_editar = uso.get(editar_id, {}).get("usos", 0) if editar_id else 0
    total = conn.execute("SELECT COUNT(*) FROM regras").fetchone()[0]
    return render_template("nomes.html", regras=regras, uso=uso, q=q, f=f, filtros=FILTROS, teste=teste,
                           regra_teste=regra_teste, erro_teste=erro_teste, editar=editar,
                           nova=request.args.get("nova") == "1", usos_editar=usos_editar, total=total,
                           date=date)


@bp.post("/nomes/salvar")
def salvar():
    conn = get_db()
    regra_id = request.form.get("id", type=int)
    try:
        avisos = salvar_regra(conn, ip(), regra_id=regra_id, tipo=request.form.get("tipo", "exata"),
                              padrao=request.form.get("padrao", ""), acao=request.form.get("acao", "renomear"),
                              nome=request.form.get("nome", ""),
                              aplicar_existentes=bool(request.form.get("aplicar_existentes")))
    except ErroOperacao as e:
        aviso(str(e), tipo="erro")
        destino = {"editar": regra_id} if regra_id else {"nova": 1}
        return redirect(url_for("nomes.lista", **destino))
    aviso("Regra salva")
    for a in avisos:
        aviso(a, tipo="alerta")
    return redirect(url_for("nomes.lista", q=request.form.get("q", "")))


@bp.post("/nomes/<int:regra_id>/alternar")
def alternar(regra_id: int):
    voltar = request.form.get("voltar") or url_for("nomes.lista")
    if not voltar.startswith("/") or voltar.startswith("//"):
        voltar = url_for("nomes.lista")
    try:
        ativa = alternar_regra(get_db(), regra_id, ip())
        aviso("Regra reativada" if ativa else "Regra desativada",
              {"url": url_for("nomes.alternar", regra_id=regra_id), "voltar": voltar})
    except ErroOperacao as e:
        aviso(str(e), tipo="erro")
    return redirect(voltar)


@bp.get("/nomes/exportar")
def exportar():
    dados = json.dumps(exportar_regras(get_db()), ensure_ascii=False, indent=2)
    nome = f"regras-calendario-{date.today().isoformat()}.json"
    return Response(dados, mimetype="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


@bp.post("/nomes/importar")
def importar():
    arq = request.files.get("arquivo")
    if not arq or not arq.filename:
        aviso("Escolha o arquivo .json exportado antes.", tipo="erro")
        return redirect(url_for("nomes.lista"))
    try:
        itens = json.loads(arq.read().decode("utf-8-sig"))
        if not isinstance(itens, list):
            raise ValueError
    except (ValueError, UnicodeDecodeError):
        aviso("Arquivo inválido. Use um .json exportado por este sistema.", tipo="erro")
        return redirect(url_for("nomes.lista"))
    cfg = current_app.config["CAL"]
    backup.criar(cfg.banco, cfg.pasta_backup, "antes-importar-regras", cfg.backups_manter)
    conn = get_db()
    with transacao(conn):
        n = importar_regras(conn, itens, ip())
    aviso(f"{n} regras novas adicionadas" if n else "Nenhuma regra nova: todas já existiam.")
    return redirect(url_for("nomes.lista"))
