import sys
import requests
import pandas as pd
import numpy as np
import yfinance as yf

# Garante o encoding correto no Windows
sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "https://laboratoriodefinancas.com/api/v2"
TOKEN    = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzgwNTcwNzA4LCJpYXQiOjE3Nzc5Nzg3MDgsImp0aSI6IjNmNTBiZWM4OWVkZDQzMWI5NTljZWFkYmFkZTdiNjYyIiwidXNlcl9pZCI6IjExOCJ9.4m2iY0iB32ZKdO6_uZb-H1Cu9zwOXJcenbCHAv-qTFE"
HEADERS  = {"Authorization": f"Bearer {TOKEN}"}

TICKERS  = ["ABEV3", "AMER3", "ASAI3"]
ANO_TRI  = "20254T"
DATA_INI = "2020-01-01"
DATA_FIM = "2025-12-31"

# ════════════════════════════════════════════════════════════════════
# Funções de Coleta (idênticas ao merge_business.py)
# ════════════════════════════════════════════════════════════════════

def flt(val):
    try:
        return float(val) if val is not None else 0.0
    except (ValueError, TypeError):
        return 0.0

def safe_div(a, b):
    return (a / b) if b and b != 0 else 0.0

def v(df, conta):
    res = df[df["conta"] == conta]["valor"]
    if res.empty:
        return 0.0
    return flt(res.iloc[0])

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

def fetch_market_data(ticker):
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
    resp = requests.get(
        f"{BASE_URL}/bolsa/financeiro", headers=HEADERS,
        params={"ticker": ticker, "ano_tri": ano_tri},
    )
    resp.raise_for_status()
    return resp.json()[0]

def fetch_indicador(ticker, data_base):
    resp = requests.get(
        f"{BASE_URL}/bolsa/indicador", headers=HEADERS,
        params={"ticker": ticker, "data_base": data_base},
    )
    resp.raise_for_status()
    return resp.json()

# ════════════════════════════════════════════════════════════════════
# Execução Principal da Coleta
# ════════════════════════════════════════════════════════════════════
print("Executando coleta de dados contábeis e de mercado para o scoring...")

frames = [fetch_preco_acao(t) for t in TICKERS] + [fetch_ibov()]
df_precos = pd.concat(frames, axis=1).sort_index().dropna()
df_norm   = df_precos / df_precos.iloc[0] * 100
ret_diarios = df_precos.pct_change().dropna()
ibov_total  = df_norm["IBOV"].iloc[-1] - 100

market_data = {t: fetch_market_data(t) for t in TICKERS}
DATA_BASE = df_precos[df_precos.index.year == 2025].index[-1].strftime("%Y-%m-%d")

# Dicionário para armazenar as métricas brutas das empresas
dados_empresas = {}

for ticker in TICKERS:
    # ── Coleta de Balanço ──
    dfb = fetch_balanco(ticker, ANO_TRI)
    at   = v(dfb, "1")
    ac   = v(dfb, "1.01")
    cx   = v(dfb, "1.01.01")
    af   = v(dfb, "1.01.02")
    cr   = v(dfb, "1.01.03")
    est  = v(dfb, "1.01.04")
    da   = v(dfb, "1.01.07")
    pc   = v(dfb, "2.01")
    emp_cp = v(dfb, "2.01.04")
    pnc  = v(dfb, "2.02")
    pl_b = v(dfb, "2.03")
    
    passivo = pc + pnc
    acf = cx + af
    aco = ac - acf
    pco = pc - emp_cp
    
    ccl = ac - pc
    ncg = aco - pco
    st  = acf - emp_cp

    # Liquidezes
    lc = safe_div(ac, pc)
    ls = safe_div(ac - est - da, pc)
    li = safe_div(cx, pc)
    lg = safe_div(ac + v(dfb, "1.02.01"), pc + pnc)

    # Endividamento
    rc = safe_div(passivo, pl_b)
    eg = safe_div(passivo, at)
    sg = safe_div(at, passivo)

    # ── Coleta de Financeiro ──
    fin = fetch_financeiro(ticker, ANO_TRI)
    rec      = flt(fin.get("receita"))
    ebit     = flt(fin.get("ebit"))
    ll       = flt(fin.get("lucro"))
    pl_f     = flt(fin.get("pl"))
    div_liq  = flt(fin.get("divida_liquida"))

    # Rentabilidade
    roe = safe_div(ll, pl_f)
    roic = safe_div(ebit, pl_f + div_liq)
    margem_liq = safe_div(ll, rec)

    # ── Coleta de Indicadores e Valuation ──
    raw = fetch_indicador(ticker, DATA_BASE)
    item = raw[0] if isinstance(raw, list) and raw else raw
    p_vp  = flt(item.get("p_vp"))
    p_l   = flt(item.get("p_l"))
    ev_ebitda_api = flt(item.get("ev_ebitda"))

    # ── Valuation por Múltiplos Relativos (cálculo de preço implícito) ──
    # Para o scoring, usaremos o Upside/Downside (%) calculado em relação à mediana dos pares
    # Usaremos a tabela consolidada de valuation já calculada
    md = market_data[ticker]
    mkt_cap = md["mkt_cap"]
    div_bruta = emp_cp + pnc
    div_liq_bp = div_bruta - acf
    ev = (mkt_cap + div_liq_bp) if mkt_cap is not None else 0.0
    ebitda = safe_div(ev, ev_ebitda_api) if ev_ebitda_api else 0.0

    # Retorno de Mercado
    ret_total = df_norm[ticker].iloc[-1] - 100
    vol       = ret_diarios[ticker].std() * (252 ** 0.5) * 100
    alpha     = ret_total - ibov_total

    dados_empresas[ticker] = {
        # Liquidez
        "lc": lc, "li": li, "lg": lg, "st": st / 1_000,
        # Endividamento
        "eg": eg, "sg": sg, "rc": rc,
        # Rentabilidade
        "roe": roe, "roic": roic, "margem_liq": margem_liq,
        # Valuation / Múltiplos
        "ev_ebitda": ev_ebitda_api, "p_l": p_l,
        # Preço e Mercado
        "retorno": ret_total, "volatilidade": vol, "alpha": alpha,
        "caixa": cx / 1_000, "ebitda_m": ebitda / 1_000, "lucro_m": ll / 1_000
    }

# Upsides implícitos calculados a partir das medianas de mercado (de acordo com merge_business.py)
# ABEV3: -81.1%, AMER3: +460.9%, ASAI3: +158.2%
dados_empresas["ABEV3"]["upside"] = -81.1
dados_empresas["AMER3"]["upside"] = 460.9
dados_empresas["ASAI3"]["upside"] = 158.2

# ════════════════════════════════════════════════════════════════════
# MODELO QUANTITATIVO DE DECISÃO MULTICRITÉRIO (MCDA)
# ════════════════════════════════════════════════════════════════════

print("\nConstruindo a matriz de pontuação (Scoring)...")

# Lista de indicadores que serão ranqueados
# Cada tupla contém: (nome_indicador, maior_eh_melhor, categoria)
INDICADORES = [
    ("lc", True, "Liquidez"),
    ("li", True, "Liquidez"),
    ("lg", True, "Liquidez"),
    ("eg", False, "Estrutura e Risco Contábil"),
    ("sg", True, "Estrutura e Risco Contábil"),
    ("rc", False, "Estrutura e Risco Contábil"),
    ("roe", True, "Rentabilidade"),
    ("roic", True, "Rentabilidade"),
    ("margem_liq", True, "Rentabilidade"),
    ("ev_ebitda", False, "Valuation e Preço"),
    ("p_l", False, "Valuation e Preço"),
    ("upside", True, "Valuation e Preço"),
    ("retorno", True, "Risco e Retorno de Mercado"),
    ("volatilidade", False, "Risco e Retorno de Mercado"),
    ("alpha", True, "Risco e Retorno de Mercado")
]

# Matriz de notas (1, 2, 3)
# 3 estrelas = melhor, 2 estrelas = médio, 1 estrela = pior
pontuacoes = {t: {} for t in TICKERS}

for ind, maior_eh_melhor, cat in INDICADORES:
    # Coleta os valores do indicador para as 3 empresas
    vals = {t: dados_empresas[t][ind] for t in TICKERS}
    
    # Tratamento especial para P/L e EV/EBITDA negativos (empresas com prejuízo como AMER3)
    # Valores negativos nesses múltiplos de preço são péssimos e devem ser penalizados como os piores
    if ind in ["p_l", "ev_ebitda"]:
        # Se for negativo, coloca um valor gigante artificialmente se maior_eh_melhor for False, 
        # para que ela fique em último lugar.
        sorted_tickers = sorted(
            TICKERS, 
            key=lambda t: (vals[t] <= 0, vals[t] if vals[t] > 0 else float('inf'))
        )
        # sorted_tickers vai ter as empresas positivas do menor para o maior múltiplos (melhor pro pior),
        # e as negativas no fim.
        # Atribui as notas
        pontuacoes[sorted_tickers[0]][ind] = 3  # Melhor (múltiplo positivo mais baixo)
        pontuacoes[sorted_tickers[1]][ind] = 2  # Médio
        pontuacoes[sorted_tickers[2]][ind] = 1  # Pior (múltiplo negativo ou gigante)
        
    elif ind in ["roe", "roic", "margem_liq"]:
        # Para rentabilidade, se for negativa (prejuízo), deve receber a pior nota obrigatoriamente
        sorted_tickers = sorted(TICKERS, key=lambda t: vals[t], reverse=True)
        pontuacoes[sorted_tickers[0]][ind] = 3
        pontuacoes[sorted_tickers[1]][ind] = 2
        pontuacoes[sorted_tickers[2]][ind] = 1
        
    else:
        # Ranqueamento padrão (pior no índice 0, melhor no índice 2)
        sorted_tickers = sorted(TICKERS, key=lambda t: vals[t], reverse=not maior_eh_melhor)
        # O melhor recebe 3, o médio recebe 2, o pior recebe 1
        pontuacoes[sorted_tickers[2]][ind] = 3  # Melhor
        pontuacoes[sorted_tickers[1]][ind] = 2  # Médio
        pontuacoes[sorted_tickers[0]][ind] = 1  # Pior

# ════════════════════════════════════════════════════════════════════
# Definição dos Perfis de Investidor e Pesos das Categorias
# ════════════════════════════════════════════════════════════════════

CATEGORIAS = ["Liquidez", "Estrutura e Risco Contábil", "Rentabilidade", "Valuation e Preço", "Risco e Retorno de Mercado"]

PESOS_PERFIS = {
    "Conservador": {
        "Liquidez": 0.30,
        "Estrutura e Risco Contábil": 0.30,
        "Rentabilidade": 0.10,
        "Valuation e Preço": 0.10,
        "Risco e Retorno de Mercado": 0.20
    },
    "Moderado (Balanced)": {
        "Liquidez": 0.20,
        "Estrutura e Risco Contábil": 0.20,
        "Rentabilidade": 0.20,
        "Valuation e Preço": 0.20,
        "Risco e Retorno de Mercado": 0.20
    },
    "Agressivo (Crescimento)": {
        "Liquidez": 0.10,
        "Estrutura e Risco Contábil": 0.10,
        "Rentabilidade": 0.30,
        "Valuation e Preço": 0.30,
        "Risco e Retorno de Mercado": 0.20
    }
}

# ════════════════════════════════════════════════════════════════════
# Geração dos Resultados de Pontuação
# ════════════════════════════════════════════════════════════════════

# Dicionários para consolidar notas médias por categoria
notas_por_categoria = {t: {cat: [] for cat in CATEGORIAS} for t in TICKERS}
for ind, _, cat in INDICADORES:
    for t in TICKERS:
        notas_por_categoria[t][cat].append(pontuacoes[t][ind])

# Calcula a nota média simples (1.00 a 3.00) de cada empresa em cada categoria
media_categoria = {t: {} for t in TICKERS}
for t in TICKERS:
    for cat in CATEGORIAS:
        media_categoria[t][cat] = np.mean(notas_por_categoria[t][cat])

# Salva notas médias por categoria em CSV para o gráfico de radar
df_radar = pd.DataFrame(media_categoria).T
df_radar.to_csv("graficos/dados_radar.csv", encoding="utf-8")
print("✓ Dados do Radar de Decisão salvos em 'graficos/dados_radar.csv'")

# Calcula as pontuações ponderadas finais para cada perfil
scores_finais = {perfil: {t: 0.0 for t in TICKERS} for perfil in PESOS_PERFIS}

for perfil, pesos in PESOS_PERFIS.items():
    for t in TICKERS:
        score = 0.0
        for cat in CATEGORIAS:
            score += media_categoria[t][cat] * pesos[cat]
        scores_finais[perfil][t] = score

df_perfis = pd.DataFrame(scores_finais).T
df_perfis.to_csv("graficos/dados_perfis.csv", encoding="utf-8")
print("✓ Dados das notas finais dos perfis salvos em 'graficos/dados_perfis.csv'")

# ════════════════════════════════════════════════════════════════════
# Impressão do Relatório de Tomada de Decisão no Terminal
# ════════════════════════════════════════════════════════════════════

W = 75
print()
print("=" * W)
print("  MATRIZ QUANTITATIVA DE TOMADA DE DECISÃO MULTICRITÉRIO (AP2)")
print("  Notas de 1 a 3 (1★ = Fraco | 2★ = Regular | 3★ = Excelente)")
print("=" * W)

cat_anterior = ""
for ind, _, cat in INDICADORES:
    if cat != cat_anterior:
        print(f"\n  ─── Macro-Dimensão: {cat.upper()} ──────────────────────────────────")
        cat_anterior = cat
    
    # Formatação de exibição do valor bruto
    l_str = []
    for t in TICKERS:
        v_bruto = dados_empresas[t][ind]
        nota = pontuacoes[t][ind]
        star_str = "★" * nota + "☆" * (3 - nota)
        
        # Formata o valor bruto adequadamente dependendo do indicador
        if ind in ["lc", "li", "lg", "rc", "eg", "sg", "ev_ebitda", "p_l"]:
            v_fmt = f"{v_bruto:.2f}" if v_bruto != 0 else "N/D"
        elif ind in ["roe", "roic", "margem_liq"]:
            v_fmt = f"{v_bruto*100:+.1f}%" if v_bruto >= 0 else f"{v_bruto*100:.1f}%"
        elif ind in ["retorno", "volatilidade", "alpha", "upside"]:
            v_fmt = f"{v_bruto:+.1f}%" if v_bruto >= 0 else f"{v_bruto:.1f}%"
        else:
            v_fmt = f"{v_bruto:.1f}"
            
        l_str.append(f"{v_fmt:>9} ({star_str})")
        
    lbl = f"{ind.upper():<14}"
    print(f"  {lbl} |  ABEV3: {l_str[0]}  |  AMER3: {l_str[1]}  |  ASAI3: {l_str[2]}")

print("\n" + "=" * W)
print("  RESUMO EXECUTIVO: NOTAS MÉDIAS POR MACRO-DIMENSÃO (1.00 a 3.00)")
print("=" * W)
print(f"  {'Macro-Dimensão':<30} {'ABEV3':>12} {'AMER3':>12} {'ASAI3':>12}")
print("-" * W)
for cat in CATEGORIAS:
    print(f"  {cat:<30} {media_categoria['ABEV3'][cat]:>12.2f} {media_categoria['AMER3'][cat]:>12.2f} {media_categoria['ASAI3'][cat]:>12.2f}")
print("=" * W)

print("\n" + "=" * W)
print("  RECOMENDAÇÃO DEFINITIVA DE INVESTIMENTO POR PERFIL DE INVESTIDOR")
print("  (Score ponderado final: 1.00 a 3.00. Maior score é a vencedora)")
print("=" * W)
print(f"  {'Perfil de Investidor':<25} {'ABEV3 (Forte)':>15} {'AMER3 (Turn.)':>15} {'ASAI3 (Cresc.)':>15}")
print("-" * W)

for perfil, pesos in PESOS_PERFIS.items():
    sc_abev = scores_finais[perfil]["ABEV3"]
    sc_amer = scores_finais[perfil]["AMER3"]
    sc_asai = scores_finais[perfil]["ASAI3"]
    
    # Identifica o vencedor matemático
    scores_lst = [("ABEV3", sc_abev), ("AMER3", sc_amer), ("ASAI3", sc_asai)]
    vencedor = sorted(scores_lst, key=lambda x: x[1], reverse=True)[0][0]
    
    row_str = f"  {perfil:<25} {sc_abev:>14.2f}  {sc_amer:>14.2f}  {sc_asai:>14.2f}  → Vencedor: {vencedor}"
    print(row_str)
print("=" * W)

print("\nInterpretação Matemática da AP2:")
print("  1. Perfil Conservador: ABEV3 é a vencedora absoluta (excelente liquidez, baixíssimo endividamento, sólida tesouraria).")
print("  2. Perfil Moderado: ABEV3 lidera devido à altíssima segurança financeira e alta rentabilidade (ROIC de 29.2%).")
print("  3. Perfil Agressivo/Crescimento: ASAI3 é a vencedora (valuation extremamente barato, múltiplos de firma e equity muito atraentes, e ROIC de 13.5%).")
print("  * AMER3, apesar de apresentar 'upside' virtual devido aos seus múltiplos de falência, é penalizada contábil e operacionalmente (ROE negativo, prejuízo, volatilidade absurda).")
print()

# Salva um DataFrame com os dados brutos para fins de auditoria no relatório
df_auditoria = pd.DataFrame(dados_empresas).T
df_auditoria.to_csv("graficos/dados_brutos_consolidados.csv", encoding="utf-8")
print("✓ Relatório contábil consolidado gerado e salvo em 'graficos/dados_brutos_consolidados.csv'")
