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

def generate_account_statement(
    transactions: list[Transaction],
    account: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> str:
    """Gera um extrato estilo bancário para uma conta (ou prefixo de conta).

    Exibe cada lançamento em ordem cronológica com o saldo acumulado linha
    a linha. Aceita filtro parcial — "ativos:banco" captura todas as subcontas
    de banco. Todo o cálculo é local.
    """
    filtered = filter_by_dates(transactions, start_date, end_date)

    # Coleta todos os postings da conta solicitada, mantendo a data da transação
    acc_lower = account.lower()
    entries: list[tuple[date, str, str, Decimal]] = []
    for t in sorted(filtered, key=lambda tx: tx.date):
        for p in t.postings:
            if acc_lower in p.account.lower():
                entries.append((t.date, t.description, p.account, p.amount))

    if not entries:
        return f"Nenhum lançamento encontrado para '{account}'."

    lines = [f"=== Extrato: {account} ==="]
    running_balance = Decimal("0")
    for dt, desc, acc, amount in entries:
        running_balance += amount
        sign = "+" if amount > 0 else ""
        lines.append(
            f"{dt} | {desc:<35} | {acc:<40} | {sign}{amount:>10.2f} | Saldo: {running_balance:>10.2f}"
        )

    lines.append(f"\nSaldo final: {running_balance:.2f}")
    return "\n".join(lines)


def generate_spending_summary(
    transactions: list[Transaction],
    period: str = "month",
    start_date: date | None = None,
    end_date: date | None = None,
    top_n: int = 10,
) -> str:
    """Gera um resumo de gastos por categoria (2º nível de despesas).

    Agrupa despesas por `despesas:<subcategoria>`, calcula o total e o
    percentual de cada categoria sobre o total de despesas do período.
    Ordenado do maior para o menor. Todo o cálculo é local.

    Exemplos de agrupamento:
        despesas:alimentacao:mercado  →  despesas:alimentacao
        despesas:moradia:aluguel      →  despesas:moradia
        despesas:moradia:internet     →  despesas:moradia  (soma com a linha acima)
    """
    filtered = filter_by_dates(transactions, start_date, end_date)
    grouped = group_by_period(filtered, period)

    output = ["=== Resumo de Gastos por Categoria ==="]
    found_any = False

    for p_key, txs in grouped.items():
        bal = balance_by_account(txs)

        # Agrupa pelo 2º nível: despesas:<subcategoria>
        categories: dict[str, Decimal] = {}
        for acc, val in bal.items():
            if acc.startswith("despesas"):
                parts = acc.split(":")
                category = ":".join(parts[:2])  # mantém só despesas:subcategoria
                categories[category] = categories.get(category, Decimal("0")) + val

        if not categories:
            continue

        found_any = True
        total = sum(categories.values())
        # Ordena do maior para o menor e aplica top_n
        ranked = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        if top_n and top_n > 0:
            ranked = ranked[:top_n]

        output.append(f"\n[Período: {p_key}] Total despesas: {total:.2f}")
        for cat, val in ranked:
            pct = (val / total * 100) if total else Decimal("0")
            output.append(f"  {cat}: {val:.2f}  ({float(pct):.1f}%)")

    if not found_any:
        return "Nenhuma despesa encontrada no período informado."

    return "\n".join(output)


def generate_ledger_stats(transactions: list[Transaction]) -> str:
    """Gera um resumo estatístico geral do ledger.

    Útil como orientação de contexto no início de uma conversa — a LLM
    obtém o estado do ledger com uma única chamada, sem precisar inferir
    tamanho ou período a partir de outras ferramentas.
    """
    from collections import Counter

    if not transactions:
        return "Ledger vazio — nenhuma estatística disponível."

    sorted_txs = sorted(transactions, key=lambda t: t.date)
    first_date = sorted_txs[0].date
    last_date = sorted_txs[-1].date

    # Contas e tags distintas em uso
    accounts = {p.account for t in transactions for p in t.postings}
    tags = {tag for t in transactions for p in t.postings for tag in p.tags}

    # Média de transações por mês (baseada nos meses que efetivamente têm lançamentos)
    months_with_txs = Counter(t.date.strftime("%Y-%m") for t in transactions)
    avg_per_month = len(transactions) / len(months_with_txs)

    lines = [
        "=== Estatísticas do Ledger ===",
        f"Total de transações : {len(transactions)}",
        f"Período             : {first_date} → {last_date}",
        f"Contas distintas    : {len(accounts)}",
        f"Tags distintas      : {len(tags)}",
        f"Média / mês         : {avg_per_month:.1f} transações",
    ]
    return "\n".join(lines)


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
