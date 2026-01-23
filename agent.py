from .config import DEFAULT_SYMBOL, DEFAULT_YEARS
from .av_client import fetch_annual_statement_paths
from .statements import build_annual_dfs, to_views_in_bn


def run(symbol: str = DEFAULT_SYMBOL):
    paths = fetch_annual_statement_paths(symbol)

    is_df, bs_df, cf_df = build_annual_dfs(paths, DEFAULT_YEARS)
    is_view, bs_view, cf_view = to_views_in_bn(is_df, bs_df, cf_df)

    return {
        "symbol": symbol,
        "paths": {k: str(v) for k, v in paths.items()},
        "is_df": is_df,
        "bs_df": bs_df,
        "cf_df": cf_df,
        "is_view": is_view,
        "bs_view": bs_view,
        "cf_view": cf_view,
    }
