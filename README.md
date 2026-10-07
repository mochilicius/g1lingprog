# Chuvas e Deslizamentos no RJ

**Giovanna Poggi · Linguagens de Programação · Prof. Alexandre Louzada · Avaliação G1 (Tema 9)**

Análise de 756 registros mensais simulados (7 cidades do RJ × 9 anos × 12 meses, 2015–2023) para descobrir a partir de quanta chuva os deslizamentos começam e onde a prevenção deve agir primeiro.

## Pergunta

A partir de qual volume mensal de chuva os deslizamentos aumentam de forma relevante, e quais meses e cidades devem ser priorizados na prevenção?

## Principais resultados

- Nenhum mês abaixo de **150 mm** teve deslizamento; todos os meses a partir de 150 mm tiveram.
- Meses com **400 mm ou mais** são 38% dos meses e concentram **65%** dos deslizamentos.
- Correlação de Pearson entre chuva e deslizamentos: **0,81** (entre 0,78 e 0,84 em cada cidade).
- O mês do calendário quase não muda o risco: entre o pior e o melhor mês a diferença é de ~2,3 deslizamentos.
- **Duque de Caxias** e **Nova Friburgo** são as cidades com mais deslizamentos a cada 100 mm de chuva.

## Estrutura

```text
g1lingprog/
├── app.py                 # dashboard Streamlit
├── requirements.txt       # dependências
├── README.md
├── index.html             # página do projeto (GitHub Pages)
├── dados/
│   └── dados_chuva.xlsx   # base original do professor
├── database/
│   └── chuvas_deslizamentos.sqlite   # base tratada (recriada pelo app e pelo notebook)
├── notebooks/
│   └── analise_chuvas_deslizamentos.ipynb
└── imagens/               # gráficos exportados do notebook
```

## Como executar

```bash
git clone https://github.com/mochilicius/g1lingprog.git
cd g1lingprog
pip install -r requirements.txt
streamlit run app.py
```

O notebook está em `notebooks/` e já vem com os resultados. Para rodar de novo, abra no VS Code ou Jupyter e execute todas as células (ele baixa a base com `requests`, então precisa de internet).

## KPIs

| KPI | Cálculo | Para que serve |
|---|---|---|
| Média de deslizamentos por faixa de chuva (principal) | média por cidade-mês nas faixas 0–150, 150–250, 250–400, 400+ mm | as faixas viram níveis de alerta |
| Correlação chuva × deslizamentos | Pearson entre `chuva_mm` e `deslizamentos` | mede se as duas andam juntas |
| Deslizamentos por 100 mm de chuva | soma(deslizamentos) / soma(chuva) × 100, por cidade | mostra quais cidades são mais sensíveis |

## Dashboard

- Filtros por cidade, período, mês do ano e nível de alerta
- 5 KPIs recalculados a cada filtro
- 7 seções: níveis de alerta (com simulador de chuva), série temporal + 10 piores episódios, cidades, meses do ano + heatmap, dados com download CSV, consulta SQL e conclusão executiva
- Interpretação textual em cada seção

## Requisitos atendidos

| Requisito | Onde |
|---|---|
| Python, Pandas, Matplotlib, Seaborn, Streamlit, GitHub | notebook e `app.py` |
| Intermediárias | filtros múltiplos, KPIs dinâmicos, análise temporal, dashboard em seções, visualizações comparativas |
| Avançada: correlação estatística | KPI de apoio 1 (notebook) e KPI do dashboard |
| Avançada: persistência em banco | SQLAlchemy + SQLite (seção 5.1 do notebook e aba "Consulta SQL") |
| Avançada: consumo de API | download da base com `requests` (seção 4 do notebook) |
| Notebook | introdução, base, leitura, limpeza, atributos, exploração, KPIs, gráficos, interpretação, conclusão |
| Página HTML | `index.html` |

## Links de entrega

- GitHub: https://github.com/mochilicius/g1lingprog
- GitHub Pages: https://mochilicius.github.io/g1lingprog/
- Streamlit: _preencher após publicar_

## Fonte

Repositório [Dados-Simulados](https://github.com/AlexandreLouzada/Dados-Simulados) do professor Alexandre Louzada, arquivo `Simulacao_Chuva_Deslizamentos_RJ_2015_2023.xlsx`. Os dados são **simulados** e mensais, então o limite exato de 150 mm é mais limpo do que seria com registros reais.
