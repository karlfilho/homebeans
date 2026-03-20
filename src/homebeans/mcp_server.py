import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from homebeans.models import Posting, Transaction
from homebeans.reports import balance_report
from homebeans.storage import load_ledger, save_ledger
from core.suggester import extract_all_accounts

load_dotenv()

mcp = FastMCP("homebeans")

def _get_ledger_path() -> Path:
    path = os.getenv("LEDGER_PATH", "./data/ledger.yaml")
    return Path(path)

@mcp.tool()
def get_balance() -> str:
    """Retorna o balanço financeiro atual agrupado por contas do aplicativo HomeBeans."""
    ledger_path = _get_ledger_path()
    try:
        transactions = load_ledger(ledger_path)
    except Exception as e:
        return f"Erro ao carregar transações: {e}"

    report = balance_report(transactions)
    if not report:
        return "Nenhuma conta possui saldo no momento."

    output = ["Balanço de Contas HomeBeans:"]
    for account, bal in report:
        output.append(f"- {account}: {bal}")
    return "\n".join(output)

@mcp.tool()
def get_transactions(limit: int = 10) -> str:
    """
    Retorna as transações mais recentes do ledger para análise.
    
    Args:
        limit (int): Número máximo de transações para retornar (padrão 10).
    """
    ledger_path = _get_ledger_path()
    try:
        transactions = load_ledger(ledger_path)
    except Exception as e:
        return f"Erro ao carregar transações: {e}"

    if not transactions:
        return "Nenhuma transação registrada no momento."

    recent = transactions[-limit:]
    output = [f"Últimas {len(recent)} transações:"]
    for t in reversed(recent):
        postings_str = ", ".join(f"[{p.account}: {p.amount}]" for p in t.postings)
        output.append(f"Data: {t.date} | Desc: {t.description} | {postings_str}")
        
    return "\n".join(output)

@mcp.tool()
def add_transaction(date_str: str, description: str, postings: list[dict[str, Any]]) -> str:
    """
    Adiciona uma nova transação financeira ao ledger Homebeans.
    
    REGRA DE NEGÓCIO - PARTIDA DOBRADA E NOMENCLATURA (REQUISITO CRÍTICO):
    1. A soma matemática de todos os 'amount' nos postings DEVE ser exatamente zero.
    2. Valores positivos representam DÉBITOS (aumento de ativos/despesas).
    3. Valores negativos representam CRÉDITOS (aumento de passivos/entradas, ou redução de ativos).
    4. CADA CONTA OBRIGATORIAMENTE DEVE INICIAR COM UM DOS 5 PREFIXOS:
       ativos, passivos, entradas, despesas, patrimônio.
    5. CADA CONTA DEVE TER NO MÁXIMO 3 NÍVEIS (tipo:subtipo:detalhe). O 4º nível é estritamente proibido!
       Exemplo Correto (3 níveis): "despesas:transporte:combustivel"
       Exemplo Proibido (4 níveis): "despesas:transporte:veiculo:meteor" (O "meteor" deve virar uma tag).
    6. TODAS AS TAGS OBRIGATORIAMENTE DEVEM SEGUIR O FORMATO CHAVE:VALOR. Ex: "veiculo:meteor" ou "categoria:fixa".
       IMPORTANTE: VOCÊ DEVE PRIORIZAR O REUSO DE TAGS E CONTAS JÁ EXISTENTES PARA MANTER A CONSISTÊNCIA.
       Use as ferramentas get_accounts_tree() e get_tags_list() para consultar as nomenclaturas do usuário antes de inventar novas.
    7. Se o usuário disser apenas "Comprei pão por R$ 10", ELE FORNECEU APENAS UMA PERNA DA TRANSAÇÃO. 
       Você TEM a obrigação de perguntar proativamente: "De qual conta esse dinheiro saiu?"
       ANTES de tentar chamar esta ferramenta. Não adivinhe a conta de origem sem ter certeza.
    8. Explique sua lógica: "Vou debitar 10.00 de despesas:alimentacao:padaria e creditar -10.00 de ativos:carteira com a tag 'tipo:lanche'".
    
    Args:
        date_str (str): A data da transação no formato YYYY-MM-DD.
        description (str): Descrição curta e objetiva. Iniciar preferencialmente de forma consistente.
        postings (list[dict]): A lista balanceada de lançamentos. Ex: [{"account": "despesas:moradia:internet", "amount": "99.00", "tags": ["fornecedor:claro"]}]
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return "Erro: Data deve estar no formato YYYY-MM-DD."

    postings_list = []
    for p_dict in postings:
        if "account" not in p_dict or "amount" not in p_dict:
            return "Erro: Cada posting deve conter 'account' e 'amount'."
        try:
            amt = Decimal(str(p_dict["amount"]))
            posting = Posting(
                account=p_dict["account"], 
                amount=amt, 
                tags=p_dict.get("tags", [])
            )
            postings_list.append(posting)
        except Exception as e:
            return f"Erro na validação do posting {p_dict}: {e}"

    try:
        t = Transaction(date=dt, description=description, postings=postings_list)
    except Exception as e:
        return f"Erro na validação da transação (partida dobrada etc): {e}"

    ledger_path = _get_ledger_path()
    # Cria diretório caso não exista
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        transactions = load_ledger(ledger_path)
    except Exception:
        # Se falhou ler por outro motivo e já tivermos o ledger, inicializa nulo
        if ledger_path.exists():
            return "Erro: Falha ao carregar arquivo de ledger existente."
        transactions = []

    transactions.append(t)
    save_ledger(ledger_path, transactions)
    return f"Transação adicionada com sucesso em {date_str} - {description}."

@mcp.tool()
def get_accounts_tree() -> str:
    """Retorna a lista completa das contas contábeis organizadas por hierarquia atualmente em uso no HomeBeans."""
    ledger_path = _get_ledger_path()
    try:
        transactions = load_ledger(ledger_path)
    except Exception as e:
        return f"Erro ao carregar transações: {e}"

    if not transactions:
        return "Nenhuma conta encontrada no ledger vazio."

    accounts = extract_all_accounts(transactions)
    if not accounts:
        return "Nenhuma conta foi utilizada ainda."

    output = ["Contas Financeiras Em Uso:"]
    for acc in accounts:
        output.append(f"- {acc}")
    return "\n".join(output)

@mcp.tool()
def get_tags_list() -> str:
    """Retorna uma lista de todas as tags (chave:valor) atualmente em uso no HomeBeans, ordenadas de forma única."""
    ledger_path = _get_ledger_path()
    try:
        transactions = load_ledger(ledger_path)
    except Exception as e:
        return f"Erro ao carregar transações: {e}"

    if not transactions:
        return "Nenhuma tag foi utilizada ainda no ledger vazio."

    tags_set = set()
    for t in transactions:
        for p in t.postings:
            if p.tags:
                for tag in p.tags:
                    tags_set.add(tag)
                    
    if not tags_set:
        return "Nenhuma tag está em uso atualmente."

    output = ["Tags em uso no sistema (priorize-as antes de criar novas):"]
    for tag in sorted(tags_set):
        output.append(f"- {tag}")
    return "\n".join(output)

@mcp.tool()
def delete_transaction(date_str: str, description: str) -> str:
    """
    Remove uma transação específica do ledger baseando-se na data (YYYY-MM-DD) e descrição exata (case-insensitive).
    Dica: use get_transactions primeiro para listar os registros recentes e obter a data e descrição corretas.
    
    Args:
        date_str (str): A data exata da transação (ex: 2024-01-15).
        description (str): A descrição da transação.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return "Erro: Data deve estar no formato YYYY-MM-DD."

    ledger_path = _get_ledger_path()
    try:
        transactions = load_ledger(ledger_path)
    except Exception as e:
        return f"Erro ao carregar transações: {e}"

    if not transactions:
        return "Erro: Ledger está vazio."

    target_desc = description.strip().lower()
    matching_idx = -1
    
    # Busca a primeira transação que casa com data e descrição
    for i, t in enumerate(transactions):
        if t.date == dt and t.description.strip().lower() == target_desc:
            matching_idx = i
            break

    if matching_idx == -1:
        return f"Erro: Nenhuma transação encontrada no dia {date_str} com a descrição '{description}'."

    deleted = transactions.pop(matching_idx)
    save_ledger(ledger_path, transactions)
    return f"Transação '{deleted.description}' do dia {deleted.date} removida com sucesso."

@mcp.tool()
def edit_transaction(
    date_str: str, 
    description: str,
    new_date_str: str | None = None,
    new_description: str | None = None,
    new_postings: list[dict[str, Any]] | None = None
) -> str:
    """
    Edita uma transação existente no ledger. Localiza a transação pela data e descrição originais.
    Apenas passe os campos 'new_...' que você deseja alterar.
    
    REGRA DE NEGÓCIO - PARTIDA DOBRADA (REQUISITO CRÍTICO):
    Se for alterar os postings (para corrigir um valor, por exemplo), você deve fornecer a lista 
    INTEIRA balanceada novamente nos 'new_postings', cuja soma de valores seja 0.
    Se o usuário pedir "agora o mercado foi R$ 60 em vez de R$ 50", lembre-se de atualizar
    a contrapartida (ex: o saldo negativo de ativos:banco) proporcionalmente e avise-o disso.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return "Erro: A data atual deve estar no formato YYYY-MM-DD."

    new_dt = dt
    if new_date_str:
        try:
            new_dt = datetime.strptime(new_date_str, "%Y-%m-%d").date()
        except ValueError:
            return "Erro: A nova data deve estar no formato YYYY-MM-DD."

    ledger_path = _get_ledger_path()
    try:
        transactions = load_ledger(ledger_path)
    except Exception as e:
        return f"Erro ao carregar transações: {e}"

    if not transactions:
        return "Erro: Ledger está vazio."

    target_desc = description.strip().lower()
    matching_idx = -1
    for i, t in enumerate(transactions):
        if t.date == dt and t.description.strip().lower() == target_desc:
            matching_idx = i
            break

    if matching_idx == -1:
        return f"Erro: Nenhuma transação encontrada na data {date_str} com a descrição '{description}'."

    t_edit = transactions[matching_idx]
    
    final_desc = new_description if new_description else t_edit.description
    final_postings = t_edit.postings

    if new_postings is not None:
        postings_list = []
        for p_dict in new_postings:
            if "account" not in p_dict or "amount" not in p_dict:
                return "Erro: Cada posting deve conter 'account' e 'amount'."
            try:
                amt = Decimal(str(p_dict["amount"]))
                posting = Posting(
                    account=p_dict["account"], 
                    amount=amt, 
                    tags=p_dict.get("tags", [])
                )
                postings_list.append(posting)
            except Exception as e:
                return f"Erro na validação do novo posting {p_dict}: {e}"
        final_postings = postings_list

    try:
        valid_t = Transaction(date=new_dt, description=final_desc, postings=final_postings)
        transactions[matching_idx] = valid_t
    except Exception as e:
        return f"Erro de validação na nova transação (provavelmente o saldo não zera): {e}"

    save_ledger(ledger_path, transactions)
    return f"Transação editada com sucesso! Atualizada para: {valid_t.date} - {valid_t.description}."

@mcp.tool()
def generate_html_report(output_filename: str = "balance_chart.html") -> str:
    """
    Gera um gráfico interativo (HTML) do balanço financeiro atual e o salva no disco.
    Retorna o caminho absoluto do arquivo para o usuário poder abrir no navegador.
    """
    import os
    from homebeans.viz import export_balance_chart
    
    ledger_path = _get_ledger_path()
    try:
        transactions = load_ledger(ledger_path)
    except Exception as e:
        return f"Erro ao carregar transações: {e}"

    if not transactions:
        return "Erro: Ledger está vazio, não há dados para gerar gráfico."

    report = balance_report(transactions)
    if not report:
        return "Erro: Nenhuma conta possui saldo para gerar gráfico."

    balances = {acc: float(bal) for acc, bal in report}
    out_path = Path(os.getcwd()) / output_filename
    try:
        export_balance_chart(balances, out_path)
        return f"Relatório gráfico gerado com sucesso! Arquivo salvo em: {out_path.absolute()}"
    except Exception as e:
        return f"Erro ao gerar gráfico: {e}"

@mcp.tool()
def clear_journal(confirmation: str) -> str:
    """
    Apaga todas as transações do livro-razão (journal) atual.
    ATENÇÃO: Operação irreversível. A IA deve informar o usuário das consequências.
    Para confirmar a operação, o argumento 'confirmation' deve ser "CONFIRMO_LIMPEZA_TOTAL".
    """
    if confirmation != "CONFIRMO_LIMPEZA_TOTAL":
        return "Erro: Limpeza cancelada. Você deve passar a string exata 'CONFIRMO_LIMPEZA_TOTAL'."
        
    ledger_path = _get_ledger_path()
    try:
        _ = load_ledger(ledger_path)
    except Exception as e:
        return f"Erro ao acessar o arquivo YAML do ledger: {e}"

    save_ledger(ledger_path, [])
    return "Journal limpo com sucesso! Nenhuma transação restou no arquivo."

@mcp.prompt()
def homebeans_guide() -> str:
    """
    Prompt embutido para guiar o assistente fiscal na lógica do Homebeans app (Partida Dobrada).
    """
    return (
        "Você é o assistente financeiro do HomeBeans, um sistema de contabilidade em Python baseado em texto (YAML). "
        "Sua principal regra inquebrável é: Partida Dobrada (Double-Entry Bookkeeping). "
        "Soma dos lançamentos de uma transação DEVE ser sempre zero. \n\n"
        "Comandos Básicos de Contas e Sintaxe OBRIGATÓRIA 'tipo:subtipo:detalhe':\n"
        "- Somente 5 raízes são permitidas: ativos, passivos, entradas, despesas, patrimônio.\n"
        "- O limite máximo é de 3 níveis por conta. Um quarto nível é expressamente proibido. Empurre detalhes extras para uma tag.\n"
        "- Ativos (Dinheiro, Bancos) crescem com débitos (positivo) e reduzem com créditos (negativo).\n"
        "- Despesas crescem com débitos (positivo).\n"
        "- Entradas (Receitas) e Passivos (Dívidas) crescem com créditos (negativos).\n"
        "- Patrimônio (Equity) representa o patrimônio líquido.\n\n"
        "Regra OBRIGATÓRIA de Tags:\n"
        "- Tags SEMPRE devem seguir o formato chave:valor (ex: 'veiculo:meteor', 'viagem:sp').\n"
        "- DÊ PREFERÊNCIA ABSOLUTA às tags já existentes no sistema (use a ferramenta get_tags_list() para checar).\n\n"
        "Sempre comunique o usuário detalhadamente o que vai contabilizar prestando atenção à consistência total."
    )

