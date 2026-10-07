"""Teste de aceitação (PLANEJAMENTO.md §5.5): a lista de outubro/2026 tem que gerar
exatamente as 42 linhas validadas em 07/10/2026."""
from conftest import FIXTURES

from app.normalizer import processar
from app.parser import ler


def test_outubro_2026_gera_as_42_linhas_validadas(texto_outubro, regras_seed):
    leitura = ler(texto_outubro)
    assert not leitura.erros
    assert len(leitura.linhas) == 53

    res = processar(leitura.linhas, regras_seed)
    assert res.pendentes == 0
    assert not res.conflitos
    assert res.contar("ignorada") == 1                      # NOVA NOTIFICAÇÃO TEF

    obtido = [f"{l.linha.data.strftime('%d/%m/%Y')}\t{l.nome}" for l in res.no_calendario]
    esperado = (FIXTURES / "outubro_2026_esperado.txt").read_text(encoding="utf-8").strip().splitlines()
    assert obtido == esperado
    assert len(obtido) == 42


def test_dia_15_tem_7_tarefas(texto_outubro, regras_seed):
    res = processar(ler(texto_outubro).linhas, regras_seed)
    dia15 = [l for l in res.no_calendario if l.linha.data.day == 15]
    assert len(dia15) == 7
