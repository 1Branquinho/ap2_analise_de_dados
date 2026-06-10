import os
import sys
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from dotenv import load_dotenv

# Configura encoding correto para Windows
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
BASE_URL = "https://laboratoriodefinancas.com/api/v2"
TOKEN    = os.getenv("LAB_FIN_TOKEN") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzgwNTcwNzA4LCJpYXQiOjE3Nzc5Nzg3MDgsImp0aSI6IjNmNTBiZWM4OWVkZDQzMWI5NTljZWFkYmFkZTdiNjYyIiwidXNlcl9pZCI6IjExOCJ9.4m2iY0iB32ZKdO6_uZb-H1Cu9zwOXJcenbCHAv-qTFE"
HEADERS  = {"Authorization": f"Bearer {TOKEN}"}

TICKERS  = ["ABEV3", "AMER3", "ASAI3"]
DATA_INI = "2021-01-01"
DATA_FIM = "2025-12-31"

# Parâmetros da Simulação
N_SIMULACOES = 10_000
N_DIAS       = 252  # 1 ano de pregões
SEED         = 42   # Para reprodutibilidade

# Configuração Visual Global
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False

CORES = {
    "ABEV3": "#0F172A",
    "AMER3": "#E11D48",
    "ASAI3": "#D97706",
}

CORES_FUNIL = {
    "ABEV3": {"median": "#0F172A", "ci": "#3B82F6", "paths": "#93C5FD"},
    "AMER3": {"median": "#E11D48", "ci": "#F43F5E", "paths": "#FDA4AF"},
    "ASAI3": {"median": "#D97706", "ci": "#F59E0B", "paths": "#FCD34D"},
}

NOMES = {
    "ABEV3": "Ambev S.A.",
    "AMER3": "Americanas S.A.",
    "ASAI3": "Assaí Atacadista",
}

# Cria pasta de saída
if not os.path.exists("graficos"):
    os.makedirs("graficos")

W = 95
print("=" * W)
print("        SIMULAÇÃO DE MONTE CARLO — PROJEÇÃO DE COTAÇÕES (2026)")
print("=" * W)
print(f"  Parâmetros: {N_SIMULACOES:,} simulações | {N_DIAS} dias úteis | Seed = {SEED}")
print("=" * W)

# ════════════════════════════════════════════════════════════════════
# 1. Obtenção de Dados Históricos
# ════════════════════════════════════════════════════════════════════
print("\n  CARREGANDO PREÇOS HISTÓRICOS (2021-2025)...")

precos = {}
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
        df = df.set_index("data")[["fechamento"]].rename(columns={"fechamento": ticker}).sort_index()
        precos[ticker] = df
        print(f"    ✓ {ticker}: {len(df)} registros carregados.")
    except Exception as e:
        print(f"    [ERRO] {ticker}: {e}")
        sys.exit(1)

# ════════════════════════════════════════════════════════════════════
# 2. Cálculo dos Parâmetros Estatísticos
# ════════════════════════════════════════════════════════════════════
print(f"\n{'=' * W}")
print("  PARÂMETROS ESTATÍSTICOS PARA SIMULAÇÃO (Movimento Browniano Geométrico)")
print(f"{'=' * W}")
print(f"  {'Ticker':<12} {'Último Preço (R$)':>18} {'μ diário':>14} {'σ diário':>14} {'μ anual':>14} {'σ anual':>14}")
print(f"  {'-' * 86}")

parametros = {}
for ticker in TICKERS:
    series = precos[ticker][ticker].dropna()
    retornos = series.pct_change().dropna()

    S0    = series.iloc[-1]
    mu    = retornos.mean()
    sigma = retornos.std()

    mu_anual    = mu * 252
    sigma_anual = sigma * np.sqrt(252)

    parametros[ticker] = {"S0": S0, "mu": mu, "sigma": sigma}

    print(f"  {ticker:<12} {S0:>18,.2f} {mu:>14.6f} {sigma:>14.6f} {mu_anual * 100:>13.2f}% {sigma_anual * 100:>13.2f}%")

print(f"{'=' * W}")

# ════════════════════════════════════════════════════════════════════
# 3. Execução da Simulação de Monte Carlo
# ════════════════════════════════════════════════════════════════════
print("\n  EXECUTANDO SIMULAÇÃO DE MONTE CARLO...")

np.random.seed(SEED)
resultados = {}

for ticker in TICKERS:
    S0    = parametros[ticker]["S0"]
    mu    = parametros[ticker]["mu"]
    sigma = parametros[ticker]["sigma"]

    # Gera choques aleatórios: matriz (N_DIAS x N_SIMULACOES)
    epsilon = np.random.normal(0, 1, (N_DIAS, N_SIMULACOES))

    # Calcula retornos diários simulados via Movimento Browniano Geométrico
    drift = (mu - 0.5 * sigma ** 2)
    retornos_sim = np.exp(drift + sigma * epsilon)

    # Constrói matriz de caminhos de preços
    caminhos = np.zeros((N_DIAS + 1, N_SIMULACOES))
    caminhos[0] = S0

    for t in range(1, N_DIAS + 1):
        caminhos[t] = caminhos[t - 1] * retornos_sim[t - 1]

    # Garante que nenhum preço fique abaixo de zero
    caminhos = np.maximum(caminhos, 0.0)

    # Calcula estatísticas finais (último dia projetado)
    precos_finais = caminhos[-1]

    mediana   = np.median(precos_finais)
    media     = np.mean(precos_finais)
    p5        = np.percentile(precos_finais, 5)
    p25       = np.percentile(precos_finais, 25)
    p75       = np.percentile(precos_finais, 75)
    p95       = np.percentile(precos_finais, 95)

    # VaR (Value at Risk) — Perda máxima projetada com 95% de confiança
    var_95_pct  = (p5 / S0 - 1.0) * 100.0
    var_95_abs  = S0 - p5

    # Probabilidade de perda (preço final < preço inicial)
    prob_perda = np.mean(precos_finais < S0) * 100.0

    resultados[ticker] = {
        "caminhos": caminhos,
        "precos_finais": precos_finais,
        "mediana": mediana,
        "media": media,
        "p5": p5,
        "p25": p25,
        "p75": p75,
        "p95": p95,
        "var_95_pct": var_95_pct,
        "var_95_abs": var_95_abs,
        "prob_perda": prob_perda,
    }

    print(f"    ✓ {ticker}: Simulação concluída.")

# ════════════════════════════════════════════════════════════════════
# 4. Exibição dos Resultados Estatísticos
# ════════════════════════════════════════════════════════════════════
print(f"\n{'=' * W}")
print("  RESULTADOS DA SIMULAÇÃO DE MONTE CARLO — PROJEÇÃO PARA 2026")
print(f"{'=' * W}")
print(f"  {'Estatística / Métrica':<45} {'ABEV3':>14} {'AMER3':>14} {'ASAI3':>14}")
print(f"  {'-' * 87}")

def pr(label, key, fmt="price"):
    row = f"  {label:<45}"
    for t in TICKERS:
        val = resultados[t][key]
        if fmt == "price":
            row += f"  R$ {val:>10,.2f}"
        elif fmt == "pct":
            row += f"  {val:>11,.2f}%"
    print(row)

# Print S0 (Último Preço Real)
row_s0 = f"  {'Último Preço Real (Dez/2025)':<45}"
for t in TICKERS:
    row_s0 += f"  R$ {parametros[t]['S0']:>10,.2f}"
print(row_s0)

pr("Preço Mediano Projetado (Dez/2026)", "mediana")
pr("Preço Médio Projetado (Dez/2026)", "media")

print(f"  {'-' * 87}")
print(f"  {'INTERVALOS DE CONFIANÇA':<45}")
pr("  Percentil 5% (Pior Cenário a 95%)", "p5")
pr("  Percentil 25%", "p25")
pr("  Percentil 75%", "p75")
pr("  Percentil 95% (Melhor Cenário a 95%)", "p95")

print(f"  {'-' * 87}")
print(f"  {'INDICADORES DE RISCO':<45}")
pr("  VaR 95% (Perda Máxima Projetada)", "var_95_pct", fmt="pct")
pr("  VaR 95% (Perda em R$)", "var_95_abs")
pr("  Probabilidade de Perda no Período", "prob_perda", fmt="pct")

print(f"{'=' * W}")

# ════════════════════════════════════════════════════════════════════
# 5. Diagnóstico Acadêmico Automático
# ════════════════════════════════════════════════════════════════════
print(f"\n  DIAGNÓSTICO DA PROJEÇÃO ESTOCÁSTICA:")
print(f"  {'-' * 87}")

for ticker in TICKERS:
    S0 = parametros[ticker]["S0"]
    r  = resultados[ticker]
    retorno_mediano = (r["mediana"] / S0 - 1.0) * 100.0

    print(f"\n  {ticker} ({NOMES[ticker]}):")
    print(f"    Preço Atual: R$ {S0:,.2f} → Projeção Mediana: R$ {r['mediana']:,.2f} ({retorno_mediano:+.2f}%)")
    print(f"    Intervalo de Confiança 90%: [R$ {r['p5']:,.2f} — R$ {r['p95']:,.2f}]")
    print(f"    VaR 95%: O investidor pode perder até {abs(r['var_95_pct']):.2f}% no cenário pessimista.")
    print(f"    Probabilidade de Perda: {r['prob_perda']:.1f}% das simulações terminaram abaixo do preço inicial.")

print(f"\n{'=' * W}")

# ════════════════════════════════════════════════════════════════════
# 6. Geração dos Gráficos de Monte Carlo (Premium Design)
# ════════════════════════════════════════════════════════════════════
print("\n  GERANDO GRÁFICOS DE PROJEÇÃO DE MONTE CARLO...")

for ticker in TICKERS:
    S0       = parametros[ticker]["S0"]
    caminhos = resultados[ticker]["caminhos"]
    r        = resultados[ticker]
    cores    = CORES_FUNIL[ticker]

    fig, ax = plt.subplots(figsize=(12, 6.5), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    dias_eixo = np.arange(N_DIAS + 1)

    # Desenha uma amostra de 200 caminhos individuais (fundo do funil)
    n_mostrar = min(200, N_SIMULACOES)
    for i in range(n_mostrar):
        ax.plot(dias_eixo, caminhos[:, i], color=cores["paths"], alpha=0.04, linewidth=0.5, zorder=1)

    # Calcula e desenha os percentis ao longo do tempo (faixas do funil)
    p5_arr  = np.percentile(caminhos, 5, axis=1)
    p25_arr = np.percentile(caminhos, 25, axis=1)
    p75_arr = np.percentile(caminhos, 75, axis=1)
    p95_arr = np.percentile(caminhos, 95, axis=1)
    med_arr = np.median(caminhos, axis=1)

    # Faixa externa (5% — 95%) com transparência muito leve
    ax.fill_between(dias_eixo, p5_arr, p95_arr, color=cores["ci"], alpha=0.10, zorder=2, label="Intervalo 90% (P5–P95)")

    # Faixa interna (25% — 75%) com transparência mais visível
    ax.fill_between(dias_eixo, p25_arr, p75_arr, color=cores["ci"], alpha=0.20, zorder=3, label="Intervalo 50% (P25–P75)")

    # Linha da Mediana (trajetória central mais provável)
    ax.plot(dias_eixo, med_arr, color=cores["median"], linewidth=2.5, zorder=5, label=f"Mediana: R$ {r['mediana']:,.2f}")

    # Linha horizontal pontilhada no preço inicial
    ax.axhline(S0, color="#94A3B8", linestyle="--", linewidth=1.0, alpha=0.6, zorder=4, label=f"Preço Inicial: R$ {S0:,.2f}")

    # Grid horizontal sutil
    ax.grid(True, axis='y', color='#E2E8F0', linestyle='-', linewidth=0.6, zorder=0)
    for spine in ['top', 'right', 'left']:
        ax.spines[spine].set_visible(False)
    ax.spines['bottom'].set_color('#CBD5E1')
    ax.spines['bottom'].set_linewidth(1.0)

    # Título e Subtítulo
    ax.text(0.0, 1.12, f"Simulação de Monte Carlo — {ticker} ({NOMES[ticker]})", transform=ax.transAxes,
            fontsize=15, fontweight='bold', color='#0F172A', ha='left')
    ax.text(0.0, 1.06, f"{N_SIMULACOES:,} simulações | {N_DIAS} dias úteis | Modelo: Movimento Browniano Geométrico",
            transform=ax.transAxes, fontsize=9.5, color='#64748B', ha='left')

    # Formatação dos eixos
    ax.set_xlabel("Dia Útil Projetado (2026)", fontsize=11, color='#475569', labelpad=10)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, p: f"R$ {x:,.2f}"))
    ax.tick_params(axis='x', colors='#64748B', labelsize=9.5, length=4, width=1)
    ax.tick_params(axis='y', which='both', left=False, colors='#64748B', labelsize=9.5)

    # Legenda
    legend = ax.legend(loc="upper left", frameon=True, facecolor='#FFFFFF', edgecolor='#E2E8F0',
                       framealpha=0.9, fontsize=9.5)
    legend.get_frame().set_boxstyle("round,pad=0.4")

    # Anotação do VaR no canto inferior direito
    ax.text(0.98, 0.04,
            f"VaR 95%: {r['var_95_pct']:.2f}%  |  Prob. Perda: {r['prob_perda']:.1f}%",
            transform=ax.transAxes, fontsize=9, color='#64748B', ha='right', va='bottom',
            bbox=dict(boxstyle="round,pad=0.4", facecolor='#F8FAFC', edgecolor='#E2E8F0', alpha=0.9))

    plot_path = f"graficos/monte_carlo_{ticker.lower()}.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"    ✓ Gráfico salvo em '{plot_path}'")

print(f"{'=' * W}")
print("  SIMULAÇÃO DE MONTE CARLO CONCLUÍDA COM SUCESSO.")
print(f"{'=' * W}")
