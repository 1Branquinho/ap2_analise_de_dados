import requests
import pandas as pd
import numpy as np
import yfinance as yf

BASE_URL = "https://laboratoriodefinancas.com/api/v2"
TOKEN    = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzgwNTcwNzA4LCJpYXQiOjE3Nzc5Nzg3MDgsImp0aSI6IjNmNTBiZWM4OWVkZDQzMWI5NTljZWFkYmFkZTdiNjYyIiwidXNlcl9pZCI6IjExOCJ9.4m2iY0iB32ZKdO6_uZb-H1Cu9zwOXJcenbCHAv-qTFE"
HEADERS  = {"Authorization": f"Bearer {TOKEN}"}

TICKERS  = ["ABEV3", "AMER3", "ASAI3"]
ANO_TRI  = "20244T"
DATA_INI = "2020-01-01"
DATA_FIM = "2025-12-31"
W        = 72


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════

def ano_tri_to_date(ano_tri):
    """Converte '20244T' → '2024-12-31'"""
    year = ano_tri[:4]
    q    = ano_tri[4]
    fim  = {"1": "03-31", "2": "06-30", "3": "09-30", "4": "12-31"}
    return f"{year}-{fim[q]}"


def flt(val):
    try:
        return float(val) if val is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


def safe_div(a, b):
    return (a / b) if b and b != 0 else None


def v(df, conta):
    res = df[df["conta"] == conta]["valor"]
    if res.empty:
        return 0.0
    return flt(res.iloc[0])


# ════════════════════════════════════════════════════════════════════
# Funções de coleta
# ════════════════════════════════════════════════════════════════════

def fetch_market_data(ticker):
    """Retorna preço atual, qtd. de ações e market cap via yfinance."""
    try:
        info = yf.Ticker(f"{ticker}.SA").info
        preco    = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
        n_shares = info.get("sharesOutstanding") or 0
        mkt_cap  = preco * n_shares if (preco and n_shares) else None
        return {"preco": preco, "n_shares": n_shares, "mkt_cap": mkt_cap}
    except Exception as e:
        print(f"  [AVISO] yfinance {ticker}: {e}")
        return {"preco": None, "n_shares": None, "mkt_cap": None}


def fetch_balanco(ticker, ano_tri):
    resp = requests.get(
        f"{BASE_URL}/bolsa/balanco", headers=HEADERS,
        params={"ticker": ticker, "ano_tri": ano_tri},
    )
    resp.raise_for_status()
    return pd.DataFrame(resp.json()[0]["balanco"])


def fetch_financeiro(ticker, ano_tri):
    """Retorna dict flat com receita, ebit, lucro, pl, divida_liquida, capital..."""
    resp = requests.get(
        f"{BASE_URL}/bolsa/financeiro", headers=HEADERS,
        params={"ticker": ticker, "ano_tri": ano_tri},
    )
    resp.raise_for_status()
    return resp.json()[0]


def fetch_indicador(ticker, data_base):
    """Retorna indicadores de mercado (VPA, LPA, P/L, DY). Requer data_base='YYYY-MM-DD'."""
    resp = requests.get(
        f"{BASE_URL}/bolsa/indicador", headers=HEADERS,
        params={"ticker": ticker, "data_base": data_base},
    )
    resp.raise_for_status()
    return resp.json()


def fetch_preco_acao(ticker):
    resp = requests.get(
        f"{BASE_URL}/preco/corrigido", headers=HEADERS,
        params={"ticker": ticker, "data_ini": DATA_INI, "data_fim": DATA_FIM},
    )
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    df["data"] = pd.to_datetime(df["data"])
    df["fechamento"] = pd.to_numeric(df["fechamento"], errors="coerce")
    return df.set_index("data")[["fechamento"]].rename(columns={"fechamento": ticker})


def fetch_ibov():
    resp = requests.get(
        f"{BASE_URL}/preco/diversos", headers=HEADERS,
        params={"ticker": "ibov", "data_ini": DATA_INI, "data_fim": DATA_FIM},
    )
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    df["data"] = pd.to_datetime(df["data"])
    df["fechamento"] = pd.to_numeric(df["fechamento"], errors="coerce")
    return df.set_index("data")[["fechamento"]].rename(columns={"fechamento": "IBOV"})


# ════════════════════════════════════════════════════════════════════
# Coleta de preços e métricas de mercado
# ════════════════════════════════════════════════════════════════════
print("Coletando preços...")
frames = [fetch_preco_acao(t) for t in TICKERS] + [fetch_ibov()]
df_precos = pd.concat(frames, axis=1).sort_index().dropna()
df_norm   = df_precos / df_precos.iloc[0] * 100

ret_diarios = df_precos.pct_change().dropna()
ibov_total  = df_norm["IBOV"].iloc[-1] - 100

metricas_preco = {}
for ticker in TICKERS:
    ret_total = df_norm[ticker].iloc[-1] - 100
    vol       = ret_diarios[ticker].std() * (252 ** 0.5) * 100
    corr      = ret_diarios[ticker].corr(ret_diarios["IBOV"])
    metricas_preco[ticker] = {
        "Retorno Total (%)":      ret_total,
        "IBOV no período (%)":    ibov_total,
        "Alpha vs IBOV (pp)":     ret_total - ibov_total,
        "Volatilidade Anual (%)": vol,
        "Correlação c/ IBOV":     corr,
    }
df_preco_tab = pd.DataFrame(metricas_preco).T


# ════════════════════════════════════════════════════════════════════
# Coleta de balanço + financeiro + indicador
# ════════════════════════════════════════════════════════════════════
print("Coletando dados de mercado (yfinance)...")
market_data = {t: fetch_market_data(t) for t in TICKERS}

print("Coletando balanços, DRE e indicadores...")

ind_balanco    = {}
ind_rentab     = {}
ind_atividade  = {}
ind_pfund      = {}
ind_multiplos  = {}

# Último dia de pregão de 2024 disponível nos dados de preço
DATA_BASE = df_precos[df_precos.index.year == 2024].index[-1].strftime("%Y-%m-%d")
print(f"Data base para indicadores: {DATA_BASE}")

for ticker in TICKERS:

    # ── Balanço ──────────────────────────────────────────────────────
    dfb    = fetch_balanco(ticker, ANO_TRI)
    at     = v(dfb, "1")
    ac     = v(dfb, "1.01")
    cx     = v(dfb, "1.01.01")
    af     = v(dfb, "1.01.02")
    cr     = v(dfb, "1.01.03")
    est    = v(dfb, "1.01.04")
    da     = v(dfb, "1.01.07")
    arlp   = v(dfb, "1.02.01")
    inv    = v(dfb, "1.02.02")
    imob   = v(dfb, "1.02.03")
    intg   = v(dfb, "1.02.04")
    pc     = v(dfb, "2.01")
    forn   = v(dfb, "2.01.02")
    emp_cp = v(dfb, "2.01.04")
    pnc    = v(dfb, "2.02")
    pl_b   = v(dfb, "2.03")

    passivo = pc + pnc
    at_fixo = imob + intg + inv
    acf     = cx + af
    aco     = ac - acf
    pcf     = emp_cp
    pco     = pc - pcf

    ind_balanco[ticker] = {
        "Liquidez Corrente":        safe_div(ac, pc),
        "Liquidez Seca":            safe_div(ac - est - da, pc),
        "Liquidez Imediata":        safe_div(cx, pc),
        "Liquidez Geral":           safe_div(ac + arlp, pc + pnc),
        "CCL (R$ mil)":             (ac - pc) / 1_000,
        "NCG (R$ mil)":             (aco - pco) / 1_000,
        "CGL (R$ mil)":             (ac - pc) / 1_000,
        "ST (R$ mil)":              (acf - pcf) / 1_000,
        "Relação Capitais":         safe_div(passivo, pl_b),
        "Endividamento Geral":      safe_div(passivo, at),
        "Solvência Geral":          safe_div(at, passivo),
        "Composição Endividamento": safe_div(pc, passivo),
        "Imobilização PL":          safe_div(at_fixo, pl_b),
    }

    # ── Financeiro (DRE resumida) ─────────────────────────────────────
    fin = fetch_financeiro(ticker, ANO_TRI)
    rec      = flt(fin.get("receita"))
    ebit     = flt(fin.get("ebit"))
    ll       = flt(fin.get("lucro"))
    pl_f     = flt(fin.get("pl"))
    div_liq  = flt(fin.get("divida_liquida"))
    cap_inv  = flt(fin.get("capital"))   # pl + divida_liquida

    ind_rentab[ticker] = {
        "ROE  (LL / PL)":         safe_div(ll, pl_f),
        "ROA  (LL / AT)":         safe_div(ll, at),
        "ROI  (EBIT / AT)":       safe_div(ebit, at),
        "ROCE (EBIT / AT-PC)":    safe_div(ebit, at - pc),
        "ROIC (EBIT / Cap.Inv.)": safe_div(ebit, cap_inv),
        "Margem Líquida":         safe_div(ll, rec),
        "Receita Líq. (R$ mil)":  rec / 1_000,
        "Lucro Líq. (R$ mil)":    ll / 1_000,
        "EBIT (R$ mil)":          ebit / 1_000,
        "Dívida Líq. (R$ mil)":   div_liq / 1_000,
    }

    # ── Indicadores de preço — buscado antes da atividade para ter margem_bruta
    p_vp = p_l = mb = 0.0
    try:
        raw = fetch_indicador(ticker, DATA_BASE)
        item = raw
        while isinstance(item, list) and item:
            item = item[0]
        if not isinstance(item, dict):
            raise ValueError(f"Estrutura inesperada: {type(item)}")
        preco = flt(item.get("preco"))
        p_vp  = flt(item.get("p_vp"))
        p_l   = flt(item.get("p_l"))
        mb    = flt(item.get("margem_bruta"))
        ind_pfund[ticker] = {
            "Preço (R$)":   preco,
            "VPA (R$)":     safe_div(preco, p_vp),
            "LPA (R$)":     safe_div(preco, p_l),
            "P/L":          p_l,
            "P/VPA":        p_vp,
            "P/EBIT":       flt(item.get("p_ebit")),
            "EV/EBITDA":    flt(item.get("ev_ebitda")),
            "DY (%)":       flt(item.get("dividend_yield")),
            "Margem Bruta": mb,
        }
    except Exception as e:
        print(f"  [AVISO] Indicador {ticker}: {e}")
        ind_pfund[ticker] = {"Preço (R$)": None, "VPA (R$)": None, "LPA (R$)": None,
                             "P/L": None, "P/VPA": None, "P/EBIT": None,
                             "EV/EBITDA": None, "DY (%)": None, "Margem Bruta": None}

    # ── Atividade (CMV derivado de Receita × (1 - Margem Bruta)) ─────
    cmv     = rec * (1 - mb) if rec and mb else 0.0
    compras = cmv  # simplificação sem estoque inicial

    pme  = safe_div(est * 365, cmv)
    giro = safe_div(cmv, est)
    pmrv = safe_div(cr * 365, rec)
    pmpf = safe_div(forn * 365, compras)
    co   = (pme or 0) + (pmrv or 0) if (pme is not None and pmrv is not None) else None
    cf   = (co - (pmpf or 0))       if (co  is not None and pmpf is not None) else None

    ind_atividade[ticker] = {
        "PME  (Est/CMV×365)":     pme,
        "Giro Estoque (CMV/Est)": giro,
        "PMRV (CR/Rec×365)":      pmrv,
        "PMPF (Forn/Comp×365)":   pmpf,
        "Ciclo Operacional":      co,
        "Ciclo Financeiro":       cf,
        "Ciclo Econômico (PME)":  pme,
        "ACF (Cx + Aplic.)":      acf / 1_000,
        "ACO (AC - ACF)":         aco / 1_000,
        "PCF (Emp. CP)":          pcf / 1_000,
        "PCO (PC - PCF)":         pco / 1_000,
    }

    # ── Avaliação por Múltiplos ────────────────────────────────────────
    # Market Cap = Preço × Qtd. Ações  (yfinance)
    md      = market_data[ticker]
    mkt_cap = md["mkt_cap"]
    # Dívida Bruta = Empréstimos CP + Passivo Não Circulante (oneroso)
    div_bruta = emp_cp + pnc
    # Caixa = Caixa e Equiv. + Aplicações Financeiras CP
    caixa     = cx + af
    # Dívida Líquida = Dívida Bruta − Caixa
    div_liq_bp = div_bruta - caixa
    # EV = Market Cap + Dívida Líquida (calculado do balanço)
    ev = (mkt_cap + div_liq_bp) if mkt_cap is not None else None
    # EBITDA back-calculado via EV/EBITDA da API
    ev_ebitda_api = flt(ind_pfund[ticker].get("EV/EBITDA"))
    ebitda = safe_div(ev, ev_ebitda_api) if (ev and ev_ebitda_api) else None

    ind_multiplos[ticker] = {
        "Preço (R$)":            md["preco"],
        "Qtd. Ações (mil)":      (md["n_shares"] / 1_000) if md["n_shares"] else None,
        "Market Cap (R$ mil)":   (mkt_cap    / 1_000) if mkt_cap    is not None else None,
        "Dívida Líq. BP (R$ mil)":(div_liq_bp / 1_000),
        "EV (R$ mil)":           (ev          / 1_000) if ev          is not None else None,
        "EBITDA est. (R$ mil)":  (ebitda      / 1_000) if ebitda      is not None else None,
        "Margem EBIT":           safe_div(ebit, rec),
        "Margem EBITDA":         safe_div(ebitda, rec),
        "EV / EBITDA":           ev_ebitda_api if ev_ebitda_api else None,
        "EV / EBIT":             safe_div(ev, ebit),
        "EV / Receita":          safe_div(ev, rec),
        "P/L":                   p_l  if p_l  else None,
        "P/VPA":                 p_vp if p_vp else None,
        "DY (%)":                flt(ind_pfund[ticker].get("DY (%)")),
        "PL (R$ mil)":           (pl_f / 1_000) if pl_f else None,
    }

df_cont_tab   = pd.DataFrame(ind_balanco).T
df_rentab_tab = pd.DataFrame(ind_rentab).T
df_ativ_tab   = pd.DataFrame(ind_atividade).T
df_pfund_tab  = pd.DataFrame(ind_pfund).T
df_mult_tab   = pd.DataFrame(ind_multiplos).T


# ════════════════════════════════════════════════════════════════════
# Valuation por múltiplos — preço implícito via mediana dos pares
# ════════════════════════════════════════════════════════════════════

def mediana_pares(ticker, campo, df, apenas_positivos=True):
    """Mediana dos 2 pares excluindo o próprio ticker e valores inválidos."""
    vals = []
    for t in TICKERS:
        if t == ticker:
            continue
        try:
            v = float(df.loc[t, campo])
            if not apenas_positivos or v > 0:
                vals.append(v)
        except (KeyError, TypeError, ValueError):
            pass
    if not vals:
        return None
    vals.sort()
    n = len(vals)
    return vals[n // 2] if n % 2 == 1 else (vals[n // 2 - 1] + vals[n // 2]) / 2


ind_valuation = {}
for ticker in TICKERS:
    try:
        preco_atual = float(df_mult_tab.loc[ticker, "Preço (R$)"])
        n_shares    = float(df_mult_tab.loc[ticker, "Qtd. Ações (mil)"]) * 1_000
        div_liq_bp  = float(df_mult_tab.loc[ticker, "Dívida Líq. BP (R$ mil)"]) * 1_000

        ebitda = flt(df_mult_tab.loc[ticker, "EBITDA est. (R$ mil)"]) * 1_000
        ebit   = flt(df_rentab_tab.loc[ticker, "EBIT (R$ mil)"])       * 1_000
        rec    = flt(df_rentab_tab.loc[ticker, "Receita Líq. (R$ mil)"]) * 1_000
        ll     = flt(df_rentab_tab.loc[ticker, "Lucro Líq. (R$ mil)"])   * 1_000
        pl     = flt(df_mult_tab.loc[ticker,  "PL (R$ mil)"])            * 1_000

        pi = {}  # preços implícitos

        for nome, mult_campo, metrica, ev_based in [
            ("EV/EBITDA",  "EV / EBITDA", ebitda, True),
            ("EV/EBIT",    "EV / EBIT",   ebit,   True),
            ("EV/Receita", "EV / Receita",rec,    True),
            ("P/L",        "P/L",         ll,     False),
            ("P/VPA",      "P/VPA",       pl,     False),
        ]:
            med = mediana_pares(ticker, mult_campo, df_mult_tab)
            if med and metrica and metrica > 0 and n_shares:
                if ev_based:
                    imp_mktcap = med * metrica - div_liq_bp
                else:
                    imp_mktcap = med * metrica
                pi[nome] = imp_mktcap / n_shares

        validos = [v for v in pi.values() if v is not None]
        preco_medio = sum(validos) / len(validos) if validos else None
        upside = ((preco_medio - preco_atual) / preco_atual * 100) if preco_medio else None

        ind_valuation[ticker] = {
            "Preço Atual (R$)":    preco_atual,
            "P.Impl. EV/EBITDA":   pi.get("EV/EBITDA"),
            "P.Impl. EV/EBIT":     pi.get("EV/EBIT"),
            "P.Impl. EV/Receita":  pi.get("EV/Receita"),
            "P.Impl. P/L":         pi.get("P/L"),
            "P.Impl. P/VPA":       pi.get("P/VPA"),
            "Preço Médio Impl.":   preco_medio,
            "Upside/Downside (%)": upside,
        }
    except Exception as e:
        print(f"  [AVISO] Valuation {ticker}: {e}")
        ind_valuation[ticker] = {}

df_val_tab = pd.DataFrame(ind_valuation).T


# ════════════════════════════════════════════════════════════════════
# Impressão
# ════════════════════════════════════════════════════════════════════

def cabecalho(titulo):
    print()
    print("=" * W)
    print(f"  {titulo}")
    print("=" * W)
    print(f"  {'Indicador':<34}" + "".join(f"{t:>12}" for t in TICKERS))
    print("-" * W)


def linha(df, ind, fmt="{:>12.4f}"):
    row = f"  {ind:<34}"
    for t in TICKERS:
        val = df.loc[t, ind] if (t in df.index and ind in df.columns) else None
        try:
            row += fmt.format(float(val)) if val is not None else f"{'N/D':>12}"
        except (TypeError, ValueError):
            row += f"{'N/D':>12}"
    print(row)


def sep(label):
    print(f"\n  ─── {label} {'─' * (W - 8 - len(label))}")


data_ini_str = df_norm.index[0].strftime("%d/%m/%Y")
data_fim_str = df_norm.index[-1].strftime("%d/%m/%Y")

# ── Mercado ───────────────────────────────────────────────────────────
cabecalho(f"COMPARATIVO DE MERCADO  ({data_ini_str} → {data_fim_str})")
for ind, fmt in [
    ("Retorno Total (%)",       "{:>+11.1f}%"),
    ("IBOV no período (%)",     "{:>+11.1f}%"),
    ("Alpha vs IBOV (pp)",      "{:>+11.1f}p"),
    ("Volatilidade Anual (%)",  "{:>11.1f}% "),
    ("Correlação c/ IBOV",      "{:>12.4f} "),
]:
    linha(df_preco_tab, ind, fmt)
print("=" * W)

# ── Indicadores de Preço ─────────────────────────────────────────────
cabecalho(f"INDICADORES DE PREÇO  (ref: {DATA_BASE})")
for ind, fmt in [
    ("Preço (R$)",   "{:>12.2f}"),
    ("VPA (R$)",     "{:>12.2f}"),
    ("LPA (R$)",     "{:>12.2f}"),
    ("P/L",          "{:>12.2f}"),
    ("P/VPA",        "{:>12.2f}"),
    ("P/EBIT",       "{:>12.2f}"),
    ("EV/EBITDA",    "{:>12.2f}"),
    ("DY (%)",       "{:>12.2f}"),
    ("Margem Bruta", "{:>12.4f}"),
]:
    linha(df_pfund_tab, ind, fmt)
print("=" * W)

# ── Rentabilidade ─────────────────────────────────────────────────────
cabecalho(f"RENTABILIDADE  (ref: {ANO_TRI})")
for ind, fmt in [
    ("ROE  (LL / PL)",         "{:>12.4f}"),
    ("ROA  (LL / AT)",         "{:>12.4f}"),
    ("ROI  (EBIT / AT)",       "{:>12.4f}"),
    ("ROCE (EBIT / AT-PC)",    "{:>12.4f}"),
    ("ROIC (EBIT / Cap.Inv.)", "{:>12.4f}"),
    ("Margem Líquida",         "{:>12.4f}"),
    ("Receita Líq. (R$ mil)",  "{:>12,.0f}"),
    ("Lucro Líq. (R$ mil)",    "{:>12,.0f}"),
    ("EBIT (R$ mil)",          "{:>12,.0f}"),
    ("Dívida Líq. (R$ mil)",   "{:>12,.0f}"),
]:
    linha(df_rentab_tab, ind, fmt)
print("=" * W)

# ── Atividade ─────────────────────────────────────────────────────────
cabecalho(f"ATIVIDADE  (ref: {ANO_TRI})")
print("  (CMV aproximado via Receita x (1 - Margem Bruta))")
for ind, fmt in [
    ("PME  (Est/CMV×365)",     "{:>12.1f}"),
    ("Giro Estoque (CMV/Est)", "{:>12.4f}"),
    ("PMRV (CR/Rec×365)",      "{:>12.1f}"),
    ("PMPF (Forn/Comp×365)",   "{:>12.1f}"),
    ("Ciclo Operacional",      "{:>12.1f}"),
    ("Ciclo Financeiro",       "{:>12.1f}"),
    ("Ciclo Econômico (PME)",  "{:>12.1f}"),
    ("ACF (Cx + Aplic.)",      "{:>12,.0f}"),
    ("ACO (AC - ACF)",         "{:>12,.0f}"),
    ("PCF (Emp. CP)",          "{:>12,.0f}"),
    ("PCO (PC - PCF)",         "{:>12,.0f}"),
]:
    linha(df_ativ_tab, ind, fmt)
print("=" * W)

# ── Contábil ──────────────────────────────────────────────────────────
cabecalho(f"CONTÁBIL  (ref: {ANO_TRI})")
sep("LIQUIDEZ")
for ind in ["Liquidez Corrente", "Liquidez Seca", "Liquidez Imediata",
            "Liquidez Geral", "CCL (R$ mil)"]:
    linha(df_cont_tab, ind, "{:>12,.0f}" if "mil" in ind else "{:>12.4f}")
sep("CAPITAL DE GIRO")
for ind in ["NCG (R$ mil)", "CGL (R$ mil)", "ST (R$ mil)"]:
    linha(df_cont_tab, ind, "{:>12,.0f}")
sep("ENDIVIDAMENTO")
for ind in ["Relação Capitais", "Endividamento Geral", "Solvência Geral",
            "Composição Endividamento", "Imobilização PL"]:
    linha(df_cont_tab, ind, "{:>12.4f}")
print()
print("=" * W)

# ── Avaliação por Múltiplos ───────────────────────────────────────────
cabecalho(f"AVALIAÇÃO POR MÚLTIPLOS  (ref: {ANO_TRI} | preços: {DATA_BASE})")
sep("VALOR DE MERCADO  (Market Cap = Preço × Qtd. Ações — yfinance)")
for ind, fmt in [
    ("Preço (R$)",             "{:>12.2f}"),
    ("Qtd. Ações (mil)",       "{:>12,.0f}"),
    ("Market Cap (R$ mil)",    "{:>12,.0f}"),
    ("Dívida Líq. BP (R$ mil)","{:>12,.0f}"),
    ("EV (R$ mil)",            "{:>12,.0f}"),
    ("EBITDA est. (R$ mil)",   "{:>12,.0f}"),
]:
    linha(df_mult_tab, ind, fmt)
sep("MÚLTIPLOS DE FIRMA  (EV-based — neutros à estrutura de capital)")
for ind, fmt in [
    ("EV / EBITDA", "{:>12.2f}"),
    ("EV / EBIT",   "{:>12.2f}"),
    ("EV / Receita","{:>12.4f}"),
]:
    linha(df_mult_tab, ind, fmt)
sep("MÚLTIPLOS DE EQUITY")
for ind, fmt in [
    ("P/L",    "{:>12.2f}"),
    ("P/VPA",  "{:>12.2f}"),
    ("DY (%)", "{:>12.2f}"),
]:
    linha(df_mult_tab, ind, fmt)
sep("DRIVERS DOS MÚLTIPLOS  (companion variables — Damodaran)")
print("  P/L  → ROE + crescimento  |  EV/EBITDA → ROIC + crescimento  |  P/VPA → ROE − Ke")
for ind, fmt in [
    ("Margem EBIT",            "{:>12.4f}"),
    ("Margem EBITDA",          "{:>12.4f}"),
    ("ROE  (LL / PL)",         "{:>12.4f}"),
    ("ROIC (EBIT / Cap.Inv.)", "{:>12.4f}"),
]:
    if ind in df_mult_tab.columns:
        linha(df_mult_tab, ind, fmt)
    else:
        linha(df_rentab_tab, ind, fmt)
print()
print("=" * W)

# ── Valuation — Preço Implícito por Múltiplos ────────────────────────
cabecalho("VALUATION — PREÇO IMPLÍCITO POR MÚLTIPLOS")
print("  Mediana dos 2 pares aplicada ao dado financeiro de cada empresa")
sep("PREÇOS IMPLÍCITOS (R$)")
for ind, fmt in [
    ("Preço Atual (R$)",   "{:>12.2f}"),
    ("P.Impl. EV/EBITDA",  "{:>12.2f}"),
    ("P.Impl. EV/EBIT",    "{:>12.2f}"),
    ("P.Impl. EV/Receita", "{:>12.2f}"),
    ("P.Impl. P/L",        "{:>12.2f}"),
    ("P.Impl. P/VPA",      "{:>12.2f}"),
]:
    linha(df_val_tab, ind, fmt)
sep("RESUMO")
for ind, fmt in [
    ("Preço Médio Impl.",   "{:>12.2f}"),
    ("Upside/Downside (%)", "{:>+11.1f}%"),
]:
    linha(df_val_tab, ind, fmt)
print()
print("=" * W)

print("\nDataFrames disponíveis:")
print("  df_preco_tab | df_pfund_tab | df_rentab_tab | df_ativ_tab | df_cont_tab | df_mult_tab | df_val_tab")
