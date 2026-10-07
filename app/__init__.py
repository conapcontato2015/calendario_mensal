"""Calendário de Tarefas — fábrica da aplicação Flask."""
from __future__ import annotations

import secrets
from datetime import date

from flask import Flask, flash, request

from . import config as cfgmod
from .db import conectar, fechar_db, migrar
from .servicos import garantir_seed
from .textutil import DIAS_CURTOS, MESES

__version__ = "1.0.0"


def _segredo(cfg: cfgmod.Config) -> str:
    arq = cfg.pasta_dados / "chave_secreta.txt"
    if arq.exists():
        return arq.read_text(encoding="utf-8").strip()
    cfg.pasta_dados.mkdir(parents=True, exist_ok=True)
    s = secrets.token_hex(32)
    arq.write_text(s, encoding="utf-8")
    return s


def preparar_banco(cfg: cfgmod.Config) -> list[int]:
    """Aplica migrações pendentes e carrega as regras iniciais. Retorna migrações aplicadas."""
    conn = conectar(cfg.banco)
    try:
        aplicadas = migrar(conn)
        garantir_seed(conn)
        return aplicadas
    finally:
        conn.close()


def create_app(cfg: cfgmod.Config | None = None) -> Flask:
    cfg = cfg or cfgmod.carregar()
    app = Flask(__name__)
    app.config["CAL"] = cfg
    app.config["SECRET_KEY"] = _segredo(cfg)
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
    preparar_banco(cfg)

    app.teardown_appcontext(fechar_db)

    from .routes import calendario, config as rconfig, importar, nomes
    app.register_blueprint(calendario.bp)
    app.register_blueprint(importar.bp)
    app.register_blueprint(nomes.bp)
    app.register_blueprint(rconfig.bp)

    @app.context_processor
    def _globais():
        return {"MESES": MESES, "DIAS_CURTOS": DIAS_CURTOS, "hoje": date.today(), "versao": __version__}

    @app.template_filter("dm")
    def _dm(d):
        return d.strftime("%d/%m") if d else ""

    @app.template_filter("dmy")
    def _dmy(d):
        if isinstance(d, str):
            d = date.fromisoformat(d[:10])
        return d.strftime("%d/%m/%Y") if d else ""

    return app


def aviso(msg: str, desfazer: dict | None = None, tipo: str = "ok") -> None:
    """Mensagem curta no canto da tela, opcionalmente com botão Desfazer (POST)."""
    flash({"msg": msg, "desfazer": desfazer, "tipo": tipo})


def ip() -> str:
    return request.remote_addr or ""
