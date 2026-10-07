"""Configurações: backups e histórico de alterações."""
from __future__ import annotations

from flask import Blueprint, abort, current_app, redirect, render_template, request, send_file, url_for

from .. import aviso, backup, ip, preparar_banco
from ..db import fechar_db, get_db, registrar_log
from ..servicos import log_recente, transacao

bp = Blueprint("config", __name__)


def _achar(nome: str):
    cfg = current_app.config["CAL"]
    for info in backup.listar(cfg.pasta_backup):
        if info.arquivo.name == nome:
            return info
    abort(404)


@bp.get("/backups")
def backups():
    cfg = current_app.config["CAL"]
    return render_template("backups.html", itens=backup.listar(cfg.pasta_backup), cfg=cfg,
                           confirmar=request.args.get("restaurar"))


@bp.post("/backups/criar")
def criar():
    cfg = current_app.config["CAL"]
    backup.criar(cfg.banco, cfg.pasta_backup, "manual", cfg.backups_manter)
    conn = get_db()
    with transacao(conn):
        registrar_log(conn, ip(), "backup criado", "manual")
    aviso("Backup criado")
    return redirect(url_for("config.backups"))


@bp.get("/backups/<nome>/baixar")
def baixar(nome: str):
    info = _achar(nome)
    return send_file(info.arquivo, as_attachment=True, download_name=info.arquivo.name)


@bp.post("/backups/<nome>/restaurar")
def restaurar(nome: str):
    info = _achar(nome)
    if not request.form.get("confirmo"):
        aviso("Marque a confirmação para restaurar.", tipo="erro")
        return redirect(url_for("config.backups", restaurar=nome))
    cfg = current_app.config["CAL"]
    backup.criar(cfg.banco, cfg.pasta_backup, "antes-restaurar", cfg.backups_manter + 1)
    fechar_db()
    backup.restaurar(info.arquivo, cfg.banco)
    preparar_banco(cfg)   # o backup pode ser de uma versão anterior do banco
    conn = get_db()
    with transacao(conn):
        registrar_log(conn, ip(), "backup restaurado", info.arquivo.name)
    aviso(f"Backup de {info.quando.strftime('%d/%m/%Y %H:%M')} restaurado. "
          "O estado anterior foi salvo como backup “antes restaurar”.")
    return redirect(url_for("calendario.mes"))


@bp.get("/historico")
def historico():
    return render_template("historico.html", itens=log_recente(get_db()))
