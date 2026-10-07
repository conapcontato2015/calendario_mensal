"""Aplicação das regras de nomes, nomes novos e agrupamento por dia.

Ordem de aplicação (PLANEJAMENTO.md §5.3):
  1. regra exata
  2. regra "começa com" — vence o padrão mais longo
  3. regra "contém" — vence o padrão mais longo
  4. nada casou → pendente (nunca inventar nome)
Empate real entre regras do mesmo tipo e tamanho é conflito e bloqueia a importação.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from .parser import Linha
from .textutil import chave, nome_curto, prefixo_padrao

TIPOS = ("exata", "prefixo", "contem")
STOP = {"DE", "DO", "DA", "DOS", "DAS", "E", "EM", "NO", "NA"}


@dataclass
class Regra:
    tipo: str
    padrao: str
    acao: str               # renomear | ignorar
    nome_curto: str = ""
    ativa: bool = True
    id: int | None = None
    provisoria: bool = False  # criada na importação em curso, ainda não salva

    def casa(self, k: str) -> bool:
        if self.tipo == "exata":
            return k == self.padrao
        if self.tipo == "prefixo":
            return k.startswith(self.padrao)
        return self.padrao in k


class ConflitoRegras(Exception):
    def __init__(self, k: str, regras: list[Regra]):
        self.chave = k
        self.regras = regras
        nomes = ", ".join(f"“{r.padrao}”" for r in regras)
        super().__init__(f"Mais de uma regra serve para “{k}”: {nomes}")


@dataclass
class Decisao:
    acao: str = "renomear"   # renomear | ignorar
    nome: str = ""
    prefixo: bool = False    # aplicar também a tudo que começa com...
    prefixo_txt: str = ""

    @property
    def definida(self) -> bool:
        return self.acao == "ignorar" or bool(self.nome.strip())


@dataclass
class LinhaProc:
    linha: Linha
    status: str                    # ok | agrupada | ignorada | pendente | conflito
    nome: str = ""
    regra: Regra | None = None
    originais: list[str] = field(default_factory=list)
    agrupada_em: "LinhaProc | None" = None
    erro: str = ""

    @property
    def nova(self) -> bool:
        return bool(self.regra and self.regra.provisoria)


@dataclass
class NomeNovo:
    chave: str
    original: str
    primeira_data: date
    ocorrencias: int
    decisao: Decisao
    sugestao: str | None
    coberto_por: str | None = None   # padrão "começa com" de outra decisão que já cobre este nome
    padrao_prefixo: str = ""

    @property
    def resolvido(self) -> bool:
        return self.coberto_por is not None or self.decisao.definida


@dataclass
class Resultado:
    linhas: list[LinhaProc]
    novos: list[NomeNovo]
    regras_novas: list[Regra]

    def contar(self, status: str) -> int:
        return sum(1 for l in self.linhas if l.status == status)

    @property
    def no_calendario(self) -> list[LinhaProc]:
        return [l for l in self.linhas if l.status == "ok"]

    @property
    def pendentes(self) -> int:
        return sum(1 for n in self.novos if not n.resolvido)

    @property
    def conflitos(self) -> list[LinhaProc]:
        return [l for l in self.linhas if l.status == "conflito"]

    def por_dia(self) -> dict[date, list[LinhaProc]]:
        dias: dict[date, list[LinhaProc]] = {}
        for l in self.no_calendario:
            dias.setdefault(l.linha.data, []).append(l)
        return dict(sorted(dias.items()))


def achar_regra(k: str, regras: list[Regra]) -> Regra | None:
    ativas = [r for r in regras if r.ativa]
    for tipo in TIPOS:
        candidatas = [r for r in ativas if r.tipo == tipo and r.casa(k)]
        if not candidatas:
            continue
        if tipo == "exata":
            return candidatas[0]
        maior = max(len(r.padrao) for r in candidatas)
        melhores = [r for r in candidatas if len(r.padrao) == maior]
        distintas = {(r.padrao, r.acao, r.nome_curto) for r in melhores}
        if len(distintas) > 1:
            raise ConflitoRegras(k, melhores)
        return melhores[0]
    return None


def _radicais(k: str) -> set[str]:
    return {w[:5] for w in re.split(r"[^A-Z0-9]+", k) if len(w) > 2 and w not in STOP}


def sugerir(k: str, regras: list[Regra]) -> str | None:
    """Nome de uma regra existente parecida (semelhança por radicais ≥ 0,3)."""
    a = _radicais(k)
    if not a:
        return None
    melhor, nota = None, 0.0
    for r in regras:
        if not r.ativa or r.acao != "renomear":
            continue
        b = _radicais(r.padrao)
        if not b:
            continue
        n = len(a & b) / len(a | b)
        if n > nota:
            melhor, nota = r, n
    return melhor.nome_curto if melhor and nota >= 0.3 else None


def _acha_seguro(k: str, regras: list[Regra]) -> tuple[Regra | None, str]:
    try:
        return achar_regra(k, regras), ""
    except ConflitoRegras as e:
        return None, str(e)


def processar(linhas: list[Linha], regras: list[Regra],
              decisoes: dict[str, Decisao] | None = None,
              sugerir_padrao: bool = True) -> Resultado:
    decisoes = dict(decisoes or {})
    base = [r for r in regras if r.ativa]

    # 1) nomes que nenhuma regra salva cobre
    chaves_novas: list[str] = []
    primeira: dict[str, Linha] = {}
    ocorr: dict[str, int] = {}
    for l in linhas:
        regra, erro = _acha_seguro(l.chave, base)
        if regra is None and not erro:
            if l.chave not in primeira:
                chaves_novas.append(l.chave)
                primeira[l.chave] = l
            ocorr[l.chave] = ocorr.get(l.chave, 0) + 1

    # 2) decisões "começa com" viram regras provisórias
    sugestoes = {k: sugerir(k, base) for k in chaves_novas}
    for k in chaves_novas:
        if k not in decisoes:
            decisoes[k] = Decisao(nome=(sugestoes[k] or "") if sugerir_padrao else "")
    prov_pre: list[Regra] = []
    padrao_de: dict[str, str] = {}
    for k in chaves_novas:
        d = decisoes[k]
        padrao = chave(d.prefixo_txt) if d.prefixo_txt.strip() else prefixo_padrao(k)
        padrao_de[k] = padrao
        if d.prefixo and d.definida and padrao and k.startswith(padrao):
            prov_pre.append(Regra("prefixo", padrao, d.acao,
                                  "" if d.acao == "ignorar" else nome_curto(d.nome), provisoria=True))

    # 3) quem já está coberto pelo "começa com" de outra decisão
    novos: list[NomeNovo] = []
    prov_exata: list[Regra] = []
    for k in chaves_novas:
        d = decisoes[k]
        cobre, _ = _acha_seguro(k, prov_pre)
        proprio = d.prefixo and d.definida and cobre is not None and cobre.padrao == padrao_de[k]
        coberto_por = cobre.padrao if (cobre is not None and not proprio) else None
        if coberto_por is None and not proprio and d.definida:
            prov_exata.append(Regra("exata", k, d.acao,
                                    "" if d.acao == "ignorar" else nome_curto(d.nome), provisoria=True))
        novos.append(NomeNovo(k, primeira[k].original, primeira[k].data, ocorr[k], d,
                              sugestoes[k], coberto_por, padrao_de[k]))

    todas = base + prov_pre + prov_exata

    # 4) aplica a cada linha
    proc: list[LinhaProc] = []
    for l in linhas:
        regra, erro = _acha_seguro(l.chave, todas)
        if erro:
            proc.append(LinhaProc(l, "conflito", erro=erro))
        elif regra is None:
            proc.append(LinhaProc(l, "pendente"))
        elif regra.acao == "ignorar":
            proc.append(LinhaProc(l, "ignorada", regra=regra))
        else:
            proc.append(LinhaProc(l, "ok", nome=regra.nome_curto, regra=regra))

    # 5) mesmo nome no mesmo dia aparece uma vez só (ordem da primeira aparição)
    vistos: dict[tuple[date, str], LinhaProc] = {}
    for p in proc:
        if p.status != "ok":
            continue
        k = (p.linha.data, p.nome)
        if k in vistos:
            p.status = "agrupada"
            p.agrupada_em = vistos[k]
            vistos[k].originais.append(p.linha.original)
        else:
            vistos[k] = p
            p.originais = [p.linha.original]

    usadas = {id(p.regra) for p in proc if p.regra is not None}
    regras_novas = [r for r in prov_pre + prov_exata if id(r) in usadas]
    return Resultado(proc, novos, regras_novas)
