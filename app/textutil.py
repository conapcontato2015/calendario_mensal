"""Normalização de texto usada em toda a comparação de nomes."""
from __future__ import annotations

import re
import unicodedata

MESES = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO",
         "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
DIAS_SEMANA = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
               "sexta-feira", "sábado", "domingo"]  # índice = date.weekday()
DIAS_CURTOS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def chave(texto: str) -> str:
    """Maiúsculas, sem acentos, espaços repetidos reduzidos, sem espaços nas pontas."""
    sem_acento = unicodedata.normalize("NFD", texto)
    sem_acento = "".join(c for c in sem_acento if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", sem_acento).strip().upper()


def nome_curto(texto: str) -> str:
    """Nome como aparece no calendário: maiúsculas (com acento), espaços limpos."""
    return re.sub(r"\s+", " ", texto).strip().upper()


def prefixo_padrao(k: str, palavras: int = 2) -> str:
    return " ".join(k.split(" ")[:palavras])
