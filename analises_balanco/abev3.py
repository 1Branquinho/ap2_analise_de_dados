import sys
import requests
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "https://laboratoriodefinancas.com/api/v2"
TOKEN    = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc2NTEyNTU3LCJpYXQiOjE3NzM5MjA1NTcsImp0aSI6IjFkM2QxMDA0YTI4ZDRjMzk5N2ZhM2Q2ZTg3OTZhNjhlIiwidXNlcl9pZCI6Ijk3In0.M83oF3cJTJHKAk36o8hVl72eIzopngrBieqXDqOqgTc"
HEADERS  = {"Authorization": f"Bearer {TOKEN}"}
TICKER   = "ABEV3"


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


def extrair_contas(df):
    return {
        'at':     v(df, '1'),
        'ac':     v(df, '1.01'),
        'cx':     v(df, '1.01.01'),
        'af':     v(df, '1.01.02'),
        'cr':     v(df, '1.01.03'),
        'est':    v(df, '1.01.04'),
        'da':     v(df, '1.01.07'),
        'anc':    v(df, '1.02'),
        'arlp':   v(df, '1.02.01'),
        'inv':    v(df, '1.02.02'),
        'imob':   v(df, '1.02.03'),
        'intg':   v(df, '1.02.04'),
        'pc':     v(df, '2.01'),
        'forn':   v(df, '2.01.02'),
        'emp_cp': v(df, '2.01.04'),
        'pnc':    v(df, '2.02'),
        'pl':     v(df, '2.03'),
    }


def calcular_liquidez(b):
    ac, pc, est, da, cx, arlp, pnc = b['ac'], b['pc'], b['est'], b['da'], b['cx'], b['arlp'], b['pnc']
    return {
        'ccl': ac - pc,
        'lc':  ac / pc,
        'ls':  (ac - est - da) / pc,
        'li':  cx / pc,
        'lg':  (ac + arlp) / (pc + pnc),
    }


def calcular_fleuriet(b):
    ac, pc, cx, af, emp_cp = b['ac'], b['pc'], b['cx'], b['af'], b['emp_cp']
    acf = cx + af
    aco = ac - acf
    pcf = emp_cp
    pco = pc - pcf
    return {
        'acf': acf,
        'aco': aco,
        'pcf': pcf,
        'pco': pco,
        'ncg': aco - pco,
        'cgl': ac - pc,
        'st':  acf - pcf,
    }


def calcular_endividamento(b):
    pc, pnc, pl, at, imob, intg, inv = b['pc'], b['pnc'], b['pl'], b['at'], b['imob'], b['intg'], b['inv']
    passivo = pc + pnc
    at_fixo = imob + intg + inv
    return {
        'passivo': passivo,
        'rc':  passivo / pl,
        'eg':  passivo / at,
        'sg':  at / passivo,
        'ce':  pc / passivo,
        'ipl': at_fixo / pl,
    }


def imprimir_balanco(b24, b25):
    print('\n' + '─' * 72)
    print('  BALANÇO PATRIMONIAL (R$ mil)')
    print('─' * 72)
    print(f'{"Conta":<38} {"2024":>15} {"2025":>15}')
    print('─' * 72)
    linhas = [
        ('Ativo Total',                b24['at'],     b25['at']),
        ('  Ativo Circulante',         b24['ac'],     b25['ac']),
        ('    Caixa e Equiv.',         b24['cx'],     b25['cx']),
        ('    Aplicações Financeiras', b24['af'],     b25['af']),
        ('    Contas a Receber',       b24['cr'],     b25['cr']),
        ('    Estoques',               b24['est'],    b25['est']),
        ('    Despesas Antecipadas',   b24['da'],     b25['da']),
        ('  Ativo Não Circulante',     b24['anc'],    b25['anc']),
        ('    ARLP',                   b24['arlp'],   b25['arlp']),
        ('    Investimentos',          b24['inv'],    b25['inv']),
        ('    Imobilizado',            b24['imob'],   b25['imob']),
        ('    Intangível',             b24['intg'],   b25['intg']),
        ('Passivo Total',              b24['at'],     b25['at']),
        ('  Passivo Circulante',       b24['pc'],     b25['pc']),
        ('    Fornecedores',           b24['forn'],   b25['forn']),
        ('    Empréstimos CP',         b24['emp_cp'], b25['emp_cp']),
        ('  Passivo Não Circulante',   b24['pnc'],    b25['pnc']),
        ('  Patrimônio Líquido',       b24['pl'],     b25['pl']),
    ]
    for label, val24, val25 in linhas:
        print(f'{label:<38} {val24/1_000:>15,.0f} {val25/1_000:>15,.0f}')


def imprimir_liquidez(b24, b25):
    print('\n' + '─' * 72)
    print('  INDICADORES DE LIQUIDEZ')
    print('─' * 72)
    print(f'{"Indicador":<40} {"2024":>14} {"2025":>14}')
    print('─' * 72)
    l24 = calcular_liquidez(b24)
    l25 = calcular_liquidez(b25)
    print(f'{"CCL  (AC - PC)":<40} {l24["ccl"]/1_000:>14,.0f} {l25["ccl"]/1_000:>14,.0f}')
    print(f'{"Liquidez Corrente  (AC / PC)":<40} {l24["lc"]:>14.4f} {l25["lc"]:>14.4f}')
    print(f'{"Liquidez Seca  (AC-Est-DA / PC)":<40} {l24["ls"]:>14.4f} {l25["ls"]:>14.4f}')
    print(f'{"Liquidez Imediata  (Caixa / PC)":<40} {l24["li"]:>14.4f} {l25["li"]:>14.4f}')
    print(f'{"Liquidez Geral  (AC+ARLP / PC+PNC)":<40} {l24["lg"]:>14.4f} {l25["lg"]:>14.4f}')


def imprimir_fleuriet(b24, b25):
    print('\n' + '─' * 72)
    print('  CAPITAL DE GIRO (MODELO FLEURIET)')
    print('─' * 72)
    print(f'{"Indicador":<40} {"2024":>14} {"2025":>14}')
    print('─' * 72)
    f24 = calcular_fleuriet(b24)
    f25 = calcular_fleuriet(b25)
    print(f'{"ACF  (Caixa + Aplicações)":<40} {f24["acf"]/1_000:>14,.0f} {f25["acf"]/1_000:>14,.0f}')
    print(f'{"ACO  (AC - ACF)":<40} {f24["aco"]/1_000:>14,.0f} {f25["aco"]/1_000:>14,.0f}')
    print(f'{"PCF  (Empréstimos CP)":<40} {f24["pcf"]/1_000:>14,.0f} {f25["pcf"]/1_000:>14,.0f}')
    print(f'{"PCO  (PC - PCF)":<40} {f24["pco"]/1_000:>14,.0f} {f25["pco"]/1_000:>14,.0f}')
    print(f'{"NCG  (ACO - PCO)":<40} {f24["ncg"]/1_000:>14,.0f} {f25["ncg"]/1_000:>14,.0f}')
    print(f'{"CGL  (AC - PC)":<40} {f24["cgl"]/1_000:>14,.0f} {f25["cgl"]/1_000:>14,.0f}')
    print(f'{"ST   (ACF - PCF)":<40} {f24["st"]/1_000:>14,.0f} {f25["st"]/1_000:>14,.0f}')


def imprimir_endividamento(b24, b25):
    print('\n' + '─' * 72)
    print('  INDICADORES DE ENDIVIDAMENTO')
    print('─' * 72)
    print(f'{"Indicador":<45} {"2024":>12} {"2025":>12}')
    print('─' * 72)
    e24 = calcular_endividamento(b24)
    e25 = calcular_endividamento(b25)
    print(f'{"Relação de Capitais  (Passivo / PL)":<45} {e24["rc"]:>12.4f} {e25["rc"]:>12.4f}')
    print(f'{"Endividamento Geral  (Passivo / AT)":<45} {e24["eg"]:>12.4f} {e25["eg"]:>12.4f}')
    print(f'{"Solvência Geral  (AT / Passivo)":<45} {e24["sg"]:>12.4f} {e25["sg"]:>12.4f}')
    print(f'{"Composição Endividamento  (PC / Passivo)":<45} {e24["ce"]:>12.4f} {e25["ce"]:>12.4f}')
    print(f'{"Imobilização do PL  (At.Fixo / PL)":<45} {e24["ipl"]:>12.4f} {e25["ipl"]:>12.4f}')


def main():
    df24 = fetch_balanco("20244T")
    df25 = fetch_balanco("20254T")

    b24 = extrair_contas(df24)
    b25 = extrair_contas(df25)

    print('=' * 72)
    print('  ANÁLISE FINANCEIRA — AMBEV (ABEV3)')
    print('  Fonte: API laboratoriodefinancas.com  |  Em R$ mil')
    print('=' * 72)

    imprimir_balanco(b24, b25)
    imprimir_liquidez(b24, b25)
    imprimir_fleuriet(b24, b25)
    imprimir_endividamento(b24, b25)

    print('\n' + '=' * 72)


if __name__ == '__main__':
    main()
