"""Backups do banco SQLite com rotação."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

PADRAO = re.compile(r"^calendario_(\d{8}-\d{6})_([a-z0-9-]+)\.db$")


@dataclass
class InfoBackup:
    arquivo: Path
    quando: datetime
    motivo: str
    tamanho_kb: int


def _slug(motivo: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", motivo.lower()).strip("-")
    return s[:40] or "manual"


def criar(banco: Path, pasta: Path, motivo: str, manter: int = 30) -> Path | None:
    """Copia o banco de forma consistente (API de backup do SQLite). Retorna o arquivo criado."""
    if not banco.exists():
        return None
    pasta.mkdir(parents=True, exist_ok=True)
    carimbo = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = _slug(motivo)
    destino = pasta / f"calendario_{carimbo}_{base}.db"
    n = 1
    while destino.exists():
        n += 1
        destino = pasta / f"calendario_{carimbo}_{base}-{n}.db"
    origem = sqlite3.connect(banco)
    try:
        alvo = sqlite3.connect(destino)
        try:
            origem.backup(alvo)
        finally:
            alvo.close()
    finally:
        origem.close()
    rotacionar(pasta, manter)
    return destino


def listar(pasta: Path) -> list[InfoBackup]:
    if not pasta.exists():
        return []
    itens = []
    for p in pasta.glob("calendario_*.db"):
        m = PADRAO.match(p.name)
        if not m:
            continue
        itens.append(InfoBackup(
            arquivo=p,
            quando=datetime.strptime(m.group(1), "%Y%m%d-%H%M%S"),
            motivo=m.group(2).replace("-", " "),
            tamanho_kb=max(1, p.stat().st_size // 1024),
        ))
    return sorted(itens, key=lambda i: (i.quando, i.arquivo.name), reverse=True)


def rotacionar(pasta: Path, manter: int) -> None:
    for info in listar(pasta)[manter:]:
        try:
            info.arquivo.unlink()
        except OSError:
            pass


def restaurar(arquivo: Path, banco: Path) -> None:
    """Sobrescreve o banco atual com o conteúdo do backup (o chamador faz backup antes)."""
    origem = sqlite3.connect(arquivo)
    try:
        alvo = sqlite3.connect(banco)
        try:
            origem.backup(alvo)
        finally:
            alvo.close()
    finally:
        origem.close()
