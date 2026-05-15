import argparse
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Visualize fintech index scores from a final scores CSV file."
    )
    parser.add_argument(
        "--input",
        default="data/fintech_index_final_scores.csv",
        help="Path to the input CSV file containing Year, Rank, Bank, and Fintech_Index_Score.",
    )
    parser.add_argument(
        "--output",
        default="data/fintech_index_visualization.html",
        help="Path to the output HTML visualization file.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=15,
        help="Number of top banks to show in the ranking chart and default trend selection.",
    )
    parser.add_argument(
        "--banks",
        type=str,
        default="",
        help="Comma-separated list of banks to include in the trend chart.",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Year to use for the top-bank ranking chart. Defaults to the latest year in the CSV.",
    )
    return parser.parse_args()


def load_scores(input_path: Path) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    df = pd.read_csv(input_path)
    expected_columns = {"Year", "Rank", "Bank", "Fintech_Index_Score"}
    missing = expected_columns - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

    df = df.copy()
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    if df["Year"].isna().any():
        raise ValueError("Some Year values could not be parsed as numbers.")

    df["Fintech_Index_Score"] = pd.to_numeric(df["Fintech_Index_Score"], errors="coerce")
    if df["Fintech_Index_Score"].isna().any():
        raise ValueError("Some Fintech_Index_Score values could not be parsed as numbers.")

    return df


def choose_banks(df: pd.DataFrame, top_n: int, bank_list: str) -> list[str]:
    latest_year = int(df["Year"].max())
    latest_df = df[df["Year"] == latest_year]

    if bank_list:
        requested = [bank.strip() for bank in bank_list.split(",") if bank.strip()]
        found = [bank for bank in requested if bank in df["Bank"].unique()]
        if not found:
            print(
                f"Warning: none of the requested banks were found in the data. Falling back to the top {top_n} banks from {latest_year}."
            )
        else:
            return found

    sorted_latest = latest_df.sort_values(["Rank", "Fintech_Index_Score"], ascending=[True, False])
    return sorted_latest["Bank"].drop_duplicates().head(top_n).tolist()


def build_charts(df: pd.DataFrame, banks: list[str], ranking_year: int, top_n: int) -> go.Figure:
    latest_year = int(df["Year"].max())
    if ranking_year is None:
        ranking_year = latest_year

    year_df = df[df["Year"] == ranking_year]
    if year_df.empty:
        raise ValueError(f"No data available for year {ranking_year}.")

    ranking_df = year_df.sort_values(["Rank", "Fintech_Index_Score"], ascending=[True, False]).head(top_n)
    trend_df = df[df["Bank"].isin(banks)].sort_values(["Bank", "Year"])
    if trend_df.empty:
        raise ValueError("No trend data available for the selected banks.")

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=False,
        vertical_spacing=0.18,
        subplot_titles=(
            "Fintech Index Trend: Selected Banks",
            f"Top {top_n} Banks by Fintech Index Score in {ranking_year}",
        ),
    )

    for bank in banks:
        bank_df = trend_df[trend_df["Bank"] == bank]
        if bank_df.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=bank_df["Year"],
                y=bank_df["Fintech_Index_Score"],
                mode="lines+markers",
                name=bank,
                hovertemplate="%{x}: %{y:.6f}<extra>" + bank + "</extra>",
            ),
            row=1,
            col=1,
        )

    fig.add_trace(
        go.Bar(
            x=ranking_df["Fintech_Index_Score"],
            y=ranking_df["Bank"],
            orientation="h",
            text=ranking_df["Fintech_Index_Score"].map("{:.6f}".format),
            textposition="outside",
            marker_color="#2a9d8f",
            hovertemplate="%{y}: %{x:.6f}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        height=900,
        width=1200,
        title_text="Fintech Index Visualization",
        legend_title_text="Banks",
        margin=dict(t=100, l=80, r=80, b=80),
    )

    fig.update_xaxes(title_text="Year", row=1, col=1)
    fig.update_yaxes(title_text="Fintech Index Score", row=1, col=1)
    fig.update_xaxes(title_text="Score", row=2, col=1)
    fig.update_yaxes(title_text="Bank", row=2, col=1, autorange="reversed")

    fig.update_traces(marker_line_color="rgba(0,0,0,0)", selector=dict(type="bar"))
    return fig


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = load_scores(input_path)
    banks = choose_banks(df, args.top, args.banks)

    latest_year = int(df["Year"].max())
    ranking_year = args.year if args.year is not None else latest_year
    print(f"Loading {input_path} ({len(df)} rows). Latest year found: {latest_year}.")
    print(f"Selected {len(banks)} bank(s) for trend display: {banks}")
    print(f"Ranking chart will show data for year: {ranking_year}")

    fig = build_charts(df, banks, ranking_year, args.top)
    fig.write_html(output_path, full_html=True)

    print(f"Visualization saved to: {output_path}")


if __name__ == "__main__":
    main()
