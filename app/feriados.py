"""Feriados nacionais, estaduais do Ceará e extras configurados."""
from __future__ import annotations

import re
from datetime import date, timedelta
from functools import lru_cache


def _pascoa(ano: int) -> date:
    # Algoritmo de Meeus/Jones/Butcher
    a = ano % 19
    b, c = divmod(ano, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return date(ano, mes, dia)


@lru_cache(maxsize=32)
def _base(ano: int) -> dict[date, str]:
    p = _pascoa(ano)
    return {
        date(ano, 1, 1): "Confraternização Universal",
        date(ano, 3, 19): "São José (CE)",
        date(ano, 3, 25): "Data Magna do Ceará",
        date(ano, 4, 21): "Tiradentes",
        date(ano, 5, 1): "Dia do Trabalho",
        date(ano, 9, 7): "Independência",
        date(ano, 10, 12): "N. Sra. Aparecida",
        date(ano, 11, 2): "Finados",
        date(ano, 11, 15): "Proclamação da República",
        date(ano, 11, 20): "Consciência Negra",
        date(ano, 12, 25): "Natal",
        p - timedelta(days=48): "Carnaval (ponto facultativo)",
        p - timedelta(days=47): "Carnaval (ponto facultativo)",
        p - timedelta(days=2): "Sexta-feira Santa",
        p + timedelta(days=60): "Corpus Christi (ponto facultativo)",
    }


def feriados(ano: int, extras: str = "") -> dict[date, str]:
    f = dict(_base(ano))
    for item in (extras or "").split(";"):
        m = re.match(r"\s*(\d{1,2})/(\d{1,2})\s+(.+?)\s*$", item)
        if not m:
            continue
        try:
            f[date(ano, int(m.group(2)), int(m.group(1)))] = m.group(3)
        except ValueError:
            continue
    return f
