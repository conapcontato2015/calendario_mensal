"""Leitura do texto colado: cada linha é 'nome da tarefa' + 'dd/mm/aaaa' no fim."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import date

from .textutil import chave

LINHA = re.compile(r"^(?P<nome>.*?\S)[\t ]+(?P<d>\d{1,2})/(?P<m>\d{1,2})/(?P<a>\d{4})\s*$")


@dataclass
class Linha:
    numero: int          # linha no texto colado (1 = primeira)
    original: str        # nome como veio do sistema
    chave: str
    data: date


@dataclass
class LinhaErro:
    numero: int
    texto: str
    motivo: str


@dataclass
class Leitura:
    linhas: list[Linha]
    erros: list[LinhaErro]

    @property
    def mes_ref(self) -> str | None:
        """Mês com mais tarefas (AAAA-MM). Em empate, o que aparece primeiro."""
        if not self.linhas:
            return None
        cont = Counter(l.data.strftime("%Y-%m") for l in self.linhas)
        maior = max(cont.values())
        for l in self.linhas:
            mk = l.data.strftime("%Y-%m")
            if cont[mk] == maior:
                return mk
        return None

    @property
    def fora_do_mes(self) -> list[Linha]:
        mk = self.mes_ref
        return [l for l in self.linhas if l.data.strftime("%Y-%m") != mk]


def ler(texto: str) -> Leitura:
    linhas: list[Linha] = []
    erros: list[LinhaErro] = []
    for i, bruta in enumerate((texto or "").splitlines(), start=1):
        if not bruta.strip():
            continue
        m = LINHA.match(bruta.rstrip())
        if not m:
            erros.append(LinhaErro(i, bruta.strip(), "não termina com uma data no formato dd/mm/aaaa"))
            continue
        d, mes, ano = int(m.group("d")), int(m.group("m")), int(m.group("a"))
        try:
            dt = date(ano, mes, d)
        except ValueError:
            erros.append(LinhaErro(i, bruta.strip(),
                                   f"a data {m.group('d')}/{m.group('m')}/{m.group('a')} não existe"))
            continue
        nome = m.group("nome").strip()
        k = chave(nome)
        if not k:
            erros.append(LinhaErro(i, bruta.strip(), "linha sem nome de tarefa"))
            continue
        linhas.append(Linha(i, nome, k, dt))
    return Leitura(linhas, erros)
