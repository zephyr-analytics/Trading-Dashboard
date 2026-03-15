"""
╔═══════════════════════════════════════════════════════════════════════╗
║  LIVE PORTFOLIO DASHBOARD  —  Plotly Dash                             ║
║  Tab 1: Overview  |  Tab 2: Core  |  Tab 3: Momentum  |  Tab 4: Titans║
╚═══════════════════════════════════════════════════════════════════════╝

SETUP:  pip install dash plotly yfinance pandas numpy
RUN:    python portfolio_dashboard.py  →  http://127.0.0.1:8050
"""

import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json, os, warnings

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════════════
#  PERSISTENCE
# ═══════════════════════════════════════════════════════════════════════
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "portfolio_data.json")

def load_saved():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE) as f:
                d = json.load(f)
            return d
        except Exception:
            pass
    return {}

def save_all(data: dict):
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[WARN] Could not save: {e}")

_SAVED = load_saved()

# ═══════════════════════════════════════════════════════════════════════
#  PORTFOLIO DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════

# ── Core Portfolio ──────────────────────────────────────────────────
CORE_PORTFOLIO = {
    "VTI":  {"target_pct": 0.3200, "sma_period": 168},
    "VEU":  {"target_pct": 0.2200, "sma_period": 168},
    "BND":  {"target_pct": 0.2200, "sma_period": 126},
    "BNDX": {"target_pct": 0.1400, "sma_period": 126},
    "DBC":  {"target_pct": 0.0333, "sma_period": 168},
    "GLD":  {"target_pct": 0.0333, "sma_period": 168},
    "IBIT": {"target_pct": 0.0334, "sma_period": 168},
}
CORE_TICKERS = list(CORE_PORTFOLIO.keys())

# ── Momentum Portfolio ──────────────────────────────────────────────
MOM_ETF_TICKERS      = ["VTI", "VEU", "BND", "BNDX", "VGIT", "GLD", "DBC", "SGOV"]
MOM_BTC_TICKER       = "BTC-USD"
MOM_CASH_TICKER      = "SGOV"
MOM_LOOKBACKS        = [21, 63, 126, 189, 252]
MOM_MAX_LOOKBACK     = max(MOM_LOOKBACKS)
MOM_SMA_PERIOD       = 168
MOM_SMA_OVERRIDES    = {"BND": 126, "BNDX": 126, "VGIT": 126}
MOM_VOL_LOOKBACK     = 63
MOM_TARGET_VOL       = 0.20
MOM_MAX_WEIGHT       = 1.0
MOM_TOP_N            = 2
_MOM_N_BARS          = MOM_MAX_LOOKBACK + MOM_SMA_PERIOD + 10

# ── Dow Titans ──────────────────────────────────────────────────────
DOW_TITANS = [
    "NVDA","AAPL","MSFT","AVGO","TSM", "CSCO","ORCL","IBM", "SAP", "CRM", "ACN",
    "META","GOOGL","NFLX",
    "AMZN","TSLA","TM",  "MCD",
    "PG",  "KO",  "PM",  "PEP", "UL",
    "LLY", "JNJ", "ABBV","AZN", "NVS", "MRK", "ABT", "TMO", "PFE", "NVO",
    "JPM", "V",   "MA",  "HSBC","GS",  "RY",
    "XOM", "CVX", "SHEL",
    "CAT", "GE",  "LIN", "ASML",
]
TITANS_BENCHMARKS  = ["SHV", "VGIT", "ACWI"]
TITANS_EMA_PERIOD  = 200

# ── Cash Portfolio ───────────────────────────────────────────────────
CASH_INSTRUMENTS   = ["SGOV", "SHV", "ICSH"]   # $CASH is uninvested dollar cash
CASH_TICKERS_YF    = CASH_INSTRUMENTS            # tickers fetchable from yfinance
CASH_LABEL         = "$CASH"                     # display name for uninvested cash
# Equal weight across all 4 (3 ETFs + raw cash)
CASH_WEIGHT_EACH   = 0.25

# ═══════════════════════════════════════════════════════════════════════
#  COLOURS & STYLES
# ═══════════════════════════════════════════════════════════════════════
# ── Lavender-purple / grey / black / white palette ──────────────────
DARK_BG     = "#0d0d12"   # near-black with a purple tint
CARD_BG     = "#16131f"   # deep purple-grey card
CARD_BORDER = "#2d2640"   # mid purple-grey border

ACCENT      = "#c4b5fd"   # lavender-400  — Core
ACCENT2     = "#a78bfa"   # violet-400    — accents / Core tab
ACCENT3     = "#7c3aed"   # violet-700    — Dow Titans
ACCENT4     = "#e0d7ff"   # lavender-200  — Momentum (light purple)
ACCENT5     = "#ddd6fe"   # violet-200    — Cash

RED         = "#f87171"   # rose-400  (softened for dark theme)
GREEN       = "#86efac"   # green-300 (softened)
YELLOW      = "#e9d5ff"   # purple-200 (replaces gold — keeps mono feel)
TEXT        = "#f5f3ff"   # near-white with purple tint
MUTED       = "#7c6f9f"   # mid purple-grey
CASH_CLR    = "#6d6082"   # darker purple-grey

PIE_COLORS = [
    "#c4b5fd","#a78bfa","#7c3aed","#ddd6fe","#6d28d9",
    "#ede9fe","#4c1d95","#e0d7ff","#8b5cf6","#f5f3ff",
    "#5b21b6","#d8b4fe","#6d6082","#c084fc","#9333ea",
]

CARD = {"backgroundColor":CARD_BG,"border":f"1px solid {CARD_BORDER}",
        "borderRadius":"12px","padding":"20px","marginBottom":"16px"}
INP  = {"backgroundColor":"#1e1a2e","border":f"1px solid {CARD_BORDER}",
        "borderRadius":"8px","color":TEXT,"padding":"8px 12px","fontSize":"13px",
        "outline":"none","width":"100%","boxSizing":"border-box"}
BTN  = {"backgroundColor":ACCENT,"color":"#1a0a3d","border":"none",
        "borderRadius":"8px","padding":"9px 18px","fontSize":"13px",
        "fontWeight":"700","cursor":"pointer","width":"100%"}
BTN2 = {**BTN,"backgroundColor":ACCENT2,"color":"#fff"}
BTN3 = {**BTN,"backgroundColor":ACCENT3,"color":"#fff"}
BTN4 = {**BTN,"backgroundColor":ACCENT4,"color":"#fff"}
LBL  = {"fontSize":"11px","color":MUTED,"letterSpacing":"0.8px",
        "textTransform":"uppercase","marginBottom":"5px","display":"block"}

TAB_BASE = {"backgroundColor":CARD_BG,"color":MUTED,
            "border":f"1px solid {CARD_BORDER}","borderRadius":"8px 8px 0 0",
            "padding":"10px 22px","fontSize":"12px","fontWeight":"600","letterSpacing":"1px"}
def tab_sel(color):
    return {**TAB_BASE,"backgroundColor":DARK_BG,"color":color,
            "borderBottom":f"2px solid {color}"}

# ═══════════════════════════════════════════════════════════════════════
#  SHARED HELPERS
# ═══════════════════════════════════════════════════════════════════════
def fmt(val, sign=False):
    if val is None: return "—"
    pre = ("+" if val >= 0 else "") if sign else ""
    if abs(val) >= 1_000_000: return f"{pre}${val/1e6:.2f}M"
    if abs(val) >= 1_000:     return f"{pre}${val:,.2f}"
    return f"{pre}${val:.2f}"

def pcolor(val):
    if val is None: return MUTED
    return GREEN if val >= 0 else RED

def _get_close(raw, ticker):
    """
    Extract a clean Close price Series for `ticker` from a yfinance DataFrame.
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

def kpi_card(label, val, color=TEXT, sub=None, bar_color=ACCENT, min_w="150px"):
    return html.Div(style={**CARD,"flex":"1","minWidth":min_w,"marginBottom":"0",
                           "position":"relative","overflow":"hidden"}, children=[
        html.Div(label, style={"fontSize":"10px","color":MUTED,"letterSpacing":"1px",
                               "textTransform":"uppercase","marginBottom":"6px"}),
        html.Div(val,   style={"fontSize":"20px","fontWeight":"800","color":color}),
        html.Div(sub or "", style={"fontSize":"11px","color":MUTED,"marginTop":"3px"}),
        html.Div(style={"position":"absolute","bottom":"0","left":"0","height":"3px",
                        "width":"100%","background":f"linear-gradient(90deg,{bar_color},{ACCENT2})"}),
    ])

# ═══════════════════════════════════════════════════════════════════════
#  DATA FETCHERS
# ═══════════════════════════════════════════════════════════════════════

def fetch_core_market(tickers):
    result = {t: {"price":None,"sma_126":None,"sma_168":None} for t in tickers}
    try:
        raw = yf.download(tickers, period="400d", interval="1d",
                          progress=False, auto_adjust=True)
        for t in tickers:
            try:
                close = _get_close(raw, t)
                if close.empty: continue
                result[t] = {
                    "price":   float(close.iloc[-1]),
                    "sma_126": float(close.rolling(126).mean().iloc[-1]) if len(close)>=126 else None,
                    "sma_168": float(close.rolling(168).mean().iloc[-1]) if len(close)>=168 else None,
                }
            except: pass
    except: pass
    return result

def fetch_momentum_data():
    """Returns {ticker: pd.Series of closes} for all ETFs + BTC."""
    prices = {}
    # Try with multi_level_index=False first (yfinance >= 0.2.18 flat output)
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
                break  # got enough data, stop trying
        except Exception:
            pass
    # BTC separately (single ticker)
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

def fetch_titans_prices():
    all_t = DOW_TITANS + TITANS_BENCHMARKS
    prices = {}
    start = (datetime.today()-timedelta(days=420)).strftime("%Y-%m-%d")
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

def fetch_cash_market():
    """Fetch latest prices for the 3 cash ETFs."""
    result = {t: {"price": None} for t in CASH_TICKERS_YF}
    result[CASH_LABEL] = {"price": 1.0}   # $CASH always $1
    try:
        raw = yf.download(CASH_TICKERS_YF, period="5d", interval="1d",
                          progress=False, auto_adjust=True)
        for t in CASH_TICKERS_YF:
            try:
                close = _get_close(raw, t)
                if not close.empty:
                    result[t] = {"price": float(close.iloc[-1])}
            except: pass
    except: pass
    return result

# ═══════════════════════════════════════════════════════════════════════
#  SIGNAL LOGIC — Core
# ═══════════════════════════════════════════════════════════════════════
def sma_signal(td, period):
    p, s = td.get("price"), td.get(f"sma_{period}")
    if p is None or s is None: return "UNKNOWN"
    return "BUY" if p >= s else "SELL/CASH"

def compute_core_rebalance(holdings, market, alloc_value):
    cash_pct = sum(cfg["target_pct"] for t,cfg in CORE_PORTFOLIO.items()
                   if sma_signal((market or {}).get(t,{}), cfg["sma_period"])!="BUY")
    rows = []
    for t, cfg in CORE_PORTFOLIO.items():
        md     = (market or {}).get(t, {})
        price  = md.get("price")
        signal = sma_signal(md, cfg["sma_period"])
        h           = ((holdings or {}).get(t) or {})
        cur_shares  = h.get("shares") or 0
        avg_cost    = h.get("avg_cost")
        cur_val     = (price*cur_shares) if (price and cur_shares) else h.get("current_value")
        eff_pct     = cfg["target_pct"] if signal=="BUY" else 0.0
        target_val  = alloc_value * eff_pct
        delta_val   = (target_val-cur_val)  if cur_val is not None else None
        delta_sh    = (delta_val/price)     if (delta_val is not None and price) else None
        pnl = ((price-avg_cost)*cur_shares) if (cur_shares and price and avg_cost) else None
        rows.append({"ticker":t,"signal":signal,"sma_period":cfg["sma_period"],
                     "target_pct":cfg["target_pct"],"eff_target":eff_pct,
                     "price":price,"cur_shares":cur_shares,"cur_val":cur_val,
                     "target_val":target_val,"delta_val":delta_val,"delta_shares":delta_sh,
                     "avg_cost":avg_cost,"pnl_unreal":pnl})
    rows.append({"ticker":"CASH","signal":"HOLD","sma_period":None,
                 "target_pct":cash_pct,"eff_target":cash_pct,"price":1.0,
                 "cur_shares":None,"cur_val":None,"target_val":alloc_value*cash_pct,
                 "delta_val":None,"delta_shares":None,"avg_cost":None,"pnl_unreal":None})
    return rows

# ═══════════════════════════════════════════════════════════════════════
#  SIGNAL LOGIC — Momentum
# ═══════════════════════════════════════════════════════════════════════
def _mom_momentum(ticker, prices):
    s = prices.get(ticker)
    if s is None or len(s) < MOM_MAX_LOOKBACK+1: return -np.inf
    return float(np.mean([s.iloc[-1]/s.iloc[-(lb+1)]-1 for lb in MOM_LOOKBACKS]))

def _mom_passes_sma(ticker, prices):
    if ticker == MOM_CASH_TICKER: return True
    s = prices.get(ticker)
    if s is None: return False
    period = MOM_SMA_OVERRIDES.get(ticker, MOM_SMA_PERIOD)
    if len(s) < period: return False
    sma = float(s.rolling(period).mean().iloc[-1])
    return bool(s.iloc[-1] > sma) if not np.isnan(sma) else False

def _mom_vol(ticker, prices):
    s = prices.get(ticker)
    if s is None or len(s) < MOM_VOL_LOOKBACK+1: return np.nan
    lr = np.log(s/s.shift(1)).dropna()
    if len(lr) < MOM_VOL_LOOKBACK: return np.nan
    return float(lr.tail(MOM_VOL_LOOKBACK).std() * np.sqrt(252))

def _mom_ret6m(ticker, prices):
    s = prices.get(ticker)
    if s is None or len(s) < 127: return -np.inf
    return float(s.iloc[-1]/s.iloc[-127]-1)

def compute_momentum_signal(prices):
    if not prices: return {"winners":[],"cash_weight":1.0,"diagnostics":{},"as_of":"—"}
    all_tickers = list(prices.keys())
    cash_ret6m  = _mom_ret6m(MOM_CASH_TICKER, prices)
    diag = {}
    for t in all_tickers:
        period     = MOM_SMA_OVERRIDES.get(t, MOM_SMA_PERIOD)
        trend_pass = _mom_passes_sma(t, prices)
        mom        = _mom_momentum(t, prices)
        ret6m      = _mom_ret6m(t, prices)
        abs_pass   = (t==MOM_CASH_TICKER) or (ret6m > cash_ret6m)
        diag[t]    = {"sma_period":period,"trend_pass":trend_pass,"momentum":mom,
                      "ret_6m":ret6m,"abs_pass":abs_pass,"eligible":trend_pass and abs_pass,
                      "price": float(prices[t].iloc[-1]) if t in prices else None}
    eligible = [t for t in all_tickers if diag[t]["eligible"]]
    if not eligible:
        as_of = str(prices[MOM_CASH_TICKER].index[-1].date()) if MOM_CASH_TICKER in prices else "—"
        return {"winners":[(MOM_CASH_TICKER,1.0)],"cash_weight":0.0,
                "scores":{MOM_CASH_TICKER:0.0},"diagnostics":diag,"as_of":as_of}
    scores  = {t: _mom_momentum(t,prices) for t in eligible}
    top     = sorted(eligible, key=lambda t: scores[t], reverse=True)[:MOM_TOP_N]
    per_cap = MOM_MAX_WEIGHT / len(top)
    winners = []
    total   = 0.0
    for t in top:
        if t == MOM_CASH_TICKER:
            w = per_cap
        else:
            vol = _mom_vol(t, prices)
            w   = min(per_cap, MOM_TARGET_VOL/vol) if (vol and not np.isnan(vol)) else 0.0
        winners.append((t, w)); total += w
    last_idx = next(iter(prices.values())).index[-1]
    return {"winners":winners,"cash_weight":max(0.0,1.0-total),
            "scores":scores,"diagnostics":diag,"as_of":str(last_idx.date())}

# ═══════════════════════════════════════════════════════════════════════
#  SIGNAL LOGIC — Dow Titans
# ═══════════════════════════════════════════════════════════════════════
def _period_return(s, days):
    s = s.dropna()
    if s.empty: return None
    cutoff = s.index[-1]-timedelta(days=days)
    w = s[s.index>=cutoff]
    if len(w)<10: return None
    return (w.iloc[-1]/w.iloc[0]-1)*100

def run_titans_signals(prices):
    bench = {}
    for label,ticker,days in [("shv_6m","SHV",126),("vgit_6m","VGIT",126),
                               ("acwi_3m","ACWI",63),("acwi_6m","ACWI",126),("acwi_1y","ACWI",252)]:
        s = prices.get(ticker)
        if s is not None:
            v = _period_return(s, days)
            bench[label] = max(v,0) if (v is not None and "acwi" in label) else v
    rows = []
    for ticker in DOW_TITANS:
        s = prices.get(ticker)
        if s is None or s.empty:
            rows.append({"ticker":ticker,"signal":"NO DATA"}); continue
        price   = float(s.iloc[-1])
        ema_val = float(s.dropna().ewm(span=TITANS_EMA_PERIOD,adjust=False).mean().iloc[-1])
        above   = price > ema_val
        pct_ema = (price/ema_val-1)*100
        r3m=_period_return(s,63); r6m=_period_return(s,126); r1y=_period_return(s,252)
        shv=bench.get("shv_6m"); vgit=bench.get("vgit_6m")
        a3m=bench.get("acwi_3m"); a6m=bench.get("acwi_6m"); a1y=bench.get("acwi_1y")
        f1=(r6m is not None and shv  is not None and r6m>shv)
        f2=(r6m is not None and vgit is not None and r6m>vgit)
        f3=(r3m is not None and a3m  is not None and r3m>a3m and
            r6m is not None and a6m  is not None and r6m>a6m and
            r1y is not None and a1y  is not None and r1y>a1y)
        rows.append({"ticker":ticker,"price":price,"ema":ema_val,"pct_ema":pct_ema,
                     "above_ema":above,"r3m":r3m,"r6m":r6m,"r1y":r1y,
                     "f1":f1,"f2":f2,"f3":f3,"bench":bench,
                     "signal":"BUY" if (above and f1 and f2 and f3) else "OUT"})
    rows.sort(key=lambda r:(r.get("signal")!="BUY",-(r.get("pct_ema") or -999)))
    return rows

# ═══════════════════════════════════════════════════════════════════════
#  APP INIT
# ═══════════════════════════════════════════════════════════════════════
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Portfolio Dashboard"

app.layout = html.Div(
    style={"backgroundColor":DARK_BG,"minHeight":"100vh",
           "fontFamily":"'Inter','Segoe UI',sans-serif","color":TEXT},
    children=[
        # ── stores ──
        dcc.Store(id="core-market",    data={}),
        dcc.Store(id="mom-signal",     data={}),
        dcc.Store(id="titans-market",  data=[]),
        dcc.Store(id="holdings-store", data=_SAVED.get("holdings",{})),
        dcc.Store(id="settings-store", data={
            "total_value":  _SAVED.get("total_value"),
            "core_pct":     _SAVED.get("core_pct"),
            "mom_pct":      _SAVED.get("mom_pct"),
            "titans_pct":   _SAVED.get("titans_pct"),
            "cash_pct":     _SAVED.get("cash_pct"),
        }),
        dcc.Store(id="cash-market", data={}),
        # n_intervals=-1 is not valid; use max_intervals trick — fire immediately on load
        dcc.Interval(id="interval", interval=60_000, n_intervals=0, disabled=False),

        # ── header ──
        html.Div(style={"background":f"linear-gradient(135deg,{CARD_BG} 0%,#0f172a 100%)",
                        "borderBottom":f"1px solid {CARD_BORDER}",
                        "padding":"16px 32px","display":"flex",
                        "alignItems":"center","justifyContent":"space-between"},
                 children=[
                     html.Div([
                         html.Span("◈ ", style={"color":ACCENT,"fontSize":"20px"}),
                         html.Span("PORTFOLIO DASHBOARD",
                                   style={"fontSize":"17px","fontWeight":"800","letterSpacing":"3px"}),
                     ]),
                     html.Div(id="last-updated", style={"color":MUTED,"fontSize":"12px"}),
                 ]),

        # ── tabs ──
        html.Div(style={"maxWidth":"1600px","margin":"0 auto","padding":"24px 24px 0"},
                 children=[
                     dcc.Tabs(id="main-tabs", value="overview",
                              style={"borderBottom":f"1px solid {CARD_BORDER}"},
                              children=[
                                  dcc.Tab(label="◉  OVERVIEW",         value="overview",
                                          style=TAB_BASE, selected_style=tab_sel(ACCENT)),
                                  dcc.Tab(label="⬡  CORE PORTFOLIO",   value="core",
                                          style=TAB_BASE, selected_style=tab_sel(ACCENT2)),
                                  dcc.Tab(label="⚡  MOMENTUM",         value="momentum",
                                          style=TAB_BASE, selected_style=tab_sel(ACCENT4)),
                                  dcc.Tab(label="▲  DOW TITANS",        value="titans",
                                          style=TAB_BASE, selected_style=tab_sel(ACCENT3)),
                                  dcc.Tab(label="◎  CASH",               value="cash",
                                          style=TAB_BASE, selected_style=tab_sel(ACCENT5)),
                              ]),
                 ]),

        html.Div(id="tab-content",
                 style={"maxWidth":"1600px","margin":"0 auto","padding":"0 24px 40px"}),
    ]
)

# ═══════════════════════════════════════════════════════════════════════
#  CALLBACK — refresh all market data
# ═══════════════════════════════════════════════════════════════════════
@app.callback(
    Output("core-market",  "data"),
    Output("mom-signal",   "data"),
    Output("titans-market","data"),
    Output("cash-market",  "data"),
    Output("last-updated", "children"),
    Input("interval","n_intervals"),
    prevent_initial_call=False,
)
def refresh_all(_):
    core_mkt    = fetch_core_market(CORE_TICKERS)
    mom_prices  = fetch_momentum_data()
    mom_sig     = compute_momentum_signal(mom_prices)
    titans_p    = fetch_titans_prices()
    titans_rows = run_titans_signals(titans_p)
    now         = datetime.now().strftime("⟳  %H:%M:%S")
    # mom_sig: convert Series values to JSON-safe types
    safe_diag = {}
    for t, d in mom_sig.get("diagnostics",{}).items():
        safe_diag[t] = {k: (float(v) if isinstance(v,(np.floating,float)) and not np.isnan(v)
                             else (None if isinstance(v,float) and np.isnan(v) else v))
                        for k,v in d.items()}
    mom_sig["diagnostics"] = safe_diag
    mom_sig["winners"]     = [[t,float(w)] for t,w in mom_sig.get("winners",[])]
    cash_mkt = fetch_cash_market()
    return core_mkt, mom_sig, titans_rows, cash_mkt, now

# ═══════════════════════════════════════════════════════════════════════
#  CALLBACK — save overview settings
# ═══════════════════════════════════════════════════════════════════════
@app.callback(
    Output("settings-store",   "data"),
    Output("ov-save-msg",      "children"),
    Input("ov-save-btn",       "n_clicks"),
    State("ov-total-value",    "value"),
    State("ov-core-pct",       "value"),
    State("ov-mom-pct",        "value"),
    State("ov-titans-pct",     "value"),
    State("ov-cash-pct",       "value"),
    State("holdings-store",    "data"),
    prevent_initial_call=True,
)
def save_overview(_, total, core_pct, mom_pct, titans_pct, cash_pct, holdings):
    if not total or float(total) <= 0:
        return {}, "⚠ Enter a valid portfolio value."
    tv  = float(total)
    cp  = float(core_pct)   if core_pct   else 0.0
    mp  = float(mom_pct)    if mom_pct    else 0.0
    tp  = float(titans_pct) if titans_pct else 0.0
    xp  = float(cash_pct)   if cash_pct   else 0.0
    if cp+mp+tp+xp > 100:
        return {}, "⚠ Allocations exceed 100%."
    settings = {"total_value":tv,"core_pct":cp,"mom_pct":mp,"titans_pct":tp,"cash_pct":xp}
    save_all({**settings,"holdings":holdings or {}})
    return settings, f"✓ Saved — Total: {fmt(tv)}  Core:{cp:.0f}%  Mom:{mp:.0f}%  Titans:{tp:.0f}%  Cash:{xp:.0f}%"

# ═══════════════════════════════════════════════════════════════════════
#  CALLBACK — save core holdings
# ═══════════════════════════════════════════════════════════════════════
@app.callback(
    Output("holdings-store",    "data"),
    Output("core-holdings-msg", "children"),
    Input("save-holdings-btn",  "n_clicks"),
    [State({"type":"shares-input","ticker":t},"value") for t in CORE_TICKERS],
    [State({"type":"cost-input",  "ticker":t},"value") for t in CORE_TICKERS],
    [State({"type":"curval-input","ticker":t},"value") for t in CORE_TICKERS],
    State("settings-store","data"),
    prevent_initial_call=True,
)
def save_holdings(_, *args):
    n  = len(CORE_TICKERS)
    sh, co, cv = args[0:n], args[n:2*n], args[2*n:3*n]
    settings = args[3*n] or {}
    holdings = {}
    for i, t in enumerate(CORE_TICKERS):
        holdings[t] = {
            "shares":        float(sh[i]) if sh[i] is not None else None,
            "avg_cost":      float(co[i]) if co[i] is not None else None,
            "current_value": float(cv[i]) if cv[i] is not None else None,
        }
    save_all({**settings,"holdings":holdings})
    return holdings, "✓ Holdings saved to disk."

# ═══════════════════════════════════════════════════════════════════════
#  CALLBACK — render tab content
# ═══════════════════════════════════════════════════════════════════════
@app.callback(
    Output("tab-content","children"),
    Input("main-tabs",      "value"),
    Input("core-market",    "data"),
    Input("mom-signal",     "data"),
    Input("titans-market",  "data"),
    Input("holdings-store", "data"),
    Input("settings-store", "data"),
    Input("cash-market",    "data"),
)
def render_tab(tab, core_mkt, mom_sig, titans_rows, holdings, settings, cash_mkt):
    s = settings or {}
    tv  = s.get("total_value")
    cp  = s.get("core_pct",   0) or 0
    mp  = s.get("mom_pct",    0) or 0
    tp  = s.get("titans_pct", 0) or 0
    xp  = s.get("cash_pct",   0) or 0
    if   tab == "overview":  return build_overview(core_mkt,mom_sig,titans_rows,holdings,tv,cp,mp,tp,xp,cash_mkt)
    elif tab == "core":      return build_core_tab(core_mkt,holdings,tv,cp)
    elif tab == "momentum":  return build_momentum_tab(mom_sig,tv,mp)
    elif tab == "titans":    return build_titans_tab(titans_rows,tv,tp)
    elif tab == "cash":      return build_cash_tab(cash_mkt,tv,xp)
    return html.Div("Unknown tab")

# ═══════════════════════════════════════════════════════════════════════
#  TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════
def build_overview(core_mkt, mom_sig, titans_rows, holdings, tv, cp, mp, tp, xp=0, cash_mkt=None):
    tv    = tv or 0
    cp_f  = cp/100; mp_f = mp/100; tp_f = tp/100; xp_f = xp/100
    other_f = max(0, 1-cp_f-mp_f-tp_f-xp_f)

    core_alloc   = tv*cp_f
    mom_alloc    = tv*mp_f
    titans_alloc = tv*tp_f
    cash_alloc   = tv*xp_f
    other_alloc  = tv*other_f

    # Core P&L
    core_pnl = None
    if holdings and core_mkt:
        s, has = 0, False
        for t,h in holdings.items():
            p = (core_mkt.get(t) or {}).get("price")
            if p and h and h.get("shares") and h.get("avg_cost"):
                s += (p-h["avg_cost"])*h["shares"]; has=True
        if has: core_pnl = s

    # Momentum winners summary
    mom_winners = mom_sig.get("winners",[]) if mom_sig else []
    mom_cash_w  = mom_sig.get("cash_weight",1.0) if mom_sig else 1.0
    mom_as_of   = mom_sig.get("as_of","—") if mom_sig else "—"

    # Titans eligible
    eligible_t = [r for r in (titans_rows or []) if r.get("signal")=="BUY"]
    n_elig_t   = len(eligible_t)

    # Core SMA
    n_above_core = sum(1 for t,cfg in CORE_PORTFOLIO.items()
                       if sma_signal((core_mkt or {}).get(t,{}),cfg["sma_period"])=="BUY")

    # ── Grand pie ──
    pie_lbl = ["Core Portfolio","Momentum","Dow Titans","Cash","Unallocated"]
    pie_val = [cp,mp,tp,xp,other_f*100]
    pie_clr = [ACCENT,ACCENT4,ACCENT3,ACCENT5,CASH_CLR]
    pie_fig = go.Figure(go.Pie(
        labels=pie_lbl, values=pie_val, hole=0.55,
        marker=dict(colors=pie_clr,line=dict(color=DARK_BG,width=2)),
        textfont=dict(size=12,color="#fff"),
        hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
        textinfo="label+percent",
    ))
    pie_fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT),showlegend=False,
        margin=dict(t=10,b=10,l=10,r=10),height=300,
        annotations=[dict(text=fmt(tv),x=0.5,y=0.5,
                          font_size=14,font_color=YELLOW,showarrow=False)],
    )

    # ── KPI bar ──
    kpis = html.Div(style={"display":"flex","gap":"14px","marginBottom":"24px","flexWrap":"wrap"},
                    children=[
        kpi_card("Total Portfolio",   fmt(tv) if tv else "Not set", YELLOW, bar_color=YELLOW),
        kpi_card("Core Allocation",   fmt(core_alloc), ACCENT,  f"{cp:.1f}%", ACCENT),
        kpi_card("Momentum Alloc",    fmt(mom_alloc),  ACCENT4, f"{mp:.1f}%", ACCENT4),
        kpi_card("Titans Allocation", fmt(titans_alloc),ACCENT3,f"{tp:.1f}%", ACCENT3),
        kpi_card("Unallocated",       fmt(other_alloc),MUTED,   f"{other_f*100:.1f}%"),
        kpi_card("Core P&L",
                 fmt(core_pnl,sign=True) if core_pnl is not None else "Enter holdings",
                 pcolor(core_pnl), bar_color=pcolor(core_pnl)),
        kpi_card("Cash Allocation", fmt(cash_alloc), ACCENT5, f"{xp:.1f}%", ACCENT5),
    ])

    # ── Allocation setup card ──
    setup = html.Div(style=CARD, children=[
        html.H3("Portfolio Allocation",
                style={"margin":"0 0 16px","fontSize":"13px","color":ACCENT,"letterSpacing":"1px"}),
        html.Label("Total Portfolio Value ($)", style=LBL),
        dcc.Input(id="ov-total-value",type="number",min=0,placeholder="e.g. 250000",
                  value=tv if tv else None,
                  style={**INP,"marginBottom":"14px"}),
        html.Div(style={"display":"grid","gridTemplateColumns":"1fr 1fr","gap":"12px",
                        "marginBottom":"14px"}, children=[
            html.Div([html.Label("Core Portfolio (%)",style=LBL),
                      dcc.Input(id="ov-core-pct",type="number",min=0,max=100,
                                placeholder="e.g. 50",value=cp if cp else None,style=INP)]),
            html.Div([html.Label("Momentum (%)",style=LBL),
                      dcc.Input(id="ov-mom-pct",type="number",min=0,max=100,
                                placeholder="e.g. 30",value=mp if mp else None,style=INP)]),
            html.Div([html.Label("Dow Titans (%)",style=LBL),
                      dcc.Input(id="ov-titans-pct",type="number",min=0,max=100,
                                placeholder="e.g. 20",value=tp if tp else None,style=INP)]),
            html.Div([html.Label("Cash Portfolio (%)",style=LBL),
                      dcc.Input(id="ov-cash-pct",type="number",min=0,max=100,
                                placeholder="e.g. 10",value=xp if xp else None,style=INP)]),
        ]),
        html.Button("Save Allocation",id="ov-save-btn",n_clicks=0,style=BTN),
        html.Div(id="ov-save-msg",style={"marginTop":"8px","fontSize":"12px","color":ACCENT}),
    ])

    # ── Three portfolio summary cards ──
    def port_card(title, alloc, color, body_children):
        return html.Div(style={**CARD,"borderTop":f"3px solid {color}","marginBottom":"0"}, children=[
            html.Div(style={"display":"flex","justifyContent":"space-between",
                            "alignItems":"center","marginBottom":"12px"}, children=[
                html.H3(title,style={"margin":"0","fontSize":"13px",
                                     "color":color,"letterSpacing":"1px"}),
                html.Span(fmt(alloc),style={"fontSize":"16px","fontWeight":"800","color":color}),
            ]),
            *body_children,
        ])

    # Core summary
    core_sig_rows = []
    for t,cfg in CORE_PORTFOLIO.items():
        md  = (core_mkt or {}).get(t,{})
        sig = sma_signal(md,cfg["sma_period"])
        sc  = GREEN if sig=="BUY" else (RED if sig=="SELL/CASH" else MUTED)
        core_sig_rows.append(html.Div(
            style={"display":"grid","gridTemplateColumns":"50px 55px 1fr 65px",
                   "gap":"4px","padding":"5px 0","borderBottom":f"1px solid {CARD_BORDER}",
                   "fontSize":"11px","alignItems":"center"},
            children=[
                html.Span(t,style={"fontWeight":"700","color":ACCENT}),
                html.Span(f"SMA-{cfg['sma_period']}",style={"fontSize":"9px","color":MUTED}),
                html.Span(fmt(md.get("price")),style={"color":TEXT}),
                html.Span("▲ BUY" if sig=="BUY" else "▼ CASH",
                          style={"color":sc,"fontWeight":"700","fontSize":"10px"}),
            ]
        ))
    core_card = port_card("Core Portfolio", core_alloc, ACCENT, [
        html.Div(f"{n_above_core}/{len(CORE_PORTFOLIO)} above SMA",
                 style={"fontSize":"11px","color":MUTED,"marginBottom":"8px"}),
        *core_sig_rows,
    ])

    # Momentum summary
    mom_rows = []
    for t, w in mom_winners:
        amt = mom_alloc * w if mom_alloc else None
        mom_rows.append(html.Div(
            style={"display":"flex","justifyContent":"space-between","alignItems":"center",
                   "padding":"5px 0","borderBottom":f"1px solid {CARD_BORDER}","fontSize":"11px"},
            children=[
                html.Span(t, style={"fontWeight":"700","color":ACCENT4}),
                html.Span(f"{w:.1%}  {fmt(amt)}",
                          style={"color":TEXT,"fontWeight":"600"}),
            ]
        ))
    if mom_cash_w > 0.001:
        amt = mom_alloc*mom_cash_w if mom_alloc else None
        mom_rows.append(html.Div(
            style={"display":"flex","justifyContent":"space-between",
                   "padding":"5px 0","fontSize":"11px"},
            children=[html.Span("CASH(SGOV)",style={"color":MUTED}),
                      html.Span(f"{mom_cash_w:.1%}  {fmt(amt)}",style={"color":MUTED})]))
    mom_card = port_card("Momentum Portfolio", mom_alloc, ACCENT4, [
        html.Div(f"As of {mom_as_of}  •  Top-{MOM_TOP_N} vol-scaled",
                 style={"fontSize":"11px","color":MUTED,"marginBottom":"8px"}),
        *mom_rows,
    ])

    # Titans summary
    buy_tickers = [r["ticker"] for r in (titans_rows or []) if r.get("signal")=="BUY"]
    wt_each     = (100/n_elig_t) if n_elig_t else None
    titans_card = port_card("Dow Titans", titans_alloc, ACCENT3, [
        html.Div(f"{n_elig_t}/{len(DOW_TITANS)} eligible  •  Equal weight {wt_each:.1f}% each" if wt_each
                 else f"{n_elig_t}/{len(DOW_TITANS)} eligible",
                 style={"fontSize":"11px","color":MUTED,"marginBottom":"8px"}),
        html.Div(style={"display":"flex","flexWrap":"wrap","gap":"5px"}, children=[
            html.Span(t, style={"backgroundColor":"#1a1033","color":"#86efac",
                                "borderRadius":"4px","padding":"2px 7px",
                                "fontSize":"10px","fontWeight":"600"})
            for t in buy_tickers
        ]),
    ])

    # Cash summary card for overview
    cash_alloc_ov = tv*xp_f
    cash_per_val  = cash_alloc_ov * CASH_WEIGHT_EACH
    cash_mkt_ov   = cash_mkt or {}
    cash_instr_rows = []
    for name in CASH_INSTRUMENTS + [CASH_LABEL]:
        price = 1.0 if name==CASH_LABEL else (cash_mkt_ov.get(name) or {}).get("price")
        cash_instr_rows.append(html.Div(
            style={"display":"flex","justifyContent":"space-between","alignItems":"center",
                   "padding":"4px 0","borderBottom":f"1px solid {CARD_BORDER}","fontSize":"11px"},
            children=[html.Span(name,style={"fontWeight":"700","color":ACCENT5}),
                      html.Span(f"25%  {fmt(cash_per_val)}",style={"color":TEXT})]))
    cash_card = port_card("Cash Portfolio", cash_alloc_ov, ACCENT5, [
        html.Div("Equal weight: SGOV · SHV · ICSH · $CASH",
                 style={"fontSize":"11px","color":MUTED,"marginBottom":"8px"}),
        *cash_instr_rows,
    ])

    master_table = build_master_table(core_mkt, mom_sig, titans_rows, cash_mkt,
                                      holdings, tv, cp, mp, tp, xp)

    return html.Div(style={"paddingTop":"20px"}, children=[
        kpis,
        html.Div(style={"display":"grid","gridTemplateColumns":"380px 1fr","gap":"20px",
                        "alignItems":"start"}, children=[
            html.Div([setup]),
            html.Div([
                html.Div(style=CARD, children=[
                    html.H3("Portfolio Split",
                            style={"margin":"0 0 8px","fontSize":"13px","color":MUTED,"letterSpacing":"1px"}),
                    dcc.Graph(figure=pie_fig,config={"displayModeBar":False}),
                ]),
                html.Div(style={"display":"grid","gridTemplateColumns":"1fr 1fr","gap":"16px",
                                "marginBottom":"16px"},
                         children=[core_card, mom_card]),
                html.Div(style={"display":"grid","gridTemplateColumns":"1fr 1fr","gap":"16px"},
                         children=[titans_card, cash_card]),
            ]),
        ]),
        master_table,
    ])

# ═══════════════════════════════════════════════════════════════════════
#  TAB 2 — CORE PORTFOLIO
# ═══════════════════════════════════════════════════════════════════════
def build_core_tab(market, holdings, tv, cp):
    alloc = ((tv or 0)*(cp or 0)/100) or 0

    above    = sum(1 for t,cfg in CORE_PORTFOLIO.items()
                   if sma_signal((market or {}).get(t,{}),cfg["sma_period"])=="BUY")
    cash_pct = sum(cfg["target_pct"] for t,cfg in CORE_PORTFOLIO.items()
                   if sma_signal((market or {}).get(t,{}),cfg["sma_period"])!="BUY")
    total_pnl = None
    if holdings and market:
        s,has=0,False
        for t,h in holdings.items():
            p=(market.get(t) or {}).get("price")
            if p and h and h.get("shares") and h.get("avg_cost"):
                s+=(p-h["avg_cost"])*h["shares"]; has=True
        if has: total_pnl=s

    kpis = html.Div(style={"display":"flex","gap":"14px","marginBottom":"20px",
                            "flexWrap":"wrap","paddingTop":"20px"}, children=[
        kpi_card("Core Allocation", fmt(alloc),  ACCENT2, f"{cp or 0:.1f}% of total", ACCENT2),
        kpi_card("Invested",        f"{above}/{len(CORE_PORTFOLIO)}", ACCENT,
                 f"{(1-cash_pct)*100:.1f}% deployed"),
        kpi_card("Cash/Sidelined",  f"{cash_pct*100:.1f}%", YELLOW if cash_pct>0 else MUTED,
                 f"{len(CORE_PORTFOLIO)-above} below SMA", bar_color=YELLOW),
        kpi_card("Unrealized P&L",
                 fmt(total_pnl,sign=True) if total_pnl is not None else "Enter holdings",
                 pcolor(total_pnl), bar_color=pcolor(total_pnl)),
    ])

    # Holdings input
    left = html.Div(style=CARD, children=[
        html.H3("Holdings",style={"margin":"0 0 4px","fontSize":"13px","color":ACCENT2,"letterSpacing":"1px"}),
        html.P("Allocation % set on Overview tab.",
               style={"fontSize":"11px","color":MUTED,"margin":"0 0 14px"}),
        html.Div(style={"display":"grid","gridTemplateColumns":"60px 1fr 1fr 1fr",
                        "gap":"6px","marginBottom":"4px"},
                 children=[html.Span(""),
                            *[html.Span(h,style={**LBL,"marginBottom":"0"})
                              for h in ["Shares","Avg Cost","Cur Value"]]]),
        *[html.Div(style={"display":"grid","gridTemplateColumns":"60px 1fr 1fr 1fr",
                          "gap":"6px","marginBottom":"8px","alignItems":"center"}, children=[
            html.Div([html.Span(t,style={"fontWeight":"700","color":ACCENT,"fontSize":"13px"}),
                      html.Div(f"SMA-{CORE_PORTFOLIO[t]['sma_period']}",
                               style={"fontSize":"9px","color":MUTED})]),
            dcc.Input(id={"type":"shares-input","ticker":t},type="number",min=0,placeholder="0",
                      value=(_SAVED.get("holdings",{}).get(t) or {}).get("shares"),
                      style={**INP,"fontSize":"12px","padding":"6px 8px"}),
            dcc.Input(id={"type":"cost-input","ticker":t},type="number",min=0,placeholder="0.00",
                      value=(_SAVED.get("holdings",{}).get(t) or {}).get("avg_cost"),
                      style={**INP,"fontSize":"12px","padding":"6px 8px"}),
            dcc.Input(id={"type":"curval-input","ticker":t},type="number",min=0,placeholder="$",
                      value=(_SAVED.get("holdings",{}).get(t) or {}).get("current_value"),
                      style={**INP,"fontSize":"12px","padding":"6px 8px"}),
          ]) for t in CORE_TICKERS],
        html.Button("Save Holdings",id="save-holdings-btn",n_clicks=0,
                    style={**BTN2,"marginTop":"8px"}),
        html.Div(id="core-holdings-msg",style={"marginTop":"8px","fontSize":"12px","color":ACCENT2}),
    ])

    # Signal table
    sig_hdr = html.Div(
        style={"display":"grid","gridTemplateColumns":"60px 55px 90px 100px 80px 85px",
               "gap":"4px","padding":"6px 0","borderBottom":f"1px solid {CARD_BORDER}",
               "fontSize":"10px","color":MUTED,"letterSpacing":"0.8px","textTransform":"uppercase"},
        children=[html.Span(c) for c in ["Ticker","SMA","Price","SMA Val","% vs SMA","Signal"]])
    sig_rows=[]
    for t,cfg in CORE_PORTFOLIO.items():
        md=(market or {}).get(t,{}); price=md.get("price")
        sma_p=cfg["sma_period"]; sma_v=md.get(f"sma_{sma_p}")
        sig=sma_signal(md,sma_p)
        pct=((price-sma_v)/sma_v*100) if price and sma_v else None
        sc=GREEN if sig=="BUY" else (RED if sig=="SELL/CASH" else MUTED)
        sig_rows.append(html.Div(
            style={"display":"grid","gridTemplateColumns":"60px 55px 90px 100px 80px 85px",
                   "gap":"4px","padding":"9px 0","borderBottom":f"1px solid {CARD_BORDER}",
                   "fontSize":"12px","alignItems":"center"},
            children=[html.Span(t,style={"fontWeight":"700","color":ACCENT}),
                      html.Span(f"SMA-{sma_p}",style={"color":MUTED,"fontSize":"10px"}),
                      html.Span(fmt(price)),
                      html.Span(fmt(sma_v),style={"color":MUTED}),
                      html.Span(f"{pct:+.2f}%" if pct is not None else "—",
                                style={"color":pcolor(pct),"fontWeight":"600"}),
                      html.Span("▲ BUY" if sig=="BUY" else ("▼ CASH" if sig=="SELL/CASH" else "—"),
                                style={"color":sc,"fontWeight":"700","fontSize":"11px"})]))
    sig_card = html.Div(style=CARD, children=[
        html.H3("SMA Signals",style={"margin":"0 0 10px","fontSize":"13px","color":MUTED,"letterSpacing":"1px"}),
        sig_hdr,*sig_rows])

    # Rebalance
    if alloc > 0:
        rows = compute_core_rebalance(holdings or {}, market or {}, alloc)
        reb_hdr = html.Div(
            style={"display":"grid",
                   "gridTemplateColumns":"60px 65px 70px 90px 95px 100px 95px 100px",
                   "gap":"4px","padding":"6px 0","borderBottom":f"1px solid {CARD_BORDER}",
                   "fontSize":"10px","color":MUTED,"letterSpacing":"0.8px","textTransform":"uppercase"},
            children=[html.Span(c) for c in
                      ["Ticker","Signal","Target %","Target $","Current $","Δ Value","Δ Shares","Unreal P&L"]])
        reb_rows=[]
        for r in rows:
            ic=r["ticker"]=="CASH"
            sc=CASH_CLR if ic else (GREEN if r["signal"]=="BUY" else RED)
            reb_rows.append(html.Div(
                style={"display":"grid","gridTemplateColumns":"60px 65px 70px 90px 95px 100px 95px 100px",
                       "gap":"4px","padding":"9px 0","borderBottom":f"1px solid {CARD_BORDER}",
                       "fontSize":"12px","alignItems":"center","opacity":"0.5" if ic else "1"},
                children=[
                    html.Span(r["ticker"],style={"fontWeight":"700","color":CASH_CLR if ic else ACCENT}),
                    html.Span("CASH" if ic else ("▲ BUY" if r["signal"]=="BUY" else "▼ CASH"),
                              style={"color":sc,"fontWeight":"700","fontSize":"11px"}),
                    html.Span(f"{r['target_pct']*100:.2f}%",style={"color":MUTED}),
                    html.Span(fmt(r["target_val"])),
                    html.Span(fmt(r["cur_val"]) if not ic else "—",style={"color":MUTED}),
                    html.Span(fmt(r["delta_val"],sign=True) if r["delta_val"] is not None else "—",
                              style={"color":pcolor(r["delta_val"]),"fontWeight":"600"}),
                    html.Span(f"{r['delta_shares']:+.4f}" if r["delta_shares"] is not None else "—",
                              style={"color":pcolor(r["delta_shares"])}),
                    html.Span(fmt(r["pnl_unreal"],sign=True) if r["pnl_unreal"] is not None else "—",
                              style={"color":pcolor(r["pnl_unreal"])}),
                ]))
        reb_card = html.Div(style=CARD, children=[
            html.H3("Rebalance Engine",style={"margin":"0 0 4px","fontSize":"13px","color":MUTED,"letterSpacing":"1px"}),
            html.P("Δ Shares = BUY (+) or SELL (−) to reach target. Below-SMA → CASH.",
                   style={"fontSize":"11px","color":MUTED,"margin":"0 0 12px"}),
            reb_hdr,*reb_rows])
    else:
        reb_card = html.Div(style=CARD, children=[
            html.Div("Set portfolio value & Core % on Overview tab.",
                     style={"color":MUTED,"textAlign":"center","padding":"20px 0","fontSize":"13px"})])

    # Charts
    pie_lbl,pie_val,pie_clr=[],[],[]
    cash_p=0.0
    for i,(t,cfg) in enumerate(CORE_PORTFOLIO.items()):
        if sma_signal((market or {}).get(t,{}),cfg["sma_period"])=="BUY":
            pie_lbl.append(t); pie_val.append(cfg["target_pct"]*100)
            pie_clr.append(PIE_COLORS[i%len(PIE_COLORS)])
        else: cash_p+=cfg["target_pct"]
    if cash_p>0: pie_lbl.append("CASH"); pie_val.append(cash_p*100); pie_clr.append(CASH_CLR)
    pf=go.Figure(go.Pie(labels=pie_lbl,values=pie_val,hole=0.55,
                        marker=dict(colors=pie_clr,line=dict(color=DARK_BG,width=2)),
                        textfont=dict(size=12,color="#fff"),
                        hovertemplate="<b>%{label}</b><br>%{value:.2f}%<extra></extra>",
                        textinfo="label+percent"))
    pf.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                     font=dict(color=TEXT),showlegend=False,
                     margin=dict(t=10,b=10,l=10,r=10),height=300,
                     annotations=[dict(text="Effective<br>Alloc",x=0.5,y=0.5,
                                       font_size=11,font_color=MUTED,showarrow=False)])
    bt,bv,bc=[],[],[]
    for t,cfg in CORE_PORTFOLIO.items():
        md=(market or {}).get(t,{}); p=md.get("price"); sv=md.get(f"sma_{cfg['sma_period']}")
        if p and sv:
            pct=(p-sv)/sv*100; bt.append(t); bv.append(pct); bc.append(GREEN if pct>=0 else RED)
    bf=go.Figure(go.Bar(x=bt,y=bv,marker_color=bc,text=[f"{v:+.2f}%" for v in bv],
                        textposition="outside",textfont=dict(size=11,color=TEXT),
                        hovertemplate="<b>%{x}</b><br>%{y:+.2f}% vs SMA<extra></extra>"))
    bf.add_hline(y=0,line_color=CARD_BORDER,line_width=1.5)
    bf.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                     font=dict(color=TEXT),
                     xaxis=dict(showgrid=False,color=MUTED),
                     yaxis=dict(showgrid=True,gridcolor=CARD_BORDER,color=MUTED,ticksuffix="%"),
                     margin=dict(t=20,b=20,l=10,r=10),height=300,bargap=0.35)
    charts=html.Div(style=CARD,children=[
        html.Div(style={"display":"grid","gridTemplateColumns":"1fr 1fr","gap":"16px"},children=[
            html.Div([html.H3("Effective Allocation",style={"margin":"0 0 8px","fontSize":"13px","color":MUTED,"letterSpacing":"1px"}),
                      dcc.Graph(figure=pf,config={"displayModeBar":False})]),
            html.Div([html.H3("Price vs SMA (%)",style={"margin":"0 0 8px","fontSize":"13px","color":MUTED,"letterSpacing":"1px"}),
                      dcc.Graph(figure=bf,config={"displayModeBar":False})]),
        ])])

    return html.Div([kpis,
        html.Div(style={"display":"grid","gridTemplateColumns":"360px 1fr","gap":"24px","alignItems":"start"},
                 children=[left,html.Div([sig_card,reb_card,charts])])])

# ═══════════════════════════════════════════════════════════════════════
#  TAB 3 — MOMENTUM PORTFOLIO
# ═══════════════════════════════════════════════════════════════════════
def build_momentum_tab(mom_sig, tv, mp):
    sig       = mom_sig or {}
    alloc     = ((tv or 0)*(mp or 0)/100) or 0
    winners   = sig.get("winners", [])
    cash_w    = sig.get("cash_weight", 1.0)
    scores    = sig.get("scores", {})
    diag      = sig.get("diagnostics", {})
    as_of     = sig.get("as_of", "—")

    # ── KPIs ──
    n_winners = len(winners)
    deployed  = sum(w for _,w in winners)
    kpis = html.Div(style={"display":"flex","gap":"14px","marginBottom":"20px",
                            "flexWrap":"wrap","paddingTop":"20px"}, children=[
        kpi_card("Momentum Alloc",  fmt(alloc),    ACCENT4, f"{mp or 0:.1f}% of total", ACCENT4),
        kpi_card("Signal Date",     as_of,          TEXT,    "last market close"),
        kpi_card("Winners",         f"{n_winners}", ACCENT4, f"Top-{MOM_TOP_N} vol-scaled"),
        kpi_card("Deployed",        f"{deployed:.1%}", GREEN if deployed>0.5 else YELLOW,
                 f"Cash: {cash_w:.1%}", bar_color=GREEN),
    ])

    # ── Winners card ──
    winner_rows = []
    winner_tickers = {t for t,_ in winners}
    for t,w in winners:
        p   = (diag.get(t) or {}).get("price")
        amt = alloc*w if alloc else None
        d   = diag.get(t,{})
        winner_rows.append(html.Div(
            style={**CARD,"borderLeft":f"4px solid {ACCENT4}","marginBottom":"12px","padding":"16px"},
            children=[
                html.Div(style={"display":"flex","justifyContent":"space-between","alignItems":"center",
                                "marginBottom":"8px"}, children=[
                    html.Div([html.Span(t,style={"fontSize":"18px","fontWeight":"800","color":ACCENT4}),
                              html.Span(f"  #{list(winner_tickers).index(t)+1}",
                                        style={"fontSize":"12px","color":MUTED})]),
                    html.Div([html.Span(f"{w:.1%}",style={"fontSize":"16px","fontWeight":"700","color":TEXT}),
                              html.Span(f"  {fmt(amt)}",style={"fontSize":"14px","color":ACCENT4,"marginLeft":"8px"})]),
                ]),
                html.Div(style={"display":"grid","gridTemplateColumns":"repeat(4,1fr)","gap":"8px"}, children=[
                    html.Div([html.Div("Price",style={**LBL,"marginBottom":"2px"}),
                              html.Div(fmt(p),style={"fontSize":"13px","fontWeight":"600"})]),
                    html.Div([html.Div("Momentum",style={**LBL,"marginBottom":"2px"}),
                              html.Div(f"{d.get('momentum',0):+.2%}" if d.get("momentum") not in (None,-np.inf) else "—",
                                       style={"fontSize":"13px","fontWeight":"600","color":pcolor(d.get("momentum"))})]),
                    html.Div([html.Div("6m Return",style={**LBL,"marginBottom":"2px"}),
                              html.Div(f"{d.get('ret_6m',0):+.2%}" if d.get("ret_6m") not in (None,-np.inf) else "—",
                                       style={"fontSize":"13px","fontWeight":"600","color":pcolor(d.get("ret_6m"))})]),
                    html.Div([html.Div("SMA Gate",style={**LBL,"marginBottom":"2px"}),
                              html.Div("✓ Pass" if d.get("trend_pass") else "✗ Fail",
                                       style={"fontSize":"13px","fontWeight":"600",
                                              "color":"#86efac" if d.get("trend_pass") else RED})]),
                ]),
            ]))
    if cash_w > 0.001:
        amt=alloc*cash_w if alloc else None
        winner_rows.append(html.Div(
            style={**CARD,"borderLeft":f"4px solid {CASH_CLR}","marginBottom":"12px",
                   "padding":"16px","opacity":"0.7"},
            children=[html.Div(style={"display":"flex","justifyContent":"space-between"}, children=[
                html.Span("CASH (SGOV)",style={"fontSize":"16px","fontWeight":"700","color":MUTED}),
                html.Div([html.Span(f"{cash_w:.1%}",style={"fontSize":"16px","fontWeight":"700","color":MUTED}),
                          html.Span(f"  {fmt(amt)}",style={"fontSize":"14px","color":MUTED,"marginLeft":"8px"})]),
            ])]))

    winners_panel = html.Div(style=CARD, children=[
        html.H3("Current Signal — Winners",
                style={"margin":"0 0 16px","fontSize":"13px","color":ACCENT4,"letterSpacing":"1px"}),
        *winner_rows,
    ])

    # ── Full diagnostics table ──
    tbl_hdr = html.Div(
        style={"display":"grid","gridTemplateColumns":"80px 60px 60px 80px 90px 90px 70px 70px 80px",
               "gap":"4px","padding":"6px 0","borderBottom":f"1px solid {CARD_BORDER}",
               "fontSize":"10px","color":MUTED,"letterSpacing":"0.8px","textTransform":"uppercase"},
        children=[html.Span(c) for c in
                  ["Ticker","SMA","Price","Momentum","6m Ret","Trend","Abs Mom","Eligible","Status"]])
    tbl_rows=[]
    all_tickers_sorted = sorted(diag.keys(),
                                key=lambda t: (not diag[t].get("eligible",False),
                                               -(diag[t].get("momentum") or -999)))
    for t in all_tickers_sorted:
        d=diag[t]
        is_winner = t in winner_tickers
        mom_v = d.get("momentum")
        ret_v = d.get("ret_6m")
        tbl_rows.append(html.Div(
            style={"display":"grid","gridTemplateColumns":"80px 60px 60px 80px 90px 90px 70px 70px 80px",
                   "gap":"4px","padding":"8px 0","borderBottom":f"1px solid {CARD_BORDER}",
                   "fontSize":"12px","alignItems":"center",
                   "opacity":"1" if d.get("eligible") else "0.5"},
            children=[
                html.Span(t,style={"fontWeight":"700",
                                   "color":ACCENT4 if is_winner else (ACCENT if d.get("eligible") else MUTED)}),
                html.Span(f"{d.get('sma_period')}d",style={"color":MUTED,"fontSize":"10px"}),
                html.Span(fmt(d.get("price"))),
                html.Span(f"{mom_v:+.2%}" if mom_v not in (None,-np.inf,np.inf) else "—",
                          style={"color":pcolor(mom_v)}),
                html.Span(f"{ret_v:+.2%}" if ret_v not in (None,-np.inf,np.inf) else "—",
                          style={"color":pcolor(ret_v)}),
                html.Span("✓" if d.get("trend_pass") else "✗",
                          style={"color":"#86efac" if d.get("trend_pass") else RED,"fontWeight":"700"}),
                html.Span("✓" if d.get("abs_pass") else "✗",
                          style={"color":"#86efac" if d.get("abs_pass") else RED,"fontWeight":"700"}),
                html.Span("✓" if d.get("eligible") else "✗",
                          style={"color":"#86efac" if d.get("eligible") else RED,"fontWeight":"700"}),
                html.Span("★ WINNER" if is_winner else ("ELIGIBLE" if d.get("eligible") else "filtered"),
                          style={"color":ACCENT4 if is_winner else (GREEN if d.get("eligible") else MUTED),
                                 "fontWeight":"700" if is_winner else "400","fontSize":"11px"}),
            ]))
    diag_card = html.Div(style=CARD, children=[
        html.H3("Full Asset Diagnostics",
                style={"margin":"0 0 4px","fontSize":"13px","color":MUTED,"letterSpacing":"1px"}),
        html.P(f"SMA gate: {MOM_SMA_PERIOD}d default (BND/BNDX/VGIT: 126d)  |  "
               f"Abs momentum: 6m return > SGOV  |  Vol target: {MOM_TARGET_VOL:.0%}",
               style={"fontSize":"11px","color":MUTED,"margin":"0 0 12px"}),
        tbl_hdr,*tbl_rows,
    ])

    # ── Momentum bar chart ──
    valid = [(t,d["momentum"]) for t,d in diag.items()
             if d.get("momentum") not in (None,-np.inf,np.inf)]
    valid.sort(key=lambda x:-x[1])
    bt=[x[0] for x in valid]; bv=[x[1]*100 for x in valid]
    bc=[ACCENT4 if t in winner_tickers else (GREEN if diag[t].get("eligible") else MUTED)
        for t in bt]
    bf=go.Figure(go.Bar(x=bt,y=bv,marker_color=bc,
                        text=[f"{v:+.1f}%" for v in bv],textposition="outside",
                        textfont=dict(size=10,color=TEXT),
                        hovertemplate="<b>%{x}</b><br>Momentum: %{y:+.2f}%<extra></extra>"))
    bf.add_hline(y=0,line_color=CARD_BORDER,line_width=1)
    bf.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                     font=dict(color=TEXT),
                     xaxis=dict(showgrid=False,color=MUTED),
                     yaxis=dict(showgrid=True,gridcolor=CARD_BORDER,color=MUTED,ticksuffix="%"),
                     margin=dict(t=20,b=10,l=10,r=10),height=300,bargap=0.25)
    mom_chart=html.Div(style=CARD,children=[
        html.H3("Composite Momentum Score",
                style={"margin":"0 0 8px","fontSize":"13px","color":MUTED,"letterSpacing":"1px"}),
        html.P(f"Orange = winner  |  Green = eligible  |  Grey = filtered",
               style={"fontSize":"11px","color":MUTED,"margin":"0 0 8px"}),
        dcc.Graph(figure=bf,config={"displayModeBar":False})])

    return html.Div([kpis,
        html.Div(style={"display":"grid","gridTemplateColumns":"380px 1fr","gap":"24px","alignItems":"start"},
                 children=[winners_panel, html.Div([diag_card,mom_chart])])])

# ═══════════════════════════════════════════════════════════════════════
#  TAB 4 — DOW TITANS
# ═══════════════════════════════════════════════════════════════════════
def build_titans_tab(titans_rows, tv, tp):
    rows        = titans_rows or []
    eligible    = [r for r in rows if r.get("signal")=="BUY"]
    n_elig      = len(eligible)
    alloc       = ((tv or 0)*(tp or 0)/100) or 0
    weight_each = (alloc/n_elig) if n_elig else None

    bench = {}
    for r in rows:
        if "bench" in r: bench=r["bench"]; break

    kpis = html.Div(style={"display":"flex","gap":"14px","marginBottom":"20px",
                            "flexWrap":"wrap","paddingTop":"20px"}, children=[
        kpi_card("Titans Allocation", fmt(alloc),      ACCENT3, f"{tp or 0:.1f}% of total", ACCENT3),
        kpi_card("Eligible",          f"{n_elig}/{len(DOW_TITANS)}", ACCENT3, "passing all 4 gates"),
        kpi_card("Weight per Stock",  f"{100/n_elig:.2f}%" if n_elig else "—", TEXT,
                 fmt(weight_each)+" each" if weight_each else "No eligible"),
        kpi_card("EMA Filter",        f"EMA-{TITANS_EMA_PERIOD}", MUTED, "Gate 1", bar_color=MUTED),
    ])

    bench_items=[html.Div(
        style={"display":"flex","justifyContent":"space-between","padding":"5px 0",
               "borderBottom":f"1px solid {CARD_BORDER}","fontSize":"12px"},
        children=[html.Span(lbl,style={"color":MUTED}),
                  html.Span(f"{v:+.2f}%" if v is not None else "—",
                            style={"color":pcolor(v),"fontWeight":"600"})])
        for lbl,key in [("SHV 6m","shv_6m"),("VGIT 6m","vgit_6m"),
                         ("ACWI 3m","acwi_3m"),("ACWI 6m","acwi_6m"),("ACWI 1y","acwi_1y")]
        for v in [bench.get(key)]]
    bench_card=html.Div(style={**CARD,"marginBottom":"0"},children=[
        html.H3("Benchmark Returns",style={"margin":"0 0 10px","fontSize":"13px",
                                            "color":ACCENT3,"letterSpacing":"1px"}),
        *bench_items])

    tbl_hdr=html.Div(
        style={"display":"grid",
               "gridTemplateColumns":"58px 80px 80px 80px 80px 80px 80px 50px 50px 50px 80px 90px",
               "gap":"4px","padding":"6px 0","borderBottom":f"1px solid {CARD_BORDER}",
               "fontSize":"10px","color":MUTED,"letterSpacing":"0.8px","textTransform":"uppercase"},
        children=[html.Span(c) for c in
                  ["Ticker","Price","EMA-200","% vs EMA","Ret 3m","Ret 6m","Ret 1y",
                   "①>SHV","②>VGIT","③>ACWI","Signal","Target $"]])
    tbl_rows=[]
    prev=None
    for r in rows:
        if r.get("signal")=="NO DATA": continue
        if prev is not None and prev!=r.get("signal"):
            tbl_rows.append(html.Hr(style={"borderColor":CARD_BORDER,"margin":"4px 0"}))
        prev=r.get("signal")
        is_buy=r.get("signal")=="BUY"
        sc=GREEN if is_buy else RED
        def fr(v): return f"{v:+.1f}%" if v is not None else "—"
        tbl_rows.append(html.Div(
            style={"display":"grid",
                   "gridTemplateColumns":"58px 80px 80px 80px 80px 80px 80px 50px 50px 50px 80px 90px",
                   "gap":"4px","padding":"8px 0","borderBottom":f"1px solid {CARD_BORDER}",
                   "fontSize":"12px","alignItems":"center","opacity":"1" if is_buy else "0.55"},
            children=[
                html.Span(r["ticker"],style={"fontWeight":"700","color":ACCENT3 if is_buy else MUTED}),
                html.Span(fmt(r.get("price"))),
                html.Span(fmt(r.get("ema")),style={"color":MUTED}),
                html.Span(f"{r['pct_ema']:+.2f}%" if r.get("pct_ema") is not None else "—",
                          style={"color":pcolor(r.get("pct_ema")),"fontWeight":"600"}),
                html.Span(fr(r.get("r3m")),style={"color":pcolor(r.get("r3m"))}),
                html.Span(fr(r.get("r6m")),style={"color":pcolor(r.get("r6m"))}),
                html.Span(fr(r.get("r1y")),style={"color":pcolor(r.get("r1y"))}),
                html.Span("✓" if r.get("f1") else "✗",
                          style={"color":"#86efac" if r.get("f1") else RED,"fontWeight":"700"}),
                html.Span("✓" if r.get("f2") else "✗",
                          style={"color":"#86efac" if r.get("f2") else RED,"fontWeight":"700"}),
                html.Span("✓" if r.get("f3") else "✗",
                          style={"color":"#86efac" if r.get("f3") else RED,"fontWeight":"700"}),
                html.Span("✅ BUY" if is_buy else "❌ OUT",
                          style={"color":sc,"fontWeight":"700","fontSize":"11px"}),
                html.Span(fmt(weight_each) if (is_buy and weight_each) else "—",
                          style={"color":ACCENT3 if (is_buy and weight_each) else MUTED,
                                 "fontWeight":"600" if is_buy else "400"}),
            ]))
    sig_card=html.Div(style=CARD,children=[
        html.H3("Dow Titans Signal Scanner",style={"margin":"0 0 4px","fontSize":"13px",
                                                    "color":ACCENT3,"letterSpacing":"1px"}),
        html.P("Gate 1: Price>EMA-200  |  ①: 6m>SHV  |  ②: 6m>VGIT  |  ③: 3m+6m+1y>ACWI",
               style={"fontSize":"11px","color":MUTED,"margin":"0 0 12px"}),
        tbl_hdr,*tbl_rows])

    if eligible:
        eq_t=[r["ticker"] for r in eligible]
        eq_v=[weight_each]*n_elig if weight_each else [1/n_elig]*n_elig
        ef=go.Figure(go.Bar(x=eq_t,y=eq_v,marker_color=PIE_COLORS[:n_elig],
                            text=[fmt(v) for v in eq_v],textposition="outside",
                            textfont=dict(size=10,color=TEXT),
                            hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>"))
        ef.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color=TEXT),xaxis=dict(showgrid=False,color=MUTED),
                         yaxis=dict(showgrid=True,gridcolor=CARD_BORDER,color=MUTED),
                         margin=dict(t=20,b=30,l=10,r=10),height=280,bargap=0.3)
        elig_chart=html.Div(style=CARD,children=[
            html.H3("Eligible — Equal-Weight Target $",
                    style={"margin":"0 0 8px","fontSize":"13px","color":ACCENT3,"letterSpacing":"1px"}),
            dcc.Graph(figure=ef,config={"displayModeBar":False})])
    else:
        elig_chart=html.Div()

    return html.Div([kpis,
        html.Div(style={"display":"grid","gridTemplateColumns":"200px 1fr","gap":"20px","alignItems":"start"},
                 children=[bench_card,html.Div([sig_card,elig_chart])])])

# ═══════════════════════════════════════════════════════════════════════
#  CSS
# ═══════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════
#  TAB 5 — CASH PORTFOLIO
# ═══════════════════════════════════════════════════════════════════════
def build_cash_tab(cash_mkt, tv, xp):
    cash_mkt  = cash_mkt or {}
    alloc     = ((tv or 0) * (xp or 0) / 100) or 0
    all_names = CASH_INSTRUMENTS + [CASH_LABEL]
    per_wt    = CASH_WEIGHT_EACH
    per_val   = alloc * per_wt

    kpis = html.Div(style={"display":"flex","gap":"14px","marginBottom":"20px",
                            "flexWrap":"wrap","paddingTop":"20px"}, children=[
        kpi_card("Cash Allocation", fmt(alloc),   ACCENT5, f"{xp or 0:.1f}% of total", ACCENT5),
        kpi_card("Instruments",     "4",           TEXT,   "SGOV · SHV · ICSH · $CASH"),
        kpi_card("Weight Each",     "25.00%",      ACCENT5, fmt(per_val)+" per instrument"),
        kpi_card("Strategy",        "Equal Weight",MUTED,  "rebalance to 25% each", bar_color=MUTED),
    ])

    rows = []
    for name in all_names:
        is_cash_line = name == CASH_LABEL
        price  = 1.0 if is_cash_line else (cash_mkt.get(name) or {}).get("price")
        shares = (per_val / price) if (price and per_val) else None
        rows.append(html.Div(
            style={"display":"grid",
                   "gridTemplateColumns":"70px 80px 90px 100px 100px 1fr",
                   "gap":"4px","padding":"12px 0",
                   "borderBottom":f"1px solid {CARD_BORDER}",
                   "fontSize":"13px","alignItems":"center"},
            children=[
                html.Span(name, style={"fontWeight":"700","color":ACCENT5}),
                html.Span("$1.00" if is_cash_line else fmt(price), style={"color":TEXT}),
                html.Span(f"{per_wt*100:.2f}%", style={"color":MUTED}),
                html.Span(fmt(per_val), style={"color":ACCENT5,"fontWeight":"600"}),
                html.Span(f"{shares:,.4f} shares" if (shares and not is_cash_line) else
                          (fmt(per_val) if is_cash_line else "—"), style={"color":MUTED,"fontSize":"12px"}),
                html.Span("Uninvested cash — hold at brokerage" if is_cash_line
                          else "Money market / ultra-short ETF",
                          style={"color":MUTED,"fontSize":"11px","fontStyle":"italic"}),
            ]
        ))

    hdr = html.Div(
        style={"display":"grid",
               "gridTemplateColumns":"70px 80px 90px 100px 100px 1fr",
               "gap":"4px","padding":"6px 0","borderBottom":f"1px solid {CARD_BORDER}",
               "fontSize":"10px","color":MUTED,"letterSpacing":"0.8px","textTransform":"uppercase"},
        children=[html.Span(c) for c in ["Instrument","Price","Weight","Target $","Shares","Notes"]]
    )

    pf = go.Figure(go.Pie(
        labels=all_names, values=[25,25,25,25], hole=0.55,
        marker=dict(colors=[ACCENT5,"#a78bfa","#7c3aed",CASH_CLR],
                    line=dict(color=DARK_BG,width=2)),
        textfont=dict(size=13,color="#fff"),
        hovertemplate="<b>%{label}</b><br>25.00%<extra></extra>",
        textinfo="label+percent",
    ))
    pf.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT),showlegend=False,
        margin=dict(t=10,b=10,l=10,r=10),height=280,
        annotations=[dict(text=fmt(alloc),x=0.5,y=0.5,font_size=14,font_color=ACCENT5,showarrow=False)],
    )

    return html.Div([kpis,
        html.Div(style={"display":"grid","gridTemplateColumns":"320px 1fr","gap":"24px","alignItems":"start"},
                 children=[
                     html.Div(style=CARD, children=[
                         html.H3("Allocation Split",
                                 style={"margin":"0 0 8px","fontSize":"13px","color":ACCENT5,"letterSpacing":"1px"}),
                         dcc.Graph(figure=pf,config={"displayModeBar":False}),
                         html.P("Each instrument receives an equal 25% of the Cash portfolio allocation.",
                                style={"fontSize":"11px","color":MUTED,"margin":"12px 0 0","textAlign":"center"}),
                     ]),
                     html.Div(style=CARD, children=[
                         html.H3("Cash Portfolio Holdings",
                                 style={"margin":"0 0 12px","fontSize":"13px","color":ACCENT5,"letterSpacing":"1px"}),
                         hdr, *rows,
                         html.P("$CASH = uninvested dollar balance held at brokerage.",
                                style={"fontSize":"11px","color":MUTED,"marginTop":"14px"}),
                     ]),
                 ]),
    ])


# ═══════════════════════════════════════════════════════════════════════
#  MASTER HOLDINGS TABLE
# ═══════════════════════════════════════════════════════════════════════
def build_master_table(core_mkt, mom_sig, titans_rows, cash_mkt,
                       holdings, tv, cp, mp, tp, xp):
    tv = tv or 0
    rows = []

    def add_row(portfolio, ticker, color, price, target_val, shares_hint=None):
        pct_of_total = (target_val / tv * 100) if tv else None
        rows.append({"portfolio":portfolio,"ticker":ticker,"color":color,
                     "price":price,"target_val":target_val,
                     "pct_total":pct_of_total,"shares":shares_hint})

    # Core
    core_alloc = tv * cp / 100
    for t, cfg in CORE_PORTFOLIO.items():
        md    = (core_mkt or {}).get(t, {})
        price = md.get("price")
        sig   = sma_signal(md, cfg["sma_period"])
        eff   = cfg["target_pct"] if sig=="BUY" else 0.0
        tval  = core_alloc * eff
        h     = (holdings or {}).get(t) or {}
        sh    = h.get("shares") if h.get("shares") else (tval/price if (tval and price) else None)
        add_row("Core", t, ACCENT, price, tval, sh)
    core_cash_pct = sum(cfg["target_pct"] for t,cfg in CORE_PORTFOLIO.items()
                        if sma_signal((core_mkt or {}).get(t,{}),cfg["sma_period"])!="BUY")
    if core_cash_pct > 0:
        add_row("Core","CASH->SGOV",MUTED,1.0,core_alloc*core_cash_pct,None)

    # Momentum
    mom_alloc = tv * mp / 100
    if mom_sig:
        for t,w in (mom_sig.get("winners") or []):
            d     = (mom_sig.get("diagnostics") or {}).get(t) or {}
            price = d.get("price")
            tval  = mom_alloc * w
            sh    = (tval/price) if (tval and price) else None
            add_row("Momentum", t, ACCENT4, price, tval, sh)
        cw = mom_sig.get("cash_weight",0)
        if cw > 0.001:
            add_row("Momentum","CASH(SGOV)",MUTED,None,mom_alloc*cw,None)

    # Dow Titans
    titans_alloc = tv * tp / 100
    elig_t = [r for r in (titans_rows or []) if r.get("signal")=="BUY"]
    n_e    = len(elig_t)
    if n_e:
        wt_each = titans_alloc / n_e
        for r in elig_t:
            price = r.get("price")
            sh    = (wt_each/price) if (wt_each and price) else None
            add_row("Dow Titans", r["ticker"], ACCENT3, price, wt_each, sh)

    # Cash
    cash_alloc = tv * xp / 100
    per_val    = cash_alloc * CASH_WEIGHT_EACH
    for name in CASH_INSTRUMENTS + [CASH_LABEL]:
        price = 1.0 if name==CASH_LABEL else (cash_mkt or {}).get(name,{}).get("price")
        sh    = (per_val/price) if (price and per_val and name!=CASH_LABEL) else None
        add_row("Cash", name, ACCENT5, price, per_val, sh)

    if not rows:
        return html.Div("Set allocations on the Overview tab to see the master table.",
                        style={"color":MUTED,"textAlign":"center","padding":"20px","fontSize":"13px"})

    PORT_COLORS = {"Core":ACCENT,"Momentum":ACCENT4,"Dow Titans":ACCENT3,"Cash":ACCENT5}

    hdr = html.Div(
        style={"display":"grid",
               "gridTemplateColumns":"110px 80px 90px 110px 100px 90px",
               "gap":"4px","padding":"8px 12px",
               "backgroundColor":"#0d0a1a","borderRadius":"8px 8px 0 0",
               "fontSize":"10px","color":MUTED,"letterSpacing":"0.8px","textTransform":"uppercase"},
        children=[html.Span(c) for c in ["Portfolio","Ticker","Price","Target $","% of Total","Shares"]]
    )

    tbl_rows = []
    prev_port = None
    for r in rows:
        if prev_port and prev_port != r["portfolio"]:
            tbl_rows.append(html.Div(style={"height":"1px","backgroundColor":CARD_BORDER}))
        prev_port = r["portfolio"]
        pc = PORT_COLORS.get(r["portfolio"], MUTED)
        tbl_rows.append(html.Div(
            style={"display":"grid",
                   "gridTemplateColumns":"110px 80px 90px 110px 100px 90px",
                   "gap":"4px","padding":"8px 12px",
                   "borderBottom":f"1px solid {CARD_BORDER}",
                   "fontSize":"12px","alignItems":"center",
                   "opacity":"0.5" if r["target_val"]==0 else "1"},
            children=[
                html.Span(r["portfolio"],style={"fontSize":"10px","color":pc,"fontWeight":"700",
                                                "letterSpacing":"0.5px","textTransform":"uppercase"}),
                html.Span(r["ticker"],style={"fontWeight":"700","color":r["color"]}),
                html.Span(fmt(r["price"]) if r["price"] else "—",style={"color":TEXT}),
                html.Span(fmt(r["target_val"]),style={"color":pc,"fontWeight":"600"}),
                html.Span(f"{r['pct_total']:.2f}%" if r["pct_total"] is not None else "—",
                          style={"color":MUTED}),
                html.Span(f"{r['shares']:,.4f}" if r["shares"] else "—",
                          style={"color":MUTED,"fontSize":"11px"}),
            ]
        ))

    total_invested = sum(r["target_val"] for r in rows)
    footer = html.Div(
        style={"display":"grid",
               "gridTemplateColumns":"110px 80px 90px 110px 100px 90px",
               "gap":"4px","padding":"10px 12px",
               "backgroundColor":"#0d0a1a","borderRadius":"0 0 8px 8px",
               "fontSize":"12px"},
        children=[
            html.Span("TOTAL",style={"fontWeight":"800","color":YELLOW,"fontSize":"11px","letterSpacing":"1px"}),
            html.Span(f"{len(rows)} positions",style={"color":MUTED,"fontSize":"11px"}),
            html.Span(""),
            html.Span(fmt(total_invested),style={"fontWeight":"800","color":YELLOW}),
            html.Span(f"{total_invested/tv*100:.1f}%" if tv else "—",style={"color":YELLOW,"fontWeight":"700"}),
            html.Span(""),
        ]
    )

    return html.Div(style=CARD, children=[
        html.H3("Master Portfolio — All Positions",
                style={"margin":"0 0 4px","fontSize":"13px","color":YELLOW,"letterSpacing":"1px"}),
        html.P("Every position across all 4 portfolios at target weights and dollar values.",
               style={"fontSize":"11px","color":MUTED,"margin":"0 0 14px"}),
        html.Div(style={"border":f"1px solid {CARD_BORDER}","borderRadius":"8px","overflow":"hidden"},
                 children=[hdr,*tbl_rows,footer]),
    ])

app.index_string = """<!DOCTYPE html>
<html><head>
  {%metas%}<title>{%title%}</title>{%favicon%}{%css%}
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0d0d12; }
    ::-webkit-scrollbar-thumb { background: #3b2d5e; border-radius: 3px; }
    input[type=number]::-webkit-inner-spin-button { opacity: 0.3; }
    input::placeholder { color: #4b5563 !important; }
  </style>
</head><body>
  {%app_entry%}
  <footer>{%config%}{%scripts%}{%renderer%}</footer>
</body></html>"""

# ═══════════════════════════════════════════════════════════════════════
#  RUN
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=8050)
