"""Visualização de gráficos financeiros com Plotly."""

from pathlib import Path

import plotly.graph_objects as go
from minha_financa.reports import balance_by_account


def export_balance_chart(
    balances: dict[str, float],
    output_path: Path,
    title: str = "Saldo por Conta",
) -> None:
    """Exporta gráfico de barras do saldo por conta para HTML."""
    accounts = list(balances.keys())
    values = list(balances.values())
    colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in values]
    fig = go.Figure(
        data=[
            go.Bar(x=accounts, y=values, marker_color=colors),
        ],
        layout=go.Layout(
            title=title,
            xaxis_title="Conta",
            yaxis_title="Saldo",
            template="plotly_white",
        ),
    )
    fig.write_html(str(output_path))


def export_evolution_chart(
    dates: list[str],
    series: dict[str, list[float]],
    output_path: Path,
    title: str = "Evolução por Conta",
) -> None:
    """Exporta gráfico de evolução temporal para HTML."""
    fig = go.Figure(layout=go.Layout(title=title, template="plotly_white"))
    for name, values in series.items():
        fig.add_trace(
            go.Scatter(x=dates, y=values, mode="lines+markers", name=name)
        )
    fig.update_layout(
        xaxis_title="Data",
        yaxis_title="Saldo acumulado",
    )
    fig.write_html(str(output_path))
