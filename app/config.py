"""Leitura de configuração: config.example.env (padrões) + .env (opcional)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _ler_env(caminho: Path) -> dict[str, str]:
    valores: dict[str, str] = {}
    if not caminho.exists():
        return valores
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valores[chave.strip()] = valor.strip()
    return valores


def _caminho(valor: str) -> Path:
    p = Path(valor).expanduser()
    return p if p.is_absolute() else (RAIZ / p)


@dataclass
class Config:
    porta: int = 5050
    pasta_dados: Path = field(default_factory=lambda: RAIZ / "dados")
    pasta_backup: Path = field(default_factory=lambda: RAIZ / "dados" / "backups")
    backups_manter: int = 30
    semana_comeca: str = "domingo"  # domingo | segunda
    abrir_navegador: bool = True
    feriados_extras: str = ""

    @property
    def banco(self) -> Path:
        return self.pasta_dados / "calendario.db"


def carregar(sobrescrever: dict[str, str] | None = None) -> Config:
    valores = _ler_env(RAIZ / "config.example.env")
    valores.update(_ler_env(RAIZ / ".env"))
    # variáveis de ambiente com prefixo CAL_ têm prioridade (úteis em testes)
    for k, v in os.environ.items():
        if k.startswith("CAL_"):
            valores[k[4:]] = v
    if sobrescrever:
        valores.update(sobrescrever)

    cfg = Config()
    try:
        cfg.porta = int(valores.get("PORTA", cfg.porta))
    except ValueError:
        pass
    if valores.get("PASTA_DADOS"):
        cfg.pasta_dados = _caminho(valores["PASTA_DADOS"])
    if valores.get("PASTA_BACKUP"):
        cfg.pasta_backup = _caminho(valores["PASTA_BACKUP"])
    try:
        cfg.backups_manter = max(1, int(valores.get("BACKUPS_MANTER", cfg.backups_manter)))
    except ValueError:
        pass
    sc = valores.get("SEMANA_COMECA", "domingo").strip().lower()
    cfg.semana_comeca = "segunda" if sc.startswith("seg") else "domingo"
    cfg.abrir_navegador = valores.get("ABRIR_NAVEGADOR", "1").strip() not in ("0", "nao", "não", "false")
    cfg.feriados_extras = valores.get("FERIADOS_EXTRAS", "")
    return cfg
