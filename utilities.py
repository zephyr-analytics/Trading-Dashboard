"""
utilities.py  —  Portfolio Dashboard helper module
====================================================
Provides constants, styles, data-fetchers, signal logic, and persistence
for portfolio_dashboard.py.  Import as:

    import utilities

Then call as:  utilities.fmt(val)  /  utilities.fetch_core_market(tickers)  etc.
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
import plotly.graph_objects as go

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
#  PORTFOLIO DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════

# ── Core Portfolio ──────────────────────────────────────────────────
CORE_PORTFOLIO: dict[str, dict] = {
    "VTI":  {"target_pct": 0.3200, "sma_period": 168},
    "VEU":  {"target_pct": 0.2200, "sma_period": 168},
    "BND":  {"target_pct": 0.2200, "sma_period": 126},
    "BNDX": {"target_pct": 0.1400, "sma_period": 126},
    "DBC":  {"target_pct": 0.0333, "sma_period": 168},
    "GLD":  {"target_pct": 0.0333, "sma_period": 168},
    "IBIT": {"target_pct": 0.0334, "sma_period": 168},
}
CORE_TICKERS: list[str] = list(CORE_PORTFOLIO.keys())

# ── Momentum Portfolio ──────────────────────────────────────────────
MOM_ETF_TICKERS: list[str] = ["VTI", "VEU", "BND", "BNDX", "GLD", "DBC", "SGOV"]
MOM_BTC_TICKER      = "BTC-USD"
MOM_CASH_TICKER     = "SGOV"
MOM_LOOKBACKS       = [21, 63, 126, 189, 252]
MOM_MAX_LOOKBACK    = max(MOM_LOOKBACKS)
MOM_SMA_PERIOD      = 168
MOM_SMA_OVERRIDES   = {"BND": 126, "BNDX": 126}
MOM_VOL_LOOKBACK    = 63
MOM_TARGET_VOL      = 0.20
MOM_MAX_WEIGHT      = 1.0
MOM_TOP_N           = 2
_MOM_N_BARS         = MOM_MAX_LOOKBACK + MOM_SMA_PERIOD + 10

# ── Dow Titans ──────────────────────────────────────────────────────
DOW_TITANS: list[str] = [
    "NVDA", "AAPL", "MSFT", "AVGO", "TSM",  "CSCO", "ORCL", "IBM",  "SAP",  "CRM",  "ACN",
    "META", "GOOGL","NFLX",
    "AMZN", "TSLA", "TM",   "MCD",
    "PG",   "KO",   "PM",   "PEP",  "UL",
    "LLY",  "JNJ",  "ABBV", "AZN",  "NVS",  "MRK",  "ABT",  "TMO",  "PFE",  "NVO",
    "JPM",  "V",    "MA",   "HSBC", "GS",   "RY",
    "XOM",  "CVX",  "SHEL",
    "CAT",  "GE",   "LIN",  "ASML",
]
TITANS_BENCHMARKS = ["SHV", "BND", "ACWI"]
TITANS_EMA_PERIOD = 200

# ── Cash Portfolio ───────────────────────────────────────────────────
CASH_INSTRUMENTS: list[str] = ["SGOV", "SHV", "ICSH"]
CASH_TICKERS_YF:  list[str] = CASH_INSTRUMENTS
CASH_LABEL                  = "$CASH"
CASH_WEIGHT_EACH            = 0.25


# ═══════════════════════════════════════════════════════════════════════
#  COLOURS & STYLES
# ═══════════════════════════════════════════════════════════════════════
DARK_BG     = "#0d0d12"
CARD_BG     = "#16131f"
CARD_BORDER = "#2d2640"

ACCENT  = "#c4b5fd"
ACCENT2 = "#a78bfa"
ACCENT3 = "#7c3aed"
ACCENT4 = "#e0d7ff"
ACCENT5 = "#ddd6fe"

RED     = "#f87171"
GREEN   = "#86efac"
YELLOW  = "#e9d5ff"
TEXT    = "#f5f3ff"
MUTED   = "#7c6f9f"
CASH_CLR= "#6d6082"

PIE_COLORS: list[str] = [
    "#c4b5fd","#a78bfa","#7c3aed","#ddd6fe","#6d28d9",
    "#ede9fe","#4c1d95","#e0d7ff","#8b5cf6","#f5f3ff",
    "#5b21b6","#d8b4fe","#6d6082","#c084fc","#9333ea",
]

CARD: dict = {
    "backgroundColor": CARD_BG,
    "border": f"1px solid {CARD_BORDER}",
    "borderRadius": "12px",
    "padding": "20px",
    "marginBottom": "16px",
}
INP: dict = {
    "backgroundColor": "#1e1a2e",
    "border": f"1px solid {CARD_BORDER}",
    "borderRadius": "8px",
    "color": TEXT,
    "padding": "8px 12px",
    "fontSize": "13px",
    "outline": "none",
    "width": "100%",
    "boxSizing": "border-box",
}
BTN: dict = {
    "backgroundColor": ACCENT,
    "color": "#1a0a3d",
    "border": "none",
    "borderRadius": "8px",
    "padding": "9px 18px",
    "fontSize": "13px",
    "fontWeight": "700",
    "cursor": "pointer",
    "width": "100%",
}
BTN2 = {**BTN, "backgroundColor": ACCENT2, "color": "#fff"}
BTN3 = {**BTN, "backgroundColor": ACCENT3, "color": "#fff"}
BTN4 = {**BTN, "backgroundColor": ACCENT4, "color": "#fff"}
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
    "padding": "10px 22px",
    "fontSize": "12px",
    "fontWeight": "600",
    "letterSpacing": "1px",
}


def tab_sel(color: str) -> dict:
    """Return a selected-tab style dict for the given accent colour."""
    return {
        **TAB_BASE,
        "backgroundColor": DARK_BG,
        "color": color,
        "borderBottom": f"2px solid {color}",
    }


# ═══════════════════════════════════════════════════════════════════════
#  SHARED HELPERS
# ═══════════════════════════════════════════════════════════════════════

def fmt(val, sign: bool = False) -> str:
    """Format a numeric value as a dollar string."""
    if val is None:
        return "—"
    pre = ("+" if val >= 0 else "") if sign else ""
    if abs(val) >= 1_000_000:
        return f"{pre}${val / 1e6:.2f}M"
    if abs(val) >= 1_000:
        return f"{pre}${val:,.2f}"
    return f"{pre}${val:.2f}"


def pcolor(val) -> str:
    """Return GREEN, RED, or MUTED based on sign of val."""
    if val is None:
        return MUTED
    return GREEN if val >= 0 else RED


def _get_close(raw: pd.DataFrame, ticker: str) -> pd.Series:
    """
    Extract a clean Close price Series for *ticker* from a yfinance DataFrame.
    Handles every column layout across yfinance versions.
    """
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
            for lvl in [0, 1]:
                try:
                    labels = cols.get_level_values(lvl)
                    if ticker in labels:
                        idx = list(labels).index(ticker)
                        return raw.iloc[:, idx].dropna()
                except Exception:
                    pass
        if "Close" in cols:
            return raw["Close"].dropna()
        if "close" in cols:
            return raw["close"].dropna()
        if ticker in cols:
            return raw[ticker].dropna()
    except Exception:
        pass
    return pd.Series(dtype=float)


def kpi_card(
    label: str,
    val: str,
    color: str = TEXT,
    sub: str | None = None,
    bar_color: str = ACCENT,
    min_w: str = "150px",
) -> html.Div:
    """Render a single KPI card Div."""
    return html.Div(
        style={
            **CARD,
            "flex": "1",
            "minWidth": min_w,
            "marginBottom": "0",
            "position": "relative",
            "overflow": "hidden",
        },
        children=[
            html.Div(label, style={"fontSize": "10px", "color": MUTED,
                                   "letterSpacing": "1px", "textTransform": "uppercase",
                                   "marginBottom": "6px"}),
            html.Div(val,   style={"fontSize": "20px", "fontWeight": "800", "color": color}),
            html.Div(sub or "", style={"fontSize": "11px", "color": MUTED, "marginTop": "3px"}),
            html.Div(style={"position": "absolute", "bottom": "0", "left": "0",
                            "height": "3px", "width": "100%",
                            "background": f"linear-gradient(90deg,{bar_color},{ACCENT2})"}),
        ],
    )


# ═══════════════════════════════════════════════════════════════════════
#  DATA FETCHERS
# ═══════════════════════════════════════════════════════════════════════

def fetch_core_market(tickers: list[str]) -> dict:
    result = {t: {"price": None, "sma_126": None, "sma_168": None} for t in tickers}
    try:
        raw = yf.download(tickers, period="400d", interval="1d",
                          progress=False, auto_adjust=True)
        for t in tickers:
            try:
                close = _get_close(raw, t)
                if close.empty:
                    continue
                result[t] = {
                    "price":   float(close.iloc[-1]),
                    "sma_126": float(close.rolling(126).mean().iloc[-1]) if len(close) >= 126 else None,
                    "sma_168": float(close.rolling(168).mean().iloc[-1]) if len(close) >= 168 else None,
                }
            except Exception:
                pass
    except Exception:
        pass
    return result


def fetch_momentum_data() -> dict[str, pd.Series]:
    """Return {ticker: pd.Series of closes} for all ETFs + BTC."""
    prices: dict[str, pd.Series] = {}
    for use_flat in [True, False]:
        try:
            kwargs = dict(period=f"{_MOM_N_BARS}d", auto_adjust=True, progress=False)
            if use_flat:
                kwargs["multi_level_index"] = False
            raw = yf.download(MOM_ETF_TICKERS, **kwargs)
            if raw.empty:
                continue
            for t in MOM_ETF_TICKERS:
                if t in prices:
                    continue
                s = _get_close(raw, t)
                if not s.empty:
                    prices[t] = s.dropna()
            if len(prices) >= len(MOM_ETF_TICKERS) // 2:
                break
        except Exception:
            pass
    try:
        raw_btc = yf.download(MOM_BTC_TICKER, period=f"{_MOM_N_BARS}d",
                               auto_adjust=True, progress=False)
        s = _get_close(raw_btc, MOM_BTC_TICKER)
        if s.empty and "Close" in raw_btc.columns:
            s = raw_btc["Close"].dropna()
        if not s.empty:
            prices[MOM_BTC_TICKER] = s
    except Exception:
        pass
    return prices


def fetch_titans_prices() -> dict[str, pd.Series]:
    all_t = DOW_TITANS + TITANS_BENCHMARKS
    prices: dict[str, pd.Series] = {}
    start = (datetime.today() - timedelta(days=420)).strftime("%Y-%m-%d")
    for use_flat in [True, False]:
        try:
            kwargs = dict(start=start, auto_adjust=True, progress=False)
            if use_flat:
                kwargs["multi_level_index"] = False
            raw = yf.download(all_t, **kwargs)
            if raw.empty:
                continue
            for t in all_t:
                if t in prices:
                    continue
                s = _get_close(raw, t)
                if not s.empty:
                    try:
                        s.index = pd.to_datetime(s.index).tz_localize(None)
                    except Exception:
                        pass
                    prices[t] = s
            if len(prices) >= len(all_t) // 2:
                break
        except Exception:
            pass
    return prices


def fetch_cash_market() -> dict:
    """Fetch latest prices for the 3 cash ETFs."""
    result: dict = {t: {"price": None} for t in CASH_TICKERS_YF}
    result[CASH_LABEL] = {"price": 1.0}
    try:
        raw = yf.download(CASH_TICKERS_YF, period="5d", interval="1d",
                          progress=False, auto_adjust=True)
        for t in CASH_TICKERS_YF:
            try:
                close = _get_close(raw, t)
                if not close.empty:
                    result[t] = {"price": float(close.iloc[-1])}
            except Exception:
                pass
    except Exception:
        pass
    return result


# ═══════════════════════════════════════════════════════════════════════
#  SIGNAL LOGIC — Core
# ═══════════════════════════════════════════════════════════════════════

def sma_signal(td: dict, period: int) -> str:
    p, s = td.get("price"), td.get(f"sma_{period}")
    if p is None or s is None:
        return "UNKNOWN"
    return "BUY" if p >= s else "SELL/CASH"


def compute_core_rebalance(
    holdings: dict,
    market: dict,
    alloc_value: float,
) -> list[dict]:
    cash_pct = sum(
        cfg["target_pct"]
        for t, cfg in CORE_PORTFOLIO.items()
        if sma_signal((market or {}).get(t, {}), cfg["sma_period"]) != "BUY"
    )
    rows = []
    for t, cfg in CORE_PORTFOLIO.items():
        md          = (market or {}).get(t, {})
        price       = md.get("price")
        signal      = sma_signal(md, cfg["sma_period"])
        h           = ((holdings or {}).get(t) or {})
        cur_shares  = h.get("shares") or 0
        avg_cost    = h.get("avg_cost")
        cur_val     = (price * cur_shares) if (price and cur_shares) else h.get("current_value")
        eff_pct     = cfg["target_pct"] if signal == "BUY" else 0.0
        target_val  = alloc_value * eff_pct
        delta_val   = (target_val - cur_val) if cur_val is not None else None
        delta_sh    = (delta_val / price) if (delta_val is not None and price) else None
        pnl = ((price - avg_cost) * cur_shares) if (cur_shares and price and avg_cost) else None
        rows.append({
            "ticker": t, "signal": signal, "sma_period": cfg["sma_period"],
            "target_pct": cfg["target_pct"], "eff_target": eff_pct,
            "price": price, "cur_shares": cur_shares, "cur_val": cur_val,
            "target_val": target_val, "delta_val": delta_val, "delta_shares": delta_sh,
            "avg_cost": avg_cost, "pnl_unreal": pnl,
        })
    rows.append({
        "ticker": "CASH", "signal": "HOLD", "sma_period": None,
        "target_pct": cash_pct, "eff_target": cash_pct, "price": 1.0,
        "cur_shares": None, "cur_val": None, "target_val": alloc_value * cash_pct,
        "delta_val": None, "delta_shares": None, "avg_cost": None, "pnl_unreal": None,
    })
    return rows


# ═══════════════════════════════════════════════════════════════════════
#  SIGNAL LOGIC — Momentum (private helpers + public entry point)
# ═══════════════════════════════════════════════════════════════════════

def _mom_momentum(ticker: str, prices: dict) -> float:
    s = prices.get(ticker)
    if s is None or len(s) < MOM_MAX_LOOKBACK + 1:
        return -np.inf
    return float(np.mean([s.iloc[-1] / s.iloc[-(lb + 1)] - 1 for lb in MOM_LOOKBACKS]))


def _mom_passes_sma(ticker: str, prices: dict) -> bool:
    if ticker == MOM_CASH_TICKER:
        return True
    s = prices.get(ticker)
    if s is None:
        return False
    period = MOM_SMA_OVERRIDES.get(ticker, MOM_SMA_PERIOD)
    if len(s) < period:
        return False
    sma = float(s.rolling(period).mean().iloc[-1])
    return bool(s.iloc[-1] > sma) if not np.isnan(sma) else False


def _mom_vol(ticker: str, prices: dict) -> float:
    s = prices.get(ticker)
    if s is None or len(s) < MOM_VOL_LOOKBACK + 1:
        return np.nan
    lr = np.log(s / s.shift(1)).dropna()
    if len(lr) < MOM_VOL_LOOKBACK:
        return np.nan
    return float(lr.tail(MOM_VOL_LOOKBACK).std() * np.sqrt(252))


def _mom_ret6m(ticker: str, prices: dict) -> float:
    s = prices.get(ticker)
    if s is None or len(s) < 127:
        return -np.inf
    return float(s.iloc[-1] / s.iloc[-127] - 1)


def compute_momentum_signal(prices: dict) -> dict:
    if not prices:
        return {"winners": [], "cash_weight": 1.0, "diagnostics": {}, "as_of": "—"}
    all_tickers = list(prices.keys())
    cash_ret6m  = _mom_ret6m(MOM_CASH_TICKER, prices)
    diag = {}
    for t in all_tickers:
        period     = MOM_SMA_OVERRIDES.get(t, MOM_SMA_PERIOD)
        trend_pass = _mom_passes_sma(t, prices)
        mom        = _mom_momentum(t, prices)
        ret6m      = _mom_ret6m(t, prices)
        abs_pass   = (t == MOM_CASH_TICKER) or (ret6m > cash_ret6m)
        diag[t]    = {
            "sma_period": period, "trend_pass": trend_pass, "momentum": mom,
            "ret_6m": ret6m, "abs_pass": abs_pass,
            "eligible": trend_pass and abs_pass,
            "price": float(prices[t].iloc[-1]) if t in prices else None,
        }
    eligible = [t for t in all_tickers if diag[t]["eligible"]]
    if not eligible:
        as_of = str(prices[MOM_CASH_TICKER].index[-1].date()) if MOM_CASH_TICKER in prices else "—"
        return {"winners": [(MOM_CASH_TICKER, 1.0)], "cash_weight": 0.0,
                "scores": {MOM_CASH_TICKER: 0.0}, "diagnostics": diag, "as_of": as_of}
    scores = {t: _mom_momentum(t, prices) for t in eligible}
    top    = sorted(eligible, key=lambda t: scores[t], reverse=True)[:MOM_TOP_N]
    per_cap = MOM_MAX_WEIGHT / len(top)
    winners = []
    total   = 0.0
    for t in top:
        if t == MOM_CASH_TICKER:
            w = per_cap
        else:
            vol = _mom_vol(t, prices)
            w   = min(per_cap, MOM_TARGET_VOL / vol) if (vol and not np.isnan(vol)) else 0.0
        winners.append((t, w))
        total += w
    last_idx = next(iter(prices.values())).index[-1]
    return {
        "winners": winners, "cash_weight": max(0.0, 1.0 - total),
        "scores": scores, "diagnostics": diag, "as_of": str(last_idx.date()),
    }


# ═══════════════════════════════════════════════════════════════════════
#  SIGNAL LOGIC — Dow Titans
# ═══════════════════════════════════════════════════════════════════════

def _period_return(s: pd.Series, days: int) -> float | None:
    s = s.dropna()
    if s.empty:
        return None
    cutoff = s.index[-1] - timedelta(days=days)
    w = s[s.index >= cutoff]
    if len(w) < 10:
        return None
    return (w.iloc[-1] / w.iloc[0] - 1) * 100


def run_titans_signals(prices: dict) -> list[dict]:
    bench: dict[str, float | None] = {}
    for label, ticker, days in [
        ("shv_6m",  "SHV",  126),
        ("bnd_6m",  "BND",  126),
        ("acwi_3m", "ACWI",  63),
        ("acwi_6m", "ACWI", 126),
    ]:
        s = prices.get(ticker)
        if s is not None:
            v = _period_return(s, days)
            bench[label] = max(v, 0) if (v is not None and "acwi" in label) else v

    rows = []
    for ticker in DOW_TITANS:
        s = prices.get(ticker)
        if s is None or s.empty:
            rows.append({"ticker": ticker, "signal": "NO DATA"})
            continue
        price   = float(s.iloc[-1])
        ema_val = float(s.dropna().ewm(span=TITANS_EMA_PERIOD, adjust=False).mean().iloc[-1])
        above   = price > ema_val
        pct_ema = (price / ema_val - 1) * 100
        r3m = _period_return(s, 63)
        r6m = _period_return(s, 126)
        r1y = _period_return(s, 252)
        shv = bench.get("shv_6m"); bnd = bench.get("bnd_6m")
        a3m = bench.get("acwi_3m"); a6m = bench.get("acwi_6m")
        f1 = r6m is not None and shv is not None and r6m > shv
        f2 = r6m is not None and bnd is not None and r6m > bnd
        f3 = (r3m is not None and a3m is not None and r3m > a3m and
              r6m is not None and a6m is not None and r6m > a6m)
        rows.append({
            "ticker": ticker, "price": price, "ema": ema_val, "pct_ema": pct_ema,
            "above_ema": above, "r3m": r3m, "r6m": r6m,
            "f1": f1, "f2": f2, "f3": f3, "bench": bench,
            "signal": "BUY" if (above and f1 and f2 and f3) else "OUT",
        })
    rows.sort(key=lambda r: (r.get("signal") != "BUY", -(r.get("pct_ema") or -999)))
    return rows


# ═══════════════════════════════════════════════════════════════════════
#  JSON-SAFE SERIALISER  (used in the refresh callback)
# ═══════════════════════════════════════════════════════════════════════

def make_mom_sig_json_safe(mom_sig: dict) -> dict:
    """
    Convert numpy floats / NaNs inside a momentum signal dict to
    JSON-serialisable Python types so Dash can store it in a dcc.Store.
    """
    safe_diag: dict = {}
    for t, d in mom_sig.get("diagnostics", {}).items():
        safe_diag[t] = {
            k: (
                float(v) if isinstance(v, (np.floating, float)) and not np.isnan(v)
                else (None if isinstance(v, float) and np.isnan(v) else v)
            )
            for k, v in d.items()
        }
    return {
        **mom_sig,
        "diagnostics": safe_diag,
        "winners": [[t, float(w)] for t, w in mom_sig.get("winners", [])],
    }
