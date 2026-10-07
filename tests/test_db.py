import sqlite3

import pytest

from app import backup, preparar_banco
from app.db import BancoMaisNovoError, conectar, migracoes_disponiveis, migrar, versao_atual


def test_banco_vazio_chega_a_versao_atual(tmp_path):
    conn = conectar(tmp_path / "x.db")
    aplicadas = migrar(conn)
    assert aplicadas == [n for n, _ in migracoes_disponiveis()]
    assert versao_atual(conn) == aplicadas[-1]
    assert migrar(conn) == []          # rodar de novo não faz nada
    conn.close()


def test_recusa_banco_de_versao_mais_nova(tmp_path):
    conn = conectar(tmp_path / "x.db")
    migrar(conn)
    conn.execute("INSERT INTO schema_version (versao) VALUES (999)")
    with pytest.raises(BancoMaisNovoError):
        migrar(conn)
    conn.close()


def test_seed_carrega_regras_uma_vez(cfg):
    preparar_banco(cfg)
    preparar_banco(cfg)
    conn = conectar(cfg.banco)
    assert conn.execute("SELECT COUNT(*) FROM regras").fetchone()[0] == 40
    conn.close()


def test_backup_rotaciona_e_restaura(cfg):
    preparar_banco(cfg)
    for i in range(5):
        backup.criar(cfg.banco, cfg.pasta_backup, f"teste {i}", manter=3)
    itens = backup.listar(cfg.pasta_backup)
    assert len(itens) == 3

    conn = conectar(cfg.banco)
    conn.execute("DELETE FROM regras")
    conn.close()
    backup.restaurar(itens[0].arquivo, cfg.banco)
    conn = sqlite3.connect(cfg.banco)
    assert conn.execute("SELECT COUNT(*) FROM regras").fetchone()[0] == 40
    conn.close()
