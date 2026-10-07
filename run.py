"""Inicia o Calendário de Tarefas (servidor Waitress na rede local).

Uso normal: dar dois cliques em iniciar.bat. Para encerrar: fechar a janela ou Ctrl+C.
"""
from __future__ import annotations

import socket
import sys
import threading
import webbrowser

from app import config, create_app, preparar_banco
from app import backup
from app.db import BancoMaisNovoError, conectar, migracoes_pendentes


def ip_da_rede() -> str | None:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))   # não envia nada; só descobre a interface de rede
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def porta_livre(porta: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", porta))
        return True
    except OSError:
        return False
    finally:
        s.close()


def main() -> int:
    cfg = config.carregar()
    local = f"http://localhost:{cfg.porta}"

    if not porta_livre(cfg.porta):
        print(f"\n[!] A porta {cfg.porta} já está em uso.")
        print("    O sistema provavelmente já está aberto em outra janela.")
        print(f"    Tente abrir {local} no navegador, ou mude PORTA no arquivo .env.\n")
        if cfg.abrir_navegador:
            webbrowser.open(local)
        return 1

    # backup antes de migrar o banco para uma versão nova
    try:
        if cfg.banco.exists():
            conn = conectar(cfg.banco)
            try:
                pendentes = migracoes_pendentes(conn)
            finally:
                conn.close()
            if pendentes:
                backup.criar(cfg.banco, cfg.pasta_backup, "antes-atualizacao", cfg.backups_manter)
        preparar_banco(cfg)
    except BancoMaisNovoError as e:
        print(f"\n[!] {e}\n")
        return 1

    backup.criar(cfg.banco, cfg.pasta_backup, "abertura", cfg.backups_manter)
    app = create_app(cfg)

    rede = ip_da_rede()
    print("\n  CALENDÁRIO DE TAREFAS")
    print("  ---------------------")
    print(f"  Neste computador:  {local}")
    if rede:
        print(f"  Na rede:           http://{rede}:{cfg.porta}")
    print(f"  Nome do computador: http://{socket.gethostname()}:{cfg.porta}")
    print(f"  Banco de dados:    {cfg.banco}")
    print(f"  Backups:           {cfg.pasta_backup}")
    print("\n  Para encerrar: feche esta janela ou pressione Ctrl+C.\n")

    if cfg.abrir_navegador:
        threading.Timer(1.2, lambda: webbrowser.open(local)).start()

    from waitress import serve
    serve(app, host="0.0.0.0", port=cfg.porta, threads=6, ident="calendario")
    return 0


if __name__ == "__main__":
    sys.exit(main())
