"""Conexão SQLite (modo WAL) e migrações versionadas."""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import current_app, g

PASTA_MIGRACOES = Path(__file__).resolve().parent.parent / "migrations"


class BancoMaisNovoError(RuntimeError):
    """O banco foi criado por uma versão mais nova do código."""


def agora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def conectar(caminho: Path) -> sqlite3.Connection:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(caminho, timeout=10, isolation_level=None)  # autocommit; transações explícitas
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def migracoes_disponiveis() -> list[tuple[int, Path]]:
    itens = []
    for p in sorted(PASTA_MIGRACOES.glob("*.sql")):
        m = re.match(r"(\d+)_", p.name)
        if m:
            itens.append((int(m.group(1)), p))
    return itens


def versao_atual(conn: sqlite3.Connection) -> int:
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (versao INTEGER NOT NULL)")
    row = conn.execute("SELECT MAX(versao) AS v FROM schema_version").fetchone()
    return row["v"] or 0


def migracoes_pendentes(conn: sqlite3.Connection) -> list[tuple[int, Path]]:
    atual = versao_atual(conn)
    disponiveis = migracoes_disponiveis()
    maior = disponiveis[-1][0] if disponiveis else 0
    if atual > maior:
        raise BancoMaisNovoError(
            f"O banco está na versão {atual}, mas este código só conhece até a {maior}. "
            "Atualize o código (git pull) antes de abrir o sistema."
        )
    return [(n, p) for n, p in disponiveis if n > atual]


def migrar(conn: sqlite3.Connection) -> list[int]:
    aplicadas = []
    for numero, caminho in migracoes_pendentes(conn):
        sql = caminho.read_text(encoding="utf-8")
        conn.execute("BEGIN")
        try:
            for comando in [c for c in sql.split(";") if c.strip()]:
                conn.execute(comando)
            conn.execute("INSERT INTO schema_version (versao) VALUES (?)", (numero,))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        aplicadas.append(numero)
    return aplicadas


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = conectar(current_app.config["CAL"].banco)
    return g.db


def fechar_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def registrar_log(conn: sqlite3.Connection, ip: str, acao: str, detalhe: str = "") -> None:
    conn.execute(
        "INSERT INTO log (quando, ip, acao, detalhe) VALUES (?, ?, ?, ?)",
        (agora(), ip or "", acao, detalhe),
    )
