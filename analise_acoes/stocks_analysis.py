import requests
import pandas as pd

BASE_URL = "https://laboratoriodefinancas.com/api/v2"
TOKEN    = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzgwNTcwNzA4LCJpYXQiOjE3Nzc5Nzg3MDgsImp0aSI6IjNmNTBiZWM4OWVkZDQzMWI5NTljZWFkYmFkZTdiNjYyIiwidXNlcl9pZCI6IjExOCJ9.4m2iY0iB32ZKdO6_uZb-H1Cu9zwOXJcenbCHAv-qTFE"
HEADERS  = {"Authorization": f"Bearer {TOKEN}"}
DATA_INI = "2020-01-01"
DATA_FIM = "2025-12-31"
TICKERS  = ["ABEV3", "AMER3", "ASAI3"]


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


# ── Coleta ──────────────────────────────────────────────────────────
print("Buscando dados...")
frames = [fetch_acao(t) for t in TICKERS] + [fetch_ibov()]
df_precos = pd.concat(frames, axis=1).sort_index()

# ── Normalização base 100 ────────────────────────────────────────────
# dropna garante que só usamos dias com dados de todos os ativos
# (ASAI3 foi listada em 2021, então o período começa do IPO dela)
df_norm = df_precos.dropna().copy()
df_norm = df_norm / df_norm.iloc[0] * 100

data_inicio = df_norm.index[0].strftime("%d/%m/%Y")
data_fim    = df_norm.index[-1].strftime("%d/%m/%Y")

# ── Tabela de retorno total ──────────────────────────────────────────
print()
print("=" * 55)
print(f"  RETORNO TOTAL  ({data_inicio} → {data_fim})")
print("=" * 55)
print(f"  {'Ativo':<8} {'Retorno':>10}  {'Base 100 → Valor Final':>22}")
print("-" * 55)
for col in df_norm.columns:
    val_final = df_norm[col].iloc[-1]
    retorno   = val_final - 100
    print(f"  {col:<8} {retorno:>+9.1f}%  {val_final:>22.1f}")
print("=" * 55)

# ── Retorno por ano ──────────────────────────────────────────────────
print()
print("=" * 55)
print("  RETORNO POR ANO (%)")
print("=" * 55)

df_anual = df_precos.dropna().resample("YE").last()
retornos_anuais = df_anual.pct_change() * 100
retornos_anuais = retornos_anuais.dropna()

header = f"  {'Ano':<6}" + "".join(f"{col:>10}" for col in retornos_anuais.columns)
print(header)
print("-" * 55)
for ano, row in retornos_anuais.iterrows():
    linha = f"  {ano.year:<6}" + "".join(f"{v:>+9.1f}%" for v in row)
    print(linha)
print("=" * 55)

# ── Volatilidade anualizada ──────────────────────────────────────────
retornos_diarios = df_precos.dropna().pct_change().dropna()
volatilidade = retornos_diarios.std() * (252 ** 0.5) * 100

print()
print("=" * 55)
print("  VOLATILIDADE ANUALIZADA (risco)")
print("=" * 55)
for col, vol in volatilidade.items():
    print(f"  {col:<8} {vol:>8.1f}%")
print("=" * 55)

# ── Correlação com o IBOV ────────────────────────────────────────────
correlacao = retornos_diarios.corr()["IBOV"].drop("IBOV")

print()
print("=" * 55)
print("  CORRELAÇÃO COM O IBOV")
print("  (1.0 = move igual ao mercado, 0 = independente)")
print("=" * 55)
for ticker, corr in correlacao.items():
    print(f"  {ticker:<8} {corr:>8.4f}")
print("=" * 55)

print()
print("Dados prontos em: df_precos (preços brutos) | df_norm (base 100)")
