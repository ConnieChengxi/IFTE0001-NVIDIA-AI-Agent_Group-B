import pandas as pd


def build_ratios_table(is_df: pd.DataFrame, bs_df: pd.DataFrame, cf_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge 3 statements by fiscal_year and compute core profitability + returns.
    """
    df = (
        is_df.merge(bs_df, on=["fiscal_year", "fiscal_date_ending"], how="inner")
             .merge(cf_df, on=["fiscal_year", "fiscal_date_ending"], how="inner")
             .sort_values("fiscal_year")
             .reset_index(drop=True)
    )

    # averages for ROA/ROE
    df["avg_assets"] = (df["total_assets"] + df["total_assets"].shift(1)) / 2
    df["avg_equity"] = (df["total_shareholder_equity"] + df["total_shareholder_equity"].shift(1)) / 2

    df["gross_margin"] = (df["revenue"] - df["cogs"]) / df["revenue"]
    df["operating_margin"] = df["operating_income"] / df["revenue"]
    df["net_margin"] = df["net_income"] / df["revenue"]
    df["roa"] = df["net_income"] / df["avg_assets"]
    df["roe"] = df["net_income"] / df["avg_equity"]

    # simple growth rates
    df["revenue_yoy"] = df["revenue"].pct_change()
    df["net_income_yoy"] = df["net_income"].pct_change()

    return df

