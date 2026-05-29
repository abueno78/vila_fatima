import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
import os
import io
import re
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import gc

# Importa as funções de plotagem estática do script CLI para reutilização
from gerar_relatorio_imagens import (
    load_data,
    plot_profissionais,
    plot_faixa_etaria_mensal,
    plot_quantitativo_atendimentos,
    plot_pessoas_unicas,
    plot_idosos_pizza,
    plot_idosos_temporal,
    plot_retorno_faixas_gerais,
    plot_retorno_faixas_idosos,
    COLORS
)

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Análise Avançada de Atendimentos",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# ESTILIZAÇÃO PREMIUM (MODERNA & ALTA ESTRUTURA)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');

    * { font-family: 'Outfit', sans-serif; }

    .main { background-color: #0b0f19; }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: #121826;
        border-radius: 16px;
        padding: 8px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        margin-bottom: 24px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        color: #94a3b8;
        font-weight: 600;
        padding: 12px 28px;
        transition: all 0.3s ease;
        border: 1px solid transparent;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        color: #ffffff;
        background-color: rgba(255, 255, 255, 0.05);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #00508B, #009EDB) !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(0, 158, 219, 0.3);
    }

    .metric-card {
        background: linear-gradient(145deg, #131a2d, #0d1222);
        border: 1px solid rgba(0, 158, 219, 0.18);
        border-radius: 20px;
        padding: 24px;
        text-align: center;
        transition: all 0.3s ease;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
    }
    
    .metric-card:hover {
        border-color: rgba(0, 158, 219, 0.5);
        transform: translateY(-3px);
        box-shadow: 0 15px 35px rgba(0, 158, 219, 0.25);
    }
    
    .metric-icon { font-size: 2.2rem; margin-bottom: 8px; }
    
    .metric-title {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 6px;
        font-weight: 600;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #009EDB, #00DF89);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .metric-sub {
        font-size: 0.8rem;
        color: #64748b;
        margin-top: 6px;
    }

    .header-card {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 30px;
        padding: 30px;
        background: linear-gradient(135deg, #131a2d, #090d16);
        border-bottom: 3px solid #009EDB;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        margin-bottom: 35px;
    }
    
    .header-title {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff, #94a3b8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 6px;
    }
    
    .header-subtitle {
        font-size: 1.15rem;
        color: #38bdf8;
        font-weight: 500;
    }

    .desc-box {
        background-color: #111827;
        border-left: 4px solid #009EDB;
        border-radius: 0 12px 12px 0;
        padding: 20px;
        margin: 20px 0;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
    }
    
    .desc-box h4 {
        color: #38bdf8;
        margin-top: 0;
        font-weight: 700;
    }
    
    .desc-box p {
        color: #e2e8f0;
        font-size: 0.95rem;
        line-height: 1.6;
        margin-bottom: 0;
    }

    h1, h2, h3, h4, h5, h6 { color: #f1f5f9; font-weight: 700; }
    
    /* Input custom styling */
    div[data-testid="stSidebar"] {
        background-color: #0d1222;
        border-right: 1px solid rgba(0, 158, 219, 0.15);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# CACHE DE DADOS
# ==========================================
@st.cache_data(ttl=3600)
def get_cached_data():
    # Usa caminho relativo ao script para funcionar tanto em dev local
    # quanto no Streamlit Cloud (Linux), independente do CWD.
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'coleta_esus.db')
    gz_path = os.path.join(base_dir, 'coleta_esus.db.gz')

    # Auto-extração do banco comprimido (Streamlit Cloud não persiste arquivos descomprimidos)
    if not os.path.exists(db_path):
        if os.path.exists(gz_path):
            import gzip
            import shutil
            with gzip.open(gz_path, 'rb') as f_in:
                with open(db_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            st.error(
                f"Banco de dados não encontrado. "
                f"Esperado: `{gz_path}` ou `{db_path}`"
            )
            st.stop()

    df = load_data(db_path)

    # O banco público já contém apenas dados de 2025-2026.
    # Os filtros abaixo garantem consistência mesmo se o banco local
    # (desenvolvimento) ainda contiver anos anteriores.
    df_25_26 = df[df['year'].isin([2025, 2026])].copy()
    df_elderly = df[(df['age'] >= 60) & df['year'].isin([2025, 2026])].copy()

    del df
    gc.collect()

    return df_25_26, df_elderly

# Carrega os dados tratados do Cache
df_25_26, df_elderly = get_cached_data()

# ==========================================
# CABEÇALHO DO PAINEL
# ==========================================
st.markdown("""
<div class="header-card">
    <div style="text-align: center;">
        <div class="header-title">📊 Análise de Atendimentos Vila Fátima</div>
        <div class="header-subtitle">Estudo operacional e demográfico dos idosos — Biênio 2025-2026</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# BARRA LATERAL (INFORMAÇÕES & FILTROS)
# ==========================================
st.sidebar.image("logo_pucrs.png" if os.path.exists("logo_pucrs.png") else "https://via.placeholder.com/150", width=160)
st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.title("📌 Informações Gerais")
st.sidebar.info("""
Este painel apresenta análises sobre os atendimentos da Unidade de Saúde Vila Fátima.

**Período analisado:** Janeiro/2025 a Abril/2026.

*Dados anonimizados conforme LGPD para fins de apresentação pública.*
""")

# Função global para faixa etária
def categorize_age_global(age):
    if pd.isna(age): return 'Não Informado'
    if age <= 14: return 'Crianças (0-14)'
    elif age <= 29: return 'Jovens (15-29)'
    elif age <= 59: return 'Adultos (30-59)'
    else: return 'Idosos (60+)'

df_25_26['age_group'] = df_25_26['age'].apply(categorize_age_global)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛️ Filtros Globais")

# Lista de opções com 'Todos'
opcoes_area_geral = ["Todos"] + sorted([a for a in df_25_26['general_area'].unique() if pd.notna(a) and a != "Outros / Não Identificado"]) + ["Outros / Não Identificado"]
filtro_area_geral = st.sidebar.multiselect(
    "Filtrar por Área Geral:",
    options=opcoes_area_geral,
    default=["Todos"]
)

opcoes_idade = ["Todos", "Crianças (0-14)", "Jovens (15-29)", "Adultos (30-59)", "Idosos (60+)"]
filtro_idade = st.sidebar.multiselect(
    "Filtrar por Faixa Etária:",
    options=opcoes_idade,
    default=["Todos"]
)

# Aplicação dos Filtros (Modificando as variáveis originais para afetar todo o dashboard downstream)
if "Todos" not in filtro_area_geral and len(filtro_area_geral) > 0:
    df_25_26 = df_25_26[df_25_26['general_area'].isin(filtro_area_geral)]
    df_elderly = df_elderly[df_elderly['general_area'].isin(filtro_area_geral)]

if "Todos" not in filtro_idade and len(filtro_idade) > 0:
    df_25_26 = df_25_26[df_25_26['age_group'].isin(filtro_idade)]
    
# Métricas rápidas calculadas para a barra lateral
total_atend_25_26 = len(df_25_26)
unicos_25_26 = df_25_26['paciente_upper'].nunique()
media_retorno = total_atend_25_26 / unicos_25_26 if unicos_25_26 > 0 else 0
total_idosos = len(df_elderly)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📈 Métricas Rápidas (Filtradas)")
st.sidebar.metric("Total de Atendimentos", f"{total_atend_25_26:,}")
st.sidebar.metric("Pacientes Únicos", f"{unicos_25_26:,}")
st.sidebar.metric("Média de Visitas/Paciente", f"{media_retorno:.1f}")

# ==========================================
# CONTEÚDO PRINCIPAL (TABS)
# ==========================================
tab_desc, tab_prof, tab_idade, tab_vol_unicos, tab_idosos = st.tabs([
    "🏠 Caracterização da Unidade",
    "👥 Atendimento por Área Profissional",
    "👶👵 Distribuição por Faixa Etária",
    "📈 Volumes e Pacientes Únicos",
    "👴 Análise Detalhada dos Idosos"
])

# Função auxiliar para gerar botão de download para gráficos Matplotlib
def build_download_button(fig_function, data, filename):
    fig = fig_function(data)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig) # Libera memória do matplotlib
    return st.download_button(
        label="📥 Baixar Gráfico em Alta Resolução (PNG - 300 DPI)",
        data=buf,
        file_name=filename,
        mime="image/png"
    )

# ------------------------------------------
# TAB 0: CARACTERIZAÇÃO DA UNIDADE
# ------------------------------------------
with tab_desc:
    st.markdown("### 🏠 Caracterização e Indicadores Sociais da Vila Fátima (Censo 2022)")
    st.write("Apresentação de dados descritivos sobre o território, demografia e perfil socioeconômico da Unidade de Saúde Vila Fátima.")
    
    # 3 Métricas de Território & População
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-icon">👥</div>
            <div class="metric-title">População Residente</div>
            <div class="metric-value">4.890,7</div>
            <div class="metric-sub">Pessoas residentes no território</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-icon">🗺️</div>
            <div class="metric-title">Área Territorial</div>
            <div class="metric-value">0,5135 km²</div>
            <div class="metric-sub">Extensão total mapeada</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-icon">🏠</div>
            <div class="metric-title">Favela e Comunidade Urbana</div>
            <div class="metric-value">69,18%</div>
            <div class="metric-sub">Proporção da área territorial total</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 3 Métricas de Renda
    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-icon">💵</div>
            <div class="metric-title">Renda Média Mensal</div>
            <div class="metric-value">R$ 1.721,14</div>
            <div class="metric-sub">Renda média mensal familiar</div>
        </div>
        """, unsafe_allow_html=True)
    with c5:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-icon">📊</div>
            <div class="metric-title">Renda Mediana Mensal</div>
            <div class="metric-value">R$ 1.212,00</div>
            <div class="metric-sub">50% das rendas estão abaixo deste limite</div>
        </div>
        """, unsafe_allow_html=True)
    with c6:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-icon">📉</div>
            <div class="metric-title">Desvio Padrão da Renda</div>
            <div class="metric-value">R$ 378,07</div>
            <div class="metric-sub">Dispersão da renda média mensal</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col_pyramid, col_race = st.columns([1.1, 0.9])
    
    with col_pyramid:
        st.markdown("#### 📊 Distribuição por Faixa Etária (Pirâmide Etária)")
        
        categories = ['0-4 Anos', '5-9 Anos', '10-14 Anos', '15-19 Anos', '20-24 Anos', 
                      '25-29 Anos', '30-39 Anos', '40-49 Anos', '50-59 Anos', '60-69 Anos', '70 Anos ou Mais']
        
        # Contagens proporcionais da pirâmide
        male_values = [303, 380, 280, 280, 380, 290, 500, 460, 330, 230, 150]
        female_values = [275, 330, 335, 310, 380, 350, 606, 510, 420, 340, 260]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=categories,
            x=[-val for val in male_values],
            name='Masculino',
            orientation='h',
            marker=dict(color='#8ecae6'),
            hoverinfo='text',
            text=male_values,
            hovertemplate='<b>Masculino</b><br>Faixa: %{y}<br>População: %{text}<extra></extra>'
        ))
        fig.add_trace(go.Bar(
            y=categories,
            x=female_values,
            name='Feminino',
            orientation='h',
            marker=dict(color='#f1a7a1'),
            hoverinfo='text',
            text=female_values,
            hovertemplate='<b>Feminino</b><br>Faixa: %{y}<br>População: %{text}<extra></extra>'
        ))
        fig.update_layout(
            barmode='overlay',
            bargap=0.1,
            bargroupgap=0,
            xaxis=dict(
                tickvals=[-606, -303, 0, 303, 606],
                ticktext=['606', '303', '0', '303', '606'],
                title='População',
                gridcolor='rgba(255,255,255,0.08)'
            ),
            yaxis=dict(
                title='Faixa Etária'
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(x=0.75, y=0.98),
            margin=dict(l=40, r=40, t=20, b=40),
            height=450
        )
        st.plotly_chart(fig, use_container_width=True)
        
    with col_race:
        st.markdown("#### 👥 Composição por Raça/Cor (%)")
        
        raca_df = pd.DataFrame({
            'Raça/Cor': ['Branca', 'Preta', 'Parda', 'Amarela', 'Indígena'],
            'População Masculina (%)': [42.47, 31.84, 25.68, 0.00, 0.00],
            'População Feminina (%)': [43.01, 33.43, 23.32, 0.00, 0.00]
        })
        
        formatted_raca = raca_df.copy()
        formatted_raca['População Masculina (%)'] = formatted_raca['População Masculina (%)'].map('{:.2f}%'.format)
        formatted_raca['População Feminina (%)'] = formatted_raca['População Feminina (%)'].map('{:.2f}%'.format)
        
        st.dataframe(formatted_raca, use_container_width=True, hide_index=True)
        
        fig_raca = go.Figure()
        fig_raca.add_trace(go.Bar(
            x=raca_df['Raça/Cor'],
            y=raca_df['População Masculina (%)'],
            name='Masculino',
            marker_color='#8ecae6'
        ))
        fig_raca.add_trace(go.Bar(
            x=raca_df['Raça/Cor'],
            y=raca_df['População Feminina (%)'],
            name='Feminino',
            marker_color='#f1a7a1'
        ))
        fig_raca.update_layout(
            barmode='group',
            xaxis_title='Raça/Cor',
            yaxis_title='Proporção (%)',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(x=0.75, y=0.98),
            margin=dict(l=40, r=40, t=20, b=40),
            height=300,
            yaxis=dict(gridcolor='rgba(255,255,255,0.08)', range=[0, 50])
        )
        st.plotly_chart(fig_raca, use_container_width=True)

# ------------------------------------------
# TAB 1: PROFISSIONAIS
# ------------------------------------------
with tab_prof:
    st.markdown("### 👥 Agrupamento por Área Profissional (2025 - 2026)")
    st.write("Esta seção analisa o volume de atendimentos e a representatividade de cada área profissional no período de 2025 e início de 2026.")
    
    # KPIs rápidos
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">🧑‍⚕️</div>
            <div class="metric-title">Áreas Ativas</div>
            <div class="metric-value">{df_25_26['professional_area'].nunique()}</div>
            <div class="metric-sub">no período de 2025-2026</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        top_prof_name = df_25_26['professional_area'].value_counts().index[0]
        top_prof_val = df_25_26['professional_area'].value_counts().values[0]
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">👑</div>
            <div class="metric-title">Área com mais Atendimentos</div>
            <div class="metric-value" style="font-size: 1.5rem; line-height: 2.5rem; color:#009EDB; font-weight:700;">{top_prof_name}</div>
            <div class="metric-sub">{top_prof_val:,} atendimentos ({top_prof_val/total_atend_25_26*100:.1f}%)</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        concentracao_top5 = df_25_26['professional_area'].value_counts().head(5).sum() / total_atend_25_26 * 100
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">📊</div>
            <div class="metric-title">Concentração Top 5</div>
            <div class="metric-value">{concentracao_top5:.1f}%</div>
            <div class="metric-sub">dos atendimentos realizados por 5 áreas</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Divide em Colunas: Gráfico Interativo + Tabela
    col_chart, col_table = st.columns([3, 2])
    
    with col_chart:
        st.markdown("#### Gráfico Hierárquico de Explosão Solar (Sunburst)")
        st.caption("Clique nas fatias centrais (Área Geral) para expandir as áreas específicas.")
        
        # O Sunburst do Plotly exige um dataframe agrupado para melhor performance
        df_sunburst = df_25_26.groupby(['general_area', 'professional_area']).size().reset_index(name='Atendimentos')
        
        fig_sunburst = px.sunburst(
            df_sunburst,
            path=['general_area', 'professional_area'],
            values='Atendimentos',
            color='general_area',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_sunburst.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=10, l=10, r=10, b=10),
            height=500
        )
        fig_sunburst.update_traces(textinfo="label+percent parent")
        st.plotly_chart(fig_sunburst, use_container_width=True)
        
    with col_table:
        st.markdown("#### Tabela 1A: Distribuição Macro")
        df_macro = df_25_26['general_area'].value_counts().reset_index()
        df_macro.columns = ['Área Geral', 'Atendimentos']
        df_macro['Percentual'] = (df_macro['Atendimentos'] / total_atend_25_26 * 100).round(2).astype(str) + '%'
        st.dataframe(df_macro, hide_index=True, use_container_width=True, height=200)

        st.markdown("#### Tabela 1B: Distribuição Micro")
        df_micro = df_25_26.groupby(['general_area', 'professional_area']).size().reset_index(name='Atendimentos')
        df_micro = df_micro.sort_values(by=['general_area', 'Atendimentos'], ascending=[True, False])
        df_micro['Percentual'] = (df_micro['Atendimentos'] / total_atend_25_26 * 100).round(2).astype(str) + '%'
        df_micro.columns = ['Área Geral', 'Área Profissional', 'Atendimentos', 'Percentual']
        st.dataframe(df_micro, hide_index=True, use_container_width=True, height=300)
        
    # Texto Descritivo
    st.markdown("""
    <div class="desc-box">
        <h4>📝 Análise Descritiva — Distribuição por Área Profissional</h4>
        <p>
            O gráfico Sunburst ilustra a hierarquia da unidade: no círculo interior vemos as <b>Áreas Gerais</b>, e nos exteriores, 
            a sua pulverização em <b>Áreas Específicas</b>. As tabelas 1A e 1B permitem analisar não só o volume macro de cada setor (ex: total de atendimentos da Enfermagem vs. Medicina), 
            como também o peso interno de cada subespecialidade clínica dentro do setor (ex: peso da Pediatria dentro da Medicina).
        </p>
    </div>
    """, unsafe_allow_html=True)

# ------------------------------------------
# TAB 2: FAIXAS ETÁRIAS
# ------------------------------------------
with tab_idade:
    st.markdown("### 👶👵 Proporção Mensal de Atendimentos por Faixa Etária (2025 - 2026)")
    st.write("Esta seção demonstra a representatividade mensal das diferentes faixas etárias nos atendimentos clínicos realizados.")
    
    # Categorização de faixas etárias
    def categorize_age(age):
        if pd.isna(age): return 'Não Informado'
        if age <= 14: return 'Crianças (0-14)'
        elif age <= 29: return 'Jovens (15-29)'
        elif age <= 59: return 'Adultos (30-59)'
        else: return 'Idosos (60+)'

    df_age_grouped = df_25_26.copy()
    df_age_grouped['age_group'] = df_age_grouped['age'].apply(categorize_age)
    
    # KPIs Rápidos por Faixa Etária
    c1, c2, c3, c4 = st.columns(4)
    for i, grp in enumerate(['Crianças (0-14)', 'Jovens (15-29)', 'Adultos (30-59)', 'Idosos (60+)']):
        grp_cnt = (df_age_grouped['age_group'] == grp).sum()
        grp_pct = grp_cnt / total_atend_25_26 * 100
        icon = ['👶', '🎒', '🧑', '👵'][i]
        color = ['#5DADE2', '#48C9B0', '#F4D03F', '#AF7AC5'][i]
        
        with st.container():
            st.columns(4)[i].markdown(f"""
            <div class="metric-card" style="border-color: {color}33;">
                <div class="metric-icon">{icon}</div>
                <div class="metric-title">{grp}</div>
                <div class="metric-value" style="background: linear-gradient(135deg, {color}, #ffffff); -webkit-background-clip: text;">{grp_pct:.1f}%</div>
                <div class="metric-sub">{grp_cnt:,} atendimentos</div>
            </div>
            """, unsafe_allow_html=True)
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_chart2, col_table2 = st.columns([3, 2])
    
    with col_chart2:
        st.markdown("#### Evolução Mensal da Proporção de Atendimentos (%)")
        # Agrupamento Mensal
        monthly_age = df_age_grouped.groupby(['year_month', 'age_group']).size().unstack(fill_value=0)
        monthly_age_pct = monthly_age.div(monthly_age.sum(axis=1), axis=0) * 100
        order = ['Crianças (0-14)', 'Jovens (15-29)', 'Adultos (30-59)', 'Idosos (60+)']
        monthly_age_pct = monthly_age_pct.reindex(columns=order).fillna(0)
        
        # Plotly Stacked Bar Chart
        fig_plotly_age = go.Figure()
        x_lbls = [str(p) for p in monthly_age_pct.index]
        
        for idx, grp in enumerate(order):
            fig_plotly_age.add_trace(go.Bar(
                name=grp,
                x=x_lbls,
                y=monthly_age_pct[grp],
                marker_color=COLORS['age_groups'][idx],
                hovertemplate='<b>' + grp + '</b><br>Mês: %{x}<br>Proporção: %{y:.2f}%<extra></extra>'
            ))
            
        fig_plotly_age.update_layout(
            barmode='stack',
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=450,
            margin=dict(l=20, r=20, t=10, b=10),
            yaxis=dict(title='Percentual (%)', ticksuffix='%', gridcolor='rgba(255,255,255,0.08)'),
            xaxis=dict(title='Período', type='category'),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        st.plotly_chart(fig_plotly_age, use_container_width=True)
        
        build_download_button(plot_faixa_etaria_mensal, df_25_26, "2_faixa_etaria_mensal_percentual.png")
        
    with col_table2:
        st.markdown("#### Detalhamento Mensal das Proporções")
        table_df = monthly_age_pct.copy()
        table_df.index = table_df.index.astype(str)
        # Formata com % para exibição
        formatted_df = table_df.apply(lambda col: col.map(lambda x: f"{x:.1f}%"))
        st.dataframe(formatted_df, use_container_width=True, height=400)
        
    # Descritivo
    st.markdown("""
    <div class="desc-box">
        <h4>📝 Análise Descritiva — Comportamento Etário Mensal</h4>
        <p>
            Ao longo de 2025 e do início de 2026, a distribuição dos atendimentos por faixa etária permaneceu notavelmente estável:
            <ul>
                <li><b>Adultos (30 a 59 anos):</b> Representam a maior demanda na unidade de saúde, flutuando entre <b>37.6%</b> e <b>43.8%</b> dos atendimentos mensais (média de 40.6%).</li>
                <li><b>Jovens (15 a 29 anos):</b> Formam o segundo maior bloco, com média de <b>21.9%</b>.</li>
                <li><b>Crianças (0 a 14 anos):</b> Representam cerca de <b>19.3%</b> da demanda, apresentando picos sazonais discretos em meses de inverno (como maio e junho de 2025, atingindo 21.8% e 22.1%), possivelmente associados a campanhas de vacinação ou maior incidência de doenças respiratórias infantis.</li>
                <li><b>Idosos (60+ anos):</b> Representam em média <b>18.2%</b> da demanda. O maior percentual de atendimentos de idosos ocorreu em abril de 2025 (21.95%) e em abril de 2026 (20.2%), mostrando um padrão cíclico de alta demanda no início do outono.</li>
            </ul>
            A consistência desses dados sugere que a unidade Vila Fátima atende a um perfil populacional equilibrado, mas com forte pressão de cuidados crônicos e preventivos voltados à população adulta e idosa, que somam quase 60% da carga de trabalho total.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🔀 Cruzamento Demográfico Profundo (Row-wise e Col-wise)")
    st.write("Esta análise revela como as faixas etárias se distribuem pelas especialidades e como cada público consome os serviços da unidade.")
    
    col_t1, col_t2 = st.columns(2)
    
    # Prepara ordenação de colunas demográficas
    age_cols = ['Crianças (0-14)', 'Jovens (15-29)', 'Adultos (30-59)', 'Idosos (60+)']
    
    # Filtra os válidos e tira o não informado para as tabelas demográficas focadas
    df_demo = df_age_grouped[df_age_grouped['age_group'].isin(age_cols)]
    
    # Tabela 5: Perfil da Especialidade (Linha = 100%)
    with col_t1:
        st.markdown("#### Tabela 5: Perfil da Área (Linha = 100%)")
        st.caption("Lê-se: 'Dos 100% de atendimentos da especialidade X, Y% são Crianças, Z% são Jovens...'")
        
        # Cálculo Total Linha
        df_cross_row = pd.crosstab([df_demo['general_area'], df_demo['professional_area']], df_demo['age_group'], normalize='index') * 100
        df_cross_row = df_cross_row.reindex(columns=age_cols).fillna(0)
        df_cross_row['Total (%)'] = 100.0
        
        # Formatação
        fmt_row = lambda x: f"{x:.1f}%" if isinstance(x, (int, float)) else x
        styled_row = df_cross_row.map(fmt_row) if hasattr(df_cross_row, 'map') else df_cross_row.applymap(fmt_row)
        st.dataframe(styled_row, use_container_width=True, height=450)
        
    # Tabela 6: Dependência Demográfica (Coluna = 100%)
    with col_t2:
        st.markdown("#### Tabela 6: Dependência do Sistema (Coluna = 100%)")
        st.caption("Lê-se: 'De todos os Idosos atendidos na unidade (100%), W% foram consultar na especialidade X...'")
        
        # Cálculo Total Coluna
        df_cross_col = pd.crosstab([df_demo['general_area'], df_demo['professional_area']], df_demo['age_group'], normalize='columns') * 100
        df_cross_col = df_cross_col.reindex(columns=age_cols).fillna(0)
        
        # Formatação
        fmt_col = lambda x: f"{x:.1f}%" if isinstance(x, (int, float)) else x
        styled_col = df_cross_col.map(fmt_col) if hasattr(df_cross_col, 'map') else df_cross_col.applymap(fmt_col)
        st.dataframe(styled_col, use_container_width=True, height=450)

# ------------------------------------------
# TAB 3: VOLUMES E RETORNOS (MÉDIAS DE RETENÇÃO)
# ------------------------------------------
with tab_vol_unicos:
    st.markdown("### 📊 Análise de Taxas de Retorno e Retenção (2025 - 2026)")
    st.write("Esta seção analisa detalhadamente o número de atendimentos e a frequência média de visitas de cada paciente único cruzado por área.")
    
    # KPIs rápidos
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">📈</div>
            <div class="metric-title">Volume Total</div>
            <div class="metric-value">{total_atend_25_26:,}</div>
            <div class="metric-sub">atendimentos em 16 meses</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">👥</div>
            <div class="metric-title">Pacientes Únicos (Total)</div>
            <div class="metric-value">{unicos_25_26:,}</div>
            <div class="metric-sub">pessoas físicas atendidas</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">🔄</div>
            <div class="metric-title">Taxa Média de Retorno</div>
            <div class="metric-value">{media_retorno:.1f}x</div>
            <div class="metric-sub">consultas por paciente único</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Filtro local de área específica para as tabelas abaixo
    st.markdown("#### Filtros Locais da Aba de Retorno")
    opcoes_area_especifica = ["Todas as Áreas Específicas"] + sorted([a for a in df_25_26['professional_area'].unique() if pd.notna(a) and a != "Outros / Não Identificado"])
    filtro_area_especifica = st.multiselect(
        "Isolar Análise de Retorno por Área Profissional Específica:",
        options=opcoes_area_especifica,
        default=["Todas as Áreas Específicas"]
    )
    
    df_ret_filtered = df_25_26.copy()
    if "Todas as Áreas Específicas" not in filtro_area_especifica and len(filtro_area_especifica) > 0:
        df_ret_filtered = df_ret_filtered[df_ret_filtered['professional_area'].isin(filtro_area_especifica)]

    # Cálculo da Tabela 2 (Macro) e Tabela 3 (Micro)
    st.markdown("#### Tabela de Volumes e Retorno (Visão Macro e Micro)")
    col_tret1, col_tret2 = st.columns(2)
    
    with col_tret1:
        st.markdown("**Tabela 2: Taxas por Área Geral**")
        df_ret_macro = df_ret_filtered.groupby('general_area').agg(
            Atendimentos=('parsed_date', 'size'),
            Pacientes_Unicos=('paciente_upper', 'nunique')
        ).reset_index()
        df_ret_macro['Retorno Período'] = (df_ret_macro['Atendimentos'] / df_ret_macro['Pacientes_Unicos']).round(2)
        df_ret_macro['Retorno Mensal'] = (df_ret_macro['Retorno Período'] / 16).round(2) # 16 meses de analise
        st.dataframe(df_ret_macro.sort_values(by='Retorno Período', ascending=False), hide_index=True, use_container_width=True)
        
    with col_tret2:
        st.markdown("**Tabela 3: Taxas por Área Específica**")
        df_ret_micro = df_ret_filtered.groupby(['general_area', 'professional_area']).agg(
            Atendimentos=('parsed_date', 'size'),
            Pacientes_Unicos=('paciente_upper', 'nunique')
        ).reset_index()
        df_ret_micro['Retorno Período'] = (df_ret_micro['Atendimentos'] / df_ret_micro['Pacientes_Unicos']).round(2)
        df_ret_micro['Retorno Mensal'] = (df_ret_micro['Retorno Período'] / 16).round(2)
        st.dataframe(df_ret_micro.sort_values(by='Retorno Período', ascending=False), hide_index=True, use_container_width=True)
        
    st.markdown("#### Gráfico de Dispersão: Retenção vs Volume (Área Específica)")
    fig_scatter = px.scatter(
        df_ret_micro,
        x='Pacientes_Unicos',
        y='Retorno Período',
        size='Atendimentos',
        color='general_area',
        hover_name='professional_area',
        size_max=60,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig_scatter.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis_title="Pacientes Únicos (Alcance)",
        yaxis_title="Taxa de Retorno do Período (Fidelização/Frequência)",
        height=500,
        margin=dict(l=20, r=20, t=10, b=10)
    )
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    st.markdown("#### Tabelas de Retorno Demográfico Cruzado (Macro e Micro)")
    col_tret3, col_tret4 = st.columns(2)
    
    with col_tret3:
        st.markdown("**Tabela 4A: Retorno Demográfico x Área Geral**")
        df_cruz_macro = df_ret_filtered.groupby(['general_area', 'age_group']).agg(
            Atendimentos=('parsed_date', 'size'),
            Unicos=('paciente_upper', 'nunique')
        ).reset_index()
        df_cruz_macro['Retorno'] = (df_cruz_macro['Atendimentos'] / df_cruz_macro['Unicos']).round(2)
        pivot_macro = df_cruz_macro.pivot(index='general_area', columns='age_group', values='Retorno').fillna(0)
        # Filtra apenas colunas que existem (pode faltar 'Crianças' se o df estiver vazio no filtro)
        cols_existentes_macro = [c for c in ['Crianças (0-14)', 'Jovens (15-29)', 'Adultos (30-59)', 'Idosos (60+)'] if c in pivot_macro.columns]
        fmt_macro = lambda x: f"{x:.2f}x" if isinstance(x, (int, float)) else x
        styled_macro = pivot_macro.map(fmt_macro) if hasattr(pivot_macro, 'map') else pivot_macro.applymap(fmt_macro)
        st.dataframe(styled_macro, use_container_width=True)

    with col_tret4:
        st.markdown("**Tabela 4B: Retorno Demográfico x Área Específica**")
        df_cruz_micro = df_ret_filtered.groupby(['professional_area', 'age_group']).agg(
            Atendimentos=('parsed_date', 'size'),
            Unicos=('paciente_upper', 'nunique')
        ).reset_index()
        df_cruz_micro['Retorno'] = (df_cruz_micro['Atendimentos'] / df_cruz_micro['Unicos']).round(2)
        pivot_micro = df_cruz_micro.pivot(index='professional_area', columns='age_group', values='Retorno').fillna(0)
        cols_existentes_micro = [c for c in ['Crianças (0-14)', 'Jovens (15-29)', 'Adultos (30-59)', 'Idosos (60+)'] if c in pivot_micro.columns]
        fmt_micro = lambda x: f"{x:.2f}x" if isinstance(x, (int, float)) else x
        styled_micro = pivot_micro.map(fmt_micro) if hasattr(pivot_micro, 'map') else pivot_micro.applymap(fmt_micro)
        st.dataframe(styled_micro, use_container_width=True)

# ------------------------------------------
# TAB 4: IDOSOS DETALHADO
# ------------------------------------------
with tab_idosos:
    st.markdown("### 👴 Análise Avançada e Demográfica dos Pacientes Idosos")
    st.write("Estudo aprofundado dos pacientes com idade igual ou superior a 60 anos, subdivididos em subfaixas etárias específicas.")
    
    # O banco público contém exclusivamente dados de 2025-2026;
    # a análise de idosos reflete esse mesmo período.
    df_eld_filtered = df_elderly.copy()
    label_periodo_desc = "no biênio 2025-2026"
        
    # Categorização específica para idosos
    def categorize_elderly(age):
        if age <= 70: return '60-70 anos'
        elif age <= 80: return '71-80 anos'
        elif age <= 90: return '81-90 anos'
        else: return '91+ anos'
        
    df_eld = df_eld_filtered.copy()
    df_eld['elderly_group'] = df_eld['age'].apply(categorize_elderly)
    
    total_eld = len(df_eld)
    
    # Percentuais dinâmicos
    pct_60_70 = (df_eld['elderly_group']=='60-70 anos').sum() / total_eld * 100 if total_eld > 0 else 0
    pct_71_80 = (df_eld['elderly_group']=='71-80 anos').sum() / total_eld * 100 if total_eld > 0 else 0
    pct_81_90 = (df_eld['elderly_group']=='81-90 anos').sum() / total_eld * 100 if total_eld > 0 else 0
    pct_91_plus = (df_eld['elderly_group']=='91+ anos').sum() / total_eld * 100 if total_eld > 0 else 0
    
    # KPIs rápidos dos idosos
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card" style="border-color: #AED6F133;">
            <div class="metric-icon">👴</div>
            <div class="metric-title">60 a 70 anos</div>
            <div class="metric-value" style="color: #AED6F1;">{pct_60_70:.1f}%</div>
            <div class="metric-sub">{(df_eld['elderly_group']=='60-70 anos').sum():,} atendimentos</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card" style="border-color: #5DADE233;">
            <div class="metric-icon">🧓</div>
            <div class="metric-title">71 a 80 anos</div>
            <div class="metric-value" style="color: #5DADE2;">{pct_71_80:.1f}%</div>
            <div class="metric-sub">{(df_eld['elderly_group']=='71-80 anos').sum():,} atendimentos</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card" style="border-color: #2E86C133;">
            <div class="metric-icon">👵</div>
            <div class="metric-title">81 a 90 anos</div>
            <div class="metric-value" style="color: #2E86C1;">{pct_81_90:.1f}%</div>
            <div class="metric-sub">{(df_eld['elderly_group']=='81-90 anos').sum():,} atendimentos</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card" style="border-color: #1B4F7233;">
            <div class="metric-icon">🧬</div>
            <div class="metric-title">91 anos ou mais</div>
            <div class="metric-value" style="color: #85C1E9;">{pct_91_plus:.1f}%</div>
            <div class="metric-sub">{(df_eld['elderly_group']=='91+ anos').sum():,} atendimentos</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_chart4_1, col_chart4_2 = st.columns([2, 3])
    
    with col_chart4_1:
        st.markdown("#### Proporção de Subfaixas (Pizza)")
        eld_counts = df_eld['elderly_group'].value_counts()
        order = ['60-70 anos', '71-80 anos', '81-90 anos', '91+ anos']
        eld_counts = eld_counts.reindex(order).fillna(0)
        
        # Donut Plotly
        fig_plotly_donut = go.Figure(data=[go.Pie(
            labels=eld_counts.index,
            values=eld_counts.values,
            hole=.4,
            marker_colors=COLORS['elderly_groups'],
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>Atendimentos: %{value:,}<br>Proporção: %{percent}<extra></extra>'
        )])
        fig_plotly_donut.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=400,
            margin=dict(l=20, r=20, t=10, b=10),
            legend=dict(orientation='h', yanchor='bottom', y=-0.1, xanchor='center', x=0.5)
        )
        st.plotly_chart(fig_plotly_donut, use_container_width=True)
        
        build_download_button(plot_idosos_pizza, df_eld_filtered, "5_distribuicao_idosos_geral.png")
        
    with col_chart4_2:
        st.markdown("#### Evolução Temporal Mensal das Subfaixas (Área Empilhada)")
        monthly_eld = df_eld.groupby(['year_month', 'elderly_group']).size().unstack(fill_value=0)
        order_short = ['60-70 anos', '71-80 anos', '81-90 anos', '91+ anos']
        monthly_eld = monthly_eld.reindex(columns=order_short).fillna(0)
        
        x_lbls_eld = [str(p) for p in monthly_eld.index]
        
        # Plotly Stacked Area Chart
        fig_plotly_area = go.Figure()
        for idx, grp in enumerate(order_short):
            fig_plotly_area.add_trace(go.Scatter(
                name=grp,
                x=x_lbls_eld,
                y=monthly_eld[grp],
                mode='lines',
                stackgroup='one',
                line=dict(width=0.5, color=COLORS['elderly_groups'][idx]),
                fillcolor=COLORS['elderly_groups'][idx],
                hovertemplate='<b>' + grp + '</b><br>Atendimentos: %{y:,}<extra></extra>'
            ))
            
        fig_plotly_area.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=400,
            margin=dict(l=20, r=20, t=10, b=10),
            yaxis=dict(title='Atendimentos', gridcolor='rgba(255,255,255,0.08)'),
            xaxis=dict(title='Período', type='category'),
            legend=dict(orientation='h', yanchor='bottom', y=-0.1, xanchor='center', x=0.5)
        )
        st.plotly_chart(fig_plotly_area, use_container_width=True)
        
        build_download_button(plot_idosos_temporal, df_eld_filtered, "6_evolucao_idosos_temporal.png")
        
    # Tabela detalhada
    st.markdown("#### Dados Mensais por Subfaixa de Idoso")
    monthly_eld_df = monthly_eld.copy()
    monthly_eld_df.index = monthly_eld_df.index.astype(str)
    st.dataframe(monthly_eld_df, use_container_width=True, height=250)
    
    st.markdown(f"""
    <div class="desc-box">
        <h4>📝 Análise Descritiva — Demografia dos Idosos (Biênio 2025-2026)</h4>
        <p>
            O estudo dos atendimentos à população idosa (60 anos ou mais) <b>{label_periodo_desc}</b> revela um retrato demográfico claro do envelhecimento populacional assistido pela unidade Vila Fátima:
            <ul>
                <li><b>Idosos Jovens (60 a 70 anos):</b> Compõem a maioria absoluta, acumulando <b>{pct_60_70:.1f}%</b> de todos os atendimentos a idosos ({(df_eld['elderly_group']=='60-70 anos').sum():,} atendimentos). Este grupo é o mais numeroso e ativo, demandando ações preventivas e acompanhamento de doentes crônicos recém-diagnosticados.</li>
                <li><b>Idosos de Idade Média (71 a 80 anos):</b> Representam <b>{pct_71_80:.1f}%</b> da demanda ({(df_eld['elderly_group']=='71-80 anos').sum():,} atendimentos). Este grupo mostra uma transição importante para maiores taxas de comorbidades e necessidade de consultas médicas e de enfermagem mais frequentes.</li>
                <li><b>Idosos Muito Idosos (81 a 90 anos):</b> Acumulam <b>{pct_81_90:.1f}%</b> ({(df_eld['elderly_group']=='81-90 anos').sum():,} atendimentos), caracterizando um grupo de alta vulnerabilidade, demandando cuidados continuados e frequentemente domiciliares.</li>
                <li><b>Idosos Longevos (91 anos ou mais):</b> Correspondem a <b>{pct_91_plus:.1f}%</b> do total ({(df_eld['elderly_group']=='91+ anos').sum():,} atendimentos). Embora percentualmente pequeno, este é um grupo clinicamente complexo que exige coordenação de cuidado especializada de geriatria e equipes multidisciplinares (eMulti).</li>
            </ul>
            A análise do gráfico temporal mostra o volume mensal por subfaixas, com padrão de demanda consistente ao longo do biênio 2025-2026.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Nova seção de taxa de retorno por subfaixa de idosos
    st.markdown("---")
    st.markdown("### 🔄 Taxa Média de Retorno por Subfaixa de Idosos")
    st.write("Frequência média de atendimentos por paciente único dentro de cada uma das subfaixas etárias dos idosos no período selecionado.")
    
    col_chart_ret_eld, col_desc_ret_eld = st.columns([3, 2])
    
    with col_chart_ret_eld:
        order_eld_ret = ['60-70 anos', '71-80 anos', '81-90 anos', '91+ anos']
        ratios_eld_ret = []
        for grp in order_eld_ret:
            sub = df_eld[df_eld['elderly_group'] == grp]
            ratio = len(sub) / sub['paciente_upper'].nunique() if sub['paciente_upper'].nunique() > 0 else 0
            ratios_eld_ret.append(round(ratio, 2))
            
        fig_plotly_ret_eld = go.Figure()
        fig_plotly_ret_eld.add_trace(go.Bar(
            y=order_eld_ret,
            x=ratios_eld_ret,
            orientation='h',
            marker_color=COLORS['elderly_groups'],
            text=[f'{r:.2f}x' for r in ratios_eld_ret],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Média de Consultas: %{x:.2f}x<extra></extra>'
        ))
        fig_plotly_ret_eld.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=300,
            margin=dict(l=20, r=20, t=10, b=10),
            xaxis=dict(title='Média de Atendimentos por Paciente Único', gridcolor='rgba(255,255,255,0.08)'),
            yaxis=dict(gridcolor='rgba(0,0,0,0)')
        )
        st.plotly_chart(fig_plotly_ret_eld, use_container_width=True)
        
        build_download_button(plot_retorno_faixas_idosos, df_eld_filtered, "8_retorno_faixas_idosos.png")
        
    with col_desc_ret_eld:
        # Gera a descrição com valores dinâmicos calculados a partir dos dados reais
        desc_items = ""
        for grp, ratio in zip(order_eld_ret, ratios_eld_ret):
            desc_items += f"<li><b>{grp}:</b> Média de <b>{ratio:.2f}</b> atendimentos por paciente.</li>\n"
        
        st.markdown(f"""
        <div class="desc-box" style="border-left-color: #AF7AC5; margin-top: 0;">
            <h4>💡 Análise Operacional do Retorno dos Idosos</h4>
            <p>
                Analisando as subfaixas de idosos, observa-se que <b>a frequência média de retorno à unidade cresce com o avanço da idade do paciente</b>:
                <ul>
                    {desc_items}
                </ul>
                Esse gradiente demonstra o impacto direto do envelhecimento avançado na necessidade de assistência de saúde. Idosos longevos (80+) demandam acompanhamento muito mais assíduo das equipes de saúde da família para gerenciamento de múltiplas patologias crônicas.
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Nova Seção de Interseção Profunda
    st.markdown("---")
    st.markdown("### 🧬 Interseção Profunda: Subfaixa de Idosos vs. Especialidade")
    st.write("Para onde cada subfaixa de idade dentro do grupo de idosos migra suas consultas? Qual especialidade é mais dependente dos idosos mais longevos?")
    
    col_t5, col_t6 = st.columns(2)
    
    # Prepara ordenação de colunas
    eld_cols = ['60-70 anos', '71-80 anos', '81-90 anos', '91+ anos']
    df_eld_cross = df_eld[df_eld['elderly_group'].isin(eld_cols)]
    
    with col_t5:
        st.markdown("**Perfil da Área (Total Linha = 100%)**")
        df_eld_row = pd.crosstab([df_eld_cross['general_area'], df_eld_cross['professional_area']], df_eld_cross['elderly_group'], normalize='index') * 100
        df_eld_row = df_eld_row.reindex(columns=eld_cols).fillna(0)
        fmt_eld_row = lambda x: f"{x:.1f}%" if isinstance(x, (int, float)) else x
        styled_eld_row = df_eld_row.map(fmt_eld_row) if hasattr(df_eld_row, 'map') else df_eld_row.applymap(fmt_eld_row)
        st.dataframe(styled_eld_row, use_container_width=True, height=400)
        
    with col_t6:
        st.markdown("**Dependência (Total Coluna = 100%)**")
        df_eld_col = pd.crosstab([df_eld_cross['general_area'], df_eld_cross['professional_area']], df_eld_cross['elderly_group'], normalize='columns') * 100
        df_eld_col = df_eld_col.reindex(columns=eld_cols).fillna(0)
        fmt_eld_col = lambda x: f"{x:.1f}%" if isinstance(x, (int, float)) else x
        styled_eld_col = df_eld_col.map(fmt_eld_col) if hasattr(df_eld_col, 'map') else df_eld_col.applymap(fmt_eld_col)
        st.dataframe(styled_eld_col, use_container_width=True, height=400)
