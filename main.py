from pathlib import Path

import pandas as pd

from config import get_config
from src.data_fetcher import (
    ensure_cache_dir,
    fetch_financial_statements_cached,
    fetch_overview_cached,
    market_price_realtime_av,
)
from src.statements import build_standardized_statements
from src.ratios import build_ratios_table
from src.multiples import build_peer_multiples
from src.dcf import run_dcf_valuation
from src.visualization import (
    plot_ratios_trends,
    plot_multiples_charts,
)
from src.llm_report import generate_llm_report


def main():
    cfg = get_config()
    ensure_cache_dir(cfg.cache_dir)

    # 1) Data ingestion (cache-first)
    paths = fetch_financial_statements_cached(cfg.symbol, cfg)
    overview = fetch_overview_cached(cfg.symbol, cfg)

    # 2) Statements standardisation
    is_df, bs_df, cf_df = build_standardized_statements(paths, cfg.years)

    # 3) Ratios + trend outputs
    ratios_df = build_ratios_table(is_df, bs_df, cf_df)

    # 4) Peer multiples (+ charts later)
    multiples_df = build_peer_multiples(cfg, asof=cfg.asof)

    # 5) DCF valuation (revenue -> EBIT -> FCFF -> DCF -> intrinsic)
    dcf_out = run_dcf_valuation(is_df, bs_df, cf_df, overview, cfg)

    # 6) Visualisations
    out_dir = Path(cfg.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_ratios_trends(ratios_df, out_dir)
    plot_multiples_charts(multiples_df, out_dir)

    # 7) Market price + LLM grounded report
    live_price = market_price_realtime_av(cfg.symbol, cfg)
    report_path = generate_llm_report(
        cfg=cfg,
        ratios_df=ratios_df,
        multiples_df=multiples_df,
        dcf_out=dcf_out,
        live_price=live_price,
        out_dir=out_dir,
    )

    # 8) Console summary (nice for demo)
    print("\n=== SUMMARY ===")
    print(f"Symbol: {cfg.symbol}")
    print(f"Intrinsic value (DCF): {dcf_out['intrinsic_value_per_share']:.2f}")
    if live_price is not None:
        upside = (dcf_out["intrinsic_value_per_share"] / live_price) - 1.0
        print(f"Market price (live): {live_price:.2f}")
        print(f"Upside: {upside:.2%}")
    print(f"Report saved to: {report_path}")


if __name__ == "__main__":
    main()
