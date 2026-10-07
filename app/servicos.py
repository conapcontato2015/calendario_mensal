"""Operações no banco: regras, importações (lotes), tarefas e log.

Toda operação que grava usa uma transação explícita (BEGIN IMMEDIATE).
Nada é apagado de fato: lotes viram 'substituido'/'desfeito', tarefas 'removida', regras 'ativa=0'.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import parser
from .db import agora, registrar_log
from .normalizer import Decisao, Regra, Resultado, achar_regra, processar
from .textutil import chave, nome_curto

SEED = Path(__file__).resolve().parent.parent / "seed" / "regras.json"


class ErroOperacao(Exception):
    """Erro com mensagem pronta para mostrar ao usuário."""


@contextmanager
def transacao(conn: sqlite3.Connection):
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except Exception:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


# ------------------------------------------------------------------ regras

def _regra(row: sqlite3.Row) -> Regra:
    return Regra(row["tipo"], row["padrao"], row["acao"], row["nome_curto"],
                 bool(row["ativa"]), row["id"])


def carregar_regras(conn: sqlite3.Connection, so_ativas: bool = False) -> list[Regra]:
    sql = "SELECT * FROM regras" + (" WHERE ativa = 1" if so_ativas else "") + " ORDER BY id"
    return [_regra(r) for r in conn.execute(sql)]


def garantir_seed(conn: sqlite3.Connection) -> int:
    """Carrega seed/regras.json se ainda não existe nenhuma regra."""
    if conn.execute("SELECT COUNT(*) FROM regras").fetchone()[0]:
        return 0
    itens = json.loads(SEED.read_text(encoding="utf-8"))
    with transacao(conn):
        n = importar_regras(conn, itens, "", registrar=False)
        registrar_log(conn, "", "regras iniciais", f"{n} regras carregadas")
    return n


def importar_regras(conn: sqlite3.Connection, itens: list[dict], ip: str,
                    registrar: bool = True) -> int:
    """Adiciona regras de uma lista (JSON). Ignora as que já existem (mesmo tipo e padrão)."""
    n = 0
    for it in itens:
        tipo = it.get("tipo", "exata")
        acao = it.get("acao", "renomear")
        padrao = chave(it.get("padrao", ""))
        nome = nome_curto(it.get("nome_curto", ""))
        if tipo not in ("exata", "prefixo", "contem") or acao not in ("renomear", "ignorar") or not padrao:
            continue
        if acao == "renomear" and not nome:
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO regras (tipo, padrao, acao, nome_curto, ativa, criada_em, atualizada_em)"
            " VALUES (?, ?, ?, ?, 1, ?, ?)",
            (tipo, padrao, acao, nome if acao == "renomear" else "", agora(), agora()))
        n += cur.rowcount
    if registrar:
        registrar_log(conn, ip, "regras importadas", f"{n} regras novas")
    return n


def exportar_regras(conn: sqlite3.Connection) -> list[dict]:
    return [{"tipo": r["tipo"], "padrao": r["padrao"], "acao": r["acao"],
             "nome_curto": r["nome_curto"], "ativa": bool(r["ativa"])}
            for r in conn.execute("SELECT * FROM regras ORDER BY tipo, padrao")]


@dataclass
class AvisoRegra:
    texto: str


def salvar_regra(conn: sqlite3.Connection, ip: str, *, regra_id: int | None, tipo: str,
                 padrao: str, acao: str, nome: str, aplicar_existentes: bool = False) -> list[str]:
    """Cria ou edita uma regra. Retorna avisos (sobreposições) para mostrar."""
    padrao_k = chave(padrao)
    nome_c = nome_curto(nome) if acao == "renomear" else ""
    if tipo not in ("exata", "prefixo", "contem"):
        raise ErroOperacao("Tipo de regra inválido.")
    if acao not in ("renomear", "ignorar"):
        raise ErroOperacao("Ação inválida.")
    if not padrao_k:
        raise ErroOperacao("Informe o nome do sistema (ou o começo dele).")
    if acao == "renomear" and not nome_c:
        raise ErroOperacao("Informe como a tarefa aparece no calendário.")
    if tipo == "contem" and len(padrao_k) < 4:
        raise ErroOperacao("Para “contém”, use pelo menos 4 letras, senão a regra pega nomes demais.")

    outra = conn.execute("SELECT id, ativa FROM regras WHERE tipo = ? AND padrao = ?",
                         (tipo, padrao_k)).fetchone()
    with transacao(conn):
        if regra_id is None:
            if outra is not None:
                if outra["ativa"]:
                    raise ErroOperacao("Já existe uma regra igual. Edite a existente.")
                conn.execute("UPDATE regras SET acao=?, nome_curto=?, ativa=1, atualizada_em=? WHERE id=?",
                             (acao, nome_c, agora(), outra["id"]))
                regra_id = outra["id"]
                registrar_log(conn, ip, "regra reativada", f"{padrao_k} → {nome_c or 'ignorar'}")
            else:
                cur = conn.execute(
                    "INSERT INTO regras (tipo, padrao, acao, nome_curto, ativa, criada_em, atualizada_em)"
                    " VALUES (?, ?, ?, ?, 1, ?, ?)", (tipo, padrao_k, acao, nome_c, agora(), agora()))
                regra_id = cur.lastrowid
                registrar_log(conn, ip, "regra criada", f"{tipo}: {padrao_k} → {nome_c or 'ignorar'}")
        else:
            if outra is not None and outra["id"] != regra_id:
                raise ErroOperacao("Já existe outra regra com esse mesmo nome do sistema e tipo.")
            antiga = conn.execute("SELECT nome_curto FROM regras WHERE id = ?", (regra_id,)).fetchone()
            if antiga is None:
                raise ErroOperacao("Regra não encontrada.")
            conn.execute("UPDATE regras SET tipo=?, padrao=?, acao=?, nome_curto=?, atualizada_em=? WHERE id=?",
                         (tipo, padrao_k, acao, nome_c, agora(), regra_id))
            registrar_log(conn, ip, "regra editada", f"{tipo}: {padrao_k} → {nome_c or 'ignorar'}")
            if aplicar_existentes and acao == "renomear" and antiga["nome_curto"] != nome_c:
                n = conn.execute(
                    "UPDATE tarefas SET nome_curto = ? WHERE regra_id = ? AND removida = 0"
                    " AND lote_id IN (SELECT id FROM lotes WHERE status = 'ativo')",
                    (nome_c, regra_id)).rowcount
                registrar_log(conn, ip, "nome atualizado nos meses importados", f"{n} tarefas → {nome_c}")

    return avisos_sobreposicao(conn, regra_id)


def avisos_sobreposicao(conn: sqlite3.Connection, regra_id: int) -> list[str]:
    r = conn.execute("SELECT * FROM regras WHERE id = ?", (regra_id,)).fetchone()
    if r is None or r["tipo"] == "exata":
        return []
    avisos = []
    for o in conn.execute("SELECT * FROM regras WHERE ativa = 1 AND id <> ? AND tipo <> 'exata'", (regra_id,)):
        if o["padrao"].startswith(r["padrao"]) or r["padrao"].startswith(o["padrao"]) \
                or (r["tipo"] == "contem" and r["padrao"] in o["padrao"]) \
                or (o["tipo"] == "contem" and o["padrao"] in r["padrao"]):
            avisos.append(f"Esta regra se sobrepõe a “{o['padrao']}…” ({o['nome_curto'] or 'ignorar'}). "
                          "Quando as duas servirem, vale a mais específica (padrão mais longo).")
    return avisos


def alternar_regra(conn: sqlite3.Connection, regra_id: int, ip: str) -> bool:
    with transacao(conn):
        r = conn.execute("SELECT * FROM regras WHERE id = ?", (regra_id,)).fetchone()
        if r is None:
            raise ErroOperacao("Regra não encontrada.")
        nova = 0 if r["ativa"] else 1
        conn.execute("UPDATE regras SET ativa = ?, atualizada_em = ? WHERE id = ?", (nova, agora(), regra_id))
        registrar_log(conn, ip, "regra " + ("reativada" if nova else "desativada"), r["padrao"])
    return bool(nova)


def uso_regras(conn: sqlite3.Connection) -> dict[int, dict]:
    uso: dict[int, dict] = {}
    sql = ("SELECT t.regra_id, t.originais_json, t.data FROM tarefas t JOIN lotes l ON l.id = t.lote_id"
           " WHERE l.status = 'ativo' AND t.removida = 0 AND t.regra_id IS NOT NULL")
    for row in conn.execute(sql):
        u = uso.setdefault(row["regra_id"], {"usos": 0, "ultimo": None})
        u["usos"] += max(1, len(json.loads(row["originais_json"])))
        if u["ultimo"] is None or row["data"] > u["ultimo"]:
            u["ultimo"] = row["data"]
    return uso


def testar_nome(conn: sqlite3.Connection, texto: str) -> tuple[Regra | None, str]:
    k = chave(texto)
    if not k:
        return None, ""
    try:
        return achar_regra(k, carregar_regras(conn, so_ativas=True)), ""
    except Exception as e:  # ConflitoRegras
        return None, str(e)


# ------------------------------------------------------------------ importação

def decisoes_do_form(form) -> dict[str, Decisao]:
    """Lê os campos dec-N-* do formulário de importação."""
    decisoes: dict[str, Decisao] = {}
    i = 0
    while f"dec-{i}-chave" in form:
        k = form.get(f"dec-{i}-chave", "")
        decisoes[k] = Decisao(
            acao="ignorar" if form.get(f"dec-{i}-ignorar") else "renomear",
            nome=form.get(f"dec-{i}-nome", ""),
            prefixo=bool(form.get(f"dec-{i}-prefixo")),
            prefixo_txt=form.get(f"dec-{i}-prefixo-txt", ""),
        )
        i += 1
    return decisoes


@dataclass
class Previa:
    leitura: parser.Leitura
    resultado: Resultado
    mes_ref: str | None
    existentes: int
    ajustes_manuais: int
    bloqueio: str = ""
    avisos: list[str] = field(default_factory=list)


def lote_ativo(conn: sqlite3.Connection, mes_ref: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM lotes WHERE mes_ref = ? AND status = 'ativo' ORDER BY id DESC LIMIT 1",
                        (mes_ref,)).fetchone()


def previa(conn: sqlite3.Connection, texto: str, decisoes: dict[str, Decisao] | None,
           substituir: bool, sugerir: bool = True) -> Previa:
    """sugerir=True preenche nomes novos com a sugestão (tela); False exige decisão explícita (gravação)."""
    leitura = parser.ler(texto)
    resultado = processar(leitura.linhas, carregar_regras(conn, so_ativas=True), decisoes,
                          sugerir_padrao=sugerir)
    mk = leitura.mes_ref
    existentes = ajustes = 0
    if mk:
        lote = lote_ativo(conn, mk)
        if lote is not None:
            existentes = conn.execute("SELECT COUNT(*) FROM tarefas WHERE lote_id = ? AND removida = 0",
                                      (lote["id"],)).fetchone()[0]
            ajustes = conn.execute("SELECT COUNT(*) FROM tarefas WHERE lote_id = ? AND manual = 1 AND removida = 0",
                                   (lote["id"],)).fetchone()[0]
    p = Previa(leitura, resultado, mk, existentes, ajustes)
    if not leitura.linhas:
        p.bloqueio = ("Nenhuma linha válida. Cada linha precisa ter o nome da tarefa e a data no formato dd/mm/aaaa."
                      if leitura.erros else "Cole a lista para ver a prévia.")
    elif resultado.conflitos:
        p.bloqueio = "Há regras em conflito. Ajuste em Nomes antes de importar."
    elif resultado.pendentes:
        n = resultado.pendentes
        p.bloqueio = "Defina o nome novo acima para liberar." if n == 1 else f"Defina os {n} nomes novos acima para liberar."
    elif existentes and not substituir:
        p.bloqueio = "Confirme acima a substituição das tarefas que este mês já tem."
    return p


def confirmar_importacao(conn: sqlite3.Connection, texto: str, decisoes: dict[str, Decisao],
                         substituir: bool, ip: str, origem: str = "importacao") -> tuple[int, int, int]:
    """Grava a importação. Retorna (lote_id, tarefas gravadas, regras novas)."""
    p = previa(conn, texto, decisoes, substituir, sugerir=False)
    if p.bloqueio:
        raise ErroOperacao(p.bloqueio)
    mk = p.mes_ref
    with transacao(conn):
        antigo = lote_ativo(conn, mk)
        if antigo is not None:
            conn.execute("UPDATE lotes SET status = 'substituido' WHERE id = ?", (antigo["id"],))
        cur = conn.execute(
            "INSERT INTO lotes (mes_ref, origem, texto_colado, criado_em, ip_origem, status, substituiu_lote_id)"
            " VALUES (?, ?, ?, ?, ?, 'ativo', ?)",
            (mk, origem, texto, agora(), ip, antigo["id"] if antigo else None))
        lote_id = cur.lastrowid

        ids_regras: dict[int, int] = {}   # id(objeto Regra provisória) -> id no banco
        for r in p.resultado.regras_novas:
            existente = conn.execute("SELECT id FROM regras WHERE tipo = ? AND padrao = ?",
                                     (r.tipo, r.padrao)).fetchone()
            if existente is not None:   # regra inativa com o mesmo padrão: reativa
                conn.execute("UPDATE regras SET acao=?, nome_curto=?, ativa=1, atualizada_em=?, criada_no_lote=?"
                             " WHERE id=?", (r.acao, r.nome_curto, agora(), lote_id, existente["id"]))
                ids_regras[id(r)] = existente["id"]
            else:
                c2 = conn.execute(
                    "INSERT INTO regras (tipo, padrao, acao, nome_curto, ativa, criada_em, atualizada_em, criada_no_lote)"
                    " VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
                    (r.tipo, r.padrao, r.acao, r.nome_curto, agora(), agora(), lote_id))
                ids_regras[id(r)] = c2.lastrowid

        ordem: dict[date, int] = {}
        n = 0
        for lp in p.resultado.no_calendario:
            d = lp.linha.data
            ordem[d] = ordem.get(d, 0) + 1
            rid = lp.regra.id if lp.regra and lp.regra.id else ids_regras.get(id(lp.regra))
            conn.execute(
                "INSERT INTO tarefas (lote_id, data, nome_curto, originais_json, regra_id, ordem)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (lote_id, d.isoformat(), lp.nome, json.dumps(lp.originais, ensure_ascii=False), rid, ordem[d]))
            n += 1
        acao = "importação" if origem == "importacao" else "regras reaplicadas"
        registrar_log(conn, ip, acao,
                      f"{mk}: {n} tarefas, {len(p.resultado.regras_novas)} nomes novos"
                      + (f", substituiu importação #{antigo['id']}" if antigo else ""))
    return lote_id, n, len(p.resultado.regras_novas)


def pode_desfazer(conn: sqlite3.Connection, lote_id: int) -> bool:
    lote = conn.execute("SELECT * FROM lotes WHERE id = ?", (lote_id,)).fetchone()
    return lote is not None and lote["status"] == "ativo" and lote["origem"] != "manual"


def desfazer_importacao(conn: sqlite3.Connection, lote_id: int, ip: str) -> str:
    """Desfaz uma importação: volta o mês ao estado anterior e desativa os nomes criados nela."""
    with transacao(conn):
        lote = conn.execute("SELECT * FROM lotes WHERE id = ?", (lote_id,)).fetchone()
        if lote is None or lote["status"] != "ativo" or lote["origem"] == "manual":
            raise ErroOperacao("Esta importação não pode mais ser desfeita.")
        conn.execute("UPDATE lotes SET status = 'desfeito' WHERE id = ?", (lote_id,))
        if lote["substituiu_lote_id"]:
            conn.execute("UPDATE lotes SET status = 'ativo' WHERE id = ?", (lote["substituiu_lote_id"],))
        n = conn.execute("UPDATE regras SET ativa = 0, atualizada_em = ? WHERE criada_no_lote = ?",
                         (agora(), lote_id)).rowcount
        registrar_log(conn, ip, "importação desfeita", f"{lote['mes_ref']} (#{lote_id}); {n} nomes desativados")
    return lote["mes_ref"]


# ------------------------------------------------------------------ tarefas (calendário)

@dataclass
class Tarefa:
    id: int
    data: date
    nome: str
    originais: list[str]
    manual: bool
    regra_id: int | None


def tarefas_periodo(conn: sqlite3.Connection, inicio: date, fim: date) -> dict[date, list[Tarefa]]:
    sql = ("SELECT t.* FROM tarefas t JOIN lotes l ON l.id = t.lote_id"
           " WHERE l.status = 'ativo' AND t.removida = 0 AND t.data BETWEEN ? AND ?"
           " ORDER BY t.data, t.ordem, t.id")
    dias: dict[date, list[Tarefa]] = {}
    for r in conn.execute(sql, (inicio.isoformat(), fim.isoformat())):
        d = date.fromisoformat(r["data"])
        dias.setdefault(d, []).append(Tarefa(r["id"], d, r["nome_curto"], json.loads(r["originais_json"]),
                                             bool(r["manual"]), r["regra_id"]))
    return dias


def _tarefa(conn: sqlite3.Connection, tarefa_id: int) -> sqlite3.Row:
    r = conn.execute("SELECT t.*, l.status AS lote_status FROM tarefas t JOIN lotes l ON l.id = t.lote_id"
                     " WHERE t.id = ?", (tarefa_id,)).fetchone()
    if r is None:
        raise ErroOperacao("Tarefa não encontrada.")
    return r


def _nome_repetido(conn: sqlite3.Connection, data_iso: str, nome: str, exceto: int | None = None) -> bool:
    sql = ("SELECT 1 FROM tarefas t JOIN lotes l ON l.id = t.lote_id WHERE l.status = 'ativo'"
           " AND t.removida = 0 AND t.data = ? AND t.nome_curto = ?" + (" AND t.id <> ?" if exceto else ""))
    params = (data_iso, nome, exceto) if exceto else (data_iso, nome)
    return conn.execute(sql, params).fetchone() is not None


def adicionar_tarefa(conn: sqlite3.Connection, dia: date, nome: str, ip: str) -> int:
    nome_c = nome_curto(nome)
    if not nome_c:
        raise ErroOperacao("Digite o nome da tarefa.")
    if _nome_repetido(conn, dia.isoformat(), nome_c):
        raise ErroOperacao(f"{nome_c} já está neste dia.")
    mk = dia.strftime("%Y-%m")
    with transacao(conn):
        lote = lote_ativo(conn, mk)
        if lote is None:
            lote_id = conn.execute(
                "INSERT INTO lotes (mes_ref, origem, criado_em, ip_origem, status) VALUES (?, 'manual', ?, ?, 'ativo')",
                (mk, agora(), ip)).lastrowid
        else:
            lote_id = lote["id"]
        ordem = conn.execute("SELECT COALESCE(MAX(ordem), 0) + 1 FROM tarefas WHERE lote_id = ? AND data = ?",
                             (lote_id, dia.isoformat())).fetchone()[0]
        tid = conn.execute(
            "INSERT INTO tarefas (lote_id, data, nome_curto, originais_json, ordem, manual) VALUES (?, ?, ?, '[]', ?, 1)",
            (lote_id, dia.isoformat(), nome_c, ordem)).lastrowid
        registrar_log(conn, ip, "tarefa adicionada", f"{dia.strftime('%d/%m/%Y')}: {nome_c}")
    return tid


def renomear_tarefa(conn: sqlite3.Connection, tarefa_id: int, nome: str, ip: str) -> tuple[str, str]:
    nome_c = nome_curto(nome)
    if not nome_c:
        raise ErroOperacao("O nome não pode ficar vazio.")
    t = _tarefa(conn, tarefa_id)
    if _nome_repetido(conn, t["data"], nome_c, exceto=tarefa_id):
        raise ErroOperacao(f"{nome_c} já está neste dia.")
    with transacao(conn):
        conn.execute("UPDATE tarefas SET nome_curto = ? WHERE id = ?", (nome_c, tarefa_id))
        registrar_log(conn, ip, "tarefa renomeada", f"{t['data']}: {t['nome_curto']} → {nome_c}")
    return t["nome_curto"], nome_c


def remover_tarefa(conn: sqlite3.Connection, tarefa_id: int, ip: str) -> str:
    t = _tarefa(conn, tarefa_id)
    with transacao(conn):
        conn.execute("UPDATE tarefas SET removida = 1 WHERE id = ?", (tarefa_id,))
        registrar_log(conn, ip, "tarefa removida", f"{t['data']}: {t['nome_curto']}")
    return t["nome_curto"]


def restaurar_tarefa(conn: sqlite3.Connection, tarefa_id: int, ip: str) -> str:
    t = _tarefa(conn, tarefa_id)
    if _nome_repetido(conn, t["data"], t["nome_curto"], exceto=tarefa_id):
        raise ErroOperacao(f"{t['nome_curto']} já está neste dia.")
    with transacao(conn):
        conn.execute("UPDATE tarefas SET removida = 0 WHERE id = ?", (tarefa_id,))
        registrar_log(conn, ip, "tarefa restaurada", f"{t['data']}: {t['nome_curto']}")
    return t["nome_curto"]


def nomes_em_uso(conn: sqlite3.Connection) -> list[str]:
    nomes = {r[0] for r in conn.execute("SELECT nome_curto FROM regras WHERE ativa = 1 AND acao = 'renomear'")}
    nomes |= {r[0] for r in conn.execute(
        "SELECT DISTINCT t.nome_curto FROM tarefas t JOIN lotes l ON l.id = t.lote_id"
        " WHERE l.status = 'ativo' AND t.removida = 0")}
    return sorted(n for n in nomes if n)


def meses_com_tarefas(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT mes_ref FROM lotes WHERE status = 'ativo' AND origem <> 'manual' ORDER BY mes_ref DESC")]


def log_recente(conn: sqlite3.Connection, limite: int = 300) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM log ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
