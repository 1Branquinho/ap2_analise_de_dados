import os
import sys
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

# Garante o encoding correto no Windows
sys.stdout.reconfigure(encoding='utf-8')

# Cria a pasta graficos se ela não existir
if not os.path.exists("graficos"):
    os.makedirs("graficos")

# Configurações globais de estilo para Matplotlib (Aesthetics Premium)
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor":   "white",
    "axes.grid":        True,
    "grid.alpha":       0.25,
    "grid.linestyle":   "--",
    "font.family":      "sans-serif",
    "font.sans-serif":  ["DejaVu Sans", "Arial", "Liberation Sans", "sans-serif"],
    "axes.edgecolor":   "#D3D3D3",
    "axes.linewidth":   0.8,
})

# Esquema de Cores Premium Corporativo
CORES = {
    "ABEV3": "#F4A900",  # Dourado Ambev
    "AMER3": "#E8002D",  # Vermelho Americanas
    "ASAI3": "#00843D",  # Verde Assaí
    "IBOV":  "#1F3C88",  # Azul Escuro IBOV
}

BASE_URL = "https://laboratoriodefinancas.com/api/v2"
TOKEN    = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzgwNTcwNzA4LCJpYXQiOjE3Nzc5Nzg3MDgsImp0aSI6IjNmNTBiZWM4OWVkZDQzMWI5NTljZWFkYmFkZTdiNjYyIiwidXNlcl9pZCI6IjExOCJ9.4m2iY0iB32ZKdO6_uZb-H1Cu9zwOXJcenbCHAv-qTFE"
HEADERS  = {"Authorization": f"Bearer {TOKEN}"}

TICKERS  = ["ABEV3", "AMER3", "ASAI3"]
DATA_INI = "2020-01-01"
DATA_FIM = "2025-12-31"

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
# 1. GERAÇÃO DOS GRÁFICOS DE CRESCIMENTO INDIVIDUAL DAS AÇÕES (2021-2025)
# ════════════════════════════════════════════════════════════════════
print("Buscando dados de preços de fechamento históricos...")

frames = [fetch_preco_acao(t) for t in TICKERS] + [fetch_ibov()]
df_precos = pd.concat(frames, axis=1).sort_index().dropna()  # Alinhado pelo IPO da ASAI3 (05/03/2021)
df_norm = df_precos / df_precos.iloc[0] * 100

data_ini_str = df_precos.index[0].strftime("%d/%m/%Y")
data_fim_str = df_precos.index[-1].strftime("%d/%m/%Y")

print("Plotando gráficos de crescimento individual...")

# ── 1.A. Gráficos em Painel Único (Subplots 1x3 para Slides/Relatório) ──
fig, axes = plt.subplots(1, 3, figsize=(18, 5.5), sharex=False)
fig.suptitle(
    f"Evolução Individual do Preço das Ações (ref: Corrigidos) \nPeríodo: {data_ini_str} a {data_fim_str}",
    fontsize=14, fontweight="bold", y=1.02
)

titulos_label = {
    "ABEV3": "Ambev S.A. (ABEV3) - Retorno: +29.3%\nFortaleza de Caixa Contratíclica",
    "ASAI3": "Assaí Atacadista (ASAI3) - Retorno: -47.2%\nAlavancagem Sensível aos Juros",
    "AMER3": "Lojas Americanas (AMER3) - Retorno: -99.9%\nColapso e Reestruturação Judicial",
}

for i, ticker in enumerate(TICKERS):
    ax = axes[i]
    dados_preco = df_precos[ticker]
    retorno = (dados_preco.iloc[-1] / dados_preco.iloc[0] - 1) * 100
    
    # Plota a linha de preço nominal
    ax.plot(df_precos.index, dados_preco, color=CORES[ticker], linewidth=2.2, label=ticker)
    
    # Customização visual do painel
    ax.set_title(titulos_label[ticker], fontsize=11, fontweight="bold", pad=10)
    ax.set_ylabel("Preço Nominal da Ação (R$)")
    ax.set_xlabel("Ano")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    
    # Destaca preço inicial e final no gráfico
    p_ini, p_fim = dados_preco.iloc[0], dados_preco.iloc[-1]
    ax.scatter([dados_preco.index[0], dados_preco.index[-1]], [p_ini, p_fim], color="black", zorder=5, s=40)
    ax.annotate(f"R$ {p_ini:.2f}\n(Início)", xy=(dados_preco.index[0], p_ini), xytext=(10, -5),
                textcoords="offset points", fontsize=8, color="#555555", fontweight="bold")
    ax.annotate(f"R$ {p_fim:.2f}\n(Fim)", xy=(dados_preco.index[-1], p_fim), xytext=(-35, 10),
                textcoords="offset points", fontsize=8, color="black", fontweight="bold")

plt.tight_layout()
caminho_painel = "graficos/crescimento_individual_consolidado.png"
plt.savefig(caminho_painel, dpi=150, bbox_inches="tight")
plt.close()
print(f"✓ Gráfico Consolidado em Painel salvo em '{caminho_painel}'")


# ── 1.B. Gráficos de Crescimento Acumulado (%) Individuais (Arquivos Separados) ──
for ticker in TICKERS:
    fig, ax = plt.subplots(figsize=(9, 4.5))
    rentab_acumulada = df_norm[ticker] - 100
    
    # Plota rentabilidade acumulada (%)
    ax.plot(df_norm.index, rentab_acumulada, color=CORES[ticker], linewidth=2.5, label=f"Rentab. {ticker}")
    ax.axhline(0, color="black", linestyle="--", linewidth=0.8, alpha=0.5)
    
    ax.set_title(f"Rentabilidade Acumulada (%) das Ações: {ticker}\nPeríodo: {data_ini_str} → {data_fim_str}", fontsize=12, fontweight="bold")
    ax.set_ylabel("Rentabilidade Acumulada (%)")
    ax.set_xlabel("Ano")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    
    # Adiciona anotação final de rentabilidade no gráfico
    r_fim = rentab_acumulada.iloc[-1]
    ax.scatter(rentab_acumulada.index[-1], r_fim, color="black", zorder=5, s=45)
    ax.text(
        rentab_acumulada.index[-1], r_fim + (2 if r_fim >= 0 else -6),
        f"{r_fim:+.1f}%", fontsize=10, fontweight="bold", ha="right",
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=CORES[ticker], alpha=0.8)
    )
    
    plt.tight_layout()
    caminho_ind = f"graficos/crescimento_acumulado_{ticker.lower()}.png"
    plt.savefig(caminho_ind, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"✓ Gráfico Individual de Rentabilidade salvo em '{caminho_ind}'")


# ════════════════════════════════════════════════════════════════════
# 2. GRÁFICO DE RADAR - NOTAS POR CATEGORIA (MCDA DECISÃO)
# ════════════════════════════════════════════════════════════════════
print("Carregando dados para o Gráfico de Radar...")

caminho_csv_radar = "graficos/dados_radar.csv"
if not os.path.exists(caminho_csv_radar):
    print("  [ERRO] dados_radar.csv não foi encontrado! Execute 'score_decisao.py' primeiro.")
    sys.exit(1)

df_radar = pd.read_csv(caminho_csv_radar, index_col=0)

# Variáveis do Radar
categories = list(df_radar.columns)
N = len(categories)

# Ângulos de cada eixo no círculo
angles = [n / float(N) * 2 * np.pi for n in range(N)]
angles += angles[:1]  # Fecha o círculo

fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

# Ajusta posição do primeiro eixo para o topo
ax.set_theta_offset(np.pi / 2)
ax.set_theta_direction(-1)

# Eixos e labels das categorias
plt.xticks(angles[:-1], categories, color="#333333", size=10, fontweight="bold")

# Rótulos das notas (Y-axis)
ax.set_rlabel_position(0)
plt.yticks([1.0, 1.5, 2.0, 2.5, 3.0], ["1.0", "1.5", "2.0", "2.5", "3.0"], color="gray", size=8)
plt.ylim(0.5, 3.1)

# Desenha as linhas das empresas no radar
for ticker in TICKERS:
    values = list(df_radar.loc[ticker].values)
    values += values[:1]  # Fecha o círculo
    
    # Plota a linha
    ax.plot(angles, values, linewidth=2.5, linestyle="solid", label=ticker, color=CORES[ticker])
    # Preenche a área sob a linha
    ax.fill(angles, values, color=CORES[ticker], alpha=0.15)

ax.set_title(
    "Matriz Comparativa de Notas por Macro-Dimensão\n(Radar de Decisão Multicritério - AP2)",
    fontsize=13, fontweight="bold", pad=25
)
plt.legend(loc="upper right", bbox_to_anchor=(1.15, 1.1), framealpha=0.9, fontsize=10)

plt.tight_layout()
caminho_radar = "graficos/grafico_radar.png"
plt.savefig(caminho_radar, dpi=150, bbox_inches="tight")
plt.close()
print(f"✓ Gráfico de Radar salvo em '{caminho_radar}'")


# ════════════════════════════════════════════════════════════════════
# 3. GRÁFICO DE BARRAS - NOTAS FINAIS POR PERFIL DE INVESTIDOR
# ════════════════════════════════════════════════════════════════════
print("Carregando dados para o Gráfico de Perfis...")

caminho_csv_perfis = "graficos/dados_perfis.csv"
if not os.path.exists(caminho_csv_perfis):
    print("  [ERRO] dados_perfis.csv não foi encontrado! Execute 'score_decisao.py' primeiro.")
    sys.exit(1)

df_perfis = pd.read_csv(caminho_csv_perfis, index_col=0)

fig, ax = plt.subplots(figsize=(10, 5.5))

# Parâmetros de barras agrupadas
perfis = list(df_perfis.index)
x = np.arange(len(perfis))
largura = 0.22

# Plota cada empresa
for i, ticker in enumerate(TICKERS):
    scores = df_perfis[ticker].values
    bars = ax.bar(x + (i - 1) * largura, scores, largura, label=ticker, color=CORES[ticker], alpha=0.88)
    
    # Adiciona o valor no topo de cada barra
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f"{height:.2f}",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 pontos de offset vertical
                    textcoords="offset points",
                    ha="center", va="bottom", fontsize=8.5, fontweight="bold")

# Configurações do gráfico
ax.axhline(1.0, color="gray", linestyle=":", linewidth=0.8, alpha=0.5)
ax.axhline(2.0, color="gray", linestyle=":", linewidth=0.8, alpha=0.5)
ax.axhline(3.0, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)

ax.set_title("Recomendação Final: Score Ponderado por Perfil de Investidor\n(Notas de 1.00 a 3.00 | Maior nota é a vencedora)", fontsize=12, fontweight="bold", pad=12)
ax.set_ylabel("Score de Investimento Ponderado")
ax.set_xticks(x)
ax.set_xticklabels(perfis, fontsize=10, fontweight="bold")
ax.set_ylim(0, 3.4)
ax.legend(loc="lower left", framealpha=0.9, fontsize=10)

plt.tight_layout()
caminho_perfis = "graficos/grafico_perfis.png"
plt.savefig(caminho_perfis, dpi=150, bbox_inches="tight")
plt.close()
print(f"✓ Gráfico de Perfis de Investidor salvo em '{caminho_perfis}'")

print("\nVisualizações profissionais geradas e salvas com sucesso na pasta graficos/!")
