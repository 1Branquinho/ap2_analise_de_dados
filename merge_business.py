import requests
import pandas as pd
import numpy as np

BASE_URL = "https://laboratoriodefinancas.com/api/v2"
TOKEN    = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzgwNTcwNzA4LCJpYXQiOjE3Nzc5Nzg3MDgsImp0aSI6IjNmNTBiZWM4OWVkZDQzMWI5NTljZWFkYmFkZTdiNjYyIiwidXNlcl9pZCI6IjExOCJ9.4m2iY0iB32ZKdO6_uZb-H1Cu9zwOXJcenbCHAv-qTFE"
HEADERS  = {"Authorization": f"Bearer {TOKEN}"}

TICKERS  = ["ABEV3", "AMER3", "ASAI3"]
ANO_TRI  = "20244T"
DATA_INI = "2020-01-01"
DATA_FIM = "2025-12-31"
W        = 72


# ════════════════════════════════════════════════════════════════════
# Funções de coleta
# ════════════════════════════════════════════════════════════════════

def fetch_balanco(ticker, ano_tri):
    resp = requests.get(
        f"{BASE_URL}/bolsa/balanco",
        headers=HEADERS,
        params={"ticker": ticker, "ano_tri": ano_tri},
    )
    resp.raise_for_status()
    return pd.DataFrame(resp.json()[0]["balanco"])


def fetch_dre(ticker, ano_tri):
    resp = requests.get(
        f"{BASE_URL}/bolsa/financeiro",
        headers=HEADERS,
        params={"ticker": ticker, "ano_tri": ano_tri},
    )
    resp.raise_for_status()
    data = resp.json()
    # Tenta as estruturas mais comuns da API
    if isinstance(data, list) and data:
        first = data[0]
        for key in ["financeiro", "dre", "dados", "resultado"]:
            if key in first:
                return pd.DataFrame(first[key])
        # Se não tiver chave aninhada, tenta usar diretamente
        if isinstance(first, dict) and "conta" in first:
            return pd.DataFrame(data)
    return pd.DataFrame(data)


def fetch_indicador(ticker, ano_tri):
    resp = requests.get(
        f"{BASE_URL}/bolsa/indicador",
        headers=HEADERS,
        params={"ticker": ticker, "ano_tri": ano_tri},
    )
    resp.raise_for_status()
    return resp.json()


def fetch_preco_acao(ticker):
    resp = requests.get(
        f"{BASE_URL}/preco/corrigido",
        headers=HEADERS,
        params={"ticker": ticker, "data_ini": DATA_INI, "data_fim": DATA_FIM},
    )
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    df["data"] = pd.to_datetime(df["data"])
    df["fechamento"] = pd.to_numeric(df["fechamento"], errors="coerce")
    return df.set_index("data")[["fechamento"]].rename(columns={"fechamento": ticker})


def fetch_ibov():
    resp = requests.get(
        f"{BASE_URL}/preco/diversos",
        headers=HEADERS,
        params={"ticker": "ibov", "data_ini": DATA_INI, "data_fim": DATA_FIM},
    )
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    df["data"] = pd.to_datetime(df["data"])
    df["fechamento"] = pd.to_numeric(df["fechamento"], errors="coerce")
    return df.set_index("data")[["fechamento"]].rename(columns={"fechamento": "IBOV"})


def v(df, conta):
    res = df[df["conta"] == conta]["valor"]
    if res.empty:
        return 0.0
    try:
        return float(res.iloc[0])
    except (ValueError, TypeError):
        return 0.0


def safe_div(a, b):
    return (a / b) if b and b != 0 else None


# ════════════════════════════════════════════════════════════════════
# Coleta de preços e métricas de mercado
# ════════════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════════════
# DEBUG — rode isso uma vez para ver a estrutura dos endpoints
# Depois pode comentar esse bloco
# ════════════════════════════════════════════════════════════════════
print("=== DEBUG /bolsa/financeiro ===")
r = requests.get(f"{BASE_URL}/bolsa/financeiro", headers=HEADERS,
                 params={"ticker": "ABEV3", "ano_tri": ANO_TRI})
print("Status:", r.status_code)
data_raw = r.json()
print("Tipo:", type(data_raw))
if isinstance(data_raw, list):
    print("Len:", len(data_raw))
    print("Primeiro item (keys):", list(data_raw[0].keys()) if data_raw else "vazio")
    print("Amostra:", str(data_raw[0])[:400])
elif isinstance(data_raw, dict):
    print("Keys:", list(data_raw.keys()))
    print("Amostra:", str(data_raw)[:400])

print()
print("=== DEBUG /bolsa/indicador ===")
r2 = requests.get(f"{BASE_URL}/bolsa/indicador", headers=HEADERS,
                  params={"ticker": "ABEV3"})
print("Status:", r2.status_code)
if r2.status_code == 200:
    data_raw2 = r2.json()
    print("Tipo:", type(data_raw2))
    if isinstance(data_raw2, list):
        print("Len:", len(data_raw2))
        print("Primeiro item:", str(data_raw2[0])[:400])
    elif isinstance(data_raw2, dict):
        print("Keys:", list(data_raw2.keys()))
        print("Amostra:", str(data_raw2)[:400])
else:
    print("Erro:", r2.text[:300])
print("=" * 50)
print()

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
# Coleta de balanço + DRE e cálculo dos indicadores
# ════════════════════════════════════════════════════════════════════
print("Coletando balanços e DRE...")

ind_balanco     = {}
ind_rentab      = {}
ind_atividade   = {}
ind_preco_fund  = {}  # VPA, LPA via /bolsa/indicador

for ticker in TICKERS:
    # ── Balanço ──────────────────────────────────────────────────────
    dfb = fetch_balanco(ticker, ANO_TRI)

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
    pl     = v(dfb, "2.03")

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
        "Relação Capitais":         safe_div(passivo, pl),
        "Endividamento Geral":      safe_div(passivo, at),
        "Solvência Geral":          safe_div(at, passivo),
        "Composição Endividamento": safe_div(pc, passivo),
        "Imobilização PL":          safe_div(at_fixo, pl),
    }

    # ── DRE ──────────────────────────────────────────────────────────
    try:
        dfd = fetch_dre(ticker, ANO_TRI)

        rec   = abs(v(dfd, "3.01"))   # Receita Líquida
        cmv   = abs(v(dfd, "3.02"))   # CMV/CPV
        ebit  = v(dfd, "3.05")        # EBIT
        ll    = v(dfd, "3.09")        # Lucro Líquido

        # Capital investido (PL + Dívida Líquida)
        div_bruta = emp_cp + v(dfb, "2.02.01")
        div_liq   = div_bruta - cx - af
        cap_inv   = pl + div_liq

        # ── Rentabilidade ────────────────────────────────────────────
        ind_rentab[ticker] = {
            "ROE  (LL / PL)":          safe_div(ll, pl),
            "ROA  (LL / AT)":          safe_div(ll, at),
            "ROI  (EBIT / AT)":        safe_div(ebit, at),
            "ROCE (EBIT / AT-PC)":     safe_div(ebit, at - pc),
            "ROIC (EBIT / Cap.Inv.)":  safe_div(ebit, cap_inv),
            "Margem Bruta":            safe_div(rec - cmv, rec),
            "Margem Líquida":          safe_div(ll, rec),
            "Receita Líq. (R$ mil)":   rec / 1_000,
            "Lucro Líq. (R$ mil)":     ll / 1_000,
            "EBIT (R$ mil)":           ebit / 1_000,
        }

        # Compras (precisa de estoque do período anterior — aproximado)
        compras = cmv + est  # simplificação sem est. inicial
        ind_atividade[ticker] = {
            "PME  (Est/CMV×365)":      safe_div(est * 365, cmv),
            "Giro Estoque (CMV/Est)":  safe_div(cmv, est),
            "PMRV (CR/Rec×365)":       safe_div(cr * 365, rec),
            "PMPF (Forn/Comp×365)":    safe_div(forn * 365, compras),
            "Ciclo Operacional":       (safe_div(est * 365, cmv) or 0) + (safe_div(cr * 365, rec) or 0),
            "Ciclo Financeiro":        ((safe_div(est * 365, cmv) or 0)
                                       + (safe_div(cr * 365, rec) or 0)
                                       - (safe_div(forn * 365, compras) or 0)),
            "Ciclo Econômico (PME)":   safe_div(est * 365, cmv),
        }

    except Exception as e:
        print(f"  [AVISO] DRE de {ticker} não carregou: {e}")
        ind_rentab[ticker]    = {}
        ind_atividade[ticker] = {}

    # ── Indicadores de preço via /bolsa/indicador ─────────────────────
    try:
        raw = fetch_indicador(ticker, ANO_TRI)
        # Tenta extrair VPA e LPA — a estrutura varia por API
        if isinstance(raw, list) and raw:
            item = raw[0]
        elif isinstance(raw, dict):
            item = raw
        else:
            item = {}

        ind_preco_fund[ticker] = {
            "VPA":  item.get("vpa") or item.get("VPA"),
            "LPA":  item.get("lpa") or item.get("LPA"),
            "P/L":  item.get("pl")  or item.get("P/L") or item.get("preco_lucro"),
            "DY":   item.get("dy")  or item.get("DY")  or item.get("dividend_yield"),
        }
    except Exception as e:
        print(f"  [AVISO] Indicador de {ticker} não carregou: {e}")
        ind_preco_fund[ticker] = {"VPA": None, "LPA": None, "P/L": None, "DY": None}

df_cont_tab    = pd.DataFrame(ind_balanco).T
df_rentab_tab  = pd.DataFrame(ind_rentab).T
df_ativ_tab    = pd.DataFrame(ind_atividade).T
df_pfund_tab   = pd.DataFrame(ind_preco_fund).T


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

def linha_num(df, ind, fmt="{:>12.4f}"):
    row = f"  {ind:<34}"
    for t in TICKERS:
        val = df.loc[t, ind] if t in df.index and ind in df.columns else None
        try:
            row += fmt.format(float(val)) if val is not None else f"{'N/D':>12}"
        except (TypeError, ValueError):
            row += f"{'N/D':>12}"
    print(row)

def separador(label):
    print(f"\n  {'─'*3} {label} {'─'*(W-8-len(label))}")


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
    linha_num(df_preco_tab, ind, fmt)
print("=" * W)

# ── Indicadores de Preço/Fundamentalistas ────────────────────────────
cabecalho(f"INDICADORES DE PREÇO  (ref: {ANO_TRI})")
for ind in ["VPA", "LPA", "P/L", "DY"]:
    linha_num(df_pfund_tab, ind, "{:>12.4f}")
print("=" * W)

# ── Rentabilidade ─────────────────────────────────────────────────────
cabecalho(f"RENTABILIDADE  (ref: {ANO_TRI})")
for ind, fmt in [
    ("ROE  (LL / PL)",          "{:>12.4f}"),
    ("ROA  (LL / AT)",          "{:>12.4f}"),
    ("ROI  (EBIT / AT)",        "{:>12.4f}"),
    ("ROCE (EBIT / AT-PC)",     "{:>12.4f}"),
    ("ROIC (EBIT / Cap.Inv.)",  "{:>12.4f}"),
    ("Margem Bruta",            "{:>12.4f}"),
    ("Margem Líquida",          "{:>12.4f}"),
    ("Receita Líq. (R$ mil)",   "{:>12,.0f}"),
    ("Lucro Líq. (R$ mil)",     "{:>12,.0f}"),
    ("EBIT (R$ mil)",           "{:>12,.0f}"),
]:
    linha_num(df_rentab_tab, ind, fmt)
print("=" * W)

# ── Atividade ─────────────────────────────────────────────────────────
cabecalho(f"ATIVIDADE  (ref: {ANO_TRI})")
for ind, fmt in [
    ("PME  (Est/CMV×365)",      "{:>12.1f}"),
    ("Giro Estoque (CMV/Est)",  "{:>12.4f}"),
    ("PMRV (CR/Rec×365)",       "{:>12.1f}"),
    ("PMPF (Forn/Comp×365)",    "{:>12.1f}"),
    ("Ciclo Operacional",       "{:>12.1f}"),
    ("Ciclo Financeiro",        "{:>12.1f}"),
    ("Ciclo Econômico (PME)",   "{:>12.1f}"),
]:
    linha_num(df_ativ_tab, ind, fmt)
print("=" * W)

# ── Liquidez + Capital de Giro + Endividamento ────────────────────────
cabecalho(f"CONTÁBIL  (ref: {ANO_TRI})")
separador("LIQUIDEZ")
for ind in ["Liquidez Corrente", "Liquidez Seca", "Liquidez Imediata", "Liquidez Geral", "CCL (R$ mil)"]:
    fmt = "{:>12,.0f}" if "mil" in ind else "{:>12.4f}"
    linha_num(df_cont_tab, ind, fmt)
separador("CAPITAL DE GIRO")
for ind in ["NCG (R$ mil)", "CGL (R$ mil)", "ST (R$ mil)"]:
    linha_num(df_cont_tab, ind, "{:>12,.0f}")
separador("ENDIVIDAMENTO")
for ind in ["Relação Capitais", "Endividamento Geral", "Solvência Geral",
            "Composição Endividamento", "Imobilização PL"]:
    linha_num(df_cont_tab, ind, "{:>12.4f}")
print()
print("=" * W)

print("\nDataFrames disponíveis:")
print("  df_preco_tab  | df_pfund_tab | df_rentab_tab | df_ativ_tab | df_cont_tab")
