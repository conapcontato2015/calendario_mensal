-- Esquema inicial do Calendário de Tarefas

CREATE TABLE lotes (
    id                  INTEGER PRIMARY KEY,
    mes_ref             TEXT NOT NULL,                 -- AAAA-MM
    origem              TEXT NOT NULL DEFAULT 'importacao'
                        CHECK (origem IN ('importacao', 'manual', 'reaplicacao')),
    texto_colado        TEXT NOT NULL DEFAULT '',
    criado_em           TEXT NOT NULL,
    ip_origem           TEXT NOT NULL DEFAULT '',
    status              TEXT NOT NULL DEFAULT 'ativo'
                        CHECK (status IN ('ativo', 'substituido', 'desfeito')),
    substituiu_lote_id  INTEGER REFERENCES lotes(id)
);
CREATE INDEX ix_lotes_mes ON lotes (mes_ref, status);

CREATE TABLE regras (
    id              INTEGER PRIMARY KEY,
    tipo            TEXT NOT NULL CHECK (tipo IN ('exata', 'prefixo', 'contem')),
    padrao          TEXT NOT NULL,                     -- chave normalizada
    acao            TEXT NOT NULL CHECK (acao IN ('renomear', 'ignorar')),
    nome_curto      TEXT NOT NULL DEFAULT '',
    ativa           INTEGER NOT NULL DEFAULT 1,
    criada_em       TEXT NOT NULL,
    atualizada_em   TEXT NOT NULL,
    criada_no_lote  INTEGER REFERENCES lotes(id),
    UNIQUE (tipo, padrao)
);

CREATE TABLE tarefas (
    id              INTEGER PRIMARY KEY,
    lote_id         INTEGER NOT NULL REFERENCES lotes(id),
    data            TEXT NOT NULL,                     -- AAAA-MM-DD
    nome_curto      TEXT NOT NULL,
    originais_json  TEXT NOT NULL DEFAULT '[]',        -- nomes do sistema agrupados nesta tarefa
    regra_id        INTEGER REFERENCES regras(id),
    ordem           INTEGER NOT NULL DEFAULT 0,
    manual          INTEGER NOT NULL DEFAULT 0,
    removida        INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX ix_tarefas_data ON tarefas (data);
CREATE INDEX ix_tarefas_lote ON tarefas (lote_id);

CREATE TABLE log (
    id       INTEGER PRIMARY KEY,
    quando   TEXT NOT NULL,
    ip       TEXT NOT NULL DEFAULT '',
    acao     TEXT NOT NULL,
    detalhe  TEXT NOT NULL DEFAULT ''
);
