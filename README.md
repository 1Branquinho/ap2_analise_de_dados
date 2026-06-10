# Análise de Geração de Valor (EVA) e Risco Estocástico (Monte Carlo)
### Estudo Comparativo Multicritério: Ambev (`ABEV3`), Assaí (`ASAI3`) e Americanas (`AMER3`) frente ao Ibovespa (`IBOV`) (2021-2025)

Este repositório contém o trabalho completo de análise financeira, contábil, de mercado e prospecção estocástica para o período de 2021 a 2025. O projeto está estruturado de forma limpa e organizada, dividindo os entregáveis em documentos formatados no padrão de apresentação acadêmica/profissional e os códigos-fonte utilizados para as simulações e processamentos estatísticos.

---

## 📂 Estrutura do Repositório

### 📄 Entregáveis Principais (Raiz do Projeto)
Estes são os arquivos prontos para entrega final, nomeados sequencialmente para facilitar a leitura:
*   **`1_Relatorio_Escrito_Completo.docx`**: Monografia acadêmica de 9 páginas, cobrindo introdução, perfil estratégico das empresas, análise contábil horizontal/vertical (2025), estudo de criação de valor (EVA), performance de mercado e os resultados estocásticos da Simulação de Monte Carlo. Inclui todas as tabelas e gráficos integrados, com notas metodológicas e referências completas.
*   **`2_Apresentacao_Executiva.pptx`**: Apresentação executiva de 16 slides em formato widescreen (16:9) em *Light Theme*. O design foi polido utilizando cores sóbrias (Slate/Deep Blue) com caixas minimalistas de cantos retos e *bullet points* sintéticos (text-light) para focar na fala e nos gráficos financeiros.
*   **`3_Roteiro_de_Falas_Speech.docx`**: Script de apoio ao apresentador estruturado slide por slide. Fornece uma introdução macro, contextualização das três marcas e seções individuais dedicadas para a Ambev, Assaí e Americanas, facilitando a divisão de temas durante a apresentação.
*   **`4_Referencias_Bibliograficas.docx`**: Documentação bibliográfica completa no padrão **ABNT NBR 6023:2018**, organizando de forma rigorosa as fontes primárias (demonstrações contábeis e relatórios de RI), secundárias (dados de mercado, cotações e APIs), bases teóricas, manuais acadêmicos e ferramentas computacionais/linguagens de programação.

---

### 💻 Módulos de Código e Scripts (`/codigo`)
Diretório dedicado a toda a engenharia de dados e modelagem estatística. Os scripts estão estruturados e podem ser executados a partir do diretório raiz:
*   **`codigo/comparativo_decisao.py`**: Consolida os dados financeiros e calcula margens, estrutura de capital, indicadores de liquidez clássicos e de Fleuriet, endividamento geral, ROIC e o **Economic Value Added (EVA)**.
*   **`codigo/comparativo_acoes.py`**: Baixa cotações diárias de fechamento (2021–2025), calcula retornos acumulados, anualizados (CAGR), volatilidades históricas, Betas sistemáticos, Índices Sharpe (com taxa livre de risco Selic de 10,75% a.a.) e Máximos Drawdowns. Gera as curvas comparativas e os gráficos individuais.
*   **`codigo/monte_carlo.py`**: Executa a simulação estocástica por **Movimento Browniano Geométrico (MBG)** com 10.000 caminhos projetados para 252 dias úteis de 2026. Calcula o Value at Risk (VaR 95%), preços medianos projetados e as probabilidades de perda nominal.
*   **`codigo/analises_balanco/`**: Contém os scripts individuais de raspagem e tratamento de dados contábeis (balanços e DREs):
    *   `abev3.py` (Ambev S.A.)
    *   `asai3.py` (Assaí Atacadista)
    *   `amer3.py` (Lojas Americanas S.A.)
*   **Scripts de Geração (`gerar_*.py`)**: Scripts utilitários que automatizam a compilação e formatação dos documentos de Word e PowerPoint utilizando bibliotecas Python (`python-docx` e `python-pptx`), garantindo conformidade visual com os dados estatísticos gerados.

---

### 📊 Ativos Dinâmicos e Caches (`/graficos`)
Diretório contendo os caches de dados em JSON e as imagens geradas pelos scripts Python:
*   `dados_*.json`: Caches contábeis coletados da API regulatória.
*   `evolucao_*.png`: Gráficos de cotações de fechamento diárias históricas das empresas.
*   `comparativo_retorno.png`: Curva normalizada de retornos das 3 ações frente ao Ibovespa.
*   `monte_carlo_*.png`: Gráficos contendo os funis de probabilidade de Monte Carlo para 2026.

---

## 🚀 Como Executar os Scripts e Coletar os Dados

### 1. Pré-requisitos e Dependências
Certifique-se de ter o Python 3 instalado no sistema. Instale as bibliotecas necessárias utilizando o comando:
```bash
pip install pandas numpy matplotlib yfinance python-docx python-pptx requests
```

### 2. Configurando as Variáveis de Ambiente
1. Renomeie o arquivo `.env.example` para `.env`:
   ```bash
   mv .env.example .env  # No terminal Bash ou comando equivalente no Windows (rename)
   ```
2. Abra o arquivo `.env` e preencha o seu token de acesso à API:
   ```env
   API_TOKEN=seu_token_aqui
   ```

### 3. Execução Passo a Passo
Todos os scripts devem ser executados a partir do diretório raiz do projeto para manter a integridade dos caminhos relativos de leitura/gravação:

1.  **Coletar Dados Contábeis (API)**:
    ```bash
    python codigo/analises_balanco/abev3.py
    python codigo/analises_balanco/amer3.py
    python codigo/analises_balanco/asai3.py
    ```
    *Isso criará os caches JSON na pasta `graficos/`.*

2.  **Visualizar Painel Contábil & EVA**:
    ```bash
    python codigo/comparativo_decisao.py
    ```

3.  **Processar Dados de Mercado & Gráficos**:
    ```bash
    python codigo/comparativo_acoes.py
    ```
    *Gera as curvas de retornos históricos e correlação diária.*

4.  **Rodar a Simulação de Monte Carlo**:
    ```bash
    python codigo/monte_carlo.py
    ```
    *Simula 10.000 caminhos de preços para 2026 e desenha os funis de risco.*

5.  **Regenerar Documentos Finais (Opcional)**:
    Se desejar alterar textos ou atualizar dados e compilar os arquivos DOCX/PPTX novamente, execute:
    ```bash
    python codigo/gerar_trabalho_completo.py
    python codigo/gerar_apresentacao.py
    python codigo/gerar_roteiro_docx.py
    python codigo/gerar_referencias.py
    ```
