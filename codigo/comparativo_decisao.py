import os
import sys
import json

# Configura encoding correto para Windows
sys.stdout.reconfigure(encoding='utf-8')

TICKERS = ["ABEV3", "AMER3", "ASAI3"]
DATA_DIR = "graficos"

# ════════════════════════════════════════════════════════════════════
# 1. Carregar os Dados de Cache
# ════════════════════════════════════════════════════════════════════
dados_empresas = {}
for ticker in TICKERS:
    json_path = os.path.join(DATA_DIR, f"dados_{ticker.lower()}.json")
    if not os.path.exists(json_path):
        print(f"[ERRO] O arquivo de cache {json_path} não existe.")
        print(f"       Por favor, execute o script individual primeiro: python analises_balanco/{ticker.lower()}.py")
        sys.exit(1)
        
    with open(json_path, "r", encoding="utf-8") as f:
        dados_empresas[ticker] = json.load(f)

# ════════════════════════════════════════════════════════════════════
# 2. Exibição da Grande Tabela Comparativa de Indicadores Contábeis
# ════════════════════════════════════════════════════════════════════
W = 95
print("=" * W)
print("             TABELA COMPARATIVA DE INDICADORES CONTÁBEIS E GERAÇÃO DE VALOR (2025)")
print("=" * W)
print(f"  {'Grupo / Indicador / Métrica':<45} {'ABEV3':>14} {'AMER3':>14} {'ASAI3':>14}")
print("=" * W)

def print_row(label, key, formatter_type, divisor=1):
    row_str = f"  {label:<45}"
    for t in TICKERS:
        val = dados_empresas[t].get(key)
        if val is None or val == "":
            row_str += f" {'N/D':>14}"
            continue
        
        val_calc = val / divisor
        if formatter_type == 'currency':
            val_mi = val_calc / 1000.0
            row_str += f"  R$ {val_mi:>8,.0f} mi"
        elif formatter_type == 'currency_raw':
            row_str += f"  R$ {val_calc:>8,.2f}"
        elif formatter_type == 'percent':
            row_str += f" {val_calc*100:>13.2f}%"
        elif formatter_type == 'decimal':
            row_str += f" {val_calc:>14.4f}"
        elif formatter_type == 'decimal_short':
            row_str += f" {val_calc:>14.2f}"
        elif formatter_type == 'int':
            row_str += f" {int(val_calc):>14,}"
        else:
            row_str += f" {str(val_calc):>14}"
    print(row_str)

# 1. DESEMPENHO OPERACIONAL E RENTABILIDADE (DRE)
print("  1. DESEMPENHO OPERACIONAL E RENTABILIDADE (DRE)")
print_row("     Receita Líquida", "receita", "currency")
print_row("     Lucro Bruto", "lb", "currency")
print_row("     Margem Bruta", "mb", "percent")
print_row("     EBITDA", "ebitda", "currency")
print_row("     Margem EBITDA", "m_ebitda", "percent")
print_row("     EBIT (Lucro Operacional)", "ebit", "currency")
print_row("     Margem EBIT", "m_ebit", "percent")
print_row("     NOPAT (Lucro Operac. Pós-Tributação)", "nopat", "currency")
print_row("     Lucro Líquido", "ll", "currency")
print_row("     Margem Líquida", "margem_liq", "percent")
print("-" * W)

# 2. ESTRUTURA PATRIMONIAL (BP)
print("  2. ESTRUTURA PATRIMONIAL (Balanço Patrimonial)")
print_row("     Ativo Total", "at", "currency")
print_row("     Ativo Circulante (AC)", "ac", "currency")
print_row("     Ativo Não Circulante (ANC)", "anc", "currency")
print_row("     Passivo Circulante (PC)", "pc", "currency")
print_row("     Passivo Não Circulante (PNC)", "pnc", "currency")
print_row("     Patrimônio Líquido (PL)", "pl", "currency")
print_row("     Caixa e Equivalentes", "cx", "currency")
print_row("     Dívida Bruta", "div_bruta", "currency")
print_row("     Dívida Líquida", "div_liq", "currency")
print("-" * W)

# 3. LIQUIDEZ E GESTÃO DE CAPITAL DE GIRO
print("  3. LIQUIDEZ E GESTÃO DE CAPITAL DE GIRO")
print_row("     Liquidez Corrente", "lc", "decimal_short")
print_row("     Liquidez Seca", "ls", "decimal_short")
print_row("     Liquidez Imediata", "li", "decimal_short")
print_row("     Liquidez Geral", "lg", "decimal_short")
print_row("     CCL (Capital Circulante Líquido)", "ccl", "currency")
print_row("     ACO (Ativo Circulante Operacional)", "aco", "currency")
print_row("     PCO (Passivo Circulante Operacional)", "pco", "currency")
print_row("     NCG (Necessidade de Capital de Giro)", "ncg", "currency")
print_row("     ST (Saldo de Tesouraria)", "st", "currency")
print("-" * W)

# 4. ESTRUTURA DE CAPITAL E ENDIVIDAMENTO
print("  4. ESTRUTURA DE CAPITAL E ENDIVIDAMENTO")
print_row("     Endividamento Geral (Passivo/Ativo)", "eg", "percent")
print_row("     Relação de Capitais (Passivo/PL)", "rc", "decimal_short")
print_row("     Composição do Endividamento (PC/Passivo)", "ce", "percent")
print("-" * W)

# 5. RETORNO SOBRE O CAPITAL E CRIAÇÃO DE VALOR
print("  5. RETORNO SOBRE O CAPITAL E CRIAÇÃO DE VALOR")
print_row("     ROE (Retorno sobre o PL)", "roe", "percent")
print_row("     ROA (Retorno sobre o Ativo)", "roa", "percent")
print_row("     ROI (EBIT / Ativo Total)", "roi", "percent")
print_row("     ROIC (Retorno s/ Capital Investido)", "roic", "percent")
print_row("     Beta Sistemático (vs IBOV)", "beta", "decimal_short")
print_row("     Custo de Capital Próprio (Ke)", "ke", "percent")
print_row("     Custo Médio Ponderado de Capital (WACC)", "wacc", "percent")
print_row("     Capital Investido Operacional", "cap_investido", "currency")
print_row("     EVA (Economic Value Added)", "eva", "currency")
print("-" * W)

# 6. VALUATION E MÚLTIPLOS DE MERCADO
print("  6. VALUATION E MÚLTIPLOS DE MERCADO")
print_row("     Preço da Ação (R$)", "preco", "currency_raw")
print_row("     Qtd. Ações (mil)", "n_shares", "int", divisor=1000)
print_row("     Valor de Mercado (Market Cap)", "mkt_cap", "currency", divisor=1000)
print_row("     Enterprise Value (EV)", "ev", "currency", divisor=1000)
print_row("     P / L (Preço / Lucro)", "p_l", "decimal_short")
print_row("     P / VPA", "p_vpa", "decimal_short")
print_row("     EV / EBITDA", "ev_ebitda", "decimal_short")
print_row("     EV / EBIT", "ev_ebit", "decimal_short")
print_row("     Dividend Yield (DY)", "dy", "percent", divisor=100)
print("=" * W)

# ════════════════════════════════════════════════════════════════════
# 3. Análise Econômico-Financeira Acadêmica
# ════════════════════════════════════════════════════════════════════
print("\nANÁLISE COMPARATIVA CORPORATIVA E DIAGNÓSTICO DE DESEMPENHO:")
print("-" * W)
print("Esta análise avalia qual das três companhias apresenta a melhor performance corporativa sob a")
print("perspectiva de eficiência contábil, solidez patrimonial e criação de valor econômico (EVA).")
print()
print("1. ABEV3 (Ambev S.A.) - A Melhor Performance Geral e Geração de Riqueza Econômica:")
print("   * Eficiência Operacional: A Ambev é o destaque absoluto do grupo. Apresenta uma Margem Bruta de 51.42%,")
print("     Margem EBITDA de 34.29% e Margem EBIT de 26.54%. Esse forte controle de custos se reflete na Margem")
print("     Líquida de 18.12%, gerando um Lucro Líquido robusto de R$ 15,988 milhões.")
print("   * Retorno e Criação de Valor: O ROIC atingiu 29.16%, o que representa um Retorno pós-tax (ROIC pós-tax) de")
print("     19.24%. Esse retorno supera com folga o seu Custo Médio Ponderado de Capital (WACC) de 14.08%. Esse spread")
print("     de retorno positivo (+5.16%) gerou um EVA de R$ 4,148 milhões. É a única das três empresas que cria")
print("     riqueza real para os seus investidores no período.")
print("   * Estrutura de Capital: A Ambev opera com uma estrutura extremamente conservadora. O Endividamento Geral")
print("     é de 38.81% (Passivo/Ativo) e a empresa possui caixa líquido excedente (Dívida Líquida negativa em R$ 8,440 milhões).")
print("   * Diagnóstico: A Ambev combina altíssima rentabilidade operacional com ausência de endividamento nocivo, sendo")
print("     a melhor empresa sob qualquer perspectiva econômico-financeira analisada.")
print()
print("2. ASAI3 (Assaí Atacadista) - Boa Eficiência Operacional Pressionada pelo Endividamento:")
print("   * Eficiência Operacional: O Assaí opera com margens menores devido à natureza do atacarejo (Margem Bruta de 16.87%"),
print("     e Margem EBITDA de 5.07%). Contudo, em termos absolutos, gera um expressivo resultado operacional, com EBIT")
print("     de R$ 3,623 milhões e NOPAT de R$ 2,391 milhões.")
print("   * Retorno e Criação de Valor: O ROIC pré-tax é de 13.48%, gerando um ROIC pós-tax de 8.89%. Embora a operação seja")
print("     eficiente, este retorno é inferior ao seu Custo Médio Ponderado de Capital (WACC) de 10.14%. Esse spread")
print("     pós-tax negativo (-1.25%) sobre a volumosa base de Capital Investido (R$ 26,873 milhões) resulta em uma")
print("     destruição residual de valor econômico, com EVA de -R$ 333 milhões.")
print("   * Estrutura de Capital: O principal problema do Assaí é o endividamento. O Endividamento Geral é de 88.39%")
print("     e a Relação de Capitais (Passivo/PL) é de 7.61, demonstrando elevada dependência de capital de terceiros.")
print("   * Diagnóstico: Uma operação comercial saudável e rentável, porém sobrecarregada por despesas financeiras decorrentes")
print("     da forte alavancagem, o que impossibilita a geração de valor econômico líquido.")
print()
print("3. AMER3 (Lojas Americanas S.A.) - Situação Crítica e Forte Destruição de Valor:")
print("   * Eficiência Operacional: A Americanas apresenta prejuízo contábil de R$ 271 milhões (Margem Líquida de -2.20%).")
print("     Margem EBIT de apenas 2.69% e NOPAT irrelevante de R$ 218 milhões.")
print("   * Retorno e Criação de Valor: O ROIC pré-tax é de 3.14% (ROIC pós-tax de 2.07%), muito inferior ao seu WACC de 12.28%.")
print("     Este spread destrutivo de -10.21% resulta em um EVA negativo de -R$ 1,074 milhões, caracterizando severa")
print("     destruição de riqueza corporativa.")
print("   * Estrutura de Capital: Embora a liquidez corrente seja temporariamente inflada (1.67) e o saldo de tesouraria")
print("     esteja positivo devido ao processo de recuperação judicial (retenção de caixa por postergação de dívidas), o")
print("     risco sistemático é altíssimo (Beta de 1.24) e o endividamento geral é de 70.71%.")
print("   * Diagnóstico: Trata-se de uma corporação em estado de insolvência prática, com forte destruição de valor e")
print("     totalmente dependente de reestruturações societárias e contábeis de curto prazo.")
print()
print("CONCLUSÃO FINAL:")
print("A análise dos indicadores e a mensuração do EVA revelam com clareza a classificação corporativa:")
print("  1º Lugar: Ambev (ABEV3) - Excelente rentabilidade, estrutura patrimonial impecável e geração de valor econômico.")
print("  2º Lugar: Assaí (ASAI3) - Operação comercial robusta, mas prejudicada financeiramente pelo alto custo do endividamento.")
print("  3º Lugar: Americanas (AMER3) - Destruição de valor acentuada, prejuízos operacionais e alto risco corporativo.")
print("=" * W)
