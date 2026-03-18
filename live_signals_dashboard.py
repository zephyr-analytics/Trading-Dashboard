"""
╔═══════════════════════════════════════════════════════════════════════╗
║  LIVE PORTFOLIO DASHBOARD  —  Plotly Dash                             ║
║  Tab 1: Overview  |  Tab 2: Core  |  Tab 3: Momentum  |  Tab 4: Titans║
╚═══════════════════════════════════════════════════════════════════════╝

SETUP:  pip install dash plotly yfinance pandas numpy
RUN:    python portfolio_dashboard.py  →  http://127.0.0.1:8050
"""

import numpy as np
import plotly.graph_objects as go
from datetime import datetime

import dash
from dash import dcc, html, Input, Output, State

import utilities

# ── convenience aliases so tab-builder code stays readable ─────────────
_fmt       = utilities.fmt
_pcolor    = utilities.pcolor
_kpi       = utilities.kpi_card

# ── style shorthands ──────────────────────────────────────────────────
CARD       = utilities.CARD
INP        = utilities.INP
BTN        = utilities.BTN
BTN2       = utilities.BTN2
LBL        = utilities.LBL
TAB_BASE   = utilities.TAB_BASE

# ── colour shorthands ─────────────────────────────────────────────────
DARK_BG    = utilities.DARK_BG
CARD_BG    = utilities.CARD_BG
CARD_BORDER= utilities.CARD_BORDER
ACCENT     = utilities.ACCENT
ACCENT2    = utilities.ACCENT2
ACCENT3    = utilities.ACCENT3
ACCENT4    = utilities.ACCENT4
ACCENT5    = utilities.ACCENT5
RED        = utilities.RED
GREEN      = utilities.GREEN
YELLOW     = utilities.YELLOW
TEXT       = utilities.TEXT
MUTED      = utilities.MUTED
CASH_CLR   = utilities.CASH_CLR
PIE_COLORS = utilities.PIE_COLORS

# ── portfolio constants ───────────────────────────────────────────────
CORE_PORTFOLIO        = utilities.CORE_PORTFOLIO
CORE_TICKERS          = utilities.CORE_TICKERS
MOM_TOP_N             = utilities.MOM_TOP_N
MOM_SMA_PERIOD        = utilities.MOM_SMA_PERIOD
MOM_TARGET_VOL        = utilities.MOM_TARGET_VOL
DOW_TITANS            = utilities.DOW_TITANS
TITANS_EMA_PERIOD     = utilities.TITANS_EMA_PERIOD
TITANS_ACWI_SMA_PERIOD= utilities.TITANS_ACWI_SMA_PERIOD   # circuit breaker
CASH_INSTRUMENTS      = utilities.CASH_INSTRUMENTS
CASH_LABEL            = utilities.CASH_LABEL
CASH_WEIGHT_EACH      = utilities.CASH_WEIGHT_EACH

_SAVED = utilities.load_saved()

# ═══════════════════════════════════════════════════════════════════════
#  APP INIT
# ═══════════════════════════════════════════════════════════════════════
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Portfolio Dashboard"

app.layout = html.Div(
    style={"backgroundColor": DARK_BG, "minHeight": "100vh",
           "fontFamily": "'Inter','Segoe UI',sans-serif", "color": TEXT},
    children=[
        # ── stores ──
        dcc.Store(id="core-market",    data={}),
        dcc.Store(id="mom-signal",     data={}),
        dcc.Store(id="titans-market",  data=[]),
        dcc.Store(id="holdings-store", data=_SAVED.get("holdings", {})),
        dcc.Store(id="settings-store", data={
            "total_value": _SAVED.get("total_value"),
            "core_pct":    _SAVED.get("core_pct"),
            "mom_pct":     _SAVED.get("mom_pct"),
            "titans_pct":  _SAVED.get("titans_pct"),
            "cash_pct":    _SAVED.get("cash_pct"),
        }),
        dcc.Store(id="cash-market", data={}),
        dcc.Interval(id="interval", interval=60_000, n_intervals=0, disabled=False),

        # ── header ──
        html.Div(
            style={"background": f"linear-gradient(135deg,{CARD_BG} 0%,#0f172a 100%)",
                   "borderBottom": f"1px solid {CARD_BORDER}",
                   "padding": "16px 32px", "display": "flex",
                   "alignItems": "center", "justifyContent": "space-between"},
            children=[
                html.Div([
                    html.Span("◈ ", style={"color": ACCENT, "fontSize": "20px"}),
                    html.Span("PORTFOLIO DASHBOARD",
                              style={"fontSize": "17px", "fontWeight": "800", "letterSpacing": "3px"}),
                ]),
                html.Div(id="last-updated", style={"color": MUTED, "fontSize": "12px"}),
            ],
        ),

        # ── tabs ──
        html.Div(
            style={"maxWidth": "1600px", "margin": "0 auto", "padding": "24px 24px 0"},
            children=[
                dcc.Tabs(id="main-tabs", value="overview",
                         style={"borderBottom": f"1px solid {CARD_BORDER}"},
                         children=[
                             dcc.Tab(label="◉  OVERVIEW",       value="overview",
                                     style=TAB_BASE, selected_style=utilities.tab_sel(ACCENT)),
                             dcc.Tab(label="⬡  CORE PORTFOLIO", value="core",
                                     style=TAB_BASE, selected_style=utilities.tab_sel(ACCENT2)),
                             dcc.Tab(label="⚡  MOMENTUM",       value="momentum",
                                     style=TAB_BASE, selected_style=utilities.tab_sel(ACCENT4)),
                             dcc.Tab(label="▲  DOW TITANS",      value="titans",
                                     style=TAB_BASE, selected_style=utilities.tab_sel(ACCENT3)),
                             dcc.Tab(label="◎  CASH",            value="cash",
                                     style=TAB_BASE, selected_style=utilities.tab_sel(ACCENT5)),
                         ]),
            ],
        ),

        html.Div(id="tab-content",
                 style={"maxWidth": "1600px", "margin": "0 auto", "padding": "0 24px 40px"}),
    ],
)


# ═══════════════════════════════════════════════════════════════════════
#  CALLBACK — refresh all market data
# ═══════════════════════════════════════════════════════════════════════
@app.callback(
    Output("core-market",   "data"),
    Output("mom-signal",    "data"),
    Output("titans-market", "data"),
    Output("cash-market",   "data"),
    Output("last-updated",  "children"),
    Input("interval", "n_intervals"),
    prevent_initial_call=False,
)
def refresh_all(_):
    core_mkt    = utilities.fetch_core_market(CORE_TICKERS)
    mom_prices  = utilities.fetch_momentum_data()
    mom_sig     = utilities.compute_momentum_signal(mom_prices)
    titans_p    = utilities.fetch_titans_prices()
    titans_rows = utilities.run_titans_signals(titans_p)
    cash_mkt    = utilities.fetch_cash_market()
    now         = datetime.now().strftime("⟳  %H:%M:%S")
    return core_mkt, utilities.make_mom_sig_json_safe(mom_sig), titans_rows, cash_mkt, now


# ═══════════════════════════════════════════════════════════════════════
#  CALLBACK — save overview settings
# ═══════════════════════════════════════════════════════════════════════
@app.callback(
    Output("settings-store", "data"),
    Output("ov-save-msg",    "children"),
    Input("ov-save-btn",     "n_clicks"),
    State("ov-total-value",  "value"),
    State("ov-core-pct",     "value"),
    State("ov-mom-pct",      "value"),
    State("ov-titans-pct",   "value"),
    State("ov-cash-pct",     "value"),
    State("holdings-store",  "data"),
    prevent_initial_call=True,
)
def save_overview(_, total, core_pct, mom_pct, titans_pct, cash_pct, holdings):
    if not total or float(total) <= 0:
        return {}, "⚠ Enter a valid portfolio value."
    tv = float(total)
    cp = float(core_pct)   if core_pct   else 0.0
    mp = float(mom_pct)    if mom_pct    else 0.0
    tp = float(titans_pct) if titans_pct else 0.0
    xp = float(cash_pct)   if cash_pct   else 0.0
    if cp + mp + tp + xp > 100:
        return {}, "⚠ Allocations exceed 100%."
    settings = {"total_value": tv, "core_pct": cp, "mom_pct": mp,
                "titans_pct": tp, "cash_pct": xp}
    utilities.save_all({**settings, "holdings": holdings or {}})
    return settings, (
        f"✓ Saved — Total: {_fmt(tv)}  "
        f"Core:{cp:.0f}%  Mom:{mp:.0f}%  Titans:{tp:.0f}%  Cash:{xp:.0f}%"
    )


# ═══════════════════════════════════════════════════════════════════════
#  CALLBACK — save core holdings
# ═══════════════════════════════════════════════════════════════════════
@app.callback(
    Output("holdings-store",    "data"),
    Output("core-holdings-msg", "children"),
    Input("save-holdings-btn",  "n_clicks"),
    [State({"type": "shares-input", "ticker": t}, "value") for t in CORE_TICKERS],
    [State({"type": "cost-input",   "ticker": t}, "value") for t in CORE_TICKERS],
    [State({"type": "curval-input", "ticker": t}, "value") for t in CORE_TICKERS],
    State("settings-store", "data"),
    prevent_initial_call=True,
)
def save_holdings(_, *args):
    n = len(CORE_TICKERS)
    sh, co, cv = args[0:n], args[n:2*n], args[2*n:3*n]
    settings   = args[3*n] or {}
    holdings   = {
        t: {
            "shares":        float(sh[i]) if sh[i] is not None else None,
            "avg_cost":      float(co[i]) if co[i] is not None else None,
            "current_value": float(cv[i]) if cv[i] is not None else None,
        }
        for i, t in enumerate(CORE_TICKERS)
    }
    utilities.save_all({**settings, "holdings": holdings})
    return holdings, "✓ Holdings saved to disk."


# ═══════════════════════════════════════════════════════════════════════
#  CALLBACK — render tab content
# ═══════════════════════════════════════════════════════════════════════
@app.callback(
    Output("tab-content", "children"),
    Input("main-tabs",      "value"),
    Input("core-market",    "data"),
    Input("mom-signal",     "data"),
    Input("titans-market",  "data"),
    Input("holdings-store", "data"),
    Input("settings-store", "data"),
    Input("cash-market",    "data"),
)
def render_tab(tab, core_mkt, mom_sig, titans_rows, holdings, settings, cash_mkt):
    s  = settings or {}
    tv = s.get("total_value")
    cp = s.get("core_pct",   0) or 0
    mp = s.get("mom_pct",    0) or 0
    tp = s.get("titans_pct", 0) or 0
    xp = s.get("cash_pct",   0) or 0
    if   tab == "overview":  return build_overview(core_mkt, mom_sig, titans_rows, holdings, tv, cp, mp, tp, xp, cash_mkt)
    elif tab == "core":      return build_core_tab(core_mkt, holdings, tv, cp)
    elif tab == "momentum":  return build_momentum_tab(mom_sig, tv, mp)
    elif tab == "titans":    return build_titans_tab(titans_rows, tv, tp)
    elif tab == "cash":      return build_cash_tab(cash_mkt, tv, xp)
    return html.Div("Unknown tab")


# ═══════════════════════════════════════════════════════════════════════
#  TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════
def build_overview(core_mkt, mom_sig, titans_rows, holdings, tv, cp, mp, tp, xp=0, cash_mkt=None):
    tv = tv or 0
    cp_f = cp/100; mp_f = mp/100; tp_f = tp/100; xp_f = xp/100
    other_f = max(0, 1 - cp_f - mp_f - tp_f - xp_f)

    core_alloc   = tv * cp_f
    mom_alloc    = tv * mp_f
    titans_alloc = tv * tp_f
    cash_alloc   = tv * xp_f
    other_alloc  = tv * other_f

    # Core P&L
    core_pnl = None
    if holdings and core_mkt:
        s, has = 0, False
        for t, h in holdings.items():
            p = (core_mkt.get(t) or {}).get("price")
            if p and h and h.get("shares") and h.get("avg_cost"):
                s += (p - h["avg_cost"]) * h["shares"]; has = True
        if has:
            core_pnl = s

    mom_winners = mom_sig.get("winners", []) if mom_sig else []
    mom_cash_w  = mom_sig.get("cash_weight", 1.0) if mom_sig else 1.0
    mom_as_of   = mom_sig.get("as_of", "—") if mom_sig else "—"

    # Titans circuit breaker — pull from rows
    titans_acwi_ok = next((r["acwi_above_sma"] for r in (titans_rows or []) if "acwi_above_sma" in r), True)
    eligible_t     = [r for r in (titans_rows or []) if r.get("signal") == "BUY"] if titans_acwi_ok else []
    n_elig_t       = len(eligible_t)

    n_above_core= sum(1 for t, cfg in CORE_PORTFOLIO.items()
                      if utilities.sma_signal((core_mkt or {}).get(t, {}), cfg["sma_period"]) == "BUY")

    # ── Pie ──
    pie_fig = go.Figure(go.Pie(
        labels=["Core Portfolio", "Momentum", "Dow Titans", "Cash", "Unallocated"],
        values=[cp, mp, tp, xp, other_f * 100], hole=0.55,
        marker=dict(colors=[ACCENT, ACCENT4, ACCENT3, ACCENT5, CASH_CLR],
                    line=dict(color=DARK_BG, width=2)),
        textfont=dict(size=12, color="#fff"),
        hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
        textinfo="label+percent",
    ))
    pie_fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT), showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10), height=300,
        annotations=[dict(text=_fmt(tv), x=0.5, y=0.5,
                          font_size=14, font_color=YELLOW, showarrow=False)],
    )

    # ── KPI bar ──
    kpis = html.Div(
        style={"display": "flex", "gap": "14px", "marginBottom": "24px", "flexWrap": "wrap"},
        children=[
            _kpi("Total Portfolio",   _fmt(tv) if tv else "Not set", YELLOW, bar_color=YELLOW),
            _kpi("Core Allocation",   _fmt(core_alloc),    ACCENT,  f"{cp:.1f}%",        ACCENT),
            _kpi("Momentum Alloc",    _fmt(mom_alloc),     ACCENT4, f"{mp:.1f}%",         ACCENT4),
            _kpi("Titans Allocation", _fmt(titans_alloc),  ACCENT3, f"{tp:.1f}%",         ACCENT3),
            _kpi("Unallocated",       _fmt(other_alloc),   MUTED,   f"{other_f*100:.1f}%"),
            _kpi("Core P&L",
                 _fmt(core_pnl, sign=True) if core_pnl is not None else "Enter holdings",
                 _pcolor(core_pnl), bar_color=_pcolor(core_pnl)),
            _kpi("Cash Allocation",   _fmt(cash_alloc),    ACCENT5, f"{xp:.1f}%",         ACCENT5),
        ],
    )

    # ── Allocation setup card ──
    setup = html.Div(style=CARD, children=[
        html.H3("Portfolio Allocation",
                style={"margin": "0 0 16px", "fontSize": "13px",
                       "color": ACCENT, "letterSpacing": "1px"}),
        html.Label("Total Portfolio Value ($)", style=LBL),
        dcc.Input(id="ov-total-value", type="number", min=0, placeholder="e.g. 250000",
                  value=tv if tv else None,
                  style={**INP, "marginBottom": "14px"}),
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr",
                        "gap": "12px", "marginBottom": "14px"}, children=[
            html.Div([html.Label("Core Portfolio (%)", style=LBL),
                      dcc.Input(id="ov-core-pct", type="number", min=0, max=100,
                                placeholder="e.g. 50", value=cp if cp else None, style=INP)]),
            html.Div([html.Label("Momentum (%)", style=LBL),
                      dcc.Input(id="ov-mom-pct", type="number", min=0, max=100,
                                placeholder="e.g. 30", value=mp if mp else None, style=INP)]),
            html.Div([html.Label("Dow Titans (%)", style=LBL),
                      dcc.Input(id="ov-titans-pct", type="number", min=0, max=100,
                                placeholder="e.g. 20", value=tp if tp else None, style=INP)]),
            html.Div([html.Label("Cash Portfolio (%)", style=LBL),
                      dcc.Input(id="ov-cash-pct", type="number", min=0, max=100,
                                placeholder="e.g. 10", value=xp if xp else None, style=INP)]),
        ]),
        html.Button("Save Allocation", id="ov-save-btn", n_clicks=0, style=BTN),
        html.Div(id="ov-save-msg", style={"marginTop": "8px", "fontSize": "12px", "color": ACCENT}),
    ])

    def port_card(title, alloc, color, body_children):
        return html.Div(
            style={**CARD, "borderTop": f"3px solid {color}", "marginBottom": "0"},
            children=[
                html.Div(style={"display": "flex", "justifyContent": "space-between",
                                "alignItems": "center", "marginBottom": "12px"}, children=[
                    html.H3(title, style={"margin": "0", "fontSize": "13px",
                                          "color": color, "letterSpacing": "1px"}),
                    html.Span(_fmt(alloc), style={"fontSize": "16px", "fontWeight": "800", "color": color}),
                ]),
                *body_children,
            ],
        )

    # Core summary
    core_sig_rows = []
    for t, cfg in CORE_PORTFOLIO.items():
        md  = (core_mkt or {}).get(t, {})
        sig = utilities.sma_signal(md, cfg["sma_period"])
        sc  = GREEN if sig == "BUY" else (RED if sig == "SELL/CASH" else MUTED)
        core_sig_rows.append(html.Div(
            style={"display": "grid", "gridTemplateColumns": "50px 55px 1fr 65px",
                   "gap": "4px", "padding": "5px 0",
                   "borderBottom": f"1px solid {CARD_BORDER}",
                   "fontSize": "11px", "alignItems": "center"},
            children=[
                html.Span(t, style={"fontWeight": "700", "color": ACCENT}),
                html.Span(f"SMA-{cfg['sma_period']}", style={"fontSize": "9px", "color": MUTED}),
                html.Span(_fmt(md.get("price")), style={"color": TEXT}),
                html.Span("▲ BUY" if sig == "BUY" else "▼ CASH",
                          style={"color": sc, "fontWeight": "700", "fontSize": "10px"}),
            ],
        ))
    core_card = port_card("Core Portfolio", core_alloc, ACCENT, [
        html.Div(f"{n_above_core}/{len(CORE_PORTFOLIO)} above SMA",
                 style={"fontSize": "11px", "color": MUTED, "marginBottom": "8px"}),
        *core_sig_rows,
    ])

    # Momentum summary
    mom_rows = []
    for t, w in mom_winners:
        amt = mom_alloc * w if mom_alloc else None
        mom_rows.append(html.Div(
            style={"display": "flex", "justifyContent": "space-between", "alignItems": "center",
                   "padding": "5px 0", "borderBottom": f"1px solid {CARD_BORDER}", "fontSize": "11px"},
            children=[
                html.Span(t, style={"fontWeight": "700", "color": ACCENT4}),
                html.Span(f"{w:.1%}  {_fmt(amt)}", style={"color": TEXT, "fontWeight": "600"}),
            ],
        ))
    if mom_cash_w > 0.001:
        amt = mom_alloc * mom_cash_w if mom_alloc else None
        mom_rows.append(html.Div(
            style={"display": "flex", "justifyContent": "space-between",
                   "padding": "5px 0", "fontSize": "11px"},
            children=[html.Span("CASH(SGOV)", style={"color": MUTED}),
                      html.Span(f"{mom_cash_w:.1%}  {_fmt(amt)}", style={"color": MUTED})],
        ))
    mom_card = port_card("Momentum Portfolio", mom_alloc, ACCENT4, [
        html.Div(f"As of {mom_as_of}  •  Top-{MOM_TOP_N} vol-scaled",
                 style={"fontSize": "11px", "color": MUTED, "marginBottom": "8px"}),
        *mom_rows,
    ])

    # Titans summary — show circuit breaker state
    acwi_px  = next((r["acwi_price"]   for r in (titans_rows or []) if "acwi_price"   in r), None)
    acwi_sma = next((r["acwi_sma_val"] for r in (titans_rows or []) if "acwi_sma_val" in r), None)

    buy_tickers = [r["ticker"] for r in (titans_rows or []) if r.get("signal") == "BUY"]
    wt_each     = (100 / n_elig_t) if n_elig_t else None

    titans_summary_body = []
    if not titans_acwi_ok:
        titans_summary_body.append(html.Div(
            style={"backgroundColor": "#2d0a0a", "border": f"1px solid {RED}",
                   "borderRadius": "6px", "padding": "8px 12px", "marginBottom": "8px",
                   "fontSize": "11px", "color": RED, "fontWeight": "700"},
            children=[
                "⛔ CIRCUIT BREAKER — IN CASH  ",
                html.Span(
                    f"ACWI {_fmt(acwi_px)} < SMA-{TITANS_ACWI_SMA_PERIOD} {_fmt(acwi_sma)}"
                    if acwi_px and acwi_sma else "",
                    style={"color": MUTED, "fontWeight": "400"},
                ),
            ],
        ))
    else:
        titans_summary_body.append(html.Div(
            f"{n_elig_t}/{len(DOW_TITANS)} eligible  •  Equal weight {wt_each:.1f}% each"
            if wt_each else f"{n_elig_t}/{len(DOW_TITANS)} eligible",
            style={"fontSize": "11px", "color": MUTED, "marginBottom": "8px"},
        ))
        titans_summary_body.append(
            html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "5px"}, children=[
                html.Span(t, style={"backgroundColor": "#1a1033", "color": "#86efac",
                                    "borderRadius": "4px", "padding": "2px 7px",
                                    "fontSize": "10px", "fontWeight": "600"})
                for t in buy_tickers
            ])
        )

    titans_card = port_card("Dow Titans", titans_alloc, ACCENT3 if titans_acwi_ok else RED,
                            titans_summary_body)

    # Cash summary
    cash_per_val = (tv * xp_f) * CASH_WEIGHT_EACH
    cash_instr_rows = [
        html.Div(
            style={"display": "flex", "justifyContent": "space-between", "alignItems": "center",
                   "padding": "4px 0", "borderBottom": f"1px solid {CARD_BORDER}", "fontSize": "11px"},
            children=[html.Span(name, style={"fontWeight": "700", "color": ACCENT5}),
                      html.Span(f"25%  {_fmt(cash_per_val)}", style={"color": TEXT})],
        )
        for name in CASH_INSTRUMENTS + [CASH_LABEL]
    ]
    cash_card = port_card("Cash Portfolio", tv * xp_f, ACCENT5, [
        html.Div("Equal weight: SGOV · SHV · ICSH · $CASH",
                 style={"fontSize": "11px", "color": MUTED, "marginBottom": "8px"}),
        *cash_instr_rows,
    ])

    master_table = build_master_table(
        core_mkt, mom_sig, titans_rows, cash_mkt,
        holdings, tv, cp, mp, tp, xp,
    )

    return html.Div(style={"paddingTop": "20px"}, children=[
        kpis,
        html.Div(style={"display": "grid", "gridTemplateColumns": "380px 1fr",
                        "gap": "20px", "alignItems": "start"}, children=[
            html.Div([setup]),
            html.Div([
                html.Div(style=CARD, children=[
                    html.H3("Portfolio Split",
                            style={"margin": "0 0 8px", "fontSize": "13px",
                                   "color": MUTED, "letterSpacing": "1px"}),
                    dcc.Graph(figure=pie_fig, config={"displayModeBar": False}),
                ]),
                html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr",
                                "gap": "16px", "marginBottom": "16px"},
                         children=[core_card, mom_card]),
                html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px"},
                         children=[titans_card, cash_card]),
            ]),
        ]),
        master_table,
    ])


# ═══════════════════════════════════════════════════════════════════════
#  TAB 2 — CORE PORTFOLIO
# ═══════════════════════════════════════════════════════════════════════
def build_core_tab(market, holdings, tv, cp):
    alloc = ((tv or 0) * (cp or 0) / 100) or 0

    above     = sum(1 for t, cfg in CORE_PORTFOLIO.items()
                    if utilities.sma_signal((market or {}).get(t, {}), cfg["sma_period"]) == "BUY")
    cash_pct  = sum(cfg["target_pct"] for t, cfg in CORE_PORTFOLIO.items()
                    if utilities.sma_signal((market or {}).get(t, {}), cfg["sma_period"]) != "BUY")
    total_pnl = None
    if holdings and market:
        s, has = 0, False
        for t, h in holdings.items():
            p = (market.get(t) or {}).get("price")
            if p and h and h.get("shares") and h.get("avg_cost"):
                s += (p - h["avg_cost"]) * h["shares"]; has = True
        if has:
            total_pnl = s

    kpis = html.Div(
        style={"display": "flex", "gap": "14px", "marginBottom": "20px",
               "flexWrap": "wrap", "paddingTop": "20px"},
        children=[
            _kpi("Core Allocation", _fmt(alloc), ACCENT2, f"{cp or 0:.1f}% of total", ACCENT2),
            _kpi("Invested", f"{above}/{len(CORE_PORTFOLIO)}", ACCENT, f"{(1 - cash_pct)*100:.1f}% deployed"),
            _kpi("Cash/Sidelined", f"{cash_pct*100:.1f}%", YELLOW if cash_pct > 0 else MUTED,
                 f"{len(CORE_PORTFOLIO) - above} below SMA", bar_color=YELLOW),
            _kpi("Unrealized P&L",
                 _fmt(total_pnl, sign=True) if total_pnl is not None else "Enter holdings",
                 _pcolor(total_pnl), bar_color=_pcolor(total_pnl)),
        ],
    )

    # Holdings input
    left = html.Div(style=CARD, children=[
        html.H3("Holdings", style={"margin": "0 0 4px", "fontSize": "13px",
                                    "color": ACCENT2, "letterSpacing": "1px"}),
        html.P("Allocation % set on Overview tab.",
               style={"fontSize": "11px", "color": MUTED, "margin": "0 0 14px"}),
        html.Div(style={"display": "grid", "gridTemplateColumns": "60px 1fr 1fr 1fr",
                        "gap": "6px", "marginBottom": "4px"},
                 children=[html.Span(""),
                            *[html.Span(h, style={**LBL, "marginBottom": "0"})
                              for h in ["Shares", "Avg Cost", "Cur Value"]]]),
        *[html.Div(
            style={"display": "grid", "gridTemplateColumns": "60px 1fr 1fr 1fr",
                   "gap": "6px", "marginBottom": "8px", "alignItems": "center"},
            children=[
                html.Div([
                    html.Span(t, style={"fontWeight": "700", "color": ACCENT, "fontSize": "13px"}),
                    html.Div(f"SMA-{CORE_PORTFOLIO[t]['sma_period']}",
                             style={"fontSize": "9px", "color": MUTED}),
                ]),
                dcc.Input(id={"type": "shares-input", "ticker": t}, type="number", min=0,
                          placeholder="0",
                          value=(_SAVED.get("holdings", {}).get(t) or {}).get("shares"),
                          style={**INP, "fontSize": "12px", "padding": "6px 8px"}),
                dcc.Input(id={"type": "cost-input", "ticker": t}, type="number", min=0,
                          placeholder="0.00",
                          value=(_SAVED.get("holdings", {}).get(t) or {}).get("avg_cost"),
                          style={**INP, "fontSize": "12px", "padding": "6px 8px"}),
                dcc.Input(id={"type": "curval-input", "ticker": t}, type="number", min=0,
                          placeholder="$",
                          value=(_SAVED.get("holdings", {}).get(t) or {}).get("current_value"),
                          style={**INP, "fontSize": "12px", "padding": "6px 8px"}),
            ],
        ) for t in CORE_TICKERS],
        html.Button("Save Holdings", id="save-holdings-btn", n_clicks=0,
                    style={**utilities.BTN2, "marginTop": "8px"}),
        html.Div(id="core-holdings-msg",
                 style={"marginTop": "8px", "fontSize": "12px", "color": ACCENT2}),
    ])

    # Signal table
    sig_hdr = html.Div(
        style={"display": "grid",
               "gridTemplateColumns": "60px 55px 90px 100px 80px 85px",
               "gap": "4px", "padding": "6px 0",
               "borderBottom": f"1px solid {CARD_BORDER}",
               "fontSize": "10px", "color": MUTED,
               "letterSpacing": "0.8px", "textTransform": "uppercase"},
        children=[html.Span(c) for c in ["Ticker", "SMA", "Price", "SMA Val", "% vs SMA", "Signal"]],
    )
    sig_rows = []
    for t, cfg in CORE_PORTFOLIO.items():
        md    = (market or {}).get(t, {}); price = md.get("price")
        sma_p = cfg["sma_period"]; sma_v = md.get(f"sma_{sma_p}")
        sig   = utilities.sma_signal(md, sma_p)
        pct   = ((price - sma_v) / sma_v * 100) if price and sma_v else None
        sc    = GREEN if sig == "BUY" else (RED if sig == "SELL/CASH" else MUTED)
        sig_rows.append(html.Div(
            style={"display": "grid",
                   "gridTemplateColumns": "60px 55px 90px 100px 80px 85px",
                   "gap": "4px", "padding": "9px 0",
                   "borderBottom": f"1px solid {CARD_BORDER}",
                   "fontSize": "12px", "alignItems": "center"},
            children=[
                html.Span(t, style={"fontWeight": "700", "color": ACCENT}),
                html.Span(f"SMA-{sma_p}", style={"color": MUTED, "fontSize": "10px"}),
                html.Span(_fmt(price)),
                html.Span(_fmt(sma_v), style={"color": MUTED}),
                html.Span(f"{pct:+.2f}%" if pct is not None else "—",
                          style={"color": _pcolor(pct), "fontWeight": "600"}),
                html.Span("▲ BUY" if sig == "BUY" else ("▼ CASH" if sig == "SELL/CASH" else "—"),
                          style={"color": sc, "fontWeight": "700", "fontSize": "11px"}),
            ],
        ))
    sig_card = html.Div(style=CARD, children=[
        html.H3("SMA Signals", style={"margin": "0 0 10px", "fontSize": "13px",
                                       "color": MUTED, "letterSpacing": "1px"}),
        sig_hdr, *sig_rows,
    ])

    # Rebalance
    if alloc > 0:
        rows    = utilities.compute_core_rebalance(holdings or {}, market or {}, alloc)
        reb_hdr = html.Div(
            style={"display": "grid",
                   "gridTemplateColumns": "60px 65px 70px 90px 95px 100px 95px 100px",
                   "gap": "4px", "padding": "6px 0",
                   "borderBottom": f"1px solid {CARD_BORDER}",
                   "fontSize": "10px", "color": MUTED,
                   "letterSpacing": "0.8px", "textTransform": "uppercase"},
            children=[html.Span(c) for c in
                      ["Ticker", "Signal", "Target %", "Target $",
                       "Current $", "Δ Value", "Δ Shares", "Unreal P&L"]],
        )
        reb_rows = []
        for r in rows:
            ic = r["ticker"] == "CASH"
            sc = CASH_CLR if ic else (GREEN if r["signal"] == "BUY" else RED)
            reb_rows.append(html.Div(
                style={"display": "grid",
                       "gridTemplateColumns": "60px 65px 70px 90px 95px 100px 95px 100px",
                       "gap": "4px", "padding": "9px 0",
                       "borderBottom": f"1px solid {CARD_BORDER}",
                       "fontSize": "12px", "alignItems": "center",
                       "opacity": "0.5" if ic else "1"},
                children=[
                    html.Span(r["ticker"],
                              style={"fontWeight": "700", "color": CASH_CLR if ic else ACCENT}),
                    html.Span("CASH" if ic else ("▲ BUY" if r["signal"] == "BUY" else "▼ CASH"),
                              style={"color": sc, "fontWeight": "700", "fontSize": "11px"}),
                    html.Span(f"{r['target_pct']*100:.2f}%", style={"color": MUTED}),
                    html.Span(_fmt(r["target_val"])),
                    html.Span(_fmt(r["cur_val"]) if not ic else "—", style={"color": MUTED}),
                    html.Span(_fmt(r["delta_val"], sign=True) if r["delta_val"] is not None else "—",
                              style={"color": _pcolor(r["delta_val"]), "fontWeight": "600"}),
                    html.Span(f"{r['delta_shares']:+.4f}" if r["delta_shares"] is not None else "—",
                              style={"color": _pcolor(r["delta_shares"])}),
                    html.Span(_fmt(r["pnl_unreal"], sign=True) if r["pnl_unreal"] is not None else "—",
                              style={"color": _pcolor(r["pnl_unreal"])}),
                ],
            ))
        reb_card = html.Div(style=CARD, children=[
            html.H3("Rebalance Engine",
                    style={"margin": "0 0 4px", "fontSize": "13px", "color": MUTED, "letterSpacing": "1px"}),
            html.P("Δ Shares = BUY (+) or SELL (−) to reach target. Below-SMA → CASH.",
                   style={"fontSize": "11px", "color": MUTED, "margin": "0 0 12px"}),
            reb_hdr, *reb_rows,
        ])
    else:
        reb_card = html.Div(style=CARD, children=[
            html.Div("Set portfolio value & Core % on Overview tab.",
                     style={"color": MUTED, "textAlign": "center",
                            "padding": "20px 0", "fontSize": "13px"}),
        ])

    # Charts
    pie_lbl, pie_val, pie_clr = [], [], []
    cash_p = 0.0
    for i, (t, cfg) in enumerate(CORE_PORTFOLIO.items()):
        if utilities.sma_signal((market or {}).get(t, {}), cfg["sma_period"]) == "BUY":
            pie_lbl.append(t); pie_val.append(cfg["target_pct"] * 100)
            pie_clr.append(PIE_COLORS[i % len(PIE_COLORS)])
        else:
            cash_p += cfg["target_pct"]
    if cash_p > 0:
        pie_lbl.append("CASH"); pie_val.append(cash_p * 100); pie_clr.append(CASH_CLR)
    pf = go.Figure(go.Pie(
        labels=pie_lbl, values=pie_val, hole=0.55,
        marker=dict(colors=pie_clr, line=dict(color=DARK_BG, width=2)),
        textfont=dict(size=12, color="#fff"),
        hovertemplate="<b>%{label}</b><br>%{value:.2f}%<extra></extra>",
        textinfo="label+percent",
    ))
    pf.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT), showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10), height=300,
        annotations=[dict(text="Effective<br>Alloc", x=0.5, y=0.5,
                          font_size=11, font_color=MUTED, showarrow=False)],
    )
    bt, bv, bc = [], [], []
    for t, cfg in CORE_PORTFOLIO.items():
        md = (market or {}).get(t, {}); p = md.get("price"); sv = md.get(f"sma_{cfg['sma_period']}")
        if p and sv:
            pct = (p - sv) / sv * 100
            bt.append(t); bv.append(pct); bc.append(GREEN if pct >= 0 else RED)
    bf = go.Figure(go.Bar(
        x=bt, y=bv, marker_color=bc,
        text=[f"{v:+.2f}%" for v in bv], textposition="outside",
        textfont=dict(size=11, color=TEXT),
        hovertemplate="<b>%{x}</b><br>%{y:+.2f}% vs SMA<extra></extra>",
    ))
    bf.add_hline(y=0, line_color=CARD_BORDER, line_width=1.5)
    bf.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT), xaxis=dict(showgrid=False, color=MUTED),
        yaxis=dict(showgrid=True, gridcolor=CARD_BORDER, color=MUTED, ticksuffix="%"),
        margin=dict(t=20, b=20, l=10, r=10), height=300, bargap=0.35,
    )
    charts = html.Div(style=CARD, children=[
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px"}, children=[
            html.Div([html.H3("Effective Allocation",
                              style={"margin": "0 0 8px", "fontSize": "13px",
                                     "color": MUTED, "letterSpacing": "1px"}),
                      dcc.Graph(figure=pf, config={"displayModeBar": False})]),
            html.Div([html.H3("Price vs SMA (%)",
                              style={"margin": "0 0 8px", "fontSize": "13px",
                                     "color": MUTED, "letterSpacing": "1px"}),
                      dcc.Graph(figure=bf, config={"displayModeBar": False})]),
        ]),
    ])

    return html.Div([
        kpis,
        html.Div(style={"display": "grid", "gridTemplateColumns": "360px 1fr",
                        "gap": "24px", "alignItems": "start"},
                 children=[left, html.Div([sig_card, reb_card, charts])]),
    ])


# ═══════════════════════════════════════════════════════════════════════
#  TAB 3 — MOMENTUM PORTFOLIO
# ═══════════════════════════════════════════════════════════════════════
def build_momentum_tab(mom_sig, tv, mp):
    sig      = mom_sig or {}
    alloc    = ((tv or 0) * (mp or 0) / 100) or 0
    winners  = sig.get("winners", [])
    cash_w   = sig.get("cash_weight", 1.0)
    diag     = sig.get("diagnostics", {})
    as_of    = sig.get("as_of", "—")
    deployed = sum(w for _, w in winners)

    kpis = html.Div(
        style={"display": "flex", "gap": "14px", "marginBottom": "20px",
               "flexWrap": "wrap", "paddingTop": "20px"},
        children=[
            _kpi("Momentum Alloc", _fmt(alloc), ACCENT4, f"{mp or 0:.1f}% of total", ACCENT4),
            _kpi("Signal Date",    as_of,         TEXT,   "last market close"),
            _kpi("Winners",        f"{len(winners)}", ACCENT4, f"Top-{MOM_TOP_N} vol-scaled"),
            _kpi("Deployed", f"{deployed:.1%}", GREEN if deployed > 0.5 else YELLOW,
                 f"Cash: {cash_w:.1%}", bar_color=GREEN),
        ],
    )

    winner_tickers = {t for t, _ in winners}
    winner_rows    = []
    for t, w in winners:
        d   = diag.get(t, {})
        amt = alloc * w if alloc else None
        winner_rows.append(html.Div(
            style={**CARD, "borderLeft": f"4px solid {ACCENT4}",
                   "marginBottom": "12px", "padding": "16px"},
            children=[
                html.Div(style={"display": "flex", "justifyContent": "space-between",
                                "alignItems": "center", "marginBottom": "8px"}, children=[
                    html.Div([
                        html.Span(t, style={"fontSize": "18px", "fontWeight": "800", "color": ACCENT4}),
                        html.Span(f"  #{list(winner_tickers).index(t)+1}",
                                  style={"fontSize": "12px", "color": MUTED}),
                    ]),
                    html.Div([
                        html.Span(f"{w:.1%}", style={"fontSize": "16px", "fontWeight": "700", "color": TEXT}),
                        html.Span(f"  {_fmt(amt)}", style={"fontSize": "14px", "color": ACCENT4, "marginLeft": "8px"}),
                    ]),
                ]),
                html.Div(style={"display": "grid", "gridTemplateColumns": "repeat(4,1fr)", "gap": "8px"}, children=[
                    html.Div([html.Div("Price",    style={**LBL, "marginBottom": "2px"}),
                              html.Div(_fmt(d.get("price")), style={"fontSize": "13px", "fontWeight": "600"})]),
                    html.Div([html.Div("Momentum", style={**LBL, "marginBottom": "2px"}),
                              html.Div(
                                  f"{d.get('momentum',0):+.2%}" if d.get("momentum") not in (None, -np.inf) else "—",
                                  style={"fontSize": "13px", "fontWeight": "600", "color": _pcolor(d.get("momentum"))})]),
                    html.Div([html.Div("6m Return", style={**LBL, "marginBottom": "2px"}),
                              html.Div(
                                  f"{d.get('ret_6m',0):+.2%}" if d.get("ret_6m") not in (None, -np.inf) else "—",
                                  style={"fontSize": "13px", "fontWeight": "600", "color": _pcolor(d.get("ret_6m"))})]),
                    html.Div([html.Div("SMA Gate", style={**LBL, "marginBottom": "2px"}),
                              html.Div("✓ Pass" if d.get("trend_pass") else "✗ Fail",
                                       style={"fontSize": "13px", "fontWeight": "600",
                                              "color": "#86efac" if d.get("trend_pass") else RED})]),
                ]),
            ],
        ))
    if cash_w > 0.001:
        amt = alloc * cash_w if alloc else None
        winner_rows.append(html.Div(
            style={**CARD, "borderLeft": f"4px solid {CASH_CLR}",
                   "marginBottom": "12px", "padding": "16px", "opacity": "0.7"},
            children=[html.Div(style={"display": "flex", "justifyContent": "space-between"}, children=[
                html.Span("CASH (SGOV)", style={"fontSize": "16px", "fontWeight": "700", "color": MUTED}),
                html.Div([
                    html.Span(f"{cash_w:.1%}", style={"fontSize": "16px", "fontWeight": "700", "color": MUTED}),
                    html.Span(f"  {_fmt(amt)}", style={"fontSize": "14px", "color": MUTED, "marginLeft": "8px"}),
                ]),
            ])],
        ))
    winners_panel = html.Div(style=CARD, children=[
        html.H3("Current Signal — Winners",
                style={"margin": "0 0 16px", "fontSize": "13px", "color": ACCENT4, "letterSpacing": "1px"}),
        *winner_rows,
    ])

    # Full diagnostics table
    tbl_hdr = html.Div(
        style={"display": "grid",
               "gridTemplateColumns": "80px 60px 60px 80px 90px 90px 70px 70px 80px",
               "gap": "4px", "padding": "6px 0",
               "borderBottom": f"1px solid {CARD_BORDER}",
               "fontSize": "10px", "color": MUTED,
               "letterSpacing": "0.8px", "textTransform": "uppercase"},
        children=[html.Span(c) for c in
                  ["Ticker", "SMA", "Price", "Momentum", "6m Ret",
                   "Trend", "Abs Mom", "Eligible", "Status"]],
    )
    tbl_rows = []
    for t in sorted(diag.keys(), key=lambda t: (not diag[t].get("eligible", False),
                                                  -(diag[t].get("momentum") or -999))):
        d         = diag[t]
        is_winner = t in winner_tickers
        mom_v     = d.get("momentum"); ret_v = d.get("ret_6m")
        tbl_rows.append(html.Div(
            style={"display": "grid",
                   "gridTemplateColumns": "80px 60px 60px 80px 90px 90px 70px 70px 80px",
                   "gap": "4px", "padding": "8px 0",
                   "borderBottom": f"1px solid {CARD_BORDER}",
                   "fontSize": "12px", "alignItems": "center",
                   "opacity": "1" if d.get("eligible") else "0.5"},
            children=[
                html.Span(t, style={"fontWeight": "700",
                                    "color": ACCENT4 if is_winner else (ACCENT if d.get("eligible") else MUTED)}),
                html.Span(f"{d.get('sma_period')}d", style={"color": MUTED, "fontSize": "10px"}),
                html.Span(_fmt(d.get("price"))),
                html.Span(f"{mom_v:+.2%}" if mom_v not in (None, -np.inf, np.inf) else "—",
                          style={"color": _pcolor(mom_v)}),
                html.Span(f"{ret_v:+.2%}" if ret_v not in (None, -np.inf, np.inf) else "—",
                          style={"color": _pcolor(ret_v)}),
                html.Span("✓" if d.get("trend_pass") else "✗",
                          style={"color": "#86efac" if d.get("trend_pass") else RED, "fontWeight": "700"}),
                html.Span("✓" if d.get("abs_pass") else "✗",
                          style={"color": "#86efac" if d.get("abs_pass") else RED, "fontWeight": "700"}),
                html.Span("✓" if d.get("eligible") else "✗",
                          style={"color": "#86efac" if d.get("eligible") else RED, "fontWeight": "700"}),
                html.Span("★ WINNER" if is_winner else ("ELIGIBLE" if d.get("eligible") else "filtered"),
                          style={"color": ACCENT4 if is_winner else (GREEN if d.get("eligible") else MUTED),
                                 "fontWeight": "700" if is_winner else "400", "fontSize": "11px"}),
            ],
        ))
    diag_card = html.Div(style=CARD, children=[
        html.H3("Full Asset Diagnostics",
                style={"margin": "0 0 4px", "fontSize": "13px", "color": MUTED, "letterSpacing": "1px"}),
        html.P(f"SMA gate: {MOM_SMA_PERIOD}d default (BND/BNDX: 126d)  |  "
               f"Abs momentum: 6m return > SGOV  |  Vol target: {MOM_TARGET_VOL:.0%}",
               style={"fontSize": "11px", "color": MUTED, "margin": "0 0 12px"}),
        tbl_hdr, *tbl_rows,
    ])

    # Momentum bar chart
    valid = [(t, d["momentum"]) for t, d in diag.items()
             if d.get("momentum") not in (None, -np.inf, np.inf)]
    valid.sort(key=lambda x: -x[1])
    bt = [x[0] for x in valid]; bv = [x[1] * 100 for x in valid]
    bc = [ACCENT4 if t in winner_tickers else (GREEN if diag[t].get("eligible") else MUTED) for t in bt]
    bf = go.Figure(go.Bar(
        x=bt, y=bv, marker_color=bc,
        text=[f"{v:+.1f}%" for v in bv], textposition="outside",
        textfont=dict(size=10, color=TEXT),
        hovertemplate="<b>%{x}</b><br>Momentum: %{y:+.2f}%<extra></extra>",
    ))
    bf.add_hline(y=0, line_color=CARD_BORDER, line_width=1)
    bf.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT), xaxis=dict(showgrid=False, color=MUTED),
        yaxis=dict(showgrid=True, gridcolor=CARD_BORDER, color=MUTED, ticksuffix="%"),
        margin=dict(t=20, b=10, l=10, r=10), height=300, bargap=0.25,
    )
    mom_chart = html.Div(style=CARD, children=[
        html.H3("Composite Momentum Score",
                style={"margin": "0 0 8px", "fontSize": "13px", "color": MUTED, "letterSpacing": "1px"}),
        html.P("Orange = winner  |  Green = eligible  |  Grey = filtered",
               style={"fontSize": "11px", "color": MUTED, "margin": "0 0 8px"}),
        dcc.Graph(figure=bf, config={"displayModeBar": False}),
    ])

    return html.Div([
        kpis,
        html.Div(style={"display": "grid", "gridTemplateColumns": "380px 1fr",
                        "gap": "24px", "alignItems": "start"},
                 children=[winners_panel, html.Div([diag_card, mom_chart])]),
    ])


# ═══════════════════════════════════════════════════════════════════════
#  TAB 4 — DOW TITANS
# ═══════════════════════════════════════════════════════════════════════
def build_titans_tab(titans_rows, tv, tp):
    rows = titans_rows or []

    # ── Circuit breaker: pull ACWI SMA state stamped on row 0 ────────────
    acwi_ok  = next((r["acwi_above_sma"] for r in rows if "acwi_above_sma" in r), True)
    acwi_px  = next((r["acwi_price"]     for r in rows if "acwi_price"     in r), None)
    acwi_sma = next((r["acwi_sma_val"]   for r in rows if "acwi_sma_val"   in r), None)

    # Only count / show eligible positions when circuit breaker is clear
    eligible = [r for r in rows if r.get("signal") == "BUY"] if acwi_ok else []
    n_elig   = len(eligible)
    alloc    = ((tv or 0) * (tp or 0) / 100) or 0
    wt_each  = (alloc / n_elig) if n_elig else None
    bench    = next((r["bench"] for r in rows if "bench" in r), {})

    # ── KPIs ─────────────────────────────────────────────────────────────
    kpis = html.Div(
        style={"display": "flex", "gap": "14px", "marginBottom": "20px",
               "flexWrap": "wrap", "paddingTop": "20px"},
        children=[
            _kpi("Titans Allocation", _fmt(alloc), ACCENT3, f"{tp or 0:.1f}% of total", ACCENT3),
            _kpi(
                "Eligible",
                f"{n_elig}/{len(DOW_TITANS)}" if acwi_ok else "0 — IN CASH",
                ACCENT3 if acwi_ok else RED,
                "passing all gates" if acwi_ok else "circuit breaker active",
            ),
            _kpi(
                "Weight per Stock",
                f"{100/n_elig:.2f}%" if n_elig else "—",
                TEXT,
                _fmt(wt_each) + " each" if wt_each else ("In cash" if not acwi_ok else "No eligible"),
            ),
            _kpi("EMA Filter", f"EMA-{TITANS_EMA_PERIOD}", MUTED, "Gate 1", bar_color=MUTED),
            _kpi(
                f"ACWI SMA-{TITANS_ACWI_SMA_PERIOD}",
                "▲ ABOVE" if acwi_ok else "▼ BELOW",
                GREEN if acwi_ok else RED,
                (f"px {_fmt(acwi_px)}  SMA {_fmt(acwi_sma)}" if acwi_px and acwi_sma
                 else "Circuit breaker"),
                bar_color=GREEN if acwi_ok else RED,
            ),
        ],
    )

    # ── Circuit breaker banner (only shown when triggered) ────────────────
    circuit_banner = html.Div()
    if not acwi_ok:
        circuit_banner = html.Div(
            style={
                "backgroundColor": "#2d0a0a",
                "border": f"2px solid {RED}",
                "borderRadius": "10px",
                "padding": "16px 22px",
                "marginBottom": "20px",
                "display": "flex",
                "alignItems": "center",
                "gap": "14px",
            },
            children=[
                html.Span("⛔", style={"fontSize": "26px", "flexShrink": "0"}),
                html.Div([
                    html.Div(
                        "CIRCUIT BREAKER ACTIVE — ALL TITANS POSITIONS IN CASH",
                        style={"color": RED, "fontWeight": "800",
                               "fontSize": "13px", "letterSpacing": "1px"},
                    ),
                    html.Div(
                        (
                            f"ACWI is trading at {_fmt(acwi_px)}, below its "
                            f"{TITANS_ACWI_SMA_PERIOD}-day SMA of {_fmt(acwi_sma)}. "
                            "All Titans positions should be liquidated to cash. "
                            "Normal operation resumes once ACWI closes back above the SMA."
                        ) if acwi_px and acwi_sma else
                        f"ACWI has fallen below its {TITANS_ACWI_SMA_PERIOD}-day SMA. "
                        "Titans strategy is fully in cash.",
                        style={"color": MUTED, "fontSize": "12px", "marginTop": "5px",
                               "lineHeight": "1.5"},
                    ),
                ]),
            ],
        )

    # ── Benchmark card ────────────────────────────────────────────────────
    bench_items = [
        html.Div(
            style={"display": "flex", "justifyContent": "space-between", "padding": "5px 0",
                   "borderBottom": f"1px solid {CARD_BORDER}", "fontSize": "12px"},
            children=[
                html.Span(lbl, style={"color": MUTED}),
                html.Span(f"{bench.get(key):+.2f}%" if bench.get(key) is not None else "—",
                          style={"color": _pcolor(bench.get(key)), "fontWeight": "600"}),
            ],
        )
        for lbl, key in [("SHV 6m", "shv_6m"), ("BND 6m", "bnd_6m"),
                          ("ACWI 3m", "acwi_3m"), ("ACWI 6m", "acwi_6m")]
    ]
    # Append ACWI SMA status line to benchmark card
    bench_items.append(html.Div(
        style={"display": "flex", "justifyContent": "space-between", "padding": "8px 0 2px",
               "fontSize": "12px", "marginTop": "4px",
               "borderTop": f"1px solid {CARD_BORDER}"},
        children=[
            html.Span(f"ACWI SMA-{TITANS_ACWI_SMA_PERIOD}", style={"color": MUTED}),
            html.Span(
                "▲ ABOVE" if acwi_ok else "▼ BELOW",
                style={"color": GREEN if acwi_ok else RED, "fontWeight": "700"},
            ),
        ],
    ))
    bench_card = html.Div(style={**CARD, "marginBottom": "0"}, children=[
        html.H3("Benchmark Returns",
                style={"margin": "0 0 10px", "fontSize": "13px",
                       "color": ACCENT3, "letterSpacing": "1px"}),
        *bench_items,
    ])

    # ── Signal table ──────────────────────────────────────────────────────
    col = "58px 80px 80px 80px 80px 80px 80px 50px 50px 50px 80px 90px"
    tbl_hdr = html.Div(
        style={"display": "grid", "gridTemplateColumns": col, "gap": "4px",
               "padding": "6px 0", "borderBottom": f"1px solid {CARD_BORDER}",
               "fontSize": "10px", "color": MUTED,
               "letterSpacing": "0.8px", "textTransform": "uppercase"},
        children=[html.Span(c) for c in
                  ["Ticker", "Price", "EMA-200", "% vs EMA",
                   "Ret 3m", "Ret 6m", "①>SHV", "②>BND", "③>ACWI", "Signal", "Target $"]],
    )
    tbl_rows = []
    prev = None
    for r in rows:
        if r.get("signal") == "NO DATA":
            continue
        if prev is not None and prev != r.get("signal"):
            tbl_rows.append(html.Hr(style={"borderColor": CARD_BORDER, "margin": "4px 0"}))
        prev   = r.get("signal")
        is_buy = r.get("signal") == "BUY"

        # When circuit breaker is active, no row is treated as actionable BUY
        effective_buy = is_buy and acwi_ok
        sc = GREEN if effective_buy else (MUTED if is_buy else RED)

        def fr(v):
            return f"{v:+.1f}%" if v is not None else "—"

        tbl_rows.append(html.Div(
            style={"display": "grid", "gridTemplateColumns": col, "gap": "4px",
                   "padding": "8px 0", "borderBottom": f"1px solid {CARD_BORDER}",
                   "fontSize": "12px", "alignItems": "center",
                   # dim all rows when circuit breaker is active; otherwise dim non-BUY rows
                   "opacity": "0.35" if (not acwi_ok) else ("1" if is_buy else "0.55")},
            children=[
                html.Span(r["ticker"],
                          style={"fontWeight": "700",
                                 "color": MUTED if not acwi_ok else (ACCENT3 if is_buy else MUTED)}),
                html.Span(_fmt(r.get("price"))),
                html.Span(_fmt(r.get("ema")), style={"color": MUTED}),
                html.Span(f"{r['pct_ema']:+.2f}%" if r.get("pct_ema") is not None else "—",
                          style={"color": _pcolor(r.get("pct_ema")) if acwi_ok else MUTED,
                                 "fontWeight": "600"}),
                html.Span(fr(r.get("r3m")),
                          style={"color": _pcolor(r.get("r3m")) if acwi_ok else MUTED}),
                html.Span(fr(r.get("r6m")),
                          style={"color": _pcolor(r.get("r6m")) if acwi_ok else MUTED}),
                html.Span("✓" if r.get("f1") else "✗",
                          style={"color": ("#86efac" if r.get("f1") else RED) if acwi_ok else MUTED,
                                 "fontWeight": "700"}),
                html.Span("✓" if r.get("f2") else "✗",
                          style={"color": ("#86efac" if r.get("f2") else RED) if acwi_ok else MUTED,
                                 "fontWeight": "700"}),
                html.Span("✓" if r.get("f3") else "✗",
                          style={"color": ("#86efac" if r.get("f3") else RED) if acwi_ok else MUTED,
                                 "fontWeight": "700"}),
                html.Span(
                    "⛔ CASH" if not acwi_ok else ("✅ BUY" if is_buy else "❌ OUT"),
                    style={"color": RED if not acwi_ok else sc,
                           "fontWeight": "700", "fontSize": "11px"},
                ),
                html.Span(
                    "—" if not acwi_ok else (_fmt(wt_each) if (is_buy and wt_each) else "—"),
                    style={"color": MUTED if not acwi_ok else (ACCENT3 if (is_buy and wt_each) else MUTED),
                           "fontWeight": "600" if (effective_buy) else "400"},
                ),
            ],
        ))
    sig_card = html.Div(style=CARD, children=[
        html.H3("Dow Titans Signal Scanner",
                style={"margin": "0 0 4px", "fontSize": "13px",
                       "color": ACCENT3 if acwi_ok else RED, "letterSpacing": "1px"}),
        html.P(
            f"Gate 1: Price>EMA-{TITANS_EMA_PERIOD}  |  "
            f"①: 6m>SHV  |  ②: 6m>BND  |  ③: 3m+6m>ACWI  |  "
            f"Circuit: ACWI>SMA-{TITANS_ACWI_SMA_PERIOD}",
            style={"fontSize": "11px", "color": MUTED, "margin": "0 0 12px"},
        ),
        tbl_hdr, *tbl_rows,
    ])

    # ── Eligible chart (hidden when circuit breaker active) ───────────────
    elig_chart = html.Div()
    if eligible and acwi_ok:
        eq_t = [r["ticker"] for r in eligible]
        eq_v = [wt_each] * n_elig if wt_each else [1 / n_elig] * n_elig
        ef   = go.Figure(go.Bar(
            x=eq_t, y=eq_v, marker_color=PIE_COLORS[:n_elig],
            text=[_fmt(v) for v in eq_v], textposition="outside",
            textfont=dict(size=10, color=TEXT),
            hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>",
        ))
        ef.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT), xaxis=dict(showgrid=False, color=MUTED),
            yaxis=dict(showgrid=True, gridcolor=CARD_BORDER, color=MUTED),
            margin=dict(t=20, b=30, l=10, r=10), height=280, bargap=0.3,
        )
        elig_chart = html.Div(style=CARD, children=[
            html.H3("Eligible — Equal-Weight Target $",
                    style={"margin": "0 0 8px", "fontSize": "13px",
                           "color": ACCENT3, "letterSpacing": "1px"}),
            dcc.Graph(figure=ef, config={"displayModeBar": False}),
        ])

    return html.Div([
        kpis,
        circuit_banner,
        html.Div(style={"display": "grid", "gridTemplateColumns": "200px 1fr",
                        "gap": "20px", "alignItems": "start"},
                 children=[bench_card, html.Div([sig_card, elig_chart])]),
    ])


# ═══════════════════════════════════════════════════════════════════════
#  TAB 5 — CASH PORTFOLIO
# ═══════════════════════════════════════════════════════════════════════
def build_cash_tab(cash_mkt, tv, xp):
    cash_mkt = cash_mkt or {}
    alloc    = ((tv or 0) * (xp or 0) / 100) or 0
    per_wt   = CASH_WEIGHT_EACH
    per_val  = alloc * per_wt
    all_names= CASH_INSTRUMENTS + [CASH_LABEL]

    kpis = html.Div(
        style={"display": "flex", "gap": "14px", "marginBottom": "20px",
               "flexWrap": "wrap", "paddingTop": "20px"},
        children=[
            _kpi("Cash Allocation", _fmt(alloc),   ACCENT5, f"{xp or 0:.1f}% of total", ACCENT5),
            _kpi("Instruments",     "4",             TEXT,   "SGOV · SHV · ICSH · $CASH"),
            _kpi("Weight Each",     "25.00%",        ACCENT5, _fmt(per_val) + " per instrument"),
            _kpi("Strategy",        "Equal Weight",  MUTED,  "rebalance to 25% each", bar_color=MUTED),
        ],
    )

    hdr = html.Div(
        style={"display": "grid",
               "gridTemplateColumns": "70px 80px 90px 100px 100px 1fr",
               "gap": "4px", "padding": "6px 0",
               "borderBottom": f"1px solid {CARD_BORDER}",
               "fontSize": "10px", "color": MUTED,
               "letterSpacing": "0.8px", "textTransform": "uppercase"},
        children=[html.Span(c) for c in ["Instrument", "Price", "Weight", "Target $", "Shares", "Notes"]],
    )
    rows = []
    for name in all_names:
        is_cash = name == CASH_LABEL
        price   = 1.0 if is_cash else (cash_mkt.get(name) or {}).get("price")
        shares  = (per_val / price) if (price and per_val) else None
        rows.append(html.Div(
            style={"display": "grid",
                   "gridTemplateColumns": "70px 80px 90px 100px 100px 1fr",
                   "gap": "4px", "padding": "12px 0",
                   "borderBottom": f"1px solid {CARD_BORDER}",
                   "fontSize": "13px", "alignItems": "center"},
            children=[
                html.Span(name, style={"fontWeight": "700", "color": ACCENT5}),
                html.Span("$1.00" if is_cash else _fmt(price), style={"color": TEXT}),
                html.Span(f"{per_wt*100:.2f}%", style={"color": MUTED}),
                html.Span(_fmt(per_val), style={"color": ACCENT5, "fontWeight": "600"}),
                html.Span(
                    f"{shares:,.4f} shares" if (shares and not is_cash)
                    else (_fmt(per_val) if is_cash else "—"),
                    style={"color": MUTED, "fontSize": "12px"},
                ),
                html.Span(
                    "Uninvested cash — hold at brokerage" if is_cash
                    else "Money market / ultra-short ETF",
                    style={"color": MUTED, "fontSize": "11px", "fontStyle": "italic"},
                ),
            ],
        ))

    pf = go.Figure(go.Pie(
        labels=all_names, values=[25, 25, 25, 25], hole=0.55,
        marker=dict(colors=[ACCENT5, "#a78bfa", "#7c3aed", CASH_CLR],
                    line=dict(color=DARK_BG, width=2)),
        textfont=dict(size=13, color="#fff"),
        hovertemplate="<b>%{label}</b><br>25.00%<extra></extra>",
        textinfo="label+percent",
    ))
    pf.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT), showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10), height=280,
        annotations=[dict(text=_fmt(alloc), x=0.5, y=0.5,
                          font_size=14, font_color=ACCENT5, showarrow=False)],
    )

    return html.Div([
        kpis,
        html.Div(style={"display": "grid", "gridTemplateColumns": "320px 1fr",
                        "gap": "24px", "alignItems": "start"}, children=[
            html.Div(style=CARD, children=[
                html.H3("Allocation Split",
                        style={"margin": "0 0 8px", "fontSize": "13px",
                               "color": ACCENT5, "letterSpacing": "1px"}),
                dcc.Graph(figure=pf, config={"displayModeBar": False}),
                html.P("Each instrument receives an equal 25% of the Cash portfolio allocation.",
                       style={"fontSize": "11px", "color": MUTED,
                              "margin": "12px 0 0", "textAlign": "center"}),
            ]),
            html.Div(style=CARD, children=[
                html.H3("Cash Portfolio Holdings",
                        style={"margin": "0 0 12px", "fontSize": "13px",
                               "color": ACCENT5, "letterSpacing": "1px"}),
                hdr, *rows,
                html.P("$CASH = uninvested dollar balance held at brokerage.",
                       style={"fontSize": "11px", "color": MUTED, "marginTop": "14px"}),
            ]),
        ]),
    ])


# ═══════════════════════════════════════════════════════════════════════
#  MASTER HOLDINGS TABLE
# ═══════════════════════════════════════════════════════════════════════
def build_master_table(core_mkt, mom_sig, titans_rows, cash_mkt, holdings, tv, cp, mp, tp, xp):
    tv = tv or 0
    rows: list[dict] = []

    def add_row(portfolio, ticker, color, price, target_val, shares_hint=None):
        rows.append({
            "portfolio": portfolio, "ticker": ticker, "color": color,
            "price": price, "target_val": target_val,
            "pct_total": (target_val / tv * 100) if tv else None,
            "shares": shares_hint,
        })

    # Core
    core_alloc = tv * cp / 100
    for t, cfg in CORE_PORTFOLIO.items():
        md    = (core_mkt or {}).get(t, {})
        sig   = utilities.sma_signal(md, cfg["sma_period"])
        eff   = cfg["target_pct"] if sig == "BUY" else 0.0
        tval  = core_alloc * eff
        h     = (holdings or {}).get(t) or {}
        sh    = h.get("shares") if h.get("shares") else (tval / md["price"] if (tval and md.get("price")) else None)
        add_row("Core", t, ACCENT, md.get("price"), tval, sh)
    core_cash_pct = sum(cfg["target_pct"] for t, cfg in CORE_PORTFOLIO.items()
                        if utilities.sma_signal((core_mkt or {}).get(t, {}), cfg["sma_period"]) != "BUY")
    if core_cash_pct > 0:
        add_row("Core", "CASH->SGOV", MUTED, 1.0, core_alloc * core_cash_pct)

    # Momentum
    mom_alloc = tv * mp / 100
    if mom_sig:
        for t, w in (mom_sig.get("winners") or []):
            d     = (mom_sig.get("diagnostics") or {}).get(t) or {}
            price = d.get("price")
            tval  = mom_alloc * w
            add_row("Momentum", t, ACCENT4, price, tval,
                    (tval / price) if (tval and price) else None)
        cw = mom_sig.get("cash_weight", 0)
        if cw > 0.001:
            add_row("Momentum", "CASH(SGOV)", MUTED, None, mom_alloc * cw)

    # Dow Titans — respect circuit breaker
    titans_alloc  = tv * tp / 100
    acwi_ok_mt    = next((r["acwi_above_sma"] for r in (titans_rows or []) if "acwi_above_sma" in r), True)
    elig_t        = [r for r in (titans_rows or []) if r.get("signal") == "BUY"] if acwi_ok_mt else []
    n_e           = len(elig_t)
    if acwi_ok_mt and n_e:
        wt_each = titans_alloc / n_e
        for r in elig_t:
            price = r.get("price")
            add_row("Dow Titans", r["ticker"], ACCENT3, price, wt_each,
                    (wt_each / price) if (wt_each and price) else None)
    else:
        # Circuit breaker active — show as a single cash line
        add_row("Dow Titans", "CASH (circuit breaker)", RED, 1.0, titans_alloc)

    # Cash
    cash_alloc = tv * xp / 100
    per_val    = cash_alloc * CASH_WEIGHT_EACH
    for name in CASH_INSTRUMENTS + [CASH_LABEL]:
        price = 1.0 if name == CASH_LABEL else (cash_mkt or {}).get(name, {}).get("price")
        add_row("Cash", name, ACCENT5, price, per_val,
                (per_val / price) if (price and per_val and name != CASH_LABEL) else None)

    if not rows:
        return html.Div("Set allocations on the Overview tab to see the master table.",
                        style={"color": MUTED, "textAlign": "center",
                               "padding": "20px", "fontSize": "13px"})

    PORT_COLORS = {"Core": ACCENT, "Momentum": ACCENT4, "Dow Titans": ACCENT3, "Cash": ACCENT5}
    col = "110px 80px 90px 110px 100px 90px"

    hdr = html.Div(
        style={"display": "grid", "gridTemplateColumns": col, "gap": "4px",
               "padding": "8px 12px", "backgroundColor": "#0d0a1a",
               "borderRadius": "8px 8px 0 0",
               "fontSize": "10px", "color": MUTED,
               "letterSpacing": "0.8px", "textTransform": "uppercase"},
        children=[html.Span(c) for c in ["Portfolio", "Ticker", "Price", "Target $", "% of Total", "Shares"]],
    )

    tbl_rows  = []
    prev_port = None
    for r in rows:
        if prev_port and prev_port != r["portfolio"]:
            tbl_rows.append(html.Div(style={"height": "1px", "backgroundColor": CARD_BORDER}))
        prev_port = r["portfolio"]
        pc        = PORT_COLORS.get(r["portfolio"], MUTED)
        tbl_rows.append(html.Div(
            style={"display": "grid", "gridTemplateColumns": col, "gap": "4px",
                   "padding": "8px 12px", "borderBottom": f"1px solid {CARD_BORDER}",
                   "fontSize": "12px", "alignItems": "center",
                   "opacity": "0.5" if r["target_val"] == 0 else "1"},
            children=[
                html.Span(r["portfolio"],
                          style={"fontSize": "10px", "color": pc, "fontWeight": "700",
                                 "letterSpacing": "0.5px", "textTransform": "uppercase"}),
                html.Span(r["ticker"], style={"fontWeight": "700", "color": r["color"]}),
                html.Span(_fmt(r["price"]) if r["price"] else "—", style={"color": TEXT}),
                html.Span(_fmt(r["target_val"]), style={"color": pc, "fontWeight": "600"}),
                html.Span(f"{r['pct_total']:.2f}%" if r["pct_total"] is not None else "—",
                          style={"color": MUTED}),
                html.Span(f"{r['shares']:,.4f}" if r["shares"] else "—",
                          style={"color": MUTED, "fontSize": "11px"}),
            ],
        ))

    total_invested = sum(r["target_val"] for r in rows)
    footer = html.Div(
        style={"display": "grid", "gridTemplateColumns": col, "gap": "4px",
               "padding": "10px 12px", "backgroundColor": "#0d0a1a",
               "borderRadius": "0 0 8px 8px", "fontSize": "12px"},
        children=[
            html.Span("TOTAL", style={"fontWeight": "800", "color": YELLOW,
                                      "fontSize": "11px", "letterSpacing": "1px"}),
            html.Span(f"{len(rows)} positions", style={"color": MUTED, "fontSize": "11px"}),
            html.Span(""),
            html.Span(_fmt(total_invested), style={"fontWeight": "800", "color": YELLOW}),
            html.Span(f"{total_invested/tv*100:.1f}%" if tv else "—",
                      style={"color": YELLOW, "fontWeight": "700"}),
            html.Span(""),
        ],
    )

    return html.Div(style=CARD, children=[
        html.H3("Master Portfolio — All Positions",
                style={"margin": "0 0 4px", "fontSize": "13px",
                       "color": YELLOW, "letterSpacing": "1px"}),
        html.P("Every position across all 4 portfolios at target weights and dollar values.",
               style={"fontSize": "11px", "color": MUTED, "margin": "0 0 14px"}),
        html.Div(
            style={"border": f"1px solid {CARD_BORDER}", "borderRadius": "8px", "overflow": "hidden"},
            children=[hdr, *tbl_rows, footer],
        ),
    ])


# ═══════════════════════════════════════════════════════════════════════
#  HTML SHELL
# ═══════════════════════════════════════════════════════════════════════
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
