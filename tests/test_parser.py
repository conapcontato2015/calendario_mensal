from datetime import date

from app.parser import ler
from app.textutil import chave


def test_chave_normaliza_caixa_acento_espacos():
    assert chave("  Salvar Arquivo   ONVIO FISCAL ") == "SALVAR ARQUIVO ONVIO FISCAL"
    assert chave("Provisão PIS/COFINS Mês") == "PROVISAO PIS/COFINS MES"


def test_tab_e_espacos_como_separador():
    r = ler("DAS\t15/10/2026\nEFD ICMS IPI    20/10/2026\nSIGET 23/10/2026")
    assert [(l.original, l.data) for l in r.linhas] == [
        ("DAS", date(2026, 10, 15)), ("EFD ICMS IPI", date(2026, 10, 20)), ("SIGET", date(2026, 10, 23))]
    assert not r.erros


def test_linha_vazia_ignorada_e_cabecalho_rejeitado():
    r = ler("Tarefa\tData\n\n   \nDAS\t15/10/2026\n")
    assert len(r.linhas) == 1
    assert len(r.erros) == 1 and r.erros[0].numero == 1


def test_data_inexistente_rejeitada():
    r = ler("Guia DIFAL\t31/11/2026")
    assert not r.linhas
    assert "não existe" in r.erros[0].motivo


def test_data_com_um_digito():
    r = ler("DAS\t5/1/2027")
    assert r.linhas[0].data == date(2027, 1, 5)


def test_nome_com_barra_e_hifen():
    r = ler("MIT / DCTF\t30/10/2026\nEFD - Reinf\t15/10/2026")
    assert [l.chave for l in r.linhas] == ["MIT / DCTF", "EFD - REINF"]


def test_mes_de_referencia_e_fora_do_mes():
    r = ler("A\t30/09/2026\nB\t01/10/2026\nC\t02/10/2026")
    assert r.mes_ref == "2026-10"
    assert [l.original for l in r.fora_do_mes] == ["A"]
