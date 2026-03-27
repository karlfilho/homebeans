"""Relatórios e agregações contábeis."""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from homebeans.models import Transaction


def filter_by_dates(
    transactions: list[Transaction],
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[Transaction]:
    """Filtra transações por intervalo de datas (ambos os extremos inclusivos).

    Utilizado pelos relatórios para recortar o período antes de agregar.
    Nenhum dos parâmetros é obrigatório — sem filtro, retorna a lista inteira.
    """
    result = transactions
    if start_date:
        result = [t for t in result if t.date >= start_date]
    if end_date:
        result = [t for t in result if t.date <= end_date]
    return result


def balance_by_account(transactions: list[Transaction]) -> dict[str, Decimal]:
    """Calcula saldo por conta (débitos - créditos)."""
    balances: dict[str, Decimal] = defaultdict(Decimal)
    for t in transactions:
        for p in t.postings:
            balances[p.account] += p.amount
    return dict(balances)


def balance_report(transactions: list[Transaction]) -> list[tuple[str, Decimal]]:
    """Retorna relatório de saldo ordenado por conta."""
    bal = balance_by_account(transactions)
    return sorted(bal.items(), key=lambda x: x[0])

def format_ascii_tree(accounts: list[str]) -> str:
    """Formata uma lista de contas (raíz:sub:detalhe) em uma árvore ASCII limpa."""
    tree_dict = {}
    for acc in accounts:
        parts = acc.split(':')
        curr = tree_dict
        for p in parts:
            curr = curr.setdefault(p, {})
    
    lines = []
    def _print_tree(node, prefix=""):
        items = list(node.items())
        for i, (k, v) in enumerate(items):
            is_last = (i == len(items) - 1)
            connector = "└── " if is_last else "├── "
            lines.append(prefix + connector + k)
            child_prefix = prefix + ("    " if is_last else "│   ")
            _print_tree(v, child_prefix)
            
    _print_tree(tree_dict)
    return "\n".join(lines) if lines else "Nenhuma conta associada."

def group_by_period(transactions: list[Transaction], period: str) -> dict[str, list[Transaction]]:
    """Agrupa transações por 'day', 'week', 'month', 'year' ou 'all'."""
    grouped = defaultdict(list)
    for t in transactions:
        if period == "day":
            k = t.date.strftime("%Y-%m-%d")
        elif period == "week":
            k = t.date.strftime("%Y-W%V")
        elif period == "month":
            k = t.date.strftime("%Y-%m")
        elif period == "year":
            k = t.date.strftime("%Y")
        else:
            k = "Todos"
        grouped[k].append(t)
    return dict(sorted(grouped.items()))

def generate_income_statement(transactions: list[Transaction], period: str) -> str:
    """Gera um relatório textual de Entradas vs Despesas agrupado por período."""
    grouped = group_by_period(transactions, period)
    output = ["=== DRE (Demonstração do Resultado do Exercício) ==="]
    
    for p_key, txs in grouped.items():
        bal = balance_by_account(txs)
        entradas = {k: v for k, v in bal.items() if k.startswith("entradas")}
        despesas = {k: v for k, v in bal.items() if k.startswith("despesas")}
        
        sum_in = sum(entradas.values())
        sum_out = sum(despesas.values())
        # Entradas são saldos negativos no double-entry.
        # Despesas são positivos.
        receita_real = -sum_in
        despesa_real = sum_out
        lucro_liquido = receita_real - despesa_real
        
        output.append(f"\n[Período: {p_key}]")
        output.append(f"Receitas Totais: {receita_real:.2f}")
        for k, v in sorted(entradas.items()): output.append(f"  {k}: {-v:.2f}")
        output.append(f"Despesas Totais: {despesa_real:.2f}")
        for k, v in sorted(despesas.items()): output.append(f"  {k}: {v:.2f}")
        output.append(f"Lucro/Prejuízo Líquido: {lucro_liquido:.2f}")
        
    return "\n".join(output)

def generate_balance_sheet(transactions: list[Transaction], period: str) -> str:
    """Gera o Balanço Patrimonial (Ativos vs Passivos/Patrimônio). O Balanço Patrimonial é cumulativo no tempo."""
    grouped_keys = sorted(group_by_period(transactions, period).keys())
    output = ["=== Balanço Patrimonial ==="]
    
    # Para balance sheet, somamos tudo até a data final do período
    cumulative_txs = []
    
    sorted_all = sorted(transactions, key=lambda t: t.date)
    grouped_all = group_by_period(sorted_all, period)
    
    for p_key, txs in grouped_all.items():
        cumulative_txs.extend(txs)
        bal = balance_by_account(cumulative_txs)
        
        ativos = {k: v for k, v in bal.items() if k.startswith("ativos")}
        passivos = {k: v for k, v in bal.items() if k.startswith("passivos")}
        patrimonio = {k: v for k, v in bal.items() if k.startswith("patrimônio") or k.startswith("patrimonio")}
        
        sum_ativos = sum(ativos.values())
        # Passivos e patrimônio são créditos (negativos)
        sum_passivos = -sum(passivos.values())
        sum_patrimonio = -sum(patrimonio.values())
        
        output.append(f"\n[Acumulado até o Período: {p_key}]")
        output.append(f"Ativos Totais: {sum_ativos:.2f}")
        for k, v in sorted(ativos.items()): output.append(f"  {k}: {v:.2f}")
        output.append(f"Passivos Totais: {sum_passivos:.2f}")
        for k, v in sorted(passivos.items()): output.append(f"  {k}: {-v:.2f}")
        output.append(f"Patrimônio Líquido Declarado: {sum_patrimonio:.2f}")
        for k, v in sorted(patrimonio.items()): output.append(f"  {k}: {-v:.2f}")
        
    return "\n".join(output)

def generate_cashflow(transactions: list[Transaction], period: str) -> str:
    """Gera relatório de Fluxo de Caixa focado variação líquida de ATIVOS durante o período."""
    grouped = group_by_period(transactions, period)
    output = ["=== Fluxo de Caixa ==="]
    
    for p_key, txs in grouped.items():
        bal = balance_by_account(txs)
        ativos = {k: v for k, v in bal.items() if k.startswith("ativos")}
        variacao_caixa = sum(ativos.values())
        
        output.append(f"\n[Período: {p_key}]")
        output.append(f"Variação Líquida de Caixa (Ativos): {variacao_caixa:.2f}")
        for k, v in sorted(ativos.items()): 
            if v != 0:
                output.append(f"  {k}: {v:.2f}")
                
    return "\n".join(output)
