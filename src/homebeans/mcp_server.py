from datetime import datetime
from decimal import Decimal
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from homebeans.config import get_ledger_path
from homebeans.models import Posting, Transaction
from homebeans.reports import (
    balance_report,
    filter_by_dates,
    format_ascii_tree,
    generate_balance_sheet,
    generate_cashflow,
    generate_income_statement,
)
from homebeans.storage import load_ledger, save_ledger
from homebeans.suggester import extract_all_accounts

load_dotenv()

mcp = FastMCP("homebeans")

@mcp.tool()
def get_balance() -> str:
    """Retorna o balanço financeiro atual agrupado por contas do aplicativo HomeBeans."""
    ledger_path = get_ledger_path()
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
def get_transactions(
    limit: int = 10,
    start_date: str | None = None,
    end_date: str | None = None,
    account_filter: str | None = None,
    description_filter: str | None = None,
    tag_filter: str | None = None
) -> str:
    """
    Retorna as transações registradas no ledger.
    Útil para a IA analisar o histórico de gastos ou procurar transações específicas usando os filtros disponíveis.
    Se a busca retornar vazio, tente relaxar os filtros parciais.
    
    Args:
        limit (int): Número máximo de transações a retornar do final da lista filtrada. Padrão 10 (0 para sem limite).
        start_date (str): Filtrar transações ocorridas a partir desta data (YYYY-MM-DD).
        end_date (str): Filtrar transações ocorridas até esta data (YYYY-MM-DD).
        account_filter (str): Filtra transações onde pelo menos um posting contenha esta string na conta (case-insensitive).
        description_filter (str): Busca parcial na descrição da transação (case-insensitive).
        tag_filter (str): Filtra transações contendo uma tag que dê match nesta string (case-insensitive).
    """
    ledger_path = get_ledger_path()
    try:
        transactions = load_ledger(ledger_path)
    except Exception as e:
        return f"Erro ao carregar transações: {e}"

    if not transactions:
        return "Nenhuma transação encontrada no ledger vazio."

    # Date parsing
    dt_start = None
    dt_end = None
    try:
        if start_date: dt_start = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date: dt_end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return "Erro: Filtros de data devem estar no formato YYYY-MM-DD."

    desc_lower = description_filter.lower() if description_filter else None
    acc_lower = account_filter.lower() if account_filter else None
    tag_lower = tag_filter.lower() if tag_filter else None

    filtered = []
    for t in transactions:
        # Filtro de data
        if dt_start and t.date < dt_start: continue
        if dt_end and t.date > dt_end: continue
        
        # Filtro de descrição
        if desc_lower and desc_lower not in t.description.strip().lower(): continue
        
        # Filtro de conta e tag
        if acc_lower or tag_lower:
            match_acc = False
            match_tag = False
            for p in t.postings:
                if acc_lower and acc_lower in p.account.lower():
                    match_acc = True
                if tag_lower and p.tags:
                    for tag in p.tags:
                        if tag_lower in tag.lower():
                            match_tag = True
            
            if acc_lower and not match_acc: continue
            if tag_lower and not match_tag: continue

        filtered.append(t)

    if not filtered:
        return "Nenhuma transação atendeu aos filtros requeridos."

    if limit > 0:
        filtered = filtered[-limit:]

    output = [f"Resultados ({len(filtered)} de um histórico correspondente):"]
    for t in reversed(filtered):
        postings_str = ", ".join(
            f"[{p.account}: {p.amount}" + (f" tags: {p.tags}" if p.tags else "") + "]"
            for p in t.postings
        )
        # ID exibido para permitir referência precisa em delete/edit
        output.append(f"ID: {t.id} | Data: {t.date} | Desc: {t.description} | {postings_str}")

    return "\n".join(output)

@mcp.tool()
def get_recent_transactions(
    limit: int = 10,
    account_filter: str | None = None,
    tag_filter: str | None = None,
) -> str:
    """
    Retorna as últimas N transações do ledger, da mais recente para a mais antiga.
    Ideal para comandos como "mostre as últimas 5 transações" ou
    "últimas 10 transações da conta ativos:banco".

    A filtragem é feita localmente — a LLM não precisa calcular nada.

    Args:
        limit (int): Número de transações a retornar. Padrão: 10.
        account_filter (str): Se fornecido, retorna apenas transações onde pelo menos
            um posting contenha esta string na conta (case-insensitive).
            Ex: "ativos:banco", "despesas:alimentacao", "despesas" (filtra toda a raiz).
        tag_filter (str): Se fornecido, retorna apenas transações que contenham
            uma tag que corresponda a esta string (case-insensitive).
            Ex: "veiculo:meteor", "viagem".
    """
    ledger_path = get_ledger_path()
    try:
        transactions = load_ledger(ledger_path)
    except Exception as e:
        return f"Erro ao carregar transações: {e}"

    if not transactions:
        return "Nenhuma transação encontrada no ledger."

    # Aplica filtros opcionais de conta e tag (todo o processamento é local)
    filtered = transactions
    if account_filter:
        acc_lower = account_filter.lower()
        filtered = [
            t for t in filtered
            if any(acc_lower in p.account.lower() for p in t.postings)
        ]
    if tag_filter:
        tag_lower = tag_filter.lower()
        filtered = [
            t for t in filtered
            if any(
                tag_lower in tag.lower()
                for p in t.postings
                for tag in p.tags
            )
        ]

    if not filtered:
        return "Nenhuma transação encontrada com os filtros informados."

    # Pega as últimas `limit` e exibe da mais recente para a mais antiga
    recent = filtered[-limit:]
    filtro_desc = ""
    if account_filter:
        filtro_desc += f" | conta: '{account_filter}'"
    if tag_filter:
        filtro_desc += f" | tag: '{tag_filter}'"

    output = [f"Últimas {len(recent)} transações{filtro_desc}:"]
    for t in reversed(recent):
        postings_str = ", ".join(
            f"[{p.account}: {p.amount}" + (f" tags: {p.tags}" if p.tags else "") + "]"
            for p in t.postings
        )
        output.append(f"ID: {t.id} | Data: {t.date} | Desc: {t.description} | {postings_str}")

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

    ledger_path = get_ledger_path()
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
    # Retorna o ID para que o usuário/IA possa referenciar a transação futuramente
    return f"Transação adicionada com sucesso. ID: {t.id} | {date_str} - {description}."

@mcp.tool()
def get_accounts_tree() -> str:
    """Retorna uma árvore ASCII hierárquica completa de todas as contas em uso no HomeBeans."""
    ledger_path = get_ledger_path()
    try:
        transactions = load_ledger(ledger_path)
    except Exception as e:
        return f"Erro ao carregar transações: {e}"

    if not transactions:
        return "Nenhuma conta encontrada no ledger vazio."

    accounts = extract_all_accounts(transactions)
    if not accounts:
        return "Nenhuma conta foi utilizada ainda."

    return "=== Árvore de Contas ===\n" + format_ascii_tree(accounts)

@mcp.tool()
def get_tags_list() -> str:
    """Retorna uma lista de todas as tags (chave:valor) atualmente em uso no HomeBeans, ordenadas de forma única."""
    ledger_path = get_ledger_path()
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
def delete_transaction(
    transaction_id: str | None = None,
    date_str: str | None = None,
    description: str | None = None,
) -> str:
    """
    Remove uma transação do ledger.

    Formas de localizar a transação (use a mais precisa disponível):
    1. Por ID (preferido): passe apenas `transaction_id` — busca exata, sem ambiguidade.
    2. Por data + descrição (fallback): passe `date_str` (YYYY-MM-DD) e `description`.

    Dica: use get_transactions para obter o ID antes de remover.

    Args:
        transaction_id (str): ID único da transação (preferido).
        date_str (str): Data da transação no formato YYYY-MM-DD (fallback).
        description (str): Descrição exata da transação (fallback).
    """
    if not transaction_id and not (date_str and description):
        return "Erro: forneça `transaction_id` ou `date_str` + `description`."

    ledger_path = get_ledger_path()
    try:
        transactions = load_ledger(ledger_path)
    except Exception as e:
        return f"Erro ao carregar transações: {e}"

    if not transactions:
        return "Erro: Ledger está vazio."

    if transaction_id:
        # Busca direta por ID — precisa e sem ambiguidade
        matching_indices = [i for i, t in enumerate(transactions) if t.id == transaction_id]
        if not matching_indices:
            return f"Erro: Nenhuma transação encontrada com ID '{transaction_id}'."
    else:
        # Fallback por data + descrição
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d").date()  # type: ignore[arg-type]
        except ValueError:
            return "Erro: Data deve estar no formato YYYY-MM-DD."
        target_desc = description.strip().lower()  # type: ignore[union-attr]
        matching_indices = [
            i for i, t in enumerate(transactions)
            if t.date == dt and t.description.strip().lower() == target_desc
        ]
        if not matching_indices:
            return f"Erro: Nenhuma transação encontrada em {date_str} com a descrição '{description}'."

    duplicates_warning = ""
    if len(matching_indices) > 1:
        duplicates_warning = f" Atenção: {len(matching_indices)} transações correspondiam; apenas a primeira foi removida."

    deleted = transactions.pop(matching_indices[0])
    save_ledger(ledger_path, transactions)
    return f"Transação '{deleted.description}' do dia {deleted.date} (ID: {deleted.id}) removida com sucesso.{duplicates_warning}"

@mcp.tool()
def edit_transaction(
    new_date_str: str | None = None,
    new_description: str | None = None,
    new_postings: list[dict[str, Any]] | None = None,
    transaction_id: str | None = None,
    date_str: str | None = None,
    description: str | None = None,
) -> str:
    """
    Edita uma transação existente no ledger. Apenas passe os campos 'new_...' que deseja alterar.

    Formas de localizar a transação (use a mais precisa disponível):
    1. Por ID (preferido): passe apenas `transaction_id`.
    2. Por data + descrição (fallback): passe `date_str` (YYYY-MM-DD) e `description`.

    REGRA DE NEGÓCIO - PARTIDA DOBRADA (REQUISITO CRÍTICO):
    Se alterar os postings, forneça a lista INTEIRA e balanceada em `new_postings`.
    A soma de todos os `amount` DEVE ser zero. Lembre-se de atualizar a contrapartida
    proporcionalmente (ex: ao ajustar uma despesa, ajuste também o crédito em ativos).

    Args:
        transaction_id (str): ID único da transação (preferido para localização).
        date_str (str): Data atual da transação YYYY-MM-DD (fallback).
        description (str): Descrição atual da transação (fallback).
        new_date_str (str): Nova data (opcional).
        new_description (str): Nova descrição (opcional).
        new_postings (list): Lista completa e balanceada de postings (opcional).
    """
    if not transaction_id and not (date_str and description):
        return "Erro: forneça `transaction_id` ou `date_str` + `description`."

    if new_date_str:
        try:
            new_dt = datetime.strptime(new_date_str, "%Y-%m-%d").date()
        except ValueError:
            return "Erro: A nova data deve estar no formato YYYY-MM-DD."
    else:
        new_dt = None

    ledger_path = get_ledger_path()
    try:
        transactions = load_ledger(ledger_path)
    except Exception as e:
        return f"Erro ao carregar transações: {e}"

    if not transactions:
        return "Erro: Ledger está vazio."

    if transaction_id:
        # Busca direta por ID — precisa e sem ambiguidade
        matching_indices = [i for i, t in enumerate(transactions) if t.id == transaction_id]
        if not matching_indices:
            return f"Erro: Nenhuma transação encontrada com ID '{transaction_id}'."
    else:
        # Fallback por data + descrição
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d").date()  # type: ignore[arg-type]
        except ValueError:
            return "Erro: A data deve estar no formato YYYY-MM-DD."
        target_desc = description.strip().lower()  # type: ignore[union-attr]
        matching_indices = [
            i for i, t in enumerate(transactions)
            if t.date == dt and t.description.strip().lower() == target_desc
        ]
        if not matching_indices:
            return f"Erro: Nenhuma transação encontrada em {date_str} com a descrição '{description}'."

    duplicates_warning = ""
    if len(matching_indices) > 1:
        duplicates_warning = f" Atenção: {len(matching_indices)} transações correspondiam; apenas a primeira foi editada."

    matching_idx = matching_indices[0]
    t_edit = transactions[matching_idx]
    # Usa a data original se nenhuma nova data foi fornecida
    new_dt = new_dt or t_edit.date
    
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
        # Preserva o ID original — edição não gera um novo ID
        valid_t = Transaction(
            id=t_edit.id,
            date=new_dt,
            description=final_desc,
            postings=final_postings,
        )
        transactions[matching_idx] = valid_t
    except Exception as e:
        return f"Erro de validação na nova transação (a soma dos postings deve ser zero): {e}"

    save_ledger(ledger_path, transactions)
    return f"Transação editada com sucesso! ID: {valid_t.id} | {valid_t.date} - {valid_t.description}.{duplicates_warning}"


@mcp.tool()
def clear_journal(confirmation: str) -> str:
    """
    Apaga todas as transações do livro-razão (journal) atual.
    ATENÇÃO: Operação irreversível. A IA deve informar o usuário das consequências.
    Para confirmar a operação, o argumento 'confirmation' deve ser "CONFIRMO_LIMPEZA_TOTAL".
    """
    if confirmation != "CONFIRMO_LIMPEZA_TOTAL":
        return "Erro: Limpeza cancelada. Você deve passar a string exata 'CONFIRMO_LIMPEZA_TOTAL'."
        
    ledger_path = get_ledger_path()
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

def _parse_report_dates(start_date: str | None, end_date: str | None):
    """Converte strings YYYY-MM-DD em objetos date para os relatórios.

    Retorna (dt_start, dt_end) ou lança ValueError com mensagem amigável.
    """
    from datetime import date as date_type
    dt_start = None
    dt_end = None
    try:
        if start_date:
            dt_start = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            dt_end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Datas devem estar no formato YYYY-MM-DD.")
    return dt_start, dt_end


@mcp.tool()
def get_income_statement(
    period: str = "month",
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """
    Retorna o DRE (Demonstração do Resultado do Exercício).
    Foca apenas em Entradas e Despesas, mostrando o Lucro/Prejuízo Líquido por período.

    Args:
        period (str): Agrupamento. Opções: 'day', 'week', 'month', 'year', 'all'. Padrão: 'month'.
        start_date (str): Data inicial do recorte, formato YYYY-MM-DD (opcional).
        end_date (str): Data final do recorte, formato YYYY-MM-DD (opcional).
    """
    ledger_path = get_ledger_path()
    try:
        transactions = load_ledger(ledger_path)
    except Exception as e:
        return f"Erro ao carregar transações: {e}"

    try:
        dt_start, dt_end = _parse_report_dates(start_date, end_date)
    except ValueError as e:
        return f"Erro: {e}"

    # Filtragem local antes de passar para o relatório
    transactions = filter_by_dates(transactions, dt_start, dt_end)
    if not transactions:
        return "Nenhuma transação encontrada no período informado."

    return generate_income_statement(transactions, period)


@mcp.tool()
def get_balance_sheet(
    period: str = "month",
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """
    Retorna o Balanço Patrimonial acumulativo ao longo do tempo.
    Foca no acúmulo de Ativos, Passivos e Patrimônio.

    Args:
        period (str): Agrupamento. Opções: 'day', 'week', 'month', 'year', 'all'. Padrão: 'month'.
        start_date (str): Data inicial do recorte, formato YYYY-MM-DD (opcional).
        end_date (str): Data final do recorte, formato YYYY-MM-DD (opcional).
    """
    ledger_path = get_ledger_path()
    try:
        transactions = load_ledger(ledger_path)
    except Exception as e:
        return f"Erro ao carregar transações: {e}"

    try:
        dt_start, dt_end = _parse_report_dates(start_date, end_date)
    except ValueError as e:
        return f"Erro: {e}"

    transactions = filter_by_dates(transactions, dt_start, dt_end)
    if not transactions:
        return "Nenhuma transação encontrada no período informado."

    return generate_balance_sheet(transactions, period)


@mcp.tool()
def get_cashflow(
    period: str = "month",
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """
    Retorna o Fluxo de Caixa — variação líquida dos Ativos por período.

    Args:
        period (str): Agrupamento. Opções: 'day', 'week', 'month', 'year', 'all'. Padrão: 'month'.
        start_date (str): Data inicial do recorte, formato YYYY-MM-DD (opcional).
        end_date (str): Data final do recorte, formato YYYY-MM-DD (opcional).
    """
    ledger_path = get_ledger_path()
    try:
        transactions = load_ledger(ledger_path)
    except Exception as e:
        return f"Erro ao carregar transações: {e}"

    try:
        dt_start, dt_end = _parse_report_dates(start_date, end_date)
    except ValueError as e:
        return f"Erro: {e}"

    transactions = filter_by_dates(transactions, dt_start, dt_end)
    if not transactions:
        return "Nenhuma transação encontrada no período informado."

    return generate_cashflow(transactions, period)

