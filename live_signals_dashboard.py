"""
╔══════════════════════════════════════════════════════════════════════╗
║  MACRO SMA TREND-FOLLOWING DASHBOARD                                 ║
║  Strategy: SimpleMacroSMATrendFollowing (QuantConnect port)          ║
║  Tabs: Overview · Signals · Rebalance · Holdings                     ║
╚══════════════════════════════════════════════════════════════════════╝

SETUP:  pip install dash plotly yfinance pandas numpy
RUN:    python dashboard.py  →  http://127.0.0.1:8050
"""

import numpy as np
import plotly.graph_objects as go
from datetime import datetime

import dash
from dash import dcc, html, Input, Output, State

import utilities as U

# ── short aliases ──────────────────────────────────────────────────────
_fmt   = U.fmt
_pct   = U.pct_fmt
_pc    = U.pcolor
_kpi   = U.kpi_card
CARD   = U.CARD
INP    = U.INP
BTN    = U.BTN
BTN2   = U.BTN2
LBL    = U.LBL

DARK_BG     = U.DARK_BG
CARD_BG     = U.CARD_BG
CARD_BORDER = U.CARD_BORDER
ACCENT      = U.ACCENT
ACCENT2     = U.ACCENT2
ACCENT3     = U.ACCENT3
ACCENT4     = U.ACCENT4
ACCENT5     = U.ACCENT5
RED         = U.RED
GREEN       = U.GREEN
YELLOW      = U.YELLOW
TEXT        = U.TEXT
MUTED       = U.MUTED
CASH_CLR    = U.CASH_CLR
PIE_COLORS  = U.PIE_COLORS

_SAVED = U.load_saved()

# ═══════════════════════════════════════════════════════════════════════
#  APP
# ═══════════════════════════════════════════════════════════════════════
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Macro Trend Dashboard"

app.layout = html.Div(
    style={"backgroundColor": DARK_BG, "minHeight": "100vh",
           "fontFamily": "'JetBrains Mono','Fira Code','Cascadia Code',monospace",
           "color": TEXT},
    children=[
        # ── stores ──
        dcc.Store(id="signal-store",   data={}),
        dcc.Store(id="holdings-store", data=_SAVED.get("holdings", {})),
        dcc.Store(id="settings-store", data={
            "total_value": _SAVED.get("total_value"),
        }),
        dcc.Interval(id="interval", interval=60_000, n_intervals=0),

        # ── header ──
        html.Div(
            style={
                "background": f"linear-gradient(90deg,{CARD_BG} 0%,#060c18 100%)",
                "borderBottom": f"1px solid {CARD_BORDER}",
                "padding": "14px 32px",
                "display": "flex", "alignItems": "center",
                "justifyContent": "space-between",
            },
            children=[
                html.Div([
                    html.Span("◈ ", style={"color": ACCENT, "fontSize": "18px"}),
                    html.Span("MACRO SMA TREND",
                              style={"fontSize": "15px", "fontWeight": "800",
                                     "letterSpacing": "4px", "color": TEXT}),
                    html.Span("  //  SMA-147 / SMA-126  |  Vol-Scaled  |  Weekly Rebalance",
                              style={"fontSize": "11px", "color": MUTED, "marginLeft": "12px"}),
                ]),
                html.Div([
                    html.Span(id="last-updated",
                              style={"color": MUTED, "fontSize": "11px"}),
                ]),
            ],
        ),

        # ── tabs ──
        html.Div(
            style={"maxWidth": "1500px", "margin": "0 auto", "padding": "20px 24px 0"},
            children=[
                dcc.Tabs(id="main-tabs", value="overview",
                         style={"borderBottom": f"1px solid {CARD_BORDER}"},
                         children=[
                             dcc.Tab(label="◉  OVERVIEW",   value="overview",
                                     style=U.TAB_BASE, selected_style=U.tab_sel(ACCENT)),
                             dcc.Tab(label="⚡  SIGNALS",    value="signals",
                                     style=U.TAB_BASE, selected_style=U.tab_sel(ACCENT3)),
                             dcc.Tab(label="⟳  REBALANCE",  value="rebalance",
                                     style=U.TAB_BASE, selected_style=U.tab_sel(ACCENT4)),
                             dcc.Tab(label="◎  HOLDINGS",   value="holdings",
                                     style=U.TAB_BASE, selected_style=U.tab_sel(ACCENT2)),
                         ]),
            ],
        ),

        html.Div(id="tab-content",
                 style={"maxWidth": "1500px", "margin": "0 auto",
                        "padding": "0 24px 48px"}),
    ],
)


# ═══════════════════════════════════════════════════════════════════════
#  CALLBACK — refresh market data → signal store
# ═══════════════════════════════════════════════════════════════════════
@app.callback(
    Output("signal-store",  "data"),
    Output("last-updated",  "children"),
    Input("interval",       "n_intervals"),
    prevent_initial_call=False,
)
def refresh(_):
    prices = U.fetch_market_data()
    sig    = U.compute_signal(prices)
    now    = datetime.now().strftime("⟳  %H:%M:%S")
    return U.signal_to_json(sig), now


# ═══════════════════════════════════════════════════════════════════════
#  CALLBACK — save portfolio value
# ═══════════════════════════════════════════════════════════════════════
@app.callback(
    Output("settings-store", "data"),
    Output("ov-save-msg",    "children"),
    Input("ov-save-btn",     "n_clicks"),
    State("ov-total-value",  "value"),
    State("holdings-store",  "data"),
    prevent_initial_call=True,
)
def save_settings(_, total, holdings):
    if not total or float(total) <= 0:
        return {}, "⚠ Enter a valid portfolio value."
    tv       = float(total)
    settings = {"total_value": tv}
    U.save_all({**settings, "holdings": holdings or {}})
    return settings, f"✓ Saved  —  Portfolio value: {_fmt(tv)}"


# ═══════════════════════════════════════════════════════════════════════
#  CALLBACK — save holdings
# ═══════════════════════════════════════════════════════════════════════
@app.callback(
    Output("holdings-store",   "data"),
    Output("holdings-save-msg","children"),
    Input("save-holdings-btn", "n_clicks"),
    [State({"type": "shares-input",   "ticker": t}, "value") for t in U.ALL_TICKERS],
    [State({"type": "avgcost-input",  "ticker": t}, "value") for t in U.ALL_TICKERS],
    State("settings-store", "data"),
    prevent_initial_call=True,
)
def save_holdings(_, *args):
    n         = len(U.ALL_TICKERS)
    sh, co    = args[0:n], args[n:2*n]
    settings  = args[2*n] or {}
    holdings  = {
        t: {
            "shares":   float(sh[i]) if sh[i] is not None else None,
            "avg_cost": float(co[i]) if co[i] is not None else None,
        }
        for i, t in enumerate(U.ALL_TICKERS)
    }
    U.save_all({**settings, "holdings": holdings})
    return holdings, "✓ Holdings saved."


# ═══════════════════════════════════════════════════════════════════════
#  CALLBACK — render tab
# ═══════════════════════════════════════════════════════════════════════
@app.callback(
    Output("tab-content",   "children"),
    Input("main-tabs",      "value"),
    Input("signal-store",   "data"),
    Input("holdings-store", "data"),
    Input("settings-store", "data"),
)
def render_tab(tab, sig, holdings, settings):
    tv = (settings or {}).get("total_value") or 0
    if   tab == "overview":  return build_overview(sig, holdings, tv)
    elif tab == "signals":   return build_signals(sig, tv)
    elif tab == "rebalance": return build_rebalance(sig, holdings, tv)
    elif tab == "holdings":  return build_holdings(sig, holdings, tv)
    return html.Div("Unknown tab")


# ═══════════════════════════════════════════════════════════════════════
#  TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════
def build_overview(sig, holdings, tv):
    sig      = sig or {}
    assets   = sig.get("assets", {})
    bench3m  = sig.get("bench3m", 0) or 0
    as_of    = sig.get("as_of", "—")
    n_above  = sig.get("n_above_sma", 0)
    cash_fw  = (assets.get(U.CASH_TICKER) or {}).get("final_weight", 0) or 0

    # P&L total
    total_pnl = None
    if holdings and assets:
        s, has = 0, False
        for t, h in (holdings or {}).items():
            p = (assets.get(t) or {}).get("price")
            if p and h and h.get("shares") and h.get("avg_cost"):
                s += (p - h["avg_cost"]) * h["shares"]; has = True
        if has:
            total_pnl = s

    # Total current value
    cur_total = None
    if holdings and assets:
        s, has = 0, False
        for t, h in (holdings or {}).items():
            p = (assets.get(t) or {}).get("price")
            if p and h and h.get("shares"):
                s += p * h["shares"]; has = True
        if has:
            cur_total = s

    # KPI bar
    kpis = html.Div(
        style={"display": "flex", "gap": "12px", "marginBottom": "24px",
               "flexWrap": "wrap", "paddingTop": "20px"},
        children=[
            _kpi("Portfolio Value",  _fmt(tv) if tv else "Not set", YELLOW, "target", YELLOW),
            _kpi("Current Value",    _fmt(cur_total) if cur_total else "Enter holdings", ACCENT, as_of),
            _kpi("Unrealised P&L",
                 _fmt(total_pnl, sign=True) if total_pnl is not None else "—",
                 _pc(total_pnl), bar_color=_pc(total_pnl)),
            _kpi("Above SMA",        f"{n_above}/{len(U.RISK_TICKERS)}", ACCENT3,
                 "risk assets trending up", ACCENT3),
            _kpi("Cash / SHV",       f"{cash_fw*100:.1f}%", CASH_CLR,
                 _fmt(tv * cash_fw) if tv else "—", CASH_CLR),
            _kpi("Benchmark 3m",     _pct(bench3m),
                 _pc(bench3m), "eq-wt avg, floor 0", bar_color=_pc(bench3m)),
        ],
    )

    # ── Setup card ────────────────────────────────────────────────────
    setup = html.Div(style=CARD, children=[
        html.H3("Portfolio Setup", style={"margin": "0 0 14px", "fontSize": "12px",
                                          "color": ACCENT, "letterSpacing": "2px"}),
        html.Label("Total Portfolio Value ($)", style=LBL),
        dcc.Input(id="ov-total-value", type="number", min=0,
                  placeholder="e.g. 100000",
                  value=tv if tv else None,
                  style={**INP, "marginBottom": "12px"}),
        html.Button("Save", id="ov-save-btn", n_clicks=0, style=BTN),
        html.Div(id="ov-save-msg", style={"marginTop": "8px", "fontSize": "11px", "color": ACCENT}),
    ])

    # ── Weight pie ────────────────────────────────────────────────────
    labels, values, colors = [], [], []
    for i, t in enumerate(U.ALL_TICKERS):
        fw = (assets.get(t) or {}).get("final_weight", 0) or 0
        if fw > 0.0005:
            labels.append(U.disp(t))
            values.append(fw * 100)
            colors.append(CASH_CLR if t == U.CASH_TICKER else PIE_COLORS[i % len(PIE_COLORS)])

    pie = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=colors, line=dict(color=DARK_BG, width=2)),
        textfont=dict(size=11, color="#fff"),
        hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
        textinfo="label+percent",
    ))
    pie.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT), showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10), height=280,
        annotations=[dict(text=as_of, x=0.5, y=0.5,
                          font_size=10, font_color=MUTED, showarrow=False)],
    )

    # ── Signal summary rows ───────────────────────────────────────────
    rows = []
    for t in U.ALL_TICKERS:
        a   = assets.get(t) or {}
        fw  = a.get("final_weight", 0) or 0
        above = a.get("above_sma", False)
        is_cash = t == U.CASH_TICKER
        sc  = CASH_CLR if is_cash else (GREEN if above else RED)
        sig_txt = "CASH" if is_cash else ("▲ BUY" if above else "▼ OUT")
        rows.append(html.Div(
            style={"display": "grid",
                   "gridTemplateColumns": "80px 50px 90px 80px 80px 90px",
                   "gap": "4px", "padding": "7px 0",
                   "borderBottom": f"1px solid {CARD_BORDER}",
                   "fontSize": "12px", "alignItems": "center",
                   "opacity": "1" if (fw > 0 or is_cash) else "0.45"},
            children=[
                html.Span(U.disp(t), style={"fontWeight": "700",
                                             "color": CASH_CLR if is_cash else (ACCENT if above else MUTED)}),
                html.Span(f"SMA-{a.get('sma_period','?')}", style={"fontSize": "9px", "color": MUTED}),
                html.Span(_fmt(a.get("price")), style={"color": TEXT}),
                html.Span(sig_txt, style={"color": sc, "fontWeight": "700", "fontSize": "11px"}),
                html.Span(_pct((a.get("ret3m_bench_ratio") or 0) - 1 if a.get("ret3m_bench_ratio") else None,1),
                          style={"color": _pc(a.get("ret3m_bench_ratio", 1) - 1 if a.get("ret3m_bench_ratio") else None),
                                 "fontSize": "11px"}),
                html.Span(f"{fw*100:.1f}%",
                          style={"fontWeight": "700",
                                 "color": CASH_CLR if is_cash else (ACCENT3 if fw > 0 else MUTED)}),
            ],
        ))

    summary = html.Div(style=CARD, children=[
        html.H3("Position Summary", style={"margin": "0 0 10px", "fontSize": "12px",
                                            "color": MUTED, "letterSpacing": "2px"}),
        html.Div(style={"display": "grid",
                        "gridTemplateColumns": "80px 50px 90px 80px 80px 90px",
                        "gap": "4px", "padding": "4px 0",
                        "borderBottom": f"1px solid {CARD_BORDER}",
                        "fontSize": "10px", "color": MUTED, "letterSpacing": "0.8px",
                        "textTransform": "uppercase"},
                 children=[html.Span(c) for c in
                            ["Ticker", "Gate", "Price", "Signal", "vs Bench", "Weight"]]),
        *rows,
    ])

    return html.Div([
        kpis,
        html.Div(style={"display": "grid", "gridTemplateColumns": "280px 1fr",
                        "gap": "20px", "alignItems": "start"},
                 children=[
                     html.Div([setup]),
                     html.Div([
                         html.Div(style=CARD, children=[
                             html.H3("Current Weights",
                                     style={"margin": "0 0 8px", "fontSize": "12px",
                                            "color": MUTED, "letterSpacing": "2px"}),
                             dcc.Graph(figure=pie, config={"displayModeBar": False}),
                         ]),
                         summary,
                     ]),
                 ]),
    ])


# ═══════════════════════════════════════════════════════════════════════
#  TAB 2 — SIGNALS
# ═══════════════════════════════════════════════════════════════════════
def build_signals(sig, tv):
    sig    = sig or {}
    assets = sig.get("assets", {})
    bench3m= sig.get("bench3m", 0) or 0
    as_of  = sig.get("as_of", "—")
    fw_map = sig.get("final_weights", {})

    freed_total = (sig.get("freed_weight_total") or 0)
    freed_outp  = (sig.get("freed_to_outperf")  or 0)
    cash_pre    = (sig.get("cash_pre_norm")      or 0)
    base_wt     = (sig.get("base_weight")        or U.BASE_WEIGHT)
    n_assets    = (sig.get("n_assets")           or U.N_ASSETS)
    cash_fw     = (fw_map.get(U.CASH_TICKER)     or 0)

    kpis = html.Div(
        style={"display": "flex", "gap": "12px", "marginBottom": "24px",
               "flexWrap": "wrap", "paddingTop": "20px"},
        children=[
            _kpi("Signal Date",    as_of,  TEXT, "last market close"),
            _kpi("Above SMA",      f"{sig.get('n_above_sma',0)}/{len(U.RISK_TICKERS)}",
                 ACCENT3, "risk assets trending up", ACCENT3),
            _kpi("Base Weight",    f"{base_wt*100:.2f}%", TEXT,
                 f"1/{n_assets} assets (incl SHV)"),
            _kpi("Benchmark 3m",   _pct(bench3m), _pc(bench3m),
                 "eq-wt avg all 9 (floor 0)", _pc(bench3m)),
            _kpi("Freed Weight",   f"{freed_total*100:.1f}%", ACCENT4,
                 f"→ outperf {freed_outp*100:.1f}% → cash {cash_pre*100:.1f}%", ACCENT4),
            _kpi("SHV (pre-norm)", f"{cash_pre*100:.1f}%", CASH_CLR,
                 f"final: {cash_fw*100:.1f}%  {_fmt(tv*cash_fw) if tv else '—'}", CASH_CLR),
        ],
    )

    # ── Full signal + weight-breakdown table ──────────────────────────
    # Columns:  Ticker | Gate | Price | % vs SMA | 3m Ret | Ratio | Raw(pre) | Top-up | Raw(post) | Final
    col = "72px 48px 82px 72px 72px 60px 75px 65px 78px 72px"
    hdr_labels = ["Ticker","Gate","Price","% vs SMA","3m Ret",
                  "Ratio","Raw(pre)","Top-up","Raw(post)","Final Wt"]
    hdr = html.Div(
        style={"display": "grid", "gridTemplateColumns": col, "gap": "4px",
               "padding": "6px 0", "borderBottom": f"1px solid {CARD_BORDER}",
               "fontSize": "10px", "color": MUTED,
               "letterSpacing": "0.7px", "textTransform": "uppercase"},
        children=[html.Span(c) for c in hdr_labels],
    )

    # Legend for driver tags
    driver_color = {
        "outperformer": ACCENT3,
        "capped":       YELLOW,
        "underperformer": ACCENT,
        "floor":        RED,
        "below_sma":    RED,
        "cash":         CASH_CLR,
    }
    driver_label = {
        "outperformer":  "↑OVER",
        "capped":        "⚑CAP",
        "underperformer":"↓UNDER",
        "floor":         "⊘FLOOR",
        "below_sma":     "✗SMA",
        "cash":          "CASH",
    }

    tbl_rows = []
    for t in U.ALL_TICKERS:
        a       = assets.get(t) or {}
        above   = a.get("above_sma", False)
        is_cash = t == U.CASH_TICKER
        price   = a.get("price")
        sma_v   = a.get("sma")
        pct_sma = ((price / sma_v - 1) * 100) if (price and sma_v) else None
        ret3m   = a.get("ret3m", 0) or 0
        ratio   = a.get("ratio")        # ret3m / bench3m
        rw_pre  = a.get("raw_weight_pre", 0) or 0
        topup   = a.get("topup", 0) or 0
        rw_post = a.get("raw_weight", 0) or 0
        fw      = a.get("final_weight", 0) or 0
        driver  = a.get("driver", "")
        dc      = driver_color.get(driver, MUTED)
        dl      = driver_label.get(driver, "")

        # colour the final weight cell
        fw_color = CASH_CLR if is_cash else (GREEN if fw > base_wt else (YELLOW if fw > 0 else MUTED))

        tbl_rows.append(html.Div(
            style={"display": "grid", "gridTemplateColumns": col, "gap": "4px",
                   "padding": "8px 0", "borderBottom": f"1px solid {CARD_BORDER}",
                   "fontSize": "12px", "alignItems": "center",
                   "opacity": "1" if (above or is_cash) else "0.4"},
            children=[
                # Ticker + driver tag
                html.Div([
                    html.Span(U.disp(t), style={"fontWeight": "700",
                        "color": CASH_CLR if is_cash else (ACCENT if above else MUTED)}),
                    html.Div(dl, style={"fontSize": "9px", "color": dc,
                                        "fontWeight": "700", "letterSpacing": "0.5px"}),
                ]),
                # Gate
                html.Span(
                    "—" if is_cash else ("▲" if above else "▼"),
                    style={"color": MUTED if is_cash else (GREEN if above else RED),
                           "fontWeight": "700"}),
                html.Span(_fmt(price) if price else "—"),
                html.Span(f"{pct_sma:+.2f}%" if pct_sma is not None else "—",
                          style={"color": _pc(pct_sma), "fontWeight": "600"}),
                html.Span(_pct(ret3m, 1),
                          style={"color": _pc(ret3m)}),
                # ratio = ret3m / bench  (blank for cash and below-SMA)
                html.Span(
                    f"{ratio:.2f}×" if ratio is not None else "—",
                    style={"color": YELLOW if (ratio or 0) >= 2.0
                           else (ACCENT3 if (ratio or 0) > 1.0
                                 else (ACCENT if (ratio or 0) > 0 else MUTED)),
                           "fontWeight": "600"}),
                # raw weight before top-up
                html.Span(
                    f"{rw_pre*100:.2f}%" if (above and not is_cash) else "—",
                    style={"color": MUTED}),
                # top-up amount
                html.Span(
                    f"+{topup*100:.2f}%" if topup > 0.0001 else "—",
                    style={"color": ACCENT3, "fontWeight": "700" if topup > 0.0001 else "400"}),
                # raw weight after top-up (= what goes into normaliser)
                html.Span(
                    f"{rw_post*100:.2f}%" if (above or is_cash) else "—",
                    style={"color": ACCENT4 if (above and not is_cash) else CASH_CLR}),
                # final normalised weight
                html.Span(f"{fw*100:.2f}%",
                          style={"color": fw_color, "fontWeight": "800"}),
            ],
        ))

    # Legend row
    legend = html.Div(
        style={"display": "flex", "gap": "16px", "padding": "10px 0 0",
               "fontSize": "10px", "flexWrap": "wrap"},
        children=[
            html.Span([html.Span("↑OVER ", style={"color": ACCENT3, "fontWeight": "700"}),
                       "ratio > 1  (receives freed weight top-up)"]),
            html.Span([html.Span("⚑CAP ", style={"color": YELLOW, "fontWeight": "700"}),
                       "ratio ≥ 2 (hard cap at 2× base)"]),
            html.Span([html.Span("↓UNDER ", style={"color": ACCENT, "fontWeight": "700"}),
                       "0 < ratio < 1"]),
            html.Span([html.Span("⊘FLOOR ", style={"color": RED, "fontWeight": "700"}),
                       "ratio ≤ 0 → 0%"]),
            html.Span([html.Span("✗SMA ", style={"color": RED, "fontWeight": "700"}),
                       "below SMA → excluded"]),
        ],
    )

    sig_card = html.Div(style=CARD, children=[
        html.H3("Signal Scanner — Full Weight Calculation",
                style={"margin": "0 0 4px", "fontSize": "12px",
                       "color": ACCENT3, "letterSpacing": "2px"}),
        html.P(
            f"n_assets={n_assets}  |  base={base_wt*100:.2f}%  |  "
            f"bench={bench3m*100:+.2f}% (eq-wt all {n_assets}, floor 0)  |  "
            f"Ratio = 3m_ret / bench  |  Raw(pre) = clamp(ratio,0,2)×base  |  "
            f"Top-up from freed pool → ratio>1 assets  |  then normalise",
            style={"fontSize": "11px", "color": MUTED, "margin": "0 0 10px",
                   "lineHeight": "1.6"},
        ),
        hdr, *tbl_rows, legend,
    ])

    # ── 3m return bar chart ───────────────────────────────────────────
    tickers_sorted = sorted(
        U.ALL_TICKERS,
        key=lambda t: -(sig.get("all_returns", {}).get(t) or 0),
    )
    bt = [U.disp(t) for t in tickers_sorted]
    bv = [(sig.get("all_returns", {}).get(t) or 0) * 100 for t in tickers_sorted]
    above_set = set(sig.get("above_sma", []))
    bc = [CASH_CLR if t == U.CASH_TICKER
          else (GREEN if t in above_set else RED)
          for t in tickers_sorted]

    bar = go.Figure(go.Bar(
        x=bt, y=bv, marker_color=bc,
        text=[f"{v:+.1f}%" for v in bv], textposition="outside",
        textfont=dict(size=10, color=TEXT),
        hovertemplate="<b>%{x}</b><br>3m: %{y:+.2f}%<extra></extra>",
    ))
    bench_pct = bench3m * 100
    bar.add_hline(y=bench_pct, line_color=ACCENT4, line_width=1.5, line_dash="dot",
                  annotation_text=f"bench {bench_pct:+.1f}%",
                  annotation_font_color=ACCENT4, annotation_font_size=10,
                  annotation_position="top right")
    bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT), xaxis=dict(showgrid=False, color=MUTED),
        yaxis=dict(showgrid=True, gridcolor=CARD_BORDER, color=MUTED, ticksuffix="%"),
        margin=dict(t=30, b=10, l=10, r=10), height=300, bargap=0.3,
    )

    bar_card = html.Div(style=CARD, children=[
        html.H3("3-Month Returns vs Benchmark",
                style={"margin": "0 0 4px", "fontSize": "12px",
                       "color": MUTED, "letterSpacing": "2px"}),
        html.P("Green = above SMA  |  Red = below SMA  |  Grey = SHV  |  Orange line = benchmark",
               style={"fontSize": "11px", "color": MUTED, "margin": "0 0 8px"}),
        dcc.Graph(figure=bar, config={"displayModeBar": False}),
    ])

    # ── Final weight bar ──────────────────────────────────────────────
    fw_tickers = [t for t in U.ALL_TICKERS if (fw_map.get(t) or 0) > 0.001]
    fw_labels  = [U.disp(t) for t in fw_tickers]
    fw_vals    = [(fw_map.get(t) or 0) * 100 for t in fw_tickers]
    fw_colors  = [CASH_CLR if t == U.CASH_TICKER
                  else PIE_COLORS[i % len(PIE_COLORS)] for i, t in enumerate(fw_tickers)]
    fw_bar = go.Figure(go.Bar(
        x=fw_labels, y=fw_vals, marker_color=fw_colors,
        text=[f"{v:.1f}%" for v in fw_vals], textposition="outside",
        textfont=dict(size=10, color=TEXT),
        hovertemplate="<b>%{x}</b><br>Weight: %{y:.2f}%<extra></extra>",
    ))
    fw_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT), xaxis=dict(showgrid=False, color=MUTED),
        yaxis=dict(showgrid=True, gridcolor=CARD_BORDER, color=MUTED, ticksuffix="%"),
        margin=dict(t=30, b=10, l=10, r=10), height=280, bargap=0.3,
    )
    fw_card = html.Div(style=CARD, children=[
        html.H3("Final Normalised Weights",
                style={"margin": "0 0 8px", "fontSize": "12px",
                       "color": MUTED, "letterSpacing": "2px"}),
        dcc.Graph(figure=fw_bar, config={"displayModeBar": False}),
    ])

    # ── Weight-flow trace (audit of every calculation step) ───────────
    all_ret     = sig.get("all_returns", {})
    above_set2  = set(sig.get("above_sma", []))
    risk_assigned = sum(
        (assets.get(t) or {}).get("raw_weight_pre", 0) or 0
        for t in U.RISK_TICKERS if t in above_set2
    )

    flow_rows = []
    for t in U.ALL_TICKERS:
        a       = assets.get(t) or {}
        ratio   = a.get("ratio")
        rw_pre  = a.get("raw_weight_pre", 0) or 0
        topup   = a.get("topup", 0) or 0
        rw_post = a.get("raw_weight", 0) or 0
        fw      = a.get("final_weight", 0) or 0
        is_cash = t == U.CASH_TICKER
        above   = a.get("above_sma", False)

        if is_cash:
            formula = (f"freed_rem={cash_pre*100:.2f}%  →  "
                       f"norm={fw*100:.2f}%")
        elif not above:
            formula = "below SMA  →  0%"
        elif ratio is not None:
            topup_str = (f"  +topup {topup*100:.2f}%={rw_post*100:.2f}%"
                         if topup > 0.0001 else "")
            formula = (f"clamp({ratio:.3f},0,2)×{base_wt*100:.2f}%"
                       f"={rw_pre*100:.2f}%{topup_str}  →  norm={fw*100:.2f}%")
        else:
            formula = "—"

        flow_rows.append(html.Div(
            style={"display": "grid", "gridTemplateColumns": "72px 1fr",
                   "gap": "8px", "padding": "6px 0",
                   "borderBottom": f"1px solid {CARD_BORDER}",
                   "fontSize": "11px", "alignItems": "start",
                   "opacity": "1" if (above or is_cash) else "0.4"},
            children=[
                html.Span(U.disp(t),
                          style={"fontWeight": "700",
                                 "color": CASH_CLR if is_cash else (ACCENT if above else MUTED)}),
                html.Span(formula,
                          style={"color": MUTED, "fontFamily": "monospace"}),
            ],
        ))

    trace_card = html.Div(style=CARD, children=[
        html.H3("Weight Calculation Trace",
                style={"margin": "0 0 4px", "fontSize": "12px",
                       "color": MUTED, "letterSpacing": "2px"}),
        html.P(
            f"bench={bench3m*100:+.3f}%  |  "
            f"risk_assigned={risk_assigned*100:.2f}%  |  "
            f"freed={freed_total*100:.2f}%  →  "
            f"to_outperf={freed_outp*100:.2f}%  →  "
            f"cash_pre_norm={cash_pre*100:.2f}%",
            style={"fontSize": "11px", "color": ACCENT4,
                   "margin": "0 0 10px", "fontFamily": "monospace"},
        ),
        *flow_rows,
    ])

    return html.Div([
        kpis, sig_card, trace_card,
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr",
                        "gap": "16px"},
                 children=[bar_card, fw_card]),
    ])


# ═══════════════════════════════════════════════════════════════════════
#  TAB 3 — REBALANCE
# ═══════════════════════════════════════════════════════════════════════
def build_rebalance(sig, holdings, tv):
    sig  = sig or {}
    if not tv:
        return html.Div(
            html.Div("Set your portfolio value on the Overview tab first.",
                     style={"color": MUTED, "textAlign": "center",
                            "padding": "40px", "fontSize": "13px"}),
            style={"paddingTop": "20px"},
        )

    rows = U.compute_rebalance(sig, holdings or {}, tv)

    # KPIs
    buy_rows  = [r for r in rows if not r["is_cash"] and r["above_sma"]]
    sell_rows = [r for r in rows if not r["is_cash"] and not r["above_sma"]]
    total_pnl = sum(r["pnl"] for r in rows if r["pnl"] is not None)
    total_buys= sum(r["delta_val"] for r in rows
                    if r["delta_val"] is not None and r["delta_val"] > 0)
    total_sells=sum(r["delta_val"] for r in rows
                    if r["delta_val"] is not None and r["delta_val"] < 0)

    kpis = html.Div(
        style={"display": "flex", "gap": "12px", "marginBottom": "24px",
               "flexWrap": "wrap", "paddingTop": "20px"},
        children=[
            _kpi("Total Value",     _fmt(tv),             YELLOW, "target",       YELLOW),
            _kpi("Positions",       f"{len(buy_rows)}",   ACCENT3,"active (above SMA)", ACCENT3),
            _kpi("In Cash / SHV",   f"{len(sell_rows)}", RED,    "below SMA → exit", RED),
            _kpi("Total to Buy",    _fmt(total_buys),     GREEN,  bar_color=GREEN),
            _kpi("Total to Sell",   _fmt(total_sells),    RED,    bar_color=RED),
            _kpi("Unrealised P&L",
                 _fmt(total_pnl, sign=True) if total_pnl else "—",
                 _pc(total_pnl), bar_color=_pc(total_pnl)),
        ],
    )

    col = "80px 60px 90px 90px 90px 100px 90px 100px 100px"
    hdr = html.Div(
        style={"display": "grid", "gridTemplateColumns": col, "gap": "4px",
               "padding": "6px 0", "borderBottom": f"1px solid {CARD_BORDER}",
               "fontSize": "10px", "color": MUTED,
               "letterSpacing": "0.8px", "textTransform": "uppercase"},
        children=[html.Span(c) for c in
                  ["Ticker", "Signal", "Price", "Weight", "Target $",
                   "Current $", "Δ Value", "Δ Shares", "Unreal P&L"]],
    )

    tbl_rows = []
    for r in rows:
        is_cash   = r["is_cash"]
        above     = r["above_sma"]
        sc        = CASH_CLR if is_cash else (GREEN if above else RED)
        sig_label = ("CASH" if is_cash else ("▲ HOLD/BUY" if above else "▼ SELL/EXIT"))

        tbl_rows.append(html.Div(
            style={"display": "grid", "gridTemplateColumns": col, "gap": "4px",
                   "padding": "9px 0", "borderBottom": f"1px solid {CARD_BORDER}",
                   "fontSize": "12px", "alignItems": "center",
                   "opacity": "1" if (above or is_cash) else "0.5"},
            children=[
                html.Span(r["display"],
                          style={"fontWeight": "700",
                                 "color": CASH_CLR if is_cash else (ACCENT if above else MUTED)}),
                html.Span(sig_label, style={"color": sc, "fontWeight": "700", "fontSize": "11px"}),
                html.Span(_fmt(r["price"]) if r["price"] else "—"),
                html.Span(f"{r['final_weight']*100:.2f}%", style={"color": MUTED}),
                html.Span(_fmt(r["target_val"]), style={"color": ACCENT, "fontWeight": "600"}),
                html.Span(_fmt(r["cur_val"]) if r["cur_val"] is not None else "—",
                          style={"color": MUTED}),
                html.Span(_fmt(r["delta_val"], sign=True) if r["delta_val"] is not None else "—",
                          style={"color": _pc(r["delta_val"]), "fontWeight": "600"}),
                html.Span(f"{r['delta_shares']:+.4f}" if r["delta_shares"] is not None else "—",
                          style={"color": _pc(r["delta_shares"]), "fontSize": "11px"}),
                html.Span(_fmt(r["pnl"], sign=True) if r["pnl"] is not None else "—",
                          style={"color": _pc(r["pnl"])}),
            ],
        ))

    reb_card = html.Div(style=CARD, children=[
        html.H3("Rebalance Engine",
                style={"margin": "0 0 4px", "fontSize": "12px",
                       "color": ACCENT4, "letterSpacing": "2px"}),
        html.P("Δ Value / Δ Shares = amount to BUY (+) or SELL (−) to reach target weights. "
               "Below-SMA assets → target = 0 (full exit).",
               style={"fontSize": "11px", "color": MUTED, "margin": "0 0 12px"}),
        hdr, *tbl_rows,
    ])

    # ── Delta bar chart ───────────────────────────────────────────────
    chart_rows = [r for r in rows if r["delta_val"] is not None and abs(r["delta_val"]) > 1]
    chart_rows.sort(key=lambda r: r["delta_val"])
    dx = [r["display"] for r in chart_rows]
    dy = [r["delta_val"] for r in chart_rows]
    dc = [GREEN if v >= 0 else RED for v in dy]

    delta_fig = go.Figure(go.Bar(
        x=dx, y=dy, marker_color=dc,
        text=[_fmt(v, sign=True) for v in dy], textposition="outside",
        textfont=dict(size=10, color=TEXT),
        hovertemplate="<b>%{x}</b><br>Δ %{y:+,.2f}<extra></extra>",
    ))
    delta_fig.add_hline(y=0, line_color=CARD_BORDER, line_width=1.5)
    delta_fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT), xaxis=dict(showgrid=False, color=MUTED),
        yaxis=dict(showgrid=True, gridcolor=CARD_BORDER, color=MUTED),
        margin=dict(t=20, b=20, l=10, r=10), height=300, bargap=0.3,
    )
    delta_card = html.Div(style=CARD, children=[
        html.H3("Rebalance Δ by Position",
                style={"margin": "0 0 8px", "fontSize": "12px",
                       "color": MUTED, "letterSpacing": "2px"}),
        dcc.Graph(figure=delta_fig, config={"displayModeBar": False}),
    ])

    return html.Div([kpis, reb_card, delta_card])


# ═══════════════════════════════════════════════════════════════════════
#  TAB 4 — HOLDINGS
# ═══════════════════════════════════════════════════════════════════════
def build_holdings(sig, holdings, tv):
    sig    = sig or {}
    assets = sig.get("assets", {})

    # Computed P&L summary
    total_cost  = None
    total_cur   = None
    total_pnl   = None
    have_data   = False
    for t in U.ALL_TICKERS:
        h = (holdings or {}).get(t) or {}
        p = (assets.get(t) or {}).get("price")
        sh= h.get("shares")
        ac= h.get("avg_cost")
        if sh and p:
            total_cur = (total_cur or 0) + sh * p
            if ac:
                total_cost = (total_cost or 0) + sh * ac
                total_pnl  = (total_pnl or 0) + (p - ac) * sh
            have_data = True

    kpis = html.Div(
        style={"display": "flex", "gap": "12px", "marginBottom": "24px",
               "flexWrap": "wrap", "paddingTop": "20px"},
        children=[
            _kpi("Current Value", _fmt(total_cur) if total_cur else "—", ACCENT, bar_color=ACCENT),
            _kpi("Cost Basis",    _fmt(total_cost) if total_cost else "—", MUTED),
            _kpi("Unrealised P&L",
                 _fmt(total_pnl, sign=True) if total_pnl is not None else "—",
                 _pc(total_pnl), bar_color=_pc(total_pnl)),
            _kpi("Return",
                 f"{total_pnl/total_cost*100:+.2f}%" if (total_pnl and total_cost) else "—",
                 _pc(total_pnl), bar_color=_pc(total_pnl)),
        ],
    )

    # Input form
    hdr_row = html.Div(
        style={"display": "grid", "gridTemplateColumns": "80px 110px 110px 90px 90px 90px",
               "gap": "8px", "marginBottom": "6px"},
        children=[html.Span("")]
        + [html.Span(h, style={**LBL, "marginBottom": "0"})
           for h in ["Shares Held", "Avg Cost ($)", "Cur Price", "Cur Value", "P&L"]],
    )

    input_rows = []
    for t in U.ALL_TICKERS:
        h    = (holdings or {}).get(t) or {}
        a    = assets.get(t) or {}
        price= a.get("price")
        sh   = h.get("shares")
        ac   = h.get("avg_cost")
        cur_v= (sh * price) if (sh and price) else None
        pnl  = ((price - ac) * sh) if (sh and price and ac) else None
        is_cash = t == U.CASH_TICKER

        input_rows.append(html.Div(
            style={"display": "grid",
                   "gridTemplateColumns": "80px 110px 110px 90px 90px 90px",
                   "gap": "8px", "marginBottom": "10px", "alignItems": "center"},
            children=[
                html.Div([
                    html.Span(U.disp(t),
                              style={"fontWeight": "700",
                                     "color": CASH_CLR if is_cash else ACCENT,
                                     "fontSize": "13px"}),
                    html.Div(f"SMA-{a.get('sma_period','?')}",
                             style={"fontSize": "9px", "color": MUTED}),
                ]),
                dcc.Input(id={"type": "shares-input", "ticker": t}, type="number", min=0,
                          placeholder="0",
                          value=h.get("shares"),
                          style={**INP, "fontSize": "12px", "padding": "6px 8px"}),
                dcc.Input(id={"type": "avgcost-input", "ticker": t}, type="number", min=0,
                          placeholder="0.00",
                          value=h.get("avg_cost"),
                          style={**INP, "fontSize": "12px", "padding": "6px 8px"}),
                html.Span(_fmt(price) if price else "—", style={"fontSize": "12px", "color": MUTED}),
                html.Span(_fmt(cur_v) if cur_v else "—",
                          style={"fontSize": "12px", "color": ACCENT}),
                html.Span(_fmt(pnl, sign=True) if pnl is not None else "—",
                          style={"fontSize": "12px", "color": _pc(pnl)}),
            ],
        ))

    holdings_form = html.Div(style=CARD, children=[
        html.H3("Holdings Input",
                style={"margin": "0 0 4px", "fontSize": "12px",
                       "color": ACCENT2, "letterSpacing": "2px"}),
        html.P("Enter shares and average cost. Current price is pulled live.",
               style={"fontSize": "11px", "color": MUTED, "margin": "0 0 14px"}),
        hdr_row, *input_rows,
        html.Button("Save Holdings", id="save-holdings-btn", n_clicks=0,
                    style={**BTN2, "marginTop": "10px", "width": "200px"}),
        html.Div(id="holdings-save-msg",
                 style={"marginTop": "8px", "fontSize": "11px", "color": ACCENT2}),
    ])

    # P&L detail table (read-only)
    col2 = "80px 90px 90px 90px 90px 90px 90px"
    pnl_rows_display = []
    for t in U.ALL_TICKERS:
        h     = (holdings or {}).get(t) or {}
        a     = assets.get(t) or {}
        price = a.get("price")
        sh    = h.get("shares")
        ac    = h.get("avg_cost")
        if not sh:
            continue
        cur_v   = sh * price if price else None
        cost_v  = sh * ac    if ac    else None
        pnl_v   = ((price - ac) * sh) if (price and ac) else None
        pnl_pct = (pnl_v / cost_v) if (pnl_v is not None and cost_v) else None
        fw      = (a.get("final_weight") or 0) * 100

        pnl_rows_display.append(html.Div(
            style={"display": "grid", "gridTemplateColumns": col2, "gap": "4px",
                   "padding": "8px 0", "borderBottom": f"1px solid {CARD_BORDER}",
                   "fontSize": "12px", "alignItems": "center"},
            children=[
                html.Span(U.disp(t),
                          style={"fontWeight": "700",
                                 "color": CASH_CLR if t == U.CASH_TICKER else ACCENT}),
                html.Span(f"{sh:,.4f}", style={"color": MUTED}),
                html.Span(_fmt(ac) if ac else "—", style={"color": MUTED}),
                html.Span(_fmt(price) if price else "—"),
                html.Span(_fmt(cost_v) if cost_v else "—", style={"color": MUTED}),
                html.Span(_fmt(cur_v) if cur_v else "—", style={"color": ACCENT}),
                html.Span(_fmt(pnl_v, sign=True) if pnl_v is not None else "—",
                          style={"color": _pc(pnl_v), "fontWeight": "600"}),
            ],
        ))

    pnl_card = html.Div(style=CARD, children=[
        html.H3("P&L Summary",
                style={"margin": "0 0 10px", "fontSize": "12px",
                       "color": MUTED, "letterSpacing": "2px"}),
        html.Div(style={"display": "grid", "gridTemplateColumns": col2, "gap": "4px",
                        "padding": "4px 0", "borderBottom": f"1px solid {CARD_BORDER}",
                        "fontSize": "10px", "color": MUTED,
                        "letterSpacing": "0.8px", "textTransform": "uppercase"},
                 children=[html.Span(c) for c in
                            ["Ticker", "Shares", "Avg Cost", "Price", "Cost", "Value", "P&L"]]),
        *(pnl_rows_display if pnl_rows_display
          else [html.Div("Enter holdings above to see P&L.",
                         style={"color": MUTED, "padding": "16px 0",
                                "fontSize": "12px"})]),
    ])

    return html.Div([kpis, holdings_form, pnl_card])


# ═══════════════════════════════════════════════════════════════════════
#  HTML SHELL
# ═══════════════════════════════════════════════════════════════════════
app.index_string = """<!DOCTYPE html>
<html><head>
  {%metas%}<title>{%title%}</title>{%favicon%}{%css%}
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; }
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: #080c14; }
    ::-webkit-scrollbar-thumb { background: #1e2d45; border-radius: 3px; }
    input[type=number]::-webkit-inner-spin-button { opacity: 0.3; }
    input::placeholder { color: #374151 !important; }
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
