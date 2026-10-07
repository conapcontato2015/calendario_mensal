"""Fluxos completos pelas rotas (cliente de teste do Flask)."""
import re

from app import backup
from app.db import conectar


def _tarefas_ativas(cfg, data=None):
    conn = conectar(cfg.banco)
    sql = ("SELECT t.data, t.nome_curto FROM tarefas t JOIN lotes l ON l.id = t.lote_id "
           "WHERE l.status = 'ativo' AND t.removida = 0" + (" AND t.data = ?" if data else "") +
           " ORDER BY t.data, t.ordem")
    rows = conn.execute(sql, (data,) if data else ()).fetchall()
    conn.close()
    return [(r[0], r[1]) for r in rows]


def _importar(client, texto, **extra):
    dados = {"texto": texto, **extra}
    return client.post("/importar/confirmar", data=dados)


def test_paginas_abrem(client):
    for url in ["/", "/?mes=2026-10", "/importar", "/nomes", "/backups", "/historico", "/nomes?nova=1",
                "/nomes?teste=Parcelamento+PGFN"]:
        r = client.get(url)
        assert r.status_code == 200, url


def test_importar_outubro_e_ver_no_calendario(client, cfg, texto_outubro):
    r = _importar(client, texto_outubro)
    assert r.status_code == 302
    tarefas = _tarefas_ativas(cfg)
    assert len(tarefas) == 42
    assert len(_tarefas_ativas(cfg, "2026-10-15")) == 7
    html = client.get("/?mes=2026-10").get_data(as_text=True)
    assert "OUTUBRO" in html and "PARCELAMENTO" in html and "42 tarefas no mês" in html
    assert "N. Sra. Aparecida" in html
    # backup feito antes de gravar
    assert any("antes importacao" in b.motivo for b in backup.listar(cfg.pasta_backup))


def test_previa_mostra_contadores(client, texto_outubro):
    html = client.post("/importar/previa", data={"texto": texto_outubro}).get_data(as_text=True)
    assert "<b>53</b> linhas lidas" in html
    assert "<b>42</b> no calendário" in html
    assert "<b>1</b> ignoradas" in html
    assert "Pronto: 42 tarefas em outubro 2026" in html


def test_mes_ja_importado_exige_confirmacao_e_desfazer_volta(client, cfg, texto_outubro):
    _importar(client, texto_outubro)
    r = _importar(client, texto_outubro)
    assert r.status_code == 400
    assert "Confirme acima a substituição" in r.get_data(as_text=True)

    r = _importar(client, "DAS\t15/10/2026", substituir="1")
    assert r.status_code == 302
    assert _tarefas_ativas(cfg) == [("2026-10-15", "DAS")]

    conn = conectar(cfg.banco)
    lote = conn.execute("SELECT id FROM lotes WHERE status = 'ativo'").fetchone()[0]
    conn.close()
    client.post(f"/importar/{lote}/desfazer")
    assert len(_tarefas_ativas(cfg)) == 42


def test_nome_novo_bloqueia_ate_definir_e_vira_regra(client, cfg):
    texto = "DEFIS - Declaração de Informações Socioeconômicas\t20/11/2026\nDAS\t20/11/2026"
    html = client.post("/importar/previa", data={"texto": texto}).get_data(as_text=True)
    assert "1 nome novo" in html
    assert "Defina o nome novo acima para liberar." in html

    # confirmar sem decidir é recusado
    assert _importar(client, texto).status_code == 400

    k = "DEFIS - DECLARACAO DE INFORMACOES SOCIOECONOMICAS"
    r = _importar(client, texto, **{"dec-0-chave": k, "dec-0-nome": "defis"})
    assert r.status_code == 302
    assert _tarefas_ativas(cfg) == [("2026-11-20", "DEFIS"), ("2026-11-20", "DAS")]
    # a regra ficou salva: no mês seguinte não pergunta de novo
    html = client.post("/importar/previa", data={"texto": "DEFIS - Declaração de Informações Socioeconômicas\t20/12/2026"}).get_data(as_text=True)
    assert "nome novo" not in html.replace("<b>0</b> nomes novos", "")


def test_desfazer_desativa_regras_criadas(client, cfg):
    k = "AVISO TESTE"
    _importar(client, "Aviso teste\t10/11/2026", **{"dec-0-chave": k, "dec-0-nome": "AVISO"})
    conn = conectar(cfg.banco)
    lote = conn.execute("SELECT id FROM lotes WHERE status='ativo'").fetchone()[0]
    conn.close()
    client.post(f"/importar/{lote}/desfazer")
    conn = conectar(cfg.banco)
    ativa = conn.execute("SELECT ativa FROM regras WHERE padrao = ?", (k,)).fetchone()[0]
    conn.close()
    assert ativa == 0
    assert _tarefas_ativas(cfg) == []


def test_edicao_avulsa_com_desfazer(client, cfg, texto_outubro):
    _importar(client, texto_outubro)
    client.post("/tarefa/adicionar", data={"data": "2026-10-14", "nome": "reunião fiscal"})
    assert ("2026-10-14", "REUNIÃO FISCAL") in _tarefas_ativas(cfg, "2026-10-14")
    # repetido no mesmo dia é recusado
    client.post("/tarefa/adicionar", data={"data": "2026-10-14", "nome": "Reunião Fiscal"})
    assert len(_tarefas_ativas(cfg, "2026-10-14")) == 2

    conn = conectar(cfg.banco)
    tid = conn.execute("SELECT id FROM tarefas WHERE nome_curto = 'DIFAL NC'").fetchone()[0]
    conn.close()
    client.post(f"/tarefa/{tid}/renomear", data={"nome": "difal nao contribuinte"})
    assert ("2026-10-14", "DIFAL NAO CONTRIBUINTE") in _tarefas_ativas(cfg, "2026-10-14")
    client.post(f"/tarefa/{tid}/remover")
    assert ("2026-10-14", "DIFAL NAO CONTRIBUINTE") not in _tarefas_ativas(cfg, "2026-10-14")
    client.post(f"/tarefa/{tid}/restaurar")
    assert ("2026-10-14", "DIFAL NAO CONTRIBUINTE") in _tarefas_ativas(cfg, "2026-10-14")

    html = client.get("/?mes=2026-10&dia=2026-10-14").get_data(as_text=True)
    assert "Adicionada manualmente" in html and "Tarefas do dia" in html


def test_voltar_externo_e_ignorado(client, cfg, texto_outubro):
    _importar(client, texto_outubro)
    conn = conectar(cfg.banco)
    tid = conn.execute("SELECT id FROM tarefas LIMIT 1").fetchone()[0]
    conn.close()
    r = client.post(f"/tarefa/{tid}/remover", data={"voltar": "https://exemplo.com"})
    assert r.headers["Location"].startswith("/")


def test_regras_criar_editar_desativar_e_reaplicar(client, cfg, texto_outubro):
    _importar(client, texto_outubro)
    # editar o nome de DAS e reaplicar ao mês
    conn = conectar(cfg.banco)
    rid = conn.execute("SELECT id FROM regras WHERE padrao = 'DAS'").fetchone()[0]
    conn.close()
    client.post("/nomes/salvar", data={"id": rid, "tipo": "exata", "padrao": "DAS", "acao": "renomear",
                                       "nome": "DAS SIMPLES"})
    html = client.get("/mes/2026-10/reaplicar").get_data(as_text=True)
    assert "1 dia(s) mudam" in html and "DAS SIMPLES" in html
    client.post("/mes/2026-10/reaplicar")
    assert ("2026-10-15", "DAS SIMPLES") in _tarefas_ativas(cfg, "2026-10-15")

    # criar regra duplicada é recusado
    client.post("/nomes/salvar", data={"tipo": "exata", "padrao": "das", "acao": "renomear", "nome": "X"})
    conn = conectar(cfg.banco)
    assert conn.execute("SELECT COUNT(*) FROM regras WHERE padrao = 'DAS'").fetchone()[0] == 1
    conn.close()

    # desativar e reativar
    client.post(f"/nomes/{rid}/alternar")
    conn = conectar(cfg.banco)
    assert conn.execute("SELECT ativa FROM regras WHERE id = ?", (rid,)).fetchone()[0] == 0
    conn.close()
    html = client.get("/nomes?teste=DAS").get_data(as_text=True)
    assert "Nenhuma regra pega este nome" in html


def test_exportar_e_importar_regras(client):
    r = client.get("/nomes/exportar")
    assert r.status_code == 200 and b"PARCELAMENTO" in r.data
    import io
    dados = {"arquivo": (io.BytesIO(b'[{"tipo":"exata","padrao":"Nova tarefa","acao":"renomear","nome_curto":"NOVA"}]'),
                         "regras.json")}
    client.post("/nomes/importar", data=dados, content_type="multipart/form-data")
    html = client.get("/nomes?q=nova+tarefa").get_data(as_text=True)
    assert "NOVA TAREFA" in html


def test_backup_manual_e_restaurar(client, cfg, texto_outubro):
    client.post("/backups/criar")
    itens = backup.listar(cfg.pasta_backup)
    assert itens
    nome = itens[0].arquivo.name
    _importar(client, texto_outubro)
    assert len(_tarefas_ativas(cfg)) == 42
    # sem confirmação não restaura
    client.post(f"/backups/{nome}/restaurar")
    assert len(_tarefas_ativas(cfg)) == 42
    client.post(f"/backups/{nome}/restaurar", data={"confirmo": "1"})
    assert _tarefas_ativas(cfg) == []
    html = client.get("/historico").get_data(as_text=True)
    assert "backup restaurado" in html


def test_semana_comecando_na_segunda(cfg, texto_outubro):
    from app import create_app
    cfg.semana_comeca = "segunda"
    c = create_app(cfg).test_client()
    _importar(c, texto_outubro)
    html = c.get("/?mes=2026-10").get_data(as_text=True)
    cab = re.findall(r'<div class="dow">(\w+)</div>', html)
    assert cab[0] == "Seg" and cab[-1] == "Dom"
