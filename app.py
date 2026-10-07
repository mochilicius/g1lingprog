from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from sqlalchemy import create_engine

# ---------------- CONFIGURAÇÃO ----------------
st.set_page_config(page_title="Chuvas e Deslizamentos no RJ", layout="wide")

# mesmo padrão visual do notebook
sns.set_theme(style="ticks")
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False

CYAN = "#2ad6b1"
ROXO = "#a52ad6"
LARANJA = "#eb6834"
CINZA = "#8a8984"

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# faixas de chuva = níveis de alerta (KPI principal, definidos no notebook)
FAIXAS = [0, 150, 250, 400, np.inf]
NIVEIS = ["Sem risco", "Atenção", "Alerta", "Crítico"]
CORES_NIVEIS = [CINZA, CYAN, ROXO, LARANJA]

# caminhos relativos ao próprio .py, assim funciona rodando de qualquer pasta (inclusive no streamlit cloud)
BASE_DIR = Path(__file__).parent
CAMINHO_XLSX = BASE_DIR / "dados" / "dados_chuva.xlsx"
CAMINHO_BANCO = BASE_DIR / "database" / "chuvas_deslizamentos.sqlite"


# ---------------- DADOS ----------------
# mesma limpeza do notebook (seção 5), guardada em cache para não reler o excel a cada clique
@st.cache_data
def carregar_dados(caminho):
    df = pd.read_excel(caminho).rename(columns={
        "Cidade": "cidade",
        "Ano": "ano",
        "Mês": "mes",
        "Volume de Chuva (mm)": "chuva_mm",
        "Número de Deslizamentos": "deslizamentos",
    })
    df = df.dropna(subset=["chuva_mm", "deslizamentos"]).drop_duplicates(subset=["cidade", "ano", "mes"])

    df["mes_num"] = df["mes"].map({m: i + 1 for i, m in enumerate(MESES)})
    df["data"] = pd.to_datetime(dict(year=df["ano"], month=df["mes_num"], day=1))
    df["mes"] = pd.Categorical(df["mes"], categories=MESES, ordered=True)

    # right=False: 150 mm já cai em "Atenção"
    df["faixa_chuva"] = pd.cut(df["chuva_mm"], bins=FAIXAS, labels=NIVEIS, right=False)
    df["teve_deslizamento"] = df["deslizamentos"] > 0
    return df


df = carregar_dados(CAMINHO_XLSX)


# persistência: grava a base tratada numa tabela do sqlite (via sqlalchemy)
# cache_resource porque o engine é uma conexão, não um dado: cria uma vez e reaproveita
@st.cache_resource
def criar_banco(_df):
    CAMINHO_BANCO.parent.mkdir(exist_ok=True)
    engine = create_engine(f"sqlite:///{CAMINHO_BANCO}")
    # sqlite não tem tipo category nem datetime, então mês e faixa vão como texto
    tabela = _df[["cidade", "ano", "mes", "mes_num", "chuva_mm", "deslizamentos", "faixa_chuva"]].astype(
        {"mes": str, "faixa_chuva": str}
    )
    tabela.to_sql("chuvas", engine, if_exists="replace", index=False)
    return engine


engine = criar_banco(df)

# ---------------- FILTROS ----------------
st.sidebar.title("Filtros")

lista_cidades = sorted(df["cidade"].unique())
cidades = st.sidebar.multiselect("Cidades", options=lista_cidades, default=lista_cidades)

ano_min, ano_max = int(df["ano"].min()), int(df["ano"].max())
anos = st.sidebar.slider("Período", min_value=ano_min, max_value=ano_max, value=(ano_min, ano_max))

meses = st.sidebar.multiselect("Meses do ano", options=MESES, default=MESES)

niveis = st.sidebar.multiselect("Nível de alerta", options=NIVEIS, default=NIVEIS)

df_f = df[
    df["cidade"].isin(cidades)
    & df["ano"].between(anos[0], anos[1])
    & df["mes"].isin(meses)
    & df["faixa_chuva"].isin(niveis)
]

if df_f.empty:
    st.warning("Nenhum dado com esses filtros. Selecione pelo menos uma opção em cada filtro.")
    st.stop()

st.sidebar.caption(f"{len(df_f)} de {len(df)} registros (cidade × mês)")
st.sidebar.caption("Dados simulados, fonte: AlexandreLouzada/Dados-Simulados")

# ---------------- CABEÇALHO E KPIs ----------------
st.title("Chuvas e Deslizamentos no RJ (2015–2023)")
st.markdown(
    "A partir de qual volume mensal de chuva os deslizamentos aumentam, "
    "e quais meses e cidades devem ser priorizados na prevenção?"
)

total_desliz = int(df_f["deslizamentos"].sum())
chuva_media = df_f["chuva_mm"].mean()
pct_criticos = (df_f["faixa_chuva"] == "Crítico").mean() * 100

# correlação precisa de pelo menos 2 valores diferentes, senão dá NaN
corr = df_f["chuva_mm"].corr(df_f["deslizamentos"])
corr_txt = "—" if pd.isna(corr) else f"{corr:.2f}"

# sensibilidade: deslizamentos a cada 100 mm de chuva
sensib = total_desliz / df_f["chuva_mm"].sum() * 100

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Deslizamentos", f"{total_desliz:,}".replace(",", "."))
c2.metric("Chuva média/mês", f"{chuva_media:.0f} mm")
c3.metric("Correlação", corr_txt, help="Pearson entre chuva e deslizamentos (-1 a 1)")
c4.metric("Desliz. por 100 mm", f"{sensib:.2f}")
c5.metric("Meses críticos", f"{pct_criticos:.0f}%", help="Meses com 400 mm ou mais")

st.caption(
    "Dados mensais simulados de 7 cidades do RJ (2015–2023). "
    "Use os filtros da barra lateral: os indicadores, gráficos e tabelas são recalculados."
)

aba1, aba2, aba3, aba4, aba5, aba6, aba7 = st.tabs(
    ["Níveis de alerta", "Série temporal", "Cidades", "Meses do ano", "Dados", "Consulta SQL", "Conclusão"]
)

# ---------------- ABA 1: LIMIAR E FAIXAS ----------------
with aba1:
    col_a, col_b = st.columns(2)

    with col_a:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.scatter(df_f["chuva_mm"], df_f["deslizamentos"], color=ROXO, alpha=0.4, s=18)
        ax.axvline(150, color=LARANJA, linestyle="--", label="150 mm: começam os deslizamentos")
        ax.set_title("Chuva × deslizamentos (cada ponto = cidade no mês)")
        ax.set_xlabel("Chuva no mês (mm)")
        ax.set_ylabel("Deslizamentos no mês")
        ax.legend(frameon=False)
        st.pyplot(fig)
        plt.close(fig)

    with col_b:
        kpi_faixa = df_f.groupby("faixa_chuva", observed=False).agg(
            meses=("deslizamentos", "size"),
            media_desliz=("deslizamentos", "mean"),
            total_desliz=("deslizamentos", "sum"),
        )
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(kpi_faixa.index.astype(str), kpi_faixa["media_desliz"].fillna(0), color=CORES_NIVEIS, width=0.6)
        for i, valor in enumerate(kpi_faixa["media_desliz"]):
            if not pd.isna(valor):
                ax.text(i, valor + 0.3, f"{valor:.1f}", ha="center", fontweight="bold")
        ax.set_title("Média de deslizamentos por nível de alerta")
        ax.set_ylabel("Média de deslizamentos por mês")
        st.pyplot(fig)
        plt.close(fig)

    tabela = kpi_faixa.copy()
    tabela["% dos meses"] = tabela["meses"] / tabela["meses"].sum() * 100
    tabela["% dos deslizamentos"] = tabela["total_desliz"] / max(tabela["total_desliz"].sum(), 1) * 100
    tabela.index = ["Sem risco (< 150 mm)", "Atenção (150–250 mm)", "Alerta (250–400 mm)", "Crítico (≥ 400 mm)"]
    tabela.columns = ["Meses", "Média desliz.", "Total desliz.", "% dos meses", "% dos deslizamentos"]
    st.dataframe(tabela.round(1))

    # interpretação recalculada com os filtros
    if tabela["Total desliz."].sum() > 0:
        pct_crit = tabela.loc["Crítico (≥ 400 mm)", "% dos deslizamentos"]
        st.markdown(
            f"**Interpretação:** abaixo de 150 mm não há deslizamentos, e a média sobe a cada nível. "
            f"Nos dados filtrados, os meses críticos concentram **{pct_crit:.0f}%** de todos os deslizamentos."
        )

    # simulador: o gestor digita a chuva acumulada e vê o nível de alerta
    st.subheader("Simulador de alerta")
    chuva_sim = st.slider("Chuva acumulada no mês (mm)", 0, 600, 200, step=10)
    nivel = pd.cut([chuva_sim], bins=FAIXAS, labels=NIVEIS, right=False)[0]
    media_nivel = kpi_faixa.loc[nivel, "media_desliz"]
    texto = f"**Nível: {nivel}**"
    if not pd.isna(media_nivel):
        texto += f" · média histórica de {media_nivel:.1f} deslizamentos por cidade nesse nível"
    if nivel == "Sem risco":
        st.success(texto)
    elif nivel == "Atenção":
        st.info(texto)
    elif nivel == "Alerta":
        st.warning(texto)
    else:
        st.error(texto)

# ---------------- ABA 2: SÉRIE TEMPORAL ----------------
with aba2:
    serie = df_f.groupby("data")[["chuva_mm", "deslizamentos"]].sum()

    # dois eixos y separados porque as escalas são muito diferentes
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 5), sharex=True)
    ax1.plot(serie.index, serie["chuva_mm"], color=ROXO)
    ax1.set_ylabel("Chuva (mm)")
    ax1.set_title("Chuva e deslizamentos ao longo do tempo (soma das cidades selecionadas)")
    ax2.plot(serie.index, serie["deslizamentos"], color=LARANJA)
    ax2.set_ylabel("Deslizamentos")
    ax2.set_xlabel("Mês/Ano")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    st.markdown(
        "**Interpretação:** os picos de chuva e de deslizamentos coincidem praticamente mês a mês, "
        "e não há tendência de alta ao longo dos anos nem uma onda repetida todo verão."
    )

    st.subheader("Os 10 piores episódios")
    top10 = df_f.nlargest(10, "deslizamentos")[["cidade", "ano", "mes", "chuva_mm", "deslizamentos"]]
    st.dataframe(top10, hide_index=True)

# ---------------- ABA 3: CIDADES ----------------
with aba3:
    por_cidade = df_f.groupby("cidade").agg(
        chuva_media=("chuva_mm", "mean"),
        chuva_total=("chuva_mm", "sum"),
        desliz_total=("deslizamentos", "sum"),
        meses_criticos=("faixa_chuva", lambda s: (s == "Crítico").sum()),
    )
    por_cidade["desliz_por_100mm"] = por_cidade["desliz_total"] / por_cidade["chuva_total"] * 100
    ordem = por_cidade.sort_values("desliz_por_100mm")

    fig, ax = plt.subplots(figsize=(9, 4))
    cores_cid = [LARANJA if v > sensib else ROXO for v in ordem["desliz_por_100mm"]]
    ax.barh(ordem.index, ordem["desliz_por_100mm"], color=cores_cid)
    ax.axvline(sensib, color=CINZA, linestyle="--", label=f"média da seleção ({sensib:.2f})")
    ax.set_title("Deslizamentos a cada 100 mm de chuva (laranja = acima da média)")
    ax.set_xlabel("Deslizamentos por 100 mm de chuva")
    ax.set_xlim(0, max(ordem["desliz_por_100mm"].max() * 1.25, 0.1))
    ax.legend(frameon=False, loc="lower right")
    st.pyplot(fig)
    plt.close(fig)

    st.dataframe(
        por_cidade.sort_values("desliz_por_100mm", ascending=False).round(2)
    )

    mais_sensivel = ordem.index[-1]
    st.markdown(
        f"**Interpretação:** **{mais_sensivel}** é a cidade que mais transforma chuva em deslizamento "
        f"({ordem['desliz_por_100mm'].iloc[-1]:.2f} a cada 100 mm). "
        "As cidades em laranja devem ter prioridade em obras de contenção de encostas."
    )

# ---------------- ABA 4: SAZONALIDADE ----------------
with aba4:
    por_mes = df_f.groupby("mes", observed=True).agg(
        chuva_media=("chuva_mm", "mean"),
        desliz_medio=("deslizamentos", "mean"),
    )
    media_geral = df_f["deslizamentos"].mean()

    fig, ax = plt.subplots(figsize=(10, 4))
    cores_mes = [LARANJA if v > media_geral else ROXO for v in por_mes["desliz_medio"]]
    ax.bar(por_mes.index.astype(str), por_mes["desliz_medio"], color=cores_mes, width=0.6)
    ax.axhline(media_geral, color=CINZA, linestyle="--", label=f"média geral ({media_geral:.1f})")
    ax.set_title("Média de deslizamentos por mês do ano")
    ax.set_ylabel("Média de deslizamentos por mês")
    ax.set_ylim(0, 16)  # mesma escala do gráfico de níveis, para comparar
    ax.legend(frameon=False)
    st.pyplot(fig)
    plt.close(fig)

    st.caption(
        "Com a mesma escala do gráfico de níveis de alerta, as barras dos meses ficam todas parecidas: "
        "o volume de chuva explica muito mais do que a época do ano."
    )

    # mapa de calor: chuva média por cidade e mês
    pivot = df_f.pivot_table(index="cidade", columns="mes", values="chuva_mm", aggfunc="mean", observed=True)
    fig, ax = plt.subplots(figsize=(11, 4))
    sns.heatmap(pivot, cmap="Purples", annot=True, fmt=".0f", cbar_kws={"label": "mm"}, ax=ax)
    ax.set_title("Chuva média (mm) por cidade e mês")
    ax.set_xlabel("")
    ax.set_ylabel("")
    st.pyplot(fig)
    plt.close(fig)

# ---------------- ABA 5: DADOS ----------------
with aba5:
    colunas = ["cidade", "ano", "mes", "chuva_mm", "deslizamentos", "faixa_chuva"]
    st.dataframe(df_f[colunas], hide_index=True)

    csv = df_f[colunas].to_csv(index=False).encode("utf-8")
    st.download_button("Baixar CSV filtrado", data=csv, file_name="chuvas_deslizamentos_filtrado.csv", mime="text/csv")

# ---------------- ABA 6: CONSULTA SQL ----------------
with aba6:
    st.subheader("Consulta SQL com SQLAlchemy")
    st.markdown(
        "A base tratada foi gravada na tabela `chuvas` do banco SQLite "
        "`database/chuvas_deslizamentos.sqlite`. A consulta abaixo recalcula o KPI principal "
        "direto no banco, respeitando os filtros de cidade e período."
    )

    # um "?" por cidade selecionada: os valores vão como parâmetros, nunca colados no texto do sql
    marcadores = ", ".join("?" for _ in cidades)
    consulta = f"""
SELECT faixa_chuva,
       COUNT(*)                     AS meses,
       ROUND(AVG(deslizamentos), 2) AS media_desliz,
       SUM(deslizamentos)           AS total_desliz
FROM chuvas
WHERE cidade IN ({marcadores})
  AND ano BETWEEN ? AND ?
GROUP BY faixa_chuva
ORDER BY MIN(chuva_mm)
""".strip()
    resultado_sql = pd.read_sql(consulta, engine, params=(*cidades, anos[0], anos[1]))
    st.dataframe(resultado_sql, hide_index=True)
    st.code(consulta, language="sql")

# ---------------- ABA 7: CONCLUSÃO EXECUTIVA ----------------
with aba7:
    st.subheader("Conclusão executiva")
    st.markdown(
        """
**O risco de deslizamento depende de quanto chove, não da época do ano.**

- Nenhum mês abaixo de **150 mm** teve deslizamento; todos os meses acima tiveram.
- A partir de **400 mm** (nível crítico) acontecem cerca de **2/3 de todos os deslizamentos**.
- A correlação entre chuva e deslizamentos é forte (**0,81**) e vale para as 7 cidades.
- A diferença entre o pior e o melhor mês do calendário é de só ~2,3 deslizamentos.
- **Duque de Caxias** e **Nova Friburgo** são as cidades mais sensíveis à chuva.

**Ações recomendadas para a Defesa Civil**

1. Alerta automático por chuva acumulada no mês: atenção (150 mm), alerta (250 mm), crítico (400 mm), funcionando o ano todo.
2. Trocar o planejamento por calendário fixo (só no verão) pelo monitoramento contínuo da chuva.
3. Começar as obras de contenção por Duque de Caxias e Nova Friburgo, seguidas de Teresópolis e Petrópolis.
"""
    )
    st.info(
        "Limitações: os dados são simulados e mensais. Chuva concentrada em poucos dias "
        "não aparece no total do mês, e faltam dados de solo e ocupação das encostas."
    )
