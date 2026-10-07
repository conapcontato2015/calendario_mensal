# Calendário de Tarefas — Planejamento

> Sistema local para transformar a lista de tarefas exportada do sistema em um calendário mensal com nomes simplificados.
> Status: **v1 implementada** · Versão do documento: 1.2 · 07/10/2026
> 1.1: revisão de usabilidade (§12), fluxo de importação em tela única, edição avulsa e desfazer entram na v1.
> 1.2: decisões D1–D6 aceitas; ajustes da implementação: JavaScript próprio no lugar do HTMX, sem fontes externas (funciona sem internet), uma linha por tarefa do calendário com os nomes originais agrupados (§6.2), feriados nacionais e do Ceará.

---

## 1. Objetivo

Todo mês, colar a lista de tarefas exportada (nome longo + data) e obter, sem retrabalho:

1. os nomes **simplificados** por um dicionário de regras que aprende com o uso;
2. um **calendário mensal** pronto para consulta e impressão.

Substitui a planilha `Calendário Mensal.xlsx`, cujas fórmulas `CONT.SE` com intervalos manuais escondiam tarefas e limitavam o dia a 5 itens.

## 2. Premissas (definidas pelo usuário)

| Premissa | Consequência no projeto |
|---|---|
| Uso individual ou do setor, todos com as mesmas tarefas | Um único calendário compartilhado, sem separar por pessoa |
| Sem login e sem identificar o usuário | Nenhuma autenticação; segurança vem de backup e de não ter exclusão definitiva (ver §8) |
| Servidor ligado só durante o uso | Inicia por um `.bat` e encerra ao fechar; nada de serviço do Windows |
| Código no GitHub, atualizado via VS Code | Dados nunca vão para o Git; atualizações não podem quebrar o banco |
| Acesso pela rede local | Servidor escuta na rede, mas só em rede privada |

## 3. Escopo da v1

**Dentro**
- Importar tarefas colando o texto (tarefa + data).
- Normalizar nomes pelo dicionário, com prévia antes de salvar.
- Resolver na hora as tarefas sem regra; a regra criada fica salva.
- Regra de agrupamento: **mesmo nome curto no mesmo dia aparece uma vez só**.
- Regra de **ignorar** (ex.: "NOVA NOTIFICAÇÃO TEF" não entra no calendário).
- Calendário mensal sem limite de tarefas por dia, com impressão em A4 paisagem.
- Gerenciar o dicionário (criar, editar, desativar regras).
- **Edição avulsa no calendário:** adicionar, renomear ou remover uma tarefa sem reimportar o mês.
- **Desfazer** a última importação com um clique.
- Backup automático e restauração.

**Fora da v1** (pode vir depois)
- Marcar tarefa como concluída.
- Login, usuários e permissões.
- Exportar para Excel.
- Integração direta com o sistema de origem (continua sendo copiar e colar).
- Ajuste automático de datas em feriados ou fins de semana.

## 4. Fluxo de uso

```
Abrir sistema ──► Calendário do mês atual ──► [Importar mês] ──► Colar ──► Resolver pendentes (se houver) ──► Confirmar ──► volta ao calendário
                                                                (prévia aparece na mesma tela)                (backup + "Desfazer")
```

1. **Abrir:** o sistema abre direto no calendário do mês atual.
2. **Importar:** uma única tela. Ao colar, a prévia aparece imediatamente abaixo. O mês é detectado pelas datas.
3. **Pendentes:** ficam no topo da prévia, cada uma com o campo do nome curto já sugerido. O botão Confirmar só libera quando não restar pendência.
4. **Confirmar:** backup, gravação e retorno ao calendário, com aviso "Importado · Desfazer".

Detalhes de tela em §12.

## 5. Regras de normalização

### 5.1 Chave de comparação

Antes de comparar, o nome original vira uma **chave**: maiúsculas, sem acentos, espaços repetidos reduzidos a um, sem espaços nas pontas.

> Exemplo: `"Salvar Arquivo ONVIO FISCAL "` → `SALVAR ARQUIVO ONVIO FISCAL`

Assim, diferenças de caixa, acento e espaço sobrando não geram regras duplicadas.

### 5.2 Tipos de regra

| Tipo | Casa quando | Exemplo |
|---|---|---|
| `exata` | a chave é igual ao padrão | `PROVISAO PIS/COFINS DIA 10` → PROVISÃO PIS/COFINS DIA 10 |
| `prefixo` | a chave começa com o padrão | `PARCELAMENTO` → PARCELAMENTO |
| `contem` | a chave contém o padrão | (reservado; usar com cuidado) |

Cada regra tem uma **ação**: `renomear` (usa o nome curto) ou `ignorar` (a tarefa não entra).

### 5.3 Ordem de aplicação

1. Regra `exata`.
2. Regra `prefixo`; se mais de uma casar, vence o **padrão mais longo**.
3. Regra `contem`, pela mesma lógica.
4. Nada casou → **pendente**. Nunca inventar nome.

Se duas regras do mesmo tipo e tamanho casarem, a importação para e o conflito é mostrado. Não existe escolha silenciosa.

### 5.4 Agrupamento por dia

Depois de normalizar, tarefas com o **mesmo nome curto na mesma data** viram uma só. Dentro do dia, a ordem é a da primeira aparição na lista colada.

### 5.5 Regras iniciais (seed)

Pré-carregadas com o mapeamento fechado em outubro/2026:

| Original (chave) | Tipo | Ação / nome curto |
|---|---|---|
| PARCELAMENTO | prefixo | PARCELAMENTO |
| NOVA NOTIFICACAO TEF | exata | ignorar |
| PROVISAO PIS/COFINS MES | exata | PROVISÃO PIS/COFINS MÊS |
| FECHAMENTO ISSQN | exata | FECHAMENTO ISSQN |
| SOLICITACAO ARQUIVOS/EXTRATOS BANCARIOS | exata | SOLICITAÇÃO DE ARQUIVOS |
| ISS - SERVICOS PRESTADOS | exata | ISS - SERVIÇOS PRESTADOS |
| ISS RETIDO - SERVICOS TOMADOS | exata | ISS RETIDO - SERVIÇOS TOMADOS |
| RELATORIO RECEBIMENTOS - CAIXA - DIA 2 | exata | RELATÓRIO RECEB. - CAIXA |
| RETENCOES INSS | exata | RETENÇÕES INSS |
| PROVISAO PIS/COFINS DIA 10 | exata | PROVISÃO PIS/COFINS DIA 10 |
| COBRANCA DE CONTRATOS IMOBILIARIOS | exata | COB. DE CONTRATOS |
| DIFAL NC | exata | DIFAL NC |
| EFD CONTRIBUICOES | exata | EFD CONTRIBUIÇÕES |
| CONSULTAR PENDENCIAS FISCAIS | exata | PENDÊNCIAS FISCAIS |
| EFD - REINF | exata | EFD - REINF |
| DAS | exata | DAS |
| GUIA DE ARRECADACAO DO ICMS | exata | GUIA DE ARREC. DO ICMS |
| GUIA DE ICMS SUBSTITUICAO TRIBUTARIA | exata | GUIA DE ICMS ST |
| DARF UNIFICADO | exata | DARF UNIFICADO |
| DARF FUNRURAL | exata | DARF FUNRURAL |
| FECOP | exata | DAE FECOP |
| DARF CSRF | exata | DARF CSRF |
| DARF PIS/COFINS NAO COMULATIVO | exata | DARF PIS/COFINS NÃO CUMULATIVO |
| DARF PIS/COFINS CUMULATIVO | exata | DARF PIS/COFINS CUMULATIVO |
| DARF IPI | exata | DARF IPI |
| EFD ICMS IPI | exata | EFD ICMS IPI |
| PROVISAO PIS/COFINS DIA 20 | exata | PROVISÃO PIS/COFINS DIA 20 |
| REGULARIZACAO NFE NAO REGISTRADAS NO SITRAM | exata | NFE PEND. SELAGEM |
| DARF IRPJ E CSLL MENSAL | exata | IRPJ E CSLL MENSAL |
| RELATORIO - DIVISAO DE DAS | exata | RELATÓRIO - DIVISÃO DAS |
| SIGET | exata | SIGET |
| DARF QUOTAS IRPJ/CSLL | exata | QUOTAS IRPJ/CSLL |
| SALVAR ARQUIVO ONVIO FISCAL | exata | SALVAR ARQ. ONVIO |
| LANCAMENTO E IMPORTACAO DE DOCUMENTOS FISCAIS | exata | LANÇ. E IMP. DE DOCS. FISC. |
| RELATORIO - DIVISAO DE PIS/COFINS | exata | RELATÓRIO - DIVISÃO PIS/COFINS |
| GUIA IRPJ E CSLL LUCRO REAL | exata | GUIA IR E CS L. REAL |
| GUIA IRPJ E CSLL LUCRO PRESUMIDO | exata | GUIA IR E CS L. PRES. |
| LANCAMENTO DE TOMADOR | exata | LANÇ. DE TOMADOR |
| MIT / DCTF | exata | MIT / DCTF |
| EMISSAO DE NFS-E | exata | EMISSÃO DE NFS-E |

Teste de aceitação: importar a lista de outubro/2026 tem que produzir exatamente as 42 linhas validadas em 07/10/2026.

## 6. Arquitetura

| Peça | Escolha | Motivo |
|---|---|---|
| Linguagem | Python 3.12+ | Já usado nos outros sistemas |
| Web | Flask + Jinja | Simples e conhecido |
| Interação | JavaScript próprio (~100 linhas, `app/static/app.js`) | Prévia ao colar sem recarregar a página; nenhuma biblioteca externa para baixar |
| Estilo | CSS próprio, com `@media print` | Impressão A4 paisagem |
| Banco | SQLite em modo WAL | Arquivo único, sem instalação, aguenta alguns acessos simultâneos |
| Migrações | Scripts SQL numerados + tabela `schema_version` | Atualizar pelo Git sem perder dados |
| Servidor | Waitress | Estável no Windows e adequado à rede local |
| Testes | pytest | Cobrir parser, normalização e agrupamento |

### 6.1 Estrutura do repositório

```
calendario-tarefas/
├── app/
│   ├── __init__.py          # create_app()
│   ├── db.py                # conexão, WAL, migrações
│   ├── parser.py            # texto colado → linhas (tarefa, data)
│   ├── normalizer.py        # chave, regras, agrupamento
│   ├── backup.py
│   ├── routes/              # importar, calendario, regras, backups
│   ├── templates/
│   └── static/
├── migrations/              # 001_inicial.sql, 002_..., ...
├── seed/regras.json         # regras iniciais (§5.5)
├── tests/
├── dados/                   # banco + backups  (fora do Git)
├── iniciar.bat
├── config.example.env
├── requirements.txt
└── README.md
```

### 6.2 Modelo de dados

```
regras      id, tipo(exata|prefixo|contem), padrao_chave, acao(renomear|ignorar),
            nome_curto, ativa, criada_em, atualizada_em
lotes       id, mes_ref(AAAA-MM), texto_colado, criado_em, ip_origem, status(ativo|substituido)
tarefas     id, lote_id, data, nome_curto, originais_json, regra_id, ordem, manual, removida
            (uma linha por tarefa do calendário; originais_json lista os nomes do sistema agrupados nela)
log         id, quando, ip_origem, acao, detalhe
schema_version  versao
```

- `texto_colado` guarda a entrada bruta: sempre dá para auditar ou reprocessar.
- `tarefas` guarda o nome original **e** o nome curto aplicado, mais a regra usada.
- Nada é apagado de fato: lotes substituídos e regras desativadas ficam marcados.

## 7. Operação

- **Iniciar:** `iniciar.bat` cria o `venv` na primeira vez, instala as dependências, aplica migrações pendentes, faz um backup de abertura, sobe o servidor e abre o navegador. Na tela aparecem o endereço local e o de rede.
- **Encerrar:** fechar a janela do `.bat` (Ctrl+C).
- **Rede:** escuta em `0.0.0.0` numa porta configurável (padrão `5050`). Liberar no Firewall do Windows **só no perfil "Rede privada"**. IP fixo no roteador, ou acesso pelo nome do computador.
- **Atualizar:** encerrar o servidor → `git pull` → `iniciar.bat`. As migrações rodam sozinhas, sempre com backup antes.

## 8. Fragilidades identificadas e tratamento

| # | Fragilidade | Risco | Tratamento |
|---|---|---|---|
| F1 | Formato do texto colado varia: tab, espaços, linha em branco, cabeçalho, data com 1 dígito | Linhas perdidas ou data errada | Parser aceita tab e 2+ espaços como separador e só a data `dd/mm/aaaa` no fim da linha. Linhas não reconhecidas aparecem na prévia como **rejeitadas**, nunca descartadas em silêncio |
| F2 | Variações de caixa, acento e espaço (ex.: `"ONVIO "`) | Regras duplicadas, pendências falsas | Chave normalizada (§5.1) |
| F3 | Regras que se sobrepõem | Nome errado sem ninguém perceber | Precedência fixa (§5.3); empate bloqueia e mostra o conflito; tela de regras alerta sobreposição ao salvar |
| F4 | Regra genérica demais "engole" tarefas novas (ex.: prefixo `PARCELAMENTO`) | Tarefa nova escondida no agrupamento | Prévia mostra o original de cada linha agrupada; tipo `contem` desencorajado |
| F5 | Importar o mesmo mês duas vezes | Tarefas duplicadas | Se já existe lote ativo do mês: perguntar **substituir** (o antigo vira `substituido`) ou **cancelar**. Nunca somar em silêncio |
| F6 | Lista com datas de meses diferentes | Calendário misturado | Prévia avisa as datas fora do mês de referência; usuário confirma |
| F7 | Mudar uma regra depois da importação | Meses antigos com nome desatualizado | Tarefas guardam o nome aplicado (histórico fiel). Botão "reaplicar regras ao mês" com prévia |
| F8 | Sem login, qualquer pessoa da rede pode alterar | Exclusão ou edição acidental | Só exclusão lógica; backup antes de toda escrita relevante; log com IP; restauração pela interface. Risco aceito conforme a premissa |
| F9 | `git pull` com o servidor rodando, ou mudança de esquema | Banco corrompido ou incompatível | README e `.bat` orientam a encerrar antes; migrações versionadas com backup antes; app recusa iniciar se o banco for de versão mais nova que o código |
| F10 | Banco e backups no mesmo disco | Perda total se o disco falhar | Pasta de backup configurável (pode apontar para OneDrive ou pasta de rede); rotação mantém os últimos 30; botão "baixar backup" |
| F11 | Dicionário perdido ou divergente entre máquinas | Retrabalho mensal | Exportar e importar regras em JSON; `seed/regras.json` recria tudo do zero |
| F12 | Dois acessos gravando ao mesmo tempo | `database is locked` | Modo WAL + `busy_timeout`; volume do setor é baixíssimo |
| F13 | IP do PC muda (DHCP) | Colegas não acham o sistema | IP fixo no roteador ou nome do PC; `.bat` mostra o endereço atual |
| F14 | Porta ocupada, firewall bloqueando, Python ausente | Não inicia | `.bat` verifica Python e porta e mostra mensagem clara; README cobre o firewall |
| F15 | Dia com muitas tarefas ou nome longo | Impressão quebrada | Célula cresce com o conteúdo; CSS de impressão com fonte reduzida; teste visual com 15/10/2026 (7 tarefas) |
| F16 | Datas digitadas por extenso ou em outro formato | Data inválida | Só `dd/mm/aaaa`; fora disso a linha é rejeitada na prévia |
| F17 | Crescimento do escopo | v1 nunca termina | §3 é o contrato da v1; o resto vai para o backlog |

## 9. Testes

- **Parser:** tab e espaços, linha vazia, cabeçalho, data inválida, nome com `/` e `-`.
- **Normalizador:** chave (acentos, caixa, espaços), precedência, empate bloqueia, ação ignorar.
- **Agrupamento:** 3 parcelamentos em dias diferentes viram 3; 9 no mesmo dia viram 1; ordem preservada.
- **Aceitação:** lista de outubro/2026 → as 42 linhas validadas.
- **Migrações:** banco vazio e banco da versão anterior chegam à versão atual sem perda.

## 10. Etapas de desenvolvimento

1. Esqueleto: Flask, SQLite com migrações, `iniciar.bat`, backup de abertura.
2. Parser + normalizador + seed + testes (incluindo o de aceitação).
3. Tela de importação única: prévia ao colar, contadores, pendências com sugestão, confirmação e desfazer (§12.4).
4. Calendário mensal: hover, painel do dia com edição avulsa, estado vazio, impressão e layout para celular (§12.3, §12.6).
5. Tela de regras (CRUD, alerta de sobreposição, exportar e importar).
6. Backups pela interface, log e "reaplicar regras ao mês".
7. README final e teste em rede com outro computador.

## 11. Decisões (todas aceitas como recomendado em 07/10/2026)

| # | Pergunta | Recomendação |
|---|---|---|
| D1 | Reimportar um mês: substituir ou mesclar com o existente? | Substituir, com confirmação |
| D2 | Mostrar sábado e domingo no calendário? | Mostrar, mais estreitos |
| D3 | Onde ficam os backups? | Pasta local por padrão, configurável para OneDrive ou rede |
| D4 | Importar o histórico da planilha antiga (2023–2026)? | Não. Começar em outubro/2026 |
| D5 | Semana começa no domingo ou na segunda? | Domingo, igual à planilha, configurável |
| D6 | Cores por categoria no calendário (DARF, EFD, guias...)? | Deixar para v2; v1 em uma cor só |

## 12. Interface e usabilidade

### 12.1 Princípios

- **O uso normal é uma ação por mês:** importar e consultar. Todo o resto (regras, backups, log) fica fora do caminho, em **Configurações**.
- **Nada técnico na tela.** Nada de "lote", "chave" ou "prefixo". Use "importação", "nome no sistema" e "tudo que começa com...".
- **Nenhuma decisão escondida.** O que foi agrupado ou ignorado sempre pode ser visto, mas não polui a visão padrão.
- **Errar é barato:** desfazer, edição avulsa e confirmação só onde se perde dado.

### 12.2 Mapa de telas

```
┌ Calendário (tela inicial) ─────────────┐
│  ‹ OUTUBRO 2026 ›   [Hoje]   [Importar mês]   [Imprimir]   ⚙ │
└────────────────────────────────────────┘
        │                        │
   Importar mês            ⚙ Configurações
                           ├ Nomes (dicionário)
                           ├ Backups
                           └ Histórico de alterações
```

São só duas telas de uso diário. As de Configurações são raras.

### 12.3 Calendário (tela inicial)

```
 ‹  OUTUBRO 2026  ›    [Hoje]                         [Importar mês]  [Imprimir]  ⚙
┌──────┬──────────────────┬──────────────────┬──────────────────┬───── ─ ─
│ DOM  │ SEG              │ TER              │ QUA              │ QUI
├──────┼──────────────────┼──────────────────┼──────────────────┼───── ─ ─
│ 11   │ 12               │ 13             3 │ 14             1 │ 15            7
│      │                  │ RETENÇÕES INSS   │ DIFAL NC         │ EFD CONTRIBUIÇÕES
│      │                  │ PROVISÃO PIS/... │                  │ PENDÊNCIAS FISCAIS
│      │                  │ COB. DE CONTRATOS│                  │ EFD - REINF
│      │                  │                  │                  │ PARCELAMENTO  ⓘ
│      │                  │                  │                  │ ...
```

- Abre no mês atual; **hoje** com borda destacada.
- Sábado e domingo em colunas estreitas; dias de outro mês esmaecidos e sem tarefas.
- Contador de tarefas no canto de cada dia.
- **Passar o mouse ou tocar numa tarefa** mostra o(s) nome(s) original(is). O ⓘ indica tarefa agrupada ("PARCELAMENTO" → 9 parcelamentos).
- **Clicar no dia** abre um painel lateral com a lista do dia e as ações: adicionar, renomear e remover.
- **Mês sem importação:** tela vazia com uma única mensagem e o botão "Importar tarefas de NOVEMBRO".
- **Tela pequena (celular de colega):** a grade vira uma lista por dia.

### 12.4 Importar mês (tela única)

```
 Importar tarefas                                                     [Cancelar]
┌───────────────────────────────────────────────────────────────────────────────┐
│ Cole aqui a lista exportada do sistema (Ctrl+V)                               │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
 Mês detectado: OUTUBRO 2026
 54 linhas lidas · 42 no calendário · 10 agrupadas · 1 ignorada · 1 pendente · 0 com erro

 ⚠ 1 nome novo — defina como aparece no calendário
   "Parcelamento Simplificado - RFB - 5"   →  [ PARCELAMENTO          ▾]  ( ) ignorar
                                              sugestão: parece com PARCELAMENTO

 Resultado                                              [ver linhas originais ▸]
   06/10  PROVISÃO PIS/COFINS MÊS
   07/10  FECHAMENTO ISSQN · SOLICITAÇÃO DE ARQUIVOS · ISS - SERVIÇOS PRESTADOS · ...
   ...
                                                          [Confirmar importação]
```

- A prévia é gerada **ao colar**, sem botão "processar".
- **Contadores no topo** dão a conferência em 2 segundos.
- **Pendências primeiro**, com sugestão automática por semelhança com nomes já existentes. Aceitar a sugestão é um clique.
- O campo do nome curto completa automaticamente com os nomes já usados, o que evita criar "PARCELAMENTOS" e "PARCELAMENTO" ao mesmo tempo.
- A regra criada é `exata` por padrão. A opção "aplicar também a tudo que começa com..." fica num link discreto.
- **Visão padrão = resultado final**, agrupado por dia, igual ao calendário. As linhas originais (com agrupadas e ignoradas e o motivo) ficam atrás de "ver linhas originais".
- **Linhas com erro** (data inválida etc.) aparecem em vermelho no topo, com o texto original, e não bloqueiam o resto.
- **Mês já importado:** aviso antes de confirmar: "Outubro já tem 42 tarefas. Substituir?".
- O botão Confirmar fica desabilitado enquanto houver pendência, e diz o motivo.

### 12.5 Nomes (dicionário)

- Lista com busca: **nome no sistema → nome no calendário**, quantas vezes foi usado e quando foi usado por último.
- Filtros: todas, ignoradas, "tudo que começa com", não usadas há mais de 6 meses.
- **Campo de teste:** cola um nome e mostra qual regra pega. Serve para depurar regras.
- Editar oferece "aplicar também a meses já importados?", com prévia.
- Desativar em vez de excluir.

### 12.6 Impressão

- O botão **Imprimir** abre a impressão do navegador já formatada: A4 paisagem, sem menus, título "OUTUBRO 2026", com o mês inteiro numa página.
- Dias com muitas tarefas reduzem a fonte só naquela célula.

### 12.7 Retorno ao usuário

- **Avisos curtos** no canto, que somem sozinhos: "Importado · Desfazer", "Tarefa removida · Desfazer", "Regra salva".
- **Confirmação modal** só para substituir um mês ou restaurar backup.
- **Erros em português simples**, com o que fazer: "Esta linha não tem data no formato dd/mm/aaaa".

### 12.8 Visual

- Fundo claro, uma cor de destaque, tipografia legível em tela e papel (nomes em maiúsculas, como hoje).
- Hierarquia visual: data do dia > tarefas > contador.
- Contraste adequado para impressão em preto e branco.

### 12.9 Fragilidades de usabilidade

| # | Fragilidade | Tratamento |
|---|---|---|
| U1 | Nome curto perde informação (qual parcelamento?) | Nome original no hover, ⓘ em agrupadas, painel do dia |
| U2 | Sinônimos criados por engano ("PARCELAMENTOS" × "PARCELAMENTO") | Autocompletar com nomes existentes + sugestão por semelhança |
| U3 | "Prefixo" é conceito técnico | Linguagem "tudo que começa com..." e padrão `exata` |
| U4 | Ajuste pequeno exigiria reimportar o mês | Edição avulsa no painel do dia |
| U5 | Medo de clicar em Confirmar | Contadores + Desfazer logo depois |
| U6 | Dia com 7 ou mais tarefas quebra a grade | Célula cresce na tela; fonte reduzida só na impressão |
| U7 | Colega abre no celular | Layout em lista em telas pequenas |
| U8 | Esquecer em que mês está | Mês sempre visível no topo; botão "Hoje" |
