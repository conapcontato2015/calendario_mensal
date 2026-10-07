from datetime import date

import pytest

from app.normalizer import ConflitoRegras, Decisao, Regra, achar_regra, processar, sugerir
from app.parser import ler


def R(tipo, padrao, nome, acao="renomear"):
    return Regra(tipo, padrao, acao, nome)


def test_exata_vence_prefixo():
    regras = [R("prefixo", "PARCELAMENTO", "PARCELAMENTO"), R("exata", "PARCELAMENTO ISS", "PARC ISS")]
    assert achar_regra("PARCELAMENTO ISS", regras).nome_curto == "PARC ISS"


def test_prefixo_mais_longo_vence():
    regras = [R("prefixo", "PARCELAMENTO", "PARCELAMENTO"), R("prefixo", "PARCELAMENTO PGFN", "PGFN")]
    assert achar_regra("PARCELAMENTO PGFN TRANSACAO", regras).nome_curto == "PGFN"
    assert achar_regra("PARCELAMENTO RFB", regras).nome_curto == "PARCELAMENTO"


def test_empate_de_contem_e_conflito():
    regras = [R("contem", "ICMS", "A"), R("contem", "DIFA", "B")]
    with pytest.raises(ConflitoRegras):
        achar_regra("GUIA DIFAL ICMS", regras)


def test_regra_inativa_nao_casa():
    r = R("exata", "DAS", "DAS")
    r.ativa = False
    assert achar_regra("DAS", [r]) is None


def test_ignorar():
    res = processar(ler("NOVA NOTIFICAÇÃO TEF\t06/10/2026").linhas,
                    [R("exata", "NOVA NOTIFICACAO TEF", "", "ignorar")])
    assert res.linhas[0].status == "ignorada"
    assert not res.no_calendario


def test_agrupamento_por_dia_preserva_ordem():
    txt = ("Parcelamento A\t28/10/2026\nDAS\t28/10/2026\nParcelamento B\t28/10/2026\n"
           "Parcelamento C\t29/10/2026\nParcelamento D\t30/10/2026")
    res = processar(ler(txt).linhas, [R("prefixo", "PARCELAMENTO", "PARCELAMENTO"), R("exata", "DAS", "DAS")])
    dias = res.por_dia()
    assert [l.nome for l in dias[date(2026, 10, 28)]] == ["PARCELAMENTO", "DAS"]
    assert dias[date(2026, 10, 28)][0].originais == ["Parcelamento A", "Parcelamento B"]
    assert len(res.no_calendario) == 4   # 3 parcelamentos em dias diferentes viram 3


def test_nove_no_mesmo_dia_viram_um():
    txt = "\n".join(f"Parcelamento {i}\t28/10/2026" for i in range(9))
    res = processar(ler(txt).linhas, [R("prefixo", "PARCELAMENTO", "PARCELAMENTO")])
    assert len(res.no_calendario) == 1
    assert len(res.no_calendario[0].originais) == 9


def test_nome_sem_regra_fica_pendente_sem_sugestao():
    res = processar(ler("DEFIS - Declaração Anual\t20/11/2026").linhas, [R("exata", "DAS", "DAS")])
    assert res.pendentes == 1
    assert res.linhas[0].status == "pendente"
    assert res.novos[0].sugestao is None


def test_sugestao_por_semelhanca():
    regras = [R("exata", "CONSULTAR PENDENCIAS FISCAIS", "PENDÊNCIAS FISCAIS")]
    assert sugerir("CONSULTA SITUACAO FISCAL FEDERAL", regras) == "PENDÊNCIAS FISCAIS"
    res = processar(ler("Consulta Situação Fiscal Federal\t16/11/2026").linhas, regras)
    # a sugestão já vem preenchida, então não bloqueia
    assert res.pendentes == 0
    assert res.no_calendario[0].nome == "PENDÊNCIAS FISCAIS"
    assert res.no_calendario[0].nova


def test_decisao_exata_cria_regra_provisoria():
    res = processar(ler("DEFIS\t20/11/2026").linhas, [],
                    {"DEFIS": Decisao(nome="defis anual")})
    assert res.no_calendario[0].nome == "DEFIS ANUAL"
    assert [(r.tipo, r.padrao) for r in res.regras_novas] == [("exata", "DEFIS")]


def test_decisao_comeca_com_cobre_outros_nomes_novos():
    txt = "Consulta CND Federal\t10/11/2026\nConsulta CND Estadual\t10/11/2026\nConsulta CND Municipal\t11/11/2026"
    dec = {"CONSULTA CND FEDERAL": Decisao(nome="CND", prefixo=True, prefixo_txt="Consulta CND")}
    res = processar(ler(txt).linhas, [], dec, sugerir_padrao=False)
    assert res.pendentes == 0
    cobertos = [n for n in res.novos if n.coberto_por]
    assert len(cobertos) == 2 and cobertos[0].coberto_por == "CONSULTA CND"
    assert len(res.no_calendario) == 2      # 10/11 agrupa duas
    assert [(r.tipo, r.padrao) for r in res.regras_novas] == [("prefixo", "CONSULTA CND")]


def test_decisao_ignorar():
    res = processar(ler("Aviso X\t10/11/2026").linhas, [], {"AVISO X": Decisao(acao="ignorar")})
    assert res.linhas[0].status == "ignorada"
    assert res.regras_novas[0].acao == "ignorar"
