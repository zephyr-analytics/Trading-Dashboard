"""
utilities.py — Macro SMA Trend-Following Dashboard
====================================================
Data fetchers, signal logic, style constants, and persistence
for the SimpleMacroSMATrendFollowing strategy dashboard.
"""

from __future__ import annotations

import json
import os
import warnings
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf
from dash import html

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════════════
#  PERSISTENCE
# ═══════════════════════════════════════════════════════════════════════
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "portfolio_data.json")


def load_saved() -> dict:
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_all(data: dict) -> None:
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[WARN] Could not save: {e}")


# ═══════════════════════════════════════════════════════════════════════
#  STRATEGY CONSTANTS  (mirrors SimpleMacroSMATrendFollowing)
# ═══════════════════════════════════════════════════════════════════════
RISK_TICKERS: list[str]  = ["VTI", "VEA", "VWO", "BND", "BNDX", "DBC", "GLD", "BTC-USD"]
CASH_TICKER:  str        = "SHV"
ALL_TICKERS:  list[str]  = RISK_TICKERS + [CASH_TICKER]

# YF display labels  (BTC-USD shown as BTCUSD in UI)
DISPLAY: dict[str, str] = {"BTC-USD": "BTCUSD"}

N_ASSETS:    int   = len(ALL_TICKERS)   # 9  (8 risk + 1 cash)
BASE_WEIGHT: float = 1.0 / N_ASSETS     # ~11.11% each slot

ETF_SMA_PERIOD:  int = 147
BOND_SMA_PERIOD: int = 126
BOND_TICKERS: list[str] = ["BND", "BNDX"]

LOOKBACK_3M: int = 63   # trading-day approximation of 3 months
MIN_HISTORY:  int = ETF_SMA_PERIOD + 5


def sma_period_for(ticker: str) -> int:
    return BOND_SMA_PERIOD if ticker in BOND_TICKERS else ETF_SMA_PERIOD


# ═══════════════════════════════════════════════════════════════════════
#  COLOURS & STYLES
# ═══════════════════════════════════════════════════════════════════════
DARK_BG      = "#080c14"
CARD_BG      = "#0e1420"
CARD_BORDER  = "#1e2d45"

ACCENT   = "#38bdf8"    # sky-blue  — primary
ACCENT2  = "#818cf8"    # indigo    — secondary
ACCENT3  = "#34d399"    # emerald   — positive
ACCENT4  = "#fb923c"    # amber     — warning
ACCENT5  = "#a78bfa"    # violet    — cash

RED      = "#f87171"
GREEN    = "#4ade80"
YELLOW   = "#facc15"
TEXT     = "#e2e8f0"
MUTED    = "#64748b"
CASH_CLR = "#94a3b8"

PIE_COLORS = [
    "#38bdf8","#818cf8","#34d399","#fb923c","#a78bfa",
    "#f472b6","#fbbf24","#4ade80","#94a3b8",
]

CARD: dict = {
    "backgroundColor": CARD_BG,
    "border": f"1px solid {CARD_BORDER}",
    "borderRadius": "10px",
    "padding": "20px",
    "marginBottom": "16px",
}
INP: dict = {
    "backgroundColor": "#111827",
    "border": f"1px solid {CARD_BORDER}",
    "borderRadius": "6px",
    "color": TEXT,
    "padding": "8px 12px",
    "fontSize": "13px",
    "outline": "none",
    "width": "100%",
    "boxSizing": "border-box",
}
BTN: dict = {
    "backgroundColor": ACCENT,
    "color": "#030712",
    "border": "none",
    "borderRadius": "6px",
    "padding": "9px 18px",
    "fontSize": "13px",
    "fontWeight": "700",
    "cursor": "pointer",
    "width": "100%",
}
BTN2 = {**BTN, "backgroundColor": ACCENT2, "color": "#fff"}
LBL: dict = {
    "fontSize": "11px",
    "color": MUTED,
    "letterSpacing": "0.8px",
    "textTransform": "uppercase",
    "marginBottom": "5px",
    "display": "block",
}
TAB_BASE: dict = {
    "backgroundColor": CARD_BG,
    "color": MUTED,
    "border": f"1px solid {CARD_BORDER}",
    "borderRadius": "8px 8px 0 0",
    "padding": "10px 20px",
    "fontSize": "12px",
    "fontWeight": "600",
    "letterSpacing": "1px",
}


def tab_sel(color: str) -> dict:
    return {**TAB_BASE, "backgroundColor": DARK_BG,
            "color": color, "borderBottom": f"2px solid {color}"}


# ═══════════════════════════════════════════════════════════════════════
#  SHARED HELPERS
# ═══════════════════════════════════════════════════════════════════════

def disp(ticker: str) -> str:
    """Return display label for a ticker."""
    return DISPLAY.get(ticker, ticker)


def fmt(val, sign: bool = False) -> str:
    if val is None:
        return "—"
    pre = ("+" if val >= 0 else "") if sign else ""
    if abs(val) >= 1_000_000:
        return f"{pre}${val / 1e6:.2f}M"
    if abs(val) >= 1_000:
        return f"{pre}${val:,.2f}"
    return f"{pre}${val:.2f}"


def pct_fmt(val, decimals: int = 2) -> str:
    if val is None or (isinstance(val, float) and (np.isnan(val) or np.isinf(val))):
        return "—"
    return f"{val*100:+.{decimals}f}%"


def pcolor(val) -> str:
    if val is None:
        return MUTED
    return GREEN if val >= 0 else RED


def kpi_card(label, val, color=TEXT, sub=None, bar_color=None) -> html.Div:
    return html.Div(
        style={**CARD, "flex": "1", "minWidth": "140px", "marginBottom": "0",
               "position": "relative", "overflow": "hidden"},
        children=[
            html.Div(label, style={"fontSize": "10px", "color": MUTED,
                                   "letterSpacing": "1px", "textTransform": "uppercase",
                                   "marginBottom": "6px"}),
            html.Div(val,   style={"fontSize": "20px", "fontWeight": "800", "color": color}),
            html.Div(sub or "", style={"fontSize": "11px", "color": MUTED, "marginTop": "3px"}),
            html.Div(style={"position": "absolute", "bottom": "0", "left": "0",
                            "height": "3px", "width": "100%",
                            "background": f"linear-gradient(90deg,{bar_color or ACCENT},{ACCENT2})"}),
        ],
    )


# ═══════════════════════════════════════════════════════════════════════
#  DATA FETCHER
# ═══════════════════════════════════════════════════════════════════════

def _get_close(raw: pd.DataFrame, ticker: str) -> pd.Series:
    try:
        cols = raw.columns
        if isinstance(cols, pd.MultiIndex):
            if ("Close", ticker) in cols:
                return raw[("Close", ticker)].dropna()
            if (ticker, "Close") in cols:
                return raw[(ticker, "Close")].dropna()
            try:
                sub = raw.xs(ticker, axis=1, level=1)
                if "Close" in sub.columns:
                    return sub["Close"].dropna()
            except Exception:
                pass
            try:
                sub = raw.xs("Close", axis=1, level=0)
                if ticker in sub.columns:
                    return sub[ticker].dropna()
            except Exception:
                pass
        if "Close" in cols:
            return raw["Close"].dropna()
        if ticker in cols:
            return raw[ticker].dropna()
    except Exception:
        pass
    return pd.Series(dtype=float)


def fetch_market_data() -> dict[str, pd.Series]:
    """
    Download ~200 days of daily closes for all tickers.
    Returns {ticker: pd.Series of float closes, sorted oldest→newest}.
    """
    prices: dict[str, pd.Series] = {}
    needed_days = MIN_HISTORY + 10

    # ETFs + cash in one batch
    etf_list = [t for t in ALL_TICKERS if t != "BTC-USD"]
    try:
        raw = yf.download(etf_list, period=f"{needed_days}d",
                          auto_adjust=True, progress=False)
        for t in etf_list:
            s = _get_close(raw, t)
            if not s.empty:
                prices[t] = s.sort_index()
    except Exception as e:
        print(f"[WARN] ETF fetch failed: {e}")

    # BTC separately
    try:
        raw_btc = yf.download("BTC-USD", period=f"{needed_days}d",
                               auto_adjust=True, progress=False)
        s = _get_close(raw_btc, "BTC-USD")
        if s.empty and "Close" in raw_btc.columns:
            s = raw_btc["Close"].dropna()
        if not s.empty:
            prices["BTC-USD"] = s.sort_index()
    except Exception as e:
        print(f"[WARN] BTC fetch failed: {e}")

    return prices


# ═══════════════════════════════════════════════════════════════════════
#  SIGNAL ENGINE  (exact port of SimpleMacroSMATrendFollowing.Rebalance)
# ═══════════════════════════════════════════════════════════════════════

def _ret3m(s: pd.Series) -> float | None:
    """
    Mirrors QC GetReturn(symbol, 63):
      return (closes[-1] / closes[0]) - 1  over 64 bars (63+1).
    """
    if s is None or len(s) < LOOKBACK_3M + 1:
        return None
    return float(s.iloc[-1] / s.iloc[-(LOOKBACK_3M + 1)] - 1)


def compute_signal(prices: dict[str, pd.Series]) -> dict:
    """
    Exact port of SimpleMacroSMATrendFollowing.Rebalance().

    self.all_tickers = risk_tickers(8) + [cash_ticker]  → 9 total
    self.n_assets    = 9   (comment in QC code says 8 — that is wrong)
    self.base_weight = 1/9 ≈ 11.11%

    Steps
    ─────
    1. SMA gate on risk_tickers only (SHV is never gated)
    2. 3m returns for ALL 9 tickers; bench = mean(all 9), floor 0
    3. raw_weight[t] = clamp(ret[t]/bench, 0, 2) × base_weight  for above-SMA risk assets
    4. freed = 1 − Σraw_weights  →  top-up outperformers (ratio>1) to their 2× headroom,
       then remainder → SHV
    5. normalise all weights so they sum to 1
    """

    # ── Step 1 & prices ───────────────────────────────────────────────
    asset_data: dict = {}
    for t in ALL_TICKERS:
        s = prices.get(t)
        if s is None or s.empty:
            asset_data[t] = {
                "price": None, "sma": None, "sma_period": sma_period_for(t),
                "above_sma": False, "ret3m": None,
            }
            continue
        period = sma_period_for(t)
        price  = float(s.iloc[-1])
        sma    = float(s.rolling(period).mean().iloc[-1]) if len(s) >= period else None
        # SMA gate applies to risk_tickers only; SHV is always "pass"
        above  = (price > sma) if (sma is not None and t in RISK_TICKERS) else (t == CASH_TICKER)
        asset_data[t] = {
            "price": price, "sma": sma, "sma_period": period,
            "above_sma": above, "ret3m": _ret3m(s),
        }

    # ── Step 2: 3m returns for all 9; benchmark = mean(all 9), floor 0 ──
    all_returns: dict[str, float] = {}
    for t in ALL_TICKERS:                        # <-- all 9, including SHV
        r = asset_data[t].get("ret3m")
        all_returns[t] = r if r is not None else 0.0

    bench3m = sum(all_returns.values()) / N_ASSETS   # divide by 9
    if bench3m < 0:
        bench3m = 0.0

    # ── Step 3: raw weights for above-SMA risk assets ─────────────────
    above_sma = [t for t in RISK_TICKERS if asset_data[t]["above_sma"]]
    below_sma = [t for t in RISK_TICKERS if not asset_data[t]["above_sma"]]

    ratios: dict[str, float] = {}          # ret[t] / bench  (diagnostic)
    raw_weights: dict[str, float] = {}     # before Step-4 top-up

    for t in above_sma:
        if bench3m > 0:
            ratio = all_returns[t] / bench3m
        else:
            ratio = 1.0 if all_returns[t] > 0 else 0.0
        ratios[t] = ratio
        raw_weights[t] = max(0.0, min(ratio, 2.0)) * BASE_WEIGHT

    # Store raw weights BEFORE top-up (for display)
    raw_weights_pre_topup: dict[str, float] = dict(raw_weights)

    risk_assigned = sum(raw_weights.values())
    freed_weight  = 1.0 - risk_assigned

    # ── Step 4: freed → outperformers (ratio > 1), remainder → SHV ───
    outperformers = {
        t: ratios[t]
        for t in above_sma
        if bench3m > 0 and ratios.get(t, 0) > 1.0
    }

    topup_received: dict[str, float] = {}   # diagnostic
    if outperformers and freed_weight > 0:
        headroom = {
            t: max(0.0, 2.0 * BASE_WEIGHT - raw_weights[t])
            for t in outperformers
        }
        total_headroom = sum(headroom.values())
        if total_headroom > 0:
            to_out = min(freed_weight, total_headroom)
            for t, room in headroom.items():
                bump = to_out * (room / total_headroom)
                raw_weights[t] += bump
                topup_received[t] = bump
            freed_weight -= to_out

    # Whatever freed weight is left goes to SHV
    cash_pre_norm = max(0.0, freed_weight)
    raw_weights[CASH_TICKER] = cash_pre_norm

    # ── Step 5: normalise ─────────────────────────────────────────────
    total = sum(raw_weights.values())
    final_weights: dict[str, float] = {
        t: (raw_weights.get(t, 0.0) / total) if total > 0 else 0.0
        for t in ALL_TICKERS
    }

    # ── Pack per-asset diagnostics ────────────────────────────────────
    for t in ALL_TICKERS:
        is_risk  = t in RISK_TICKERS
        is_above = asset_data[t]["above_sma"]
        ratio    = ratios.get(t)        # only set for above-SMA risk assets

        # classify weight driver
        if not is_risk:
            driver = "cash"
        elif not is_above:
            driver = "below_sma"
        elif ratio is not None and ratio >= 2.0:
            driver = "capped"
        elif ratio is not None and ratio > 1.0:
            driver = "outperformer"
        elif ratio is not None and ratio > 0:
            driver = "underperformer"
        else:
            driver = "floor"

        asset_data[t].update({
            "ret3m":             all_returns[t],
            "ratio":             ratio,                        # ret/bench
            "raw_weight_pre":    raw_weights_pre_topup.get(t, 0.0),
            "topup":             topup_received.get(t, 0.0),
            "raw_weight":        raw_weights.get(t, 0.0),
            "final_weight":      final_weights[t],
            "base_weight":       BASE_WEIGHT,
            "driver":            driver,
            "is_outperformer":   t in outperformers,
            "cap_2x":            2.0 * BASE_WEIGHT,
        })

    # as_of
    dates = [s.index[-1] for s in prices.values() if not s.empty]
    as_of = str(max(dates).date()) if dates else "—"

    return {
        "assets":              asset_data,
        "all_returns":         all_returns,
        "bench3m":             bench3m,
        "freed_weight_total":  1.0 - risk_assigned,   # before any top-up
        "freed_to_outperf":    (1.0 - risk_assigned) - cash_pre_norm,
        "cash_pre_norm":       cash_pre_norm,
        "final_weights":       final_weights,
        "above_sma":           above_sma,
        "below_sma":           below_sma,
        "as_of":               as_of,
        "n_above_sma":         len(above_sma),
        "n_assets":            N_ASSETS,
        "base_weight":         BASE_WEIGHT,
    }


# ═══════════════════════════════════════════════════════════════════════
#  REBALANCE ENGINE
# ═══════════════════════════════════════════════════════════════════════

def compute_rebalance(signal: dict, holdings: dict, total_value: float) -> list[dict]:
    """
    Compute per-asset rebalance delta given current holdings.

    holdings = {ticker: {"shares": float, "avg_cost": float}}
    Returns list of row dicts for display.
    """
    rows = []
    for t in ALL_TICKERS:
        a       = signal["assets"].get(t, {})
        fw      = a.get("final_weight", 0.0)
        price   = a.get("price")
        h       = (holdings or {}).get(t) or {}
        shares  = h.get("shares") or 0.0
        avg_cost= h.get("avg_cost")

        cur_val    = (price * shares) if price else None
        target_val = total_value * fw
        delta_val  = (target_val - cur_val) if cur_val is not None else None
        delta_sh   = (delta_val / price)     if (delta_val is not None and price) else None
        pnl        = ((price - avg_cost) * shares
                      if (price and avg_cost and shares) else None)

        rows.append({
            "ticker":      t,
            "display":     disp(t),
            "price":       price,
            "final_weight": fw,
            "target_val":  target_val,
            "cur_val":     cur_val,
            "delta_val":   delta_val,
            "delta_shares":delta_sh,
            "pnl":         pnl,
            "above_sma":   a.get("above_sma", False),
            "is_cash":     t == CASH_TICKER,
        })

    rows.sort(key=lambda r: (-r["final_weight"], r["ticker"]))
    return rows


# ═══════════════════════════════════════════════════════════════════════
#  JSON SAFETY
# ═══════════════════════════════════════════════════════════════════════

def _clean(v):
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) or np.isinf(v) else float(v)
    if isinstance(v, float):
        return None if (np.isnan(v) or np.isinf(v)) else v
    return v


def signal_to_json(sig: dict) -> dict:
    """Make signal dict JSON-safe for dcc.Store."""
    safe_assets = {}
    for t, d in sig.get("assets", {}).items():
        safe_assets[t] = {k: _clean(v) for k, v in d.items()}
    return {
        **{k: _clean(v) for k, v in sig.items() if k not in ("assets", "all_returns", "final_weights")},
        "assets":        safe_assets,
        "all_returns":   {t: _clean(v) for t, v in sig.get("all_returns", {}).items()},
        "final_weights": {t: _clean(v) for t, v in sig.get("final_weights", {}).items()},
        "above_sma":     sig.get("above_sma", []),
        "below_sma":     sig.get("below_sma", []),
    }
