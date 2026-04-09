"""Reusable Dash DataTable builders."""

from dash import dash_table
import pandas as pd


def stat_table(df: pd.DataFrame, id: str, page_size: int = 15) -> dash_table.DataTable:
    """Standard sortable stat table."""
    return dash_table.DataTable(
        id=id,
        data=df.to_dict("records"),
        columns=[{"name": col, "id": col, "type": "numeric" if df[col].dtype in ["int64", "float64"] else "text"}
                 for col in df.columns],
        sort_action="native",
        filter_action="native",
        page_size=page_size,
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left", "padding": "8px", "fontSize": "13px"},
        style_header={"fontWeight": "bold", "backgroundColor": "#f0f0f0"},
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#fafafa"},
        ],
    )
