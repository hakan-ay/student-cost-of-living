"""Dashboard: what a month as a Turkish student in Italy costs in EUR and TRY, and how fast it is changing.

Reads only the exported marts in data/marts/ and the published weekly briefs in reports/briefs/, both committed
by the weekly refresh, so it needs no database, network access or API key.

    uv run streamlit run app/dashboard.py
"""

import json
from pathlib import Path

import duckdb
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from budget import compute_budget

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
BRIEFS = ROOT / "reports" / "briefs"
BASKET = ROOT / "dbt" / "seeds" / "basket_components.csv"
REPO = "https://github.com/hakan-ay/student-cost-of-living"

st.set_page_config(page_title="Student Cost of Living: Italy", page_icon="🎓", layout="wide")

# ---------- theme: dataviz reference palette, light and dark steps chosen separately ----------
DARK = (st.context.theme.type or "light") == "dark"
C = {
    "ink": "#f0efec" if DARK else "#0b0b0b",
    "ink2": "#c3c2b7" if DARK else "#52514e",
    "muted": "#898781",
    "grid": "#2c2c2a" if DARK else "#e1e0d9",
    "axis": "#383835" if DARK else "#c3c2b7",
    "surface": "#1a1a19" if DARK else "#fcfcfb",
    # Colour follows the entity on every chart: Italy / EUR = slot 1 (blue), Turkey / TRY = slot 2 (orange).
    "eur": "#3987e5" if DARK else "#2a78d6",
    "try": "#d95926" if DARK else "#eb6834",
}
FONT = "system-ui, -apple-system, Segoe UI, sans-serif"
PERIODS = {"1Y": 1, "3Y": 3, "5Y": 5, "10Y": 10, "All": None}


@st.cache_data
def load_marts(mtime: float) -> dict[str, pd.DataFrame]:  # mtime: reload after a data refresh
    con = duckdb.connect()
    return {name: con.execute(f"select * from read_parquet('{MARTS / name}.parquet')").df()
            for name in ("fx_daily", "cpi_monthly", "student_budget_monthly", "try_purchasing_power")}


def latest_brief() -> tuple[str, dict, list[dict]] | None:
    briefs = sorted(BRIEFS.glob("*.brief.json"))
    if not briefs:
        return None
    day = briefs[-1].name.split(".")[0]
    return day, json.loads(briefs[-1].read_text()), json.loads((BRIEFS / f"{day}.facts.json").read_text())


def fmt_pct(x: float) -> str:
    # ASCII minus: st.metric reads the delta's direction from a leading "-"
    return f"{'+' if x >= 0 else '-'}{abs(x):.1f} %"


def line_chart(df: pd.DataFrame, x: str, series: list[tuple[str, str, str]], y_title: str,
               value_fmt: str = ",.1f", area: bool = False, height: int = 320) -> go.Figure:
    """One y-axis, 2px lines, a legend for 2+ series, the end value labelled, unified hover.
    End labels that would collide are not stacked: only the first (focus) series keeps its label."""
    fig = go.Figure()
    values = pd.concat([df[col] for col, _, _ in series]).dropna()
    lo, hi = (0 if area else values.min()), values.max()
    pad = (hi - lo) * 0.08
    ends = [df[col].dropna().iloc[-1] for col, _, _ in series]
    crowded = any(abs(a - b) < (hi - lo) * 0.06 for i, a in enumerate(ends) for b in ends[i + 1:])
    for i, (col, name, color) in enumerate(series):
        fig.add_trace(go.Scatter(
            x=df[x], y=df[col], name=name, mode="lines",
            line=dict(color=color, width=2, shape="linear"),
            fill="tozeroy" if area else None,
            fillcolor=f"rgba({int(color[1:3], 16)},{int(color[3:5], 16)},{int(color[5:7], 16)},0.10)" if area else None,
            hovertemplate=f"%{{y:{value_fmt}}}<extra>{name}</extra>",
        ))
        last = df[[x, col]].dropna().iloc[-1]
        fig.add_trace(go.Scatter(  # end dot with a surface ring, part of the same entity
            x=[last[x]], y=[last[col]], mode="markers", showlegend=False, hoverinfo="skip",
            marker=dict(size=9, color=color, line=dict(color=C["surface"], width=2)), cliponaxis=False,
        ))
        if i == 0 or not crowded:
            fig.add_annotation(x=last[x], y=last[col], text=f"{last[col]:{value_fmt}}", showarrow=False,
                               xanchor="left", xshift=8, font=dict(color=C["ink"], size=12))
    fig.update_layout(
        height=height, margin=dict(l=8, r=56, t=32 if len(series) > 1 else 8, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=C["ink2"], size=12),
        hovermode="x unified", hoverlabel=dict(bgcolor=C["surface"], font_color=C["ink"], bordercolor=C["axis"]),
        showlegend=len(series) > 1,
        legend=dict(orientation="h", x=0, y=1.02, yanchor="bottom", font=dict(color=C["ink2"])),
    )
    # Exact x-range: the end dots and labels sit in the right margin instead of stretching the axis past the data.
    fig.update_xaxes(showgrid=False, linecolor=C["axis"], tickfont_color=C["muted"], range=[df[x].min(), df[x].max()],
                     spikedash="solid", spikecolor=C["axis"], spikethickness=1)
    fig.update_yaxes(title=dict(text=y_title, font=dict(color=C["muted"], size=11)), gridcolor=C["grid"],
                     range=[lo if area else lo - pad, hi + pad],
                     gridwidth=1, zeroline=False, tickfont_color=C["muted"], tickformat="~s" if area else None)
    return fig


def chart_with_table(title: str, fig: go.Figure, table: pd.DataFrame) -> None:
    # The title is page text, not part of the figure, so it never collides with a wrapped legend on a phone.
    st.markdown(f"**{title}**")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with st.expander("Data table"):
        st.dataframe(table, hide_index=True, width="stretch")


# ---------- data ----------
marts = load_marts(max(p.stat().st_mtime for p in MARTS.glob("*.parquet")))
budget = marts["student_budget_monthly"].sort_values("month")
power = marts["try_purchasing_power"].sort_values("month")
fx = marts["fx_daily"].sort_values("rate_date")
cpi = marts["cpi_monthly"]
for df, col in ((budget, "month"), (power, "month"), (fx, "rate_date"), (cpi, "month")):
    df[col] = pd.to_datetime(df[col])

reference_basket = pd.read_csv(BASKET)
latest_fx = fx.iloc[-1]
week_ago = fx[fx["rate_date"] <= latest_fx["rate_date"] - pd.Timedelta(days=7)].iloc[-1]

# ---------- header ----------
st.title("Student cost of living: Italy in EUR and TRY")
st.markdown(
    f"How much does a month as a Turkish student in Italy cost in euros and in lira, and how fast is it changing? "
    f"A reference budget for a student in Turin, moved with official price indices and converted at the ECB rate.  \n"
    f"<span style='color:{C['muted']}'>Consumer prices up to {budget['month'].max():%B %Y} · exchange rate up to "
    f"{latest_fx['rate_date']:%-d %B %Y} · refreshed weekly · [source code]({REPO})</span>",
    unsafe_allow_html=True,
)

# ---------- one filter row: period for the charts, basket for the tiles and the budget chart ----------
f_period, f_basket = st.columns([3, 2], vertical_alignment="bottom")
with f_period:
    period = st.segmented_control("Period", list(PERIODS), default="5Y", help="Applies to every chart below.") or "5Y"
with f_basket:
    basket = reference_basket.copy()
    with st.popover("Adjust the basket", width="stretch"):
        st.caption("Monthly amounts in EUR at 2025 average prices. Each one is moved with its Italian price index.")
        for i, row in basket.iterrows():
            basket.loc[i, "base_amount_eur"] = st.number_input(
                row["component"].capitalize(), min_value=0, max_value=5000, step=10,
                value=int(row["base_amount_eur"]), help=row["assumption"], key=f"basket_{row['component']}")
custom = not basket["base_amount_eur"].equals(reference_basket["base_amount_eur"])
if custom:
    st.caption(f"Custom basket: €{basket['base_amount_eur'].sum():,.0f} a month at 2025 prices "
               f"(reference €{reference_basket['base_amount_eur'].sum():,.0f}). Tiles and the budget chart use it; "
               "the weekly brief always uses the reference basket.")

mine = compute_budget(cpi, budget, power, basket)
cur = mine.iloc[-1]
prev = mine[mine["month"] == cur["month"] - pd.DateOffset(years=1)].iloc[0]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Monthly budget, EUR", f"€{cur['total_eur']:,.0f}",
          f"{fmt_pct(cur['total_eur_yoy_pct'])} vs {prev['month']:%b %Y}", delta_color="inverse")
k2.metric("Monthly budget, TRY", f"₺{cur['total_try']:,.0f}",
          f"{fmt_pct(cur['total_try_yoy_pct'])} vs {prev['month']:%b %Y}", delta_color="inverse")
k3.metric(f"EUR/TRY, {latest_fx['rate_date']:%-d %b}", f"{latest_fx['eur_try']:.2f}",
          f"{fmt_pct(100 * (latest_fx['eur_try'] / week_ago['eur_try'] - 1))} in a week", delta_color="inverse")
k4.metric("Budget in 2025 lira", f"₺{cur['budget_try_at_2025_prices']:,.0f}",
          f"{fmt_pct(cur['budget_real_try_yoy_pct'])} vs {prev['month']:%b %Y}", delta_color="inverse",
          help="The TRY budget deflated by Turkish consumer prices: what it costs a family whose income keeps up "
               "with Turkish inflation. Down means cheaper in real terms.")

years = PERIODS[period]
start = cur["month"] - pd.DateOffset(years=years) if years else mine["month"].min()

b = mine[mine["month"] >= start].copy()
b["EUR (start = 100)"] = 100 * b["total_eur"] / b["total_eur"].iloc[0]
b["TRY (start = 100)"] = 100 * b["total_try"] / b["total_try"].iloc[0]

hicp = cpi[(cpi["source"] == "eurostat_hicp") & (cpi["month"] >= start)]
gap = hicp[hicp["coicop"] == "TOTAL"].pivot(index="month", columns="geo", values="annual_rate_pct").reset_index()
rent = hicp[(hicp["geo"] == "IT") & hicp["coicop"].isin(["CP041", "TOTAL"])] \
    .pivot(index="month", columns="coicop", values="index_2025").reset_index()
f = fx[fx["rate_date"] >= start]

# ---------- charts ----------
left, right = st.columns(2)
with left:
    chart_with_table(
        f"Budget growth since {b['month'].iloc[0]:%b %Y}, EUR vs TRY",
        line_chart(b, "month", [("EUR (start = 100)", "Budget in EUR", C["eur"]),
                                ("TRY (start = 100)", "Budget in TRY", C["try"])], "Index, start = 100", ",.0f"),
        b[["month", "total_eur", "eur_try_avg", "total_try", "total_eur_yoy_pct", "total_try_yoy_pct"]]
        .rename(columns={"total_eur": "budget_eur", "total_try": "budget_try"})
        .round({"budget_eur": 2, "eur_try_avg": 4, "budget_try": 0, "total_eur_yoy_pct": 2, "total_try_yoy_pct": 2}),
    )
    st.caption("Both budgets are indexed to 100 at the start of the period so they share one axis. "
               "The gap between the lines is the effect of the exchange rate.")
with right:
    chart_with_table(
        "Inflation, Italy vs Turkey",
        line_chart(gap, "month", [("IT", "Italy", C["eur"]), ("TR", "Turkey", C["try"])], "Annual change, %"),
        gap.rename(columns={"IT": "italy_hicp_yoy_pct", "TR": "turkey_hicp_yoy_pct"}),
    )
    st.caption("Harmonised index of consumer prices (Eurostat HICP, all items), change on the same month a year earlier.")

left, right = st.columns(2)
with left:
    chart_with_table(
        "Italian rents vs all prices",
        line_chart(rent, "month", [("CP041", "Rents", C["eur"]), ("TOTAL", "All items", C["muted"])],
                   "Index, 2025 = 100"),
        rent.rename(columns={"CP041": "it_rent_index_2025", "TOTAL": "it_all_items_index_2025"}),
    )
    st.caption("Eurostat HICP for Italy: actual rentals for housing (CP041) against all items. Rent is the largest "
               "item of the student budget.")
with right:
    chart_with_table(
        "EUR/TRY, daily",
        line_chart(f, "rate_date", [("eur_try", "EUR/TRY", C["eur"])], "Lira per euro", ",.2f", area=True),
        f[["rate_date", "eur_try", "change_1d_pct", "change_30d_pct", "change_365d_pct"]],
    )
    st.caption("ECB euro reference rate for the Turkish lira, published on ECB business days.")

# ---------- latest weekly brief ----------
st.divider()
brief = latest_brief()
if brief:
    day, text, facts = brief
    by_id = {fct["id"]: fct for fct in facts}
    st.subheader(f"Weekly brief, {pd.Timestamp(day):%-d %B %Y}")
    st.markdown(f"**{text['headline']}**")
    for paragraph in text["paragraphs"]:
        st.markdown(paragraph)
    st.markdown(
        f"<span style='color:{C['muted']}'>Every number above was checked against the fact sheet before publishing. "
        f"Sources: [fact sheet]({REPO}/blob/main/reports/briefs/{day}.facts.json) · "
        f"[structured brief]({REPO}/blob/main/reports/briefs/{day}.brief.json) · "
        f"[all weekly updates]({REPO}/blob/main/WEEKLY_UPDATES.md)</span>",
        unsafe_allow_html=True,
    )
    with st.expander("Numbers in this brief and where they come from"):
        st.dataframe(pd.DataFrame([{
            "as written": c["as_written"], "fact": c["fact_id"], "value": str(by_id[c["fact_id"]]["value"]),
            "unit": by_id[c["fact_id"]]["unit"], "description": by_id[c["fact_id"]]["description"],
        } for c in text["cited_numbers"]]).drop_duplicates(), hide_index=True, width="stretch")
else:
    st.info("No weekly brief has been published yet.")

# ---------- method ----------
st.divider()
with st.expander("Reference basket and sources"):
    basket = reference_basket.copy()
    basket["weight"] = (basket["base_amount_eur"] / basket["base_amount_eur"].sum()).map("{:.1%}".format)
    st.dataframe(basket, hide_index=True, width="stretch")
    st.markdown(
        "Base amounts are monthly EUR at 2025 average prices (author's assumptions for a student in Turin) and are "
        "moved with the Italian HICP index of each category. Data: "
        "[ECB Data Portal](https://data.ecb.europa.eu/) (EXR.D.TRY.EUR.SP00.A), "
        "[Eurostat](https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_minr/default/table) (prc_hicp_minr), "
        "[Istat](https://esploradati.istat.it/) (NIC). Descriptive only, not financial advice."
    )
