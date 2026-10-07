# Calendário de Tarefas

Sistema local para transformar a lista de tarefas exportada do sistema em um calendário mensal com nomes simplificados. Roda no seu computador e pode ser acessado pelos colegas na mesma rede. O planejamento completo está em [PLANEJAMENTO.md](PLANEJAMENTO.md).

## Primeira vez

1. Instale o **Python 3.10 ou mais novo** ([python.org/downloads](https://www.python.org/downloads/)) e marque **"Add python.exe to PATH"** na instalação.
2. Clone o repositório pelo VS Code (ou `git clone https://github.com/conapcontato2015/calendario_mensal.git`).
3. Dê dois cliques em **`iniciar.bat`**.
   - Na primeira vez ele prepara o ambiente e instala as dependências (cerca de 1 minuto, precisa de internet).
   - O navegador abre sozinho no calendário.
4. Na primeira abertura, o Windows pergunta sobre o **Firewall**: marque só **"Redes privadas"** e permita. Isso libera o acesso dos colegas na rede do escritório.

## Uso do dia a dia

| O que fazer | Como |
|---|---|
| Abrir o sistema | Dois cliques em `iniciar.bat` |
| Encerrar | Fechar a janela preta (ou Ctrl+C nela) |
| Importar o mês | **Importar mês** → colar a lista → resolver os nomes novos (se houver) → **Confirmar importação** |
| Corrigir uma tarefa | Clicar no dia → Renomear / Remover / Adicionar |
| Desfazer | Botão **Desfazer** no aviso que aparece logo depois de cada ação |
| Imprimir | Botão **Imprimir** no calendário (A4 paisagem) |
| Mudar um nome curto | ⚙ Configurações › Nomes › Editar. Depois, no calendário, **Reaplicar nomes** |

A janela preta mostra o endereço para os colegas, algo como `http://192.168.0.15:5050`. Vale pedir para fixar o IP do seu computador no roteador, para o endereço não mudar.

## Atualizar para uma versão nova

1. Encerre o sistema (feche a janela).
2. No VS Code: **Source Control › Pull** (ou `git pull`).
3. Abra de novo com `iniciar.bat`. Se o banco precisar de ajuste, ele é feito sozinho, com backup antes.

Seus dados ficam na pasta `dados/`, que **não vai para o GitHub**. Atualizar o código nunca apaga suas tarefas nem seus nomes.

## Configuração (opcional)

Copie `config.example.env` para `.env` e altere o que precisar:

- `PORTA`: padrão 5050.
- `PASTA_BACKUP`: aponte para o OneDrive ou uma pasta de rede para ter cópia fora do computador.
- `BACKUPS_MANTER`: padrão 30.
- `SEMANA_COMECA`: `domingo` ou `segunda`.
- `FERIADOS_EXTRAS`: feriados municipais, ex.: `15/08 N. Sra. da Assunção`.

## Backups

- Automáticos: ao abrir o sistema e antes de importar, desfazer, reaplicar ou restaurar.
- Manuais e restauração: ⚙ Configurações › Backups.
- Para levar o dicionário de nomes para outro computador: Configurações › Nomes › **Exportar regras (.json)** e, no outro, **Importar regras**.

## Problemas comuns

| Mensagem | O que fazer |
|---|---|
| "Python não encontrado" | Instale o Python marcando "Add python.exe to PATH" |
| "A porta 5050 já está em uso" | O sistema já está aberto em outra janela. Ou mude `PORTA` no `.env` |
| Colegas não conseguem abrir | Confira se o sistema está aberto, se o Firewall permite "Redes privadas" e se o IP não mudou |
| "O banco está na versão X…" | O código está mais velho que o banco. Faça `git pull` |

## Para desenvolvimento

```bash
.venv\Scripts\python -m pytest        # 37 testes, incluindo o de aceitação de outubro/2026
```

Estrutura: `app/parser.py` (leitura do texto colado), `app/normalizer.py` (regras e agrupamento), `app/servicos.py` (banco), `app/routes/` (telas), `migrations/` (esquema versionado), `seed/regras.json` (regras iniciais).
