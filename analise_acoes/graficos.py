import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import numpy as np

BASE_URL = "https://laboratoriodefinancas.com/api/v2"
TOKEN    = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzgwNTcwNzA4LCJpYXQiOjE3Nzc5Nzg3MDgsImp0aSI6IjNmNTBiZWM4OWVkZDQzMWI5NTljZWFkYmFkZTdiNjYyIiwidXNlcl9pZCI6IjExOCJ9.4m2iY0iB32ZKdO6_uZb-H1Cu9zwOXJcenbCHAv-qTFE"
HEADERS  = {"Authorization": f"Bearer {TOKEN}"}
DATA_INI = "2020-01-01"
DATA_FIM = "2025-12-31"
TICKERS  = ["ABEV3", "AMER3", "ASAI3"]

CORES = {
    "ABEV3": "#F4A900",
    "AMER3": "#E8002D",
    "ASAI3": "#00843D",
    "IBOV":  "#1F3C88",
}

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor":   "white",
    "axes.grid":        True,
    "grid.alpha":       0.3,
    "grid.linestyle":   "--",
    "font.family":      "sans-serif",
})


def fetch_acao(ticker):
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


# ── Coleta e preparação ──────────────────────────────────────────────
print("Buscando dados para os gráficos...")
frames = [fetch_acao(t) for t in TICKERS] + [fetch_ibov()]
df_precos = pd.concat(frames, axis=1).sort_index()

df_norm = df_precos.dropna().copy()
df_norm = df_norm / df_norm.iloc[0] * 100

retornos_diarios = df_precos.dropna().pct_change().dropna()

data_inicio = df_norm.index[0].strftime("%d/%m/%Y")
data_fim_str = df_norm.index[-1].strftime("%d/%m/%Y")


# ════════════════════════════════════════════════════════════════════
# GRÁFICO 1 — Preço normalizado base 100
# ════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(14, 6))

for col in df_norm.columns:
    ax.plot(df_norm.index, df_norm[col], label=col, color=CORES[col], linewidth=1.8)

# Linha de referência em 100 (ponto de partida)
ax.axhline(100, color="black", linestyle=":", linewidth=0.8, alpha=0.4)

# Eventos-chave com linha vertical + label no topo do gráfico
eventos = [
    ("2020-03-23", "Mínimo COVID"),
    ("2021-03-05", "IPO ASAI3"),
    ("2023-01-11", "Fraude Americanas"),
]
for data_ev, label in eventos:
    x = pd.Timestamp(data_ev)
    ax.axvline(x, color="gray", linestyle="--", linewidth=1, alpha=0.6)
    ax.text(
        x, 1.01, label,
        transform=ax.get_xaxis_transform(),
        fontsize=8, ha="center", color="dimgray",
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="lightgray", alpha=0.8),
    )

ax.set_title(
    f"Desempenho das Ações vs IBOV — Base 100  ({data_inicio} → {data_fim_str})",
    fontsize=13, fontweight="bold", pad=14,
)
ax.set_ylabel("Valor (Base 100 = início do período)")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.legend(loc="upper left", framealpha=0.9)
plt.tight_layout()
plt.savefig("grafico_base100.png", dpi=150, bbox_inches="tight")
plt.show()
print("✓ grafico_base100.png salvo")


# ════════════════════════════════════════════════════════════════════
# GRÁFICO 2 — Retorno por ano (barras agrupadas)
# ════════════════════════════════════════════════════════════════════
df_anual = df_precos.dropna().resample("YE").last()
retornos_anuais = df_anual.pct_change().dropna() * 100

anos = [str(i.year) for i in retornos_anuais.index]
colunas = list(retornos_anuais.columns)
n = len(colunas)
x = np.arange(len(anos))
largura = 0.18
offsets = np.linspace(-(n - 1) / 2 * largura, (n - 1) / 2 * largura, n)

fig, ax = plt.subplots(figsize=(13, 5))

for i, col in enumerate(colunas):
    vals = retornos_anuais[col].values
    bars = ax.bar(x + offsets[i], vals, largura, label=col, color=CORES[col], alpha=0.88)
    for bar, val in zip(bars, vals):
        y_text = bar.get_height() + (1.5 if val >= 0 else -1.5)
        va = "bottom" if val >= 0 else "top"
        ax.text(
            bar.get_x() + bar.get_width() / 2, y_text,
            f"{val:+.0f}%", ha="center", va=va, fontsize=7, fontweight="bold",
        )

ax.axhline(0, color="black", linewidth=0.9)
ax.set_title("Retorno Anual por Ativo (%)", fontsize=13, fontweight="bold", pad=12)
ax.set_ylabel("Retorno (%)")
ax.set_xticks(x)
ax.set_xticklabels(anos)
ax.legend(loc="lower left", framealpha=0.9)
plt.tight_layout()
plt.savefig("grafico_retorno_anual.png", dpi=150, bbox_inches="tight")
plt.show()
print("✓ grafico_retorno_anual.png salvo")


# ════════════════════════════════════════════════════════════════════
# GRÁFICO 3 — Heatmap de correlação
# ════════════════════════════════════════════════════════════════════
corr = retornos_diarios.corr()

fig, ax = plt.subplots(figsize=(6, 5))
sns.heatmap(
    corr,
    annot=True,
    fmt=".2f",
    cmap="RdYlGn",
    vmin=-1, vmax=1,
    square=True,
    linewidths=0.5,
    linecolor="white",
    ax=ax,
    annot_kws={"size": 12, "weight": "bold"},
)
ax.set_title(
    "Correlação entre Ativos\n(retornos diários)",
    fontsize=12, fontweight="bold", pad=12,
)
plt.tight_layout()
plt.savefig("grafico_correlacao.png", dpi=150, bbox_inches="tight")
plt.show()
print("✓ grafico_correlacao.png salvo")

print("\nTodos os gráficos gerados e salvos na pasta analise_acoes/")
