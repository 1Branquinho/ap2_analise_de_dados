import sys
import requests
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "https://laboratoriodefinancas.com/api/v2"
TOKEN    = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc2NTEyNTU3LCJpYXQiOjE3NzM5MjA1NTcsImp0aSI6IjFkM2QxMDA0YTI4ZDRjMzk5N2ZhM2Q2ZTg3OTZhNjhlIiwidXNlcl9pZCI6Ijk3In0.M83oF3cJTJHKAk36o8hVl72eIzopngrBieqXDqOqgTc"
HEADERS  = {"Authorization": f"Bearer {TOKEN}"}
TICKER   = "DIGITE"


def fetch_balanco(ano_tri):
    resp = requests.get(
        f"{BASE_URL}/bolsa/balanco",
        headers=HEADERS,
        params={"ticker": TICKER, "ano_tri": ano_tri},
    )
    resp.raise_for_status()
    dados = resp.json()[0]['balanco']
    return pd.DataFrame(dados)


def v(df, conta):
    res = df[df["conta"] == conta]["valor"]
    return float(res.iloc[0]) if not res.empty else 0.0


# ─────────────────────────────────────────────
# Buscar dados
# ─────────────────────────────────────────────
df24 = fetch_balanco("20244T")
df25 = fetch_balanco("20254T")

# ── 2024 ──
at24     = v(df24, '1')
ac24     = v(df24, '1.01')
cx24     = v(df24, '1.01.01')
af24     = v(df24, '1.01.02')
cr24     = v(df24, '1.01.03')
est24    = v(df24, '1.01.04')
da24     = v(df24, '1.01.07')
anc24    = v(df24, '1.02')
arlp24   = v(df24, '1.02.01')
inv24    = v(df24, '1.02.02')
imob24   = v(df24, '1.02.03')
intg24   = v(df24, '1.02.04')
pc24     = v(df24, '2.01')
forn24   = v(df24, '2.01.02')
emp_cp24 = v(df24, '2.01.04')
pnc24    = v(df24, '2.02')
pl24     = v(df24, '2.03')

# ── 2025 ──
at25     = v(df25, '1')
ac25     = v(df25, '1.01')
cx25     = v(df25, '1.01.01')
af25     = v(df25, '1.01.02')
cr25     = v(df25, '1.01.03')
est25    = v(df25, '1.01.04')
da25     = v(df25, '1.01.07')
anc25    = v(df25, '1.02')
arlp25   = v(df25, '1.02.01')
inv25    = v(df25, '1.02.02')
imob25   = v(df25, '1.02.03')
intg25   = v(df25, '1.02.04')
pc25     = v(df25, '2.01')
forn25   = v(df25, '2.01.02')
emp_cp25 = v(df25, '2.01.04')
pnc25    = v(df25, '2.02')
pl25     = v(df25, '2.03')

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
print('=' * 72)
print('  ANÁLISE FINANCEIRA (NOME DA SUA EMPRESA)')
print('  Fonte: API laboratoriodefinancas.com  |  Em R$ mil')
print('=' * 72)

# ─────────────────────────────────────────────
# Balanço Patrimonial resumido
# ─────────────────────────────────────────────
print('\n' + '─' * 72)
print('  BALANÇO PATRIMONIAL (R$ mil)')
print('─' * 72)
print(f'{"Conta":<38} {"2024":>15} {"2025":>15}')
print('─' * 72)

bal_linhas = [
    ('Ativo Total',                at24,     at25),
    ('  Ativo Circulante',         ac24,     ac25),
    ('    Caixa e Equiv.',         cx24,     cx25),
    ('    Aplicações Financeiras', af24,     af25),
    ('    Contas a Receber',       cr24,     cr25),
    ('    Estoques',               est24,    est25),
    ('    Despesas Antecipadas',   da24,     da25),
    ('  Ativo Não Circulante',     anc24,    anc25),
    ('    ARLP',                   arlp24,   arlp25),
    ('    Investimentos',          inv24,    inv25),
    ('    Imobilizado',            imob24,   imob25),
    ('    Intangível',             intg24,   intg25),
    ('Passivo Total',              at24,     at25),
    ('  Passivo Circulante',       pc24,     pc25),
    ('    Fornecedores',           forn24,   forn25),
    ('    Empréstimos CP',         emp_cp24, emp_cp25),
    ('  Passivo Não Circulante',   pnc24,    pnc25),
    ('  Patrimônio Líquido',       pl24,     pl25),
]

for label, val24, val25 in bal_linhas:
    print(f'{label:<38} {val24/1_000:>15,.0f} {val25/1_000:>15,.0f}')

# ─────────────────────────────────────────────
# Indicadores de Liquidez
# ─────────────────────────────────────────────
print('\n' + '─' * 72)
print('  INDICADORES DE LIQUIDEZ')
print('─' * 72)
print(f'{"Indicador":<40} {"2024":>14} {"2025":>14}')
print('─' * 72)

ccl24 = ac24 - pc24
ccl25 = ac25 - pc25

lc24 = ac24 / pc24
lc25 = ac25 / pc25

ls24 = (ac24 - est24 - da24) / pc24
ls25 = (ac25 - est25 - da25) / pc25

li24 = cx24 / pc24
li25 = cx25 / pc25

lg24 = (ac24 + arlp24) / (pc24 + pnc24)
lg25 = (ac25 + arlp25) / (pc25 + pnc25)

print(f'{"CCL  (AC - PC)":<40} {ccl24/1_000:>14,.0f} {ccl25/1_000:>14,.0f}')
print(f'{"Liquidez Corrente  (AC / PC)":<40} {lc24:>14.4f} {lc25:>14.4f}')
print(f'{"Liquidez Seca  (AC-Est-DA / PC)":<40} {ls24:>14.4f} {ls25:>14.4f}')
print(f'{"Liquidez Imediata  (Caixa / PC)":<40} {li24:>14.4f} {li25:>14.4f}')
print(f'{"Liquidez Geral  (AC+ARLP / PC+PNC)":<40} {lg24:>14.4f} {lg25:>14.4f}')

# ─────────────────────────────────────────────
# Capital de Giro (modelo Fleuriet)
# ─────────────────────────────────────────────
print('\n' + '─' * 72)
print('  CAPITAL DE GIRO (MODELO FLEURIET)')
print('─' * 72)
print(f'{"Indicador":<40} {"2024":>14} {"2025":>14}')
print('─' * 72)

acf24 = cx24 + af24
acf25 = cx25 + af25

aco24 = ac24 - acf24
aco25 = ac25 - acf25

pcf24 = emp_cp24
pcf25 = emp_cp25

pco24 = pc24 - pcf24
pco25 = pc25 - pcf25

ncg24 = aco24 - pco24
ncg25 = aco25 - pco25

cgl24 = ac24 - pc24
cgl25 = ac25 - pc25

st24 = acf24 - pcf24
st25 = acf25 - pcf25

print(f'{"ACF  (Caixa + Aplicações)":<40} {acf24/1_000:>14,.0f} {acf25/1_000:>14,.0f}')
print(f'{"ACO  (AC - ACF)":<40} {aco24/1_000:>14,.0f} {aco25/1_000:>14,.0f}')
print(f'{"PCF  (Empréstimos CP)":<40} {pcf24/1_000:>14,.0f} {pcf25/1_000:>14,.0f}')
print(f'{"PCO  (PC - PCF)":<40} {pco24/1_000:>14,.0f} {pco25/1_000:>14,.0f}')
print(f'{"NCG  (ACO - PCO)":<40} {ncg24/1_000:>14,.0f} {ncg25/1_000:>14,.0f}')
print(f'{"CGL  (AC - PC)":<40} {cgl24/1_000:>14,.0f} {cgl25/1_000:>14,.0f}')
print(f'{"ST   (ACF - PCF)":<40} {st24/1_000:>14,.0f} {st25/1_000:>14,.0f}')

# ─────────────────────────────────────────────
# Indicadores de Endividamento
# ─────────────────────────────────────────────
print('\n' + '─' * 72)
print('  INDICADORES DE ENDIVIDAMENTO')
print('─' * 72)
print(f'{"Indicador":<45} {"2024":>12} {"2025":>12}')
print('─' * 72)

passivo24 = pc24 + pnc24
passivo25 = pc25 + pnc25

rc24 = passivo24 / pl24
rc25 = passivo25 / pl25

eg24 = passivo24 / at24
eg25 = passivo25 / at25

sg24 = at24 / passivo24
sg25 = at25 / passivo25

ce24 = pc24 / passivo24
ce25 = pc25 / passivo25

at_fixo24 = imob24 + intg24 + inv24
at_fixo25 = imob25 + intg25 + inv25
ipl24 = at_fixo24 / pl24
ipl25 = at_fixo25 / pl25

print(f'{"Relação de Capitais  (Passivo / PL)":<45} {rc24:>12.4f} {rc25:>12.4f}')
print(f'{"Endividamento Geral  (Passivo / AT)":<45} {eg24:>12.4f} {eg25:>12.4f}')
print(f'{"Solvência Geral  (AT / Passivo)":<45} {sg24:>12.4f} {sg25:>12.4f}')
print(f'{"Composição Endividamento  (PC / Passivo)":<45} {ce24:>12.4f} {ce25:>12.4f}')
print(f'{"Imobilização do PL  (At.Fixo / PL)":<45} {ipl24:>12.4f} {ipl25:>12.4f}')

print('\n' + '=' * 72)
