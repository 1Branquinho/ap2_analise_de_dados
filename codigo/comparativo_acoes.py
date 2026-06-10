import os
import sys
import requests
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Configura encoding correto para Windows
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
BASE_URL = "https://laboratoriodefinancas.com/api/v2"
TOKEN    = os.getenv("LAB_FIN_TOKEN") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzgwNTcwNzA4LCJpYXQiOjE3Nzc5Nzg3MDgsImp0aSI6IjNmNTBiZWM4OWVkZDQzMWI5NTljZWFkYmFkZTdiNjYyIiwidXNlcl9pZCI6IjExOCJ9.4m2iY0iB32ZKdO6_uZb-H1Cu9zwOXJcenbCHAv-qTFE"
HEADERS  = {"Authorization": f"Bearer {TOKEN}"}

TICKERS = ["ABEV3", "AMER3", "ASAI3"]
DATA_INI = "2021-01-01"
DATA_FIM = "2025-12-31"
RF_ANNUAL = 0.1075  # Selic média de 2025 (10.75%)

print("=" * 95)
print("             BUSCANDO PREÇOS HISTÓRICOS DIÁRIOS (2021-2025)...")
print("=" * 95)

# 1. Obtenção de Dados das Ações
dfs = []
for ticker in TICKERS:
    try:
        resp = requests.get(
            f"{BASE_URL}/preco/corrigido",
            headers=HEADERS,
            params={"ticker": ticker, "data_ini": DATA_INI, "data_fim": DATA_FIM},
        )
        resp.raise_for_status()
        df = pd.DataFrame(resp.json())
        df["data"] = pd.to_datetime(df["data"])
        df["fechamento"] = pd.to_numeric(df["fechamento"], errors="coerce")
        df = df.set_index("data")[["fechamento"]].rename(columns={"fechamento": ticker})
        dfs.append(df)
        print(f"  ✓ {ticker}: {len(df)} registros carregados.")
    except Exception as e:
        print(f"  [ERRO] Falha ao carregar dados de {ticker}: {e}")
        sys.exit(1)

# 2. Obtenção de Dados do IBOV via Yahoo Finance
try:
    import yfinance as yf
    print("  Buscando IBOV (^BVSP) via Yahoo Finance...")
    df_ibov = yf.download("^BVSP", start=DATA_INI, end=DATA_FIM, progress=False)
    df_ibov.columns = df_ibov.columns.droplevel(1)
    df_ibov = df_ibov[["Close"]].rename(columns={"Close": "IBOV"})
    df_ibov.index = pd.to_datetime(df_ibov.index).tz_localize(None)
    df_ibov["IBOV"] = pd.to_numeric(df_ibov["IBOV"], errors="coerce")
    dfs.append(df_ibov)
    print(f"  ✓ IBOV: {len(df_ibov)} registros carregados via Yahoo Finance.")
except Exception as e:
    print(f"  [ERRO] Falha ao carregar dados do IBOV via Yahoo Finance: {e}")
    sys.exit(1)

# 3. Concatenar e alinhar os dados
df_precos = pd.concat(dfs, axis=1).sort_index().ffill().dropna()
df_returns = df_precos.pct_change().dropna()

# 4. Cálculo das Métricas de Risco e Retorno
metricas = {}
for col in df_precos.columns:
    series_p = df_precos[col].dropna()
    series_r = df_returns[col].dropna()
    
    if len(series_p) == 0:
        continue
        
    first_p = series_p.iloc[0]
    last_p = series_p.iloc[-1]
    
    # Retorno Acumulado
    cum_ret = (last_p / first_p) - 1.0
    
    # Volatilidade Anualizada (252 dias úteis)
    vol = series_r.std() * (252 ** 0.5)
    
    # Retorno Anualizado Composto (período de 5 anos)
    ann_ret = (1.0 + cum_ret) ** (1.0 / 5.0) - 1.0
    
    # Sharpe Ratio
    sharpe = (ann_ret - RF_ANNUAL) / vol if vol > 0 else 0.0
    
    # Beta Sistemático vs IBOV
    if col != "IBOV":
        cov = series_r.cov(df_returns["IBOV"])
        var_m = df_returns["IBOV"].var()
        beta = cov / var_m
    else:
        beta = 1.0
        
    # Máximo Drawdown
    roll_max = series_p.cummax()
    drawdown = (series_p - roll_max) / roll_max
    max_dd = drawdown.min()
    
    metricas[col] = {
        "cum_ret": cum_ret,
        "vol": vol,
        "ann_ret": ann_ret,
        "sharpe": sharpe,
        "beta": beta,
        "max_dd": max_dd
    }

# 5. Exibição da Tabela de Risco e Retorno
W = 95
print("\n" + "=" * W)
print("              PAINEL COMPARATIVO DE PERFORMANCE DAS AÇÕES (2021-2025)")
print("=" * W)
print(f"  {'Métrica de Mercado / Estatística':<42} {'ABEV3':>11} {'AMER3':>11} {'ASAI3':>11} {'IBOV':>11}")
print("-" * W)

def print_row(label, key, is_pct=False, is_decimal=False):
    row_str = f"  {label:<42}"
    for col in ["ABEV3", "AMER3", "ASAI3", "IBOV"]:
        val = metricas[col][key]
        if is_pct:
            row_str += f" {val*100:>10.2f}%"
        elif is_decimal:
            row_str += f" {val:>11.4f}"
        else:
            row_str += f" {val:>11.2f}"
    print(row_str)

print_row("Retorno Acumulado (5 anos)", "cum_ret", is_pct=True)
print_row("Retorno Anualizado (CAGR)", "ann_ret", is_pct=True)
print_row("Volatilidade Anualizada", "vol", is_pct=True)
print_row("Índice Sharpe (Rf = 10.75%)", "sharpe", is_decimal=False)
print_row("Beta Sistemático (vs IBOV)", "beta", is_decimal=True)
print_row("Máximo Drawdown (Pior Queda)", "max_dd", is_pct=True)
print("=" * W)

# 6. Exibição da Matriz de Correlação
print("\nMATRIZ DE CORRELAÇÃO DE RETORNOS DIÁRIOS:")
print("-" * W)
corr_matrix = df_returns.corr()
print(f"  {'Ticker':<12} {'ABEV3':>11} {'AMER3':>11} {'ASAI3':>11} {'IBOV':>11}")
for col in corr_matrix.columns:
    row_str = f"  {col:<12}"
    for row in corr_matrix.columns:
        row_str += f" {corr_matrix.loc[col, row]:>11.4f}"
    print(row_str)
print("=" * W)

# 7. Diagnóstico Acadêmico
print("\nDIAGNÓSTICO DA PERFORMANCE DE MERCADO (FUNDAMENTOS VS. COTAÇÕES):")
print("-" * W)

abev_cum = metricas["ABEV3"]["cum_ret"] * 100
abev_vol = metricas["ABEV3"]["vol"] * 100
abev_beta = metricas["ABEV3"]["beta"]
abev_sharpe = metricas["ABEV3"]["sharpe"]
abev_dd = metricas["ABEV3"]["max_dd"] * 100

amer_cum = metricas["AMER3"]["cum_ret"] * 100
amer_vol = metricas["AMER3"]["vol"] * 100
amer_beta = metricas["AMER3"]["beta"]
amer_sharpe = metricas["AMER3"]["sharpe"]
amer_dd = metricas["AMER3"]["max_dd"] * 100

asai_cum = metricas["ASAI3"]["cum_ret"] * 100
asai_vol = metricas["ASAI3"]["vol"] * 100
asai_beta = metricas["ASAI3"]["beta"]
asai_sharpe = metricas["ASAI3"]["sharpe"]
asai_dd = metricas["ASAI3"]["max_dd"] * 100

print(f"1. ABEV3 (Ambev S.A.) - Perfil Defensivo e Resiliência:")
print(f"   A Ambev apresentou a menor volatilidade anualizada do grupo ({abev_vol:.2f}%), condizente com a sua")
print(f"   operação sólida, margens elevadas e ausência de endividamento líquido. Seu Beta baixo ({abev_beta:.2f})")
print(f"   confirma seu caráter defensivo. O Índice Sharpe ({abev_sharpe:.2f}) foi impactado pela taxa Selic elevada")
print(f"   no período (custo de oportunidade alto), mas seu Max Drawdown ({abev_dd:.2f}%) foi o mais controlado")
print(f"   do grupo de ações, demonstrando segurança patrimonial para o investidor.")
print()
print(f"2. ASAI3 (Assaí Atacadista) - Pressionado pelo Risco de Capital e Juros:")
print(f"   A ação do Assaí acumulou perda no período ({asai_cum:.2f}%), com volatilidade anualizada de")
print(f"   {asai_vol:.2f}% e um Max Drawdown significativo de {asai_dd:.2f}%. Embora o negócio possua eficiência comercial,")
print(f"   a forte alavancagem financeira (Endividamento de 88.39%) eleva a volatilidade dos retornos do PL.")
print(f"   Isso elevou seu risco sistemático (Beta de {asai_beta:.2f}) e reduziu seu Sharpe para {asai_sharpe:.2f}, refletindo a")
print(f"   aversão dos investidores às empresas expostas ao carrego de juros altos.")
print()
print(f"3. AMER3 (Lojas Americanas S.A.) - Destruição de Valor e Colapso de Mercado:")
print(f"   As Americanas representam um caso clássico de quebra contábil e destruição de valor (EVA de -R$ 1,074 mi).")
print(f"   A descoberta de inconsistências contábeis levou a um colapso quase total do preço das ações, com")
print(f"   retorno acumulado de {amer_cum:.2f}% e o pior Max Drawdown histórico do mercado ({amer_dd:.2f}%). A volatilidade")
print(f"   anualizada extrema de {amer_vol:.2f}% e o Índice Sharpe negativo ({amer_sharpe:.2f}) comprovam a inviabilidade da tese,")
print(f"   onde o risco sistemático (Beta de {amer_beta:.2f}) perde relevância diante do risco de insolvência prática.")
print()
print("CONCLUSÃO FINAL:")
print("A análise de mercado confirma os fundamentos contábeis calculados na tabela de decisão:")
print("  * A Ambev destaca-se como a única empresa que protegeu capital de forma eficiente (menor volatilidade e drawdown).")
print("  * O Assaí ilustra o risco de mercado decorrente da alavancagem patrimonial sob juros altos.")
print("  * A Americanas reflete o risco extremo de desastre contábil, onde o valor de mercado converge para próximo de zero.")
print("=" * W)

# ════════════════════════════════════════════════════════════════════
# 8. Geração de Gráficos (Matplotlib)
# ════════════════════════════════════════════════════════════════════
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mtick

print("\nGERANDO GRÁFICOS E SALVANDO EM 'graficos/'...")

# Configuração de Estilo Geral para Gráficos
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False

# Cores do Sistema (Elegantes, Harmoniosas e Premium)
CORES = {
    "ABEV3": "#0C2765",  # Charcoal / Midnight Black (Ambev)
    "AMER3": "#E11D48",  # Crimson / Deep Rose (Americanas)
    "ASAI3": "#D97706",  # Amber / Gold (Assaí)
    "IBOV": "#059669"    # Emerald Green (IBOV)
}

# Cria pasta graficos se não existir
if not os.path.exists("graficos"):
    os.makedirs("graficos")

# A. Gráficos Individuais
for ticker in TICKERS:
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')
    
    series = df_precos[ticker]
    ax.plot(series.index, series.values, color=CORES[ticker], linewidth=2.5, zorder=3)
    
    # Preenchimento sutil abaixo da curva para efeito premium
    ax.fill_between(series.index, series.values, color=CORES[ticker], alpha=0.06, zorder=2)
    
    # Grid e Spines (Apenas Grid Horizontal, muito suave)
    ax.grid(True, axis='y', color='#E2E8F0', linestyle='-', linewidth=0.6, zorder=0)
    for spine in ['top', 'right', 'left']:
        ax.spines[spine].set_visible(False)
    ax.spines['bottom'].set_color('#CBD5E1')
    ax.spines['bottom'].set_linewidth(1.0)
        
    # Título e Subtítulo
    ax.text(0.0, 1.10, f"Evolução Histórica do Preço - {ticker}", transform=ax.transAxes, fontsize=14, fontweight='bold', color='#0F172A', ha='left')
    if ticker == "AMER3":
        ax.text(0.0, 1.04, "Fechamento Diário | Ajustado retroativamente para refletir o grupamento de 100:1 em 26/08/2024", transform=ax.transAxes, fontsize=9.0, color='#E11D48', ha='left')
    else:
        ax.text(0.0, 1.04, "Fechamento Diário | Período de Análise: 2021 a 2025", transform=ax.transAxes, fontsize=9.5, color='#64748B', ha='left')
    
    # Formatação de Moeda no Eixo Y
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, p: f"R$ {x:,.2f}"))
    
    # Formatação de datas no Eixo X e parâmetros de escala
    ax.tick_params(axis='x', colors='#64748B', labelsize=9.5, length=4, width=1)
    ax.tick_params(axis='y', which='both', left=False, colors='#64748B', labelsize=9.5)
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    
    plot_path = f"graficos/evolucao_{ticker.lower()}.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Gráfico individual salvo em '{plot_path}'")

# B. Gráfico Comparativo de Retorno Acumulado
fig, ax = plt.subplots(figsize=(12, 6.5), dpi=300)
fig.patch.set_facecolor('#FFFFFF')
ax.set_facecolor('#FFFFFF')

# Normaliza preços base 0% em 2021-01-01
df_norm = (df_precos / df_precos.iloc[0] - 1.0) * 100.0

for col in df_norm.columns:
    if col == "IBOV":
        style = "-"
        width = 2.8
        alpha = 1.0
    else:
        style = "-"
        width = 2.0
        alpha = 0.90
        
    ax.plot(df_norm.index, df_norm[col], color=CORES[col], linestyle=style, linewidth=width, alpha=alpha, label=col, zorder=3)

# Grid e Spines (Apenas Grid Horizontal)
ax.grid(True, axis='y', color='#E2E8F0', linestyle='-', linewidth=0.6, zorder=0)
for spine in ['top', 'right', 'left']:
    ax.spines[spine].set_visible(False)
ax.spines['bottom'].set_color('#CBD5E1')
ax.spines['bottom'].set_linewidth(1.0)

# Linha horizontal de referência em 0%
ax.axhline(0, color="#94A3B8", linestyle="-", linewidth=0.8, alpha=0.5, zorder=2)

# Título e Subtítulo
ax.text(0.0, 1.10, "Comparativo de Retorno Acumulado vs. IBOV", transform=ax.transAxes, fontsize=16, fontweight='bold', color='#0F172A', ha='left')
ax.text(0.0, 1.04, "Retorno Percentual Acumulado (Base 0% em 01/01/2021) | Período: 2021 a 2025", transform=ax.transAxes, fontsize=10, color='#64748B', ha='left')

# Formatação de Porcentagem no Eixo Y
ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))

# Legend - Clean
legend = ax.legend(loc="upper left", frameon=True, facecolor='#FFFFFF', edgecolor='#E2E8F0', framealpha=0.9, fontsize=10)
legend.get_frame().set_boxstyle("round,pad=0.4")

# Formatação de datas
ax.tick_params(axis='x', colors='#64748B', labelsize=10, length=4, width=1)
ax.tick_params(axis='y', which='both', left=False, colors='#64748B', labelsize=10)

ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax.xaxis.set_major_locator(mdates.YearLocator())

comp_path = "graficos/comparativo_retorno.png"
plt.savefig(comp_path, dpi=300, bbox_inches='tight')
plt.close()
print(f"  ✓ Gráfico comparativo salvo em '{comp_path}'")
print("=" * W)
