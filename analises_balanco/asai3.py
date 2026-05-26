import sys
import requests
import pandas as pd
import yfinance as yf

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "https://laboratoriodefinancas.com/api/v2"
TOKEN    = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc2NTEyNTU3LCJpYXQiOjE3NzM5MjA1NTcsImp0aSI6IjFkM2QxMDA0YTI4ZDRjMzk5N2ZhM2Q2ZTg3OTZhNjhlIiwidXNlcl9pZCI6Ijk3In0.M83oF3cJTJHKAk36o8hVl72eIzopngrBieqXDqOqgTc"
HEADERS  = {"Authorization": f"Bearer {TOKEN}"}
TICKER   = "ASAI3"


def safe_div(a, b):
    return (a / b) if b and b != 0 else None


def fetch_market_data():
    try:
        info     = yf.Ticker(f"{TICKER}.SA").info
        preco    = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
        n_shares = info.get("sharesOutstanding") or 0
        mkt_cap  = preco * n_shares if (preco and n_shares) else None
        dy       = (info.get("dividendYield") or 0.0) * 100
        return {"preco": preco, "n_shares": n_shares, "mkt_cap": mkt_cap, "dy": dy}
    except Exception as e:
        print(f"  [AVISO] yfinance {TICKER}: {e}")
        return {"preco": None, "n_shares": None, "mkt_cap": None, "dy": None}


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
        # BP — Ativo
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
        # BP — Passivo e PL
        'pc':     v(df, '2.01'),
        'forn':   v(df, '2.01.02'),
        'emp_cp': v(df, '2.01.04'),
        'pnc':    v(df, '2.02'),
        'pl':     v(df, '2.03'),
        # DRE
        'rec':    v(df, '3.01'),
        'lb':     v(df, '3.03'),
        'ebit':   v(df, '3.05'),
        'll':     v(df, '3.11'),
        # DFC — D&A para cálculo do EBITDA
        'dna':    v(df, '6.01.01.02'),
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
        'rc':  safe_div(passivo, pl),
        'eg':  safe_div(passivo, at),
        'sg':  safe_div(at, passivo),
        'ce':  safe_div(pc, passivo),
        'ipl': safe_div(at_fixo, pl),
    }


def calcular_multiplos(b, md):
    rec    = b['rec']
    lb     = b['lb']
    ebit   = b['ebit']
    ll     = b['ll']
    pl_val = b['pl']
    dna    = abs(b['dna'])
    ebitda = ebit + dna

    preco    = md['preco']    or 0.0
    n_shares = md['n_shares'] or 0
    mkt_cap  = md['mkt_cap']

    div_bruta = b['emp_cp'] + b['pnc']
    caixa     = b['cx'] + b['af']
    div_liq   = div_bruta - caixa
    ev        = (mkt_cap + div_liq) if mkt_cap else None

    lpa   = safe_div(ll, n_shares)     if n_shares else None
    vpa   = safe_div(pl_val, n_shares) if n_shares else None
    p_l   = safe_div(preco, lpa)   if (lpa and lpa > 0) else None
    p_vpa = safe_div(preco, vpa)   if (vpa and vpa > 0) else None

    return {
        'preco':     preco,
        'n_shares':  n_shares,
        'mkt_cap':   mkt_cap,
        'div_liq':   div_liq,
        'ev':        ev,
        'rec':       rec,
        'lb':        lb,
        'ebit':      ebit,
        'ebitda':    ebitda,
        'll':        ll,
        'lpa':       lpa,
        'vpa':       vpa,
        'mb':        safe_div(lb, rec),
        'm_ebit':    safe_div(ebit, rec),
        'm_ebitda':  safe_div(ebitda, rec),
        'm_liq':     safe_div(ll, rec),
        'ev_ebitda': safe_div(ev, ebitda) if ev is not None else None,
        'ev_ebit':   safe_div(ev, ebit)   if ev is not None else None,
        'ev_rec':    safe_div(ev, rec)    if ev is not None else None,
        'p_l':       p_l,
        'p_vpa':     p_vpa,
        'dy':        md['dy'],
        'roe':       safe_div(ll, pl_val),
        'roa':       safe_div(ll, b['at']),
        'roi':       safe_div(ebit, b['at']),
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


def imprimir_dre(b24, b25):
    print('\n' + '─' * 72)
    print('  DEMONSTRAÇÃO DO RESULTADO (R$ mil)')
    print('─' * 72)
    print(f'{"Conta":<38} {"2024":>15} {"2025":>15}')
    print('─' * 72)
    dna24, dna25 = abs(b24['dna']), abs(b25['dna'])
    ebitda24 = b24['ebit'] + dna24
    ebitda25 = b25['ebit'] + dna25

    def pct(val, base):
        return f'{val/base*100:>14.1f}%' if base else f'{"N/D":>15}'

    print(f'{"Receita Líquida":<38} {b24["rec"]/1_000:>15,.0f} {b25["rec"]/1_000:>15,.0f}')
    print(f'{"Lucro Bruto":<38} {b24["lb"]/1_000:>15,.0f} {b25["lb"]/1_000:>15,.0f}')
    print(f'{"  Margem Bruta":<38} {pct(b24["lb"], b24["rec"])} {pct(b25["lb"], b25["rec"])}')
    print(f'{"EBIT":<38} {b24["ebit"]/1_000:>15,.0f} {b25["ebit"]/1_000:>15,.0f}')
    print(f'{"  Margem EBIT":<38} {pct(b24["ebit"], b24["rec"])} {pct(b25["ebit"], b25["rec"])}')
    print(f'{"D&A (Deprec. e Amortização)":<38} {dna24/1_000:>15,.0f} {dna25/1_000:>15,.0f}')
    print(f'{"EBITDA  (EBIT + D&A)":<38} {ebitda24/1_000:>15,.0f} {ebitda25/1_000:>15,.0f}')
    print(f'{"  Margem EBITDA":<38} {pct(ebitda24, b24["rec"])} {pct(ebitda25, b25["rec"])}')
    print(f'{"Lucro Líquido":<38} {b24["ll"]/1_000:>15,.0f} {b25["ll"]/1_000:>15,.0f}')
    print(f'{"  Margem Líquida":<38} {pct(b24["ll"], b24["rec"])} {pct(b25["ll"], b25["rec"])}')


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
    def fr(v): return f'{v:>12.4f}' if v is not None else f'{"N/D":>12}'
    print(f'{"Relação de Capitais  (Passivo / PL)":<45} {fr(e24["rc"])} {fr(e25["rc"])}')
    print(f'{"Endividamento Geral  (Passivo / AT)":<45} {fr(e24["eg"])} {fr(e25["eg"])}')
    print(f'{"Solvência Geral  (AT / Passivo)":<45} {fr(e24["sg"])} {fr(e25["sg"])}')
    print(f'{"Composição Endividamento  (PC / Passivo)":<45} {fr(e24["ce"])} {fr(e25["ce"])}')
    print(f'{"Imobilização do PL  (At.Fixo / PL)":<45} {fr(e24["ipl"])} {fr(e25["ipl"])}')


def imprimir_multiplos(m):
    def val(v, fmt): return fmt.format(v) if v is not None else f'{"N/D":>15}'
    def pct(v):      return f'{v*100:>14.1f}%' if v is not None else f'{"N/D":>15}'

    print('\n' + '─' * 72)
    print('  AVALIAÇÃO POR MÚLTIPLOS  (Market Cap = Preço × Qtd. Ações — yfinance)')
    print('─' * 72)

    print(f'\n  ── VALOR DE MERCADO {"─" * 49}')
    print(f'  {"Preço (R$)":<42} {val(m["preco"], "{:>15.2f}")}')
    print(f'  {"Qtd. Ações (mil)":<42} {val(m["n_shares"] / 1_000 if m["n_shares"] else None, "{:>15,.0f}")}')
    print(f'  {"Market Cap (R$ mil)":<42} {val(m["mkt_cap"] / 1_000 if m["mkt_cap"] else None, "{:>15,.0f}")}')
    print(f'  {"Dívida Líquida BP (R$ mil)":<42} {val(m["div_liq"] / 1_000, "{:>15,.0f}")}')
    print(f'  {"EV (R$ mil)":<42} {val(m["ev"] / 1_000 if m["ev"] is not None else None, "{:>15,.0f}")}')
    print(f'  {"EBITDA (R$ mil)":<42} {val(m["ebitda"] / 1_000 if m["ebitda"] else None, "{:>15,.0f}")}')
    print(f'  {"LPA (R$)":<42} {val(m["lpa"], "{:>15.4f}")}')
    print(f'  {"VPA (R$)":<42} {val(m["vpa"], "{:>15.4f}")}')

    print(f'\n  ── MÚLTIPLOS DE FIRMA (EV-based) {"─" * 37}')
    print(f'  {"EV / EBITDA":<42} {val(m["ev_ebitda"], "{:>15.2f}")}')
    print(f'  {"EV / EBIT":<42} {val(m["ev_ebit"], "{:>15.2f}")}')
    print(f'  {"EV / Receita":<42} {val(m["ev_rec"], "{:>15.4f}")}')

    print(f'\n  ── MÚLTIPLOS DE EQUITY {"─" * 46}')
    print(f'  {"P / L":<42} {val(m["p_l"], "{:>15.2f}")}')
    print(f'  {"P / VPA":<42} {val(m["p_vpa"], "{:>15.2f}")}')
    dy_s = f'{m["dy"]:>14.2f}%' if m["dy"] is not None else f'{"N/D":>15}'
    print(f'  {"DY (Dividend Yield)":<42} {dy_s}')

    print(f'\n  ── RENTABILIDADE {"─" * 52}')
    print(f'  {"Margem Bruta":<42} {pct(m["mb"])}')
    print(f'  {"Margem EBIT":<42} {pct(m["m_ebit"])}')
    print(f'  {"Margem EBITDA":<42} {pct(m["m_ebitda"])}')
    print(f'  {"Margem Líquida":<42} {pct(m["m_liq"])}')
    print(f'  {"ROE  (LL / PL)":<42} {pct(m["roe"])}')
    print(f'  {"ROA  (LL / AT)":<42} {pct(m["roa"])}')
    print(f'  {"ROI  (EBIT / AT)":<42} {pct(m["roi"])}')


def main():
    print(f'Buscando dados para {TICKER}...')
    md   = fetch_market_data()
    df24 = fetch_balanco("20244T")
    df25 = fetch_balanco("20254T")

    b24 = extrair_contas(df24)
    b25 = extrair_contas(df25)
    m   = calcular_multiplos(b25, md)

    print('=' * 72)
    print('  ANÁLISE FINANCEIRA — ASSAI (ASAI3)')
    print('  Fonte: API laboratoriodefinancas.com | yfinance  |  Em R$ mil')
    print('=' * 72)

    imprimir_balanco(b24, b25)
    imprimir_dre(b24, b25)
    imprimir_liquidez(b24, b25)
    imprimir_fleuriet(b24, b25)
    imprimir_endividamento(b24, b25)
    imprimir_multiplos(m)

    print('\n' + '=' * 72)


if __name__ == '__main__':
    main()
