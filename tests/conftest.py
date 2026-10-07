from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app import create_app  # noqa: E402
from app.config import Config  # noqa: E402
from app.normalizer import Regra  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def regras_seed() -> list[Regra]:
    itens = json.loads((RAIZ / "seed" / "regras.json").read_text(encoding="utf-8"))
    return [Regra(i["tipo"], i["padrao"], i["acao"], i["nome_curto"]) for i in itens]


@pytest.fixture
def texto_outubro() -> str:
    return (FIXTURES / "outubro_2026.txt").read_text(encoding="utf-8")


@pytest.fixture
def cfg(tmp_path) -> Config:
    return Config(pasta_dados=tmp_path / "dados", pasta_backup=tmp_path / "dados" / "backups",
                  abrir_navegador=False)


@pytest.fixture
def app(cfg):
    a = create_app(cfg)
    a.config["TESTING"] = True
    return a


@pytest.fixture
def client(app):
    return app.test_client()
