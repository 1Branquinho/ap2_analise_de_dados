import requests
import pandas as pd

BASE_URL = "https://laboratoriodefinancas.com/api/v2"
TOKEN    = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzgwNTcwNzA4LCJpYXQiOjE3Nzc5Nzg3MDgsImp0aSI6IjNmNTBiZWM4OWVkZDQzMWI5NTljZWFkYmFkZTdiNjYyIiwidXNlcl9pZCI6IjExOCJ9.4m2iY0iB32ZKdO6_uZb-H1Cu9zwOXJcenbCHAv-qTFE"
HEADERS  = {"Authorization": f"Bearer {TOKEN}"}

resp = requests.get(
    f"{BASE_URL}/bolsa/balanco",
    headers=HEADERS,
    params={"ticker": "ABEV3", "ano_tri": "20254T"},
)
resp.raise_for_status()

df = pd.DataFrame(resp.json()[0]["balanco"])
df["conta"] = df["conta"].astype(str)
df = df.sort_values("conta")

print("=" * 60)
print("  TODAS AS CONTAS RETORNADAS — ABEV3 20254T")
print("=" * 60)
print(f"{'Conta':<15} {'Descrição':<35} {'Valor':>10}")
print("-" * 60)
for _, row in df.iterrows():
    print(f"{str(row['conta']):<15} {str(row.get('descricao', ''))[:35]:<35} {str(row.get('valor',''))[:10]:>10}")

print("=" * 60)
print(f"\nTotal de contas: {len(df)}")
print(f"\nContas que começam com '3' (DRE):")
dre = df[df["conta"].str.startswith("3")]
if dre.empty:
    print("  Nenhuma conta DRE encontrada neste endpoint.")
else:
    for _, row in dre.iterrows():
        print(f"  {row['conta']:<15} {str(row.get('descricao','')):<35} {row.get('valor','')}")
