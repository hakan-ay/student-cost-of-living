"""Rewrites the "Latest numbers" block of README.md from the marts, between the latest-numbers markers.

Every number in the block is read from data/warehouse.duckdb, so the README never drifts from the data.
With --check the README is not written; the script exits with 1 if the block is out of date (used in CI).

Usage (after `dbt build`):
    uv run python src/update_readme.py
    uv run python src/update_readme.py --check
"""

import argparse
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
WAREHOUSE = ROOT / "data" / "warehouse.duckdb"
START, END = "<!-- latest-numbers:start -->", "<!-- latest-numbers:end -->"


def pct(x: float) -> str:
    return f"{'+' if x >= 0 else '−'}{abs(x):.1f} %"


def money(x: float) -> str:
    return f"{x:,.0f}"


def render(con: duckdb.DuckDBPyConnection) -> str:
    cur, prev = con.execute("""
        select b.month, b.total_eur, b.eur_try_avg, b.total_try, p.budget_try_at_2025_prices,
               p.tr_inflation_yoy_pct
        from marts.student_budget_monthly as b
        join marts.try_purchasing_power as p using (month)
        where b.month in (select max(month) from marts.student_budget_monthly)
           or b.month in (select max(month) - interval 12 month from marts.student_budget_monthly)
        order by b.month desc
    """).fetchall()
    fx_date = con.execute("select max(rate_date) from marts.fx_daily").fetchone()[0]

    month, prev_month = cur[0].strftime("%b %Y"), prev[0].strftime("%b %Y")

    def change(i: int) -> float:
        return 100 * (cur[i] / prev[i] - 1)

    real_change = change(4)
    lines = [
        f"Generated from the marts: consumer prices up to {cur[0]:%B %Y}, exchange rate up to {fx_date:%-d %B %Y}.",
        "",
        f"| | {prev_month} | {month} | Change |",
        "|---|---:|---:|---:|",
        f"| Monthly budget in EUR | {money(prev[1])} | {money(cur[1])} | {pct(change(1))} |",
        f"| Average EUR/TRY | {prev[2]:.1f} | {cur[2]:.1f} | {pct(change(2))} |",
        f"| Monthly budget in TRY | {money(prev[3])} | {money(cur[3])} | {pct(change(3))} |",
        f"| Budget in TRY at 2025 Turkish prices | {money(prev[4])} | {money(cur[4])} | {pct(real_change)} |",
        "",
        f"In nominal lira the budget changed by {pct(change(3))} in a year. Turkish prices rose "
        f"{'faster' if cur[5] > change(2) else 'slower'} than the euro did (Turkish HICP {pct(cur[5])} against "
        f"EUR/TRY {pct(change(2))}), so for a household whose income keeps up with Turkish inflation the same month "
        f"in Italy became about {abs(real_change):.0f} % {'cheaper' if real_change < 0 else 'more expensive'} "
        "in real terms.",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="exit 1 if README.md is out of date, do not write")
    args = parser.parse_args()

    text = README.read_text()
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    block = render(duckdb.connect(str(WAREHOUSE), read_only=True))
    new = f"{head}{START}\n{block}\n{END}{tail}"

    if args.check:
        if new != text:
            print("README.md 'Latest numbers' is out of date: run src/update_readme.py")
            sys.exit(1)
        print("README.md is up to date")
        return
    README.write_text(new)
    print(block)


if __name__ == "__main__":
    main()
