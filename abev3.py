import requests
import pandas as pd

base_url = "https://laboratoriodefinancas.com/api/v2"
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzgwMTM4ODA3LCJpYXQiOjE3Nzc1NDY4MDcsImp0aSI6IjgzNjdlMTA1NmVlOTQyM2FiNzUyMTA3MDk5NWMyMTE3IiwidXNlcl9pZCI6IjExOCJ9._IDcSkDVZ4mg1zAKhYFs7s6bLgfbErRH1pqEyXo8hpg"
params = {"ticker": "ABEV3", "ano_tri": "20254T"}
resp = requests.get(
    f"{base_url}/bolsa/balanco",
    headers={"Authorization": f"Bearer {token}"},
    params=params,
)
resp.json()

dados = resp.json()[0]['balanco']
df_2025 = pd.DataFrame(dados)

ac = float(df_2025[df_2025['conta'] == '1.01']['valor'].values[0])
pc = float(df_2025[df_2025['conta'] == '2.01']['valor'].values[0])

ccl = ac - pc
print(f"Capital de Giro Líquido: {ccl}")

lc = ac/pc
print(f"Liquidez Corrente: {lc}")

intg = float(df_2025[df_2025['conta'] == '1.02.04']['valor'].values[0])
print(f"Intangível: {intg}")
imob = float(df_2025[df_2025['conta']== '1.02.03']['valor'].values[0])
print(f"Imobilizado: {imob}")
invest = float(df_2025[df_2025['conta'] == '1.02.02']['valor'].values[0])
print(f"Investimento: {invest}")
alrp = intg + imob + invest
print(f"Ativo Realizável a Longo Prazo: {alrp}")

pnc = float(df_2025[df_2025['conta'] == '2.02']['valor'].values[0])
print(f"Passivo Não Circulante: {pnc}")

lg = (ac + alrp) / (pc + pnc)
print(f"Liquidez Geral: {lg}")