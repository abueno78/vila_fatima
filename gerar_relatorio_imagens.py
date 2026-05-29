import os
import sqlite3
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Configurações de estilo para os gráficos Matplotlib
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 14,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.titlesize': 16,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'grid.linestyle': '--'
})

# Cores institucionais elegantes
COLORS = {
    'primary': '#00508B',     # Azul Escuro PUCRS
    'secondary': '#009EDB',   # Azul Claro PUCRS
    'accent': '#EBB700',      # Amarelo/Dourado
    'success': '#00DF89',     # Verde
    'danger': '#E74C3C',      # Vermelho
    'neutral_dark': '#2C3E50',
    'neutral_light': '#ECF0F1',
    'age_groups': ['#5DADE2', '#48C9B0', '#F4D03F', '#AF7AC5'], # Cores para Crianças, Jovens, Adultos, Idosos
    'elderly_groups': ['#AED6F1', '#5DADE2', '#2E86C1', '#1B4F72'] # Tons de azul para as faixas de idosos
}

# =====================================================================
# FUNÇÕES DE TRATAMENTO DE DADOS
# =====================================================================

def parse_date(dt_str):
    if not dt_str:
        return None
    match = re.search(r'(\d{2}/\d{2}/\d{4})', dt_str)
    if match:
        try:
            return datetime.strptime(match.group(1), '%d/%m/%Y')
        except:
            return None
    return None

def extract_age(age_str):
    if not isinstance(age_str, str): 
        return None
    match = re.search(r'(\d+)\s*ano', age_str)
    if match:
        return int(match.group(1))
    if 'mes' in age_str or 'dia' in age_str or 'meses' in age_str or 'dias' in age_str:
        return 0
    match_num = re.search(r'(\d+)', age_str)
    if match_num:
        return int(match_num.group(1))
    return None

def load_data(db_path):
    """Carrega e trata os dados necessários a partir do banco de dados SQLite."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Banco de dados não encontrado em {db_path}")
        
    conn = sqlite3.connect(db_path)
    # Carrega colunas relevantes de atendimentos_padronizados
    df = pd.read_sql("""
        SELECT data_hora, nome_completo, idade, profissional_atendimento 
        FROM atendimentos_padronizados
    """, conn)
    try:
        df_classificacao = pd.read_sql("SELECT nome_profissional, area_profissional, area_geral FROM classificacao_profissionais", conn)
    except Exception:
        df_classificacao = pd.DataFrame(columns=['nome_profissional', 'area_profissional', 'area_geral'])
    conn.close()
    
    # Tratamentos básicos
    df['parsed_date'] = df['data_hora'].apply(parse_date)
    df['year'] = df['parsed_date'].dt.year
    df['month'] = df['parsed_date'].dt.month
    df['year_month'] = df['parsed_date'].dt.to_period('M')
    df['age'] = df['idade'].apply(extract_age)
    df['paciente_upper'] = df['nome_completo'].str.upper().str.strip()
    
    # Limpeza profissional
    df['profissional_atendimento'] = df['profissional_atendimento'].apply(
        lambda x: str(x).replace('Responsável:', '').strip() if pd.notna(x) else 'Não Identificado'
    )
    
    # Mapeamento profissional via banco de dados
    mapping_dict_area = {row['nome_profissional'].upper().strip(): row['area_profissional'] for _, row in df_classificacao.iterrows()}
    mapping_dict_geral = {row['nome_profissional'].upper().strip(): row['area_geral'] for _, row in df_classificacao.iterrows()}
    
    def map_prof_area(x):
        for k, v in mapping_dict_area.items():
            if k in x.upper():
                return v
        return "Outros / Não Identificado"

    def map_prof_geral(x):
        for k, v in mapping_dict_geral.items():
            if k in x.upper():
                return v
        return "Outros / Não Identificado"
        
    df['professional_area'] = df['profissional_atendimento'].apply(map_prof_area)
    df['general_area'] = df['profissional_atendimento'].apply(map_prof_geral)
    
    return df

# =====================================================================
# FUNÇÕES DE PLOTAGEM MATPLOTLIB (RETORNAM E SALVAM FIGURA)
# =====================================================================

def plot_profissionais(df_25_26, output_path=None):
    """Gera gráfico do volume de atendimentos por profissional (Top 15)."""
    prof_counts = df_25_26['profissional_atendimento'].value_counts()
    
    # Seleciona os 15 principais e agrupa o restante em "Outros"
    top_15 = prof_counts.head(15).copy()
    others_sum = prof_counts.iloc[15:].sum()
    if others_sum > 0:
        top_15['Outros Profissionais'] = others_sum
        
    top_15 = top_15.sort_values(ascending=True)
    
    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(top_15.index, top_15.values, color=COLORS['secondary'])
    
    # Destaca a barra de "Outros"
    if 'Outros Profissionais' in top_15.index:
        idx = list(top_15.index).index('Outros Profissionais')
        bars[idx].set_color('#BDC3C7')
        
    # Adiciona valores no final das barras
    for bar in bars:
        width = bar.get_width()
        ax.text(width + (width * 0.01), bar.get_y() + bar.get_height()/2, 
                f'{int(width):,}', 
                va='center', ha='left', fontsize=9, color='#2C3E50', fontweight='semibold')
                
    ax.set_title('Top 15 Profissionais por Volume de Atendimentos (2025 - 2026)', pad=20, fontweight='bold')
    ax.set_xlabel('Quantidade de Atendimentos')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.xaxis.grid(True, linestyle='--', alpha=0.5)
    ax.yaxis.grid(False)
    
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
    return fig

def plot_faixa_etaria_mensal(df_25_26, output_path=None):
    """Gera gráfico da evolução percentual mensal por faixa etária."""
    def categorize_age(age):
        if pd.isna(age): return 'Não Informado'
        if age <= 14: return 'Crianças (0-14)'
        elif age <= 29: return 'Jovens (15-29)'
        elif age <= 59: return 'Adultos (30-59)'
        else: return 'Idosos (60+)'

    df = df_25_26.copy()
    df['age_group'] = df['age'].apply(categorize_age)
    
    # Agrupa por mês e faixa etária e calcula porcentagem
    monthly_data = df.groupby(['year_month', 'age_group']).size().unstack(fill_value=0)
    monthly_data_pct = monthly_data.div(monthly_data.sum(axis=1), axis=0) * 100
    
    # Define a ordem das colunas para plotagem empilhada
    order = ['Crianças (0-14)', 'Jovens (15-29)', 'Adultos (30-59)', 'Idosos (60+)']
    monthly_data_pct = monthly_data_pct.reindex(columns=order).fillna(0)
    
    # Formatação dos rótulos do eixo X (ex: Jan/25)
    x_labels = [datetime.strptime(str(p), '%Y-%m').strftime('%b/%y') for p in monthly_data_pct.index]
    
    fig, ax = plt.subplots(figsize=(11, 6))
    
    # Plot de barras empilhadas 100%
    bottom = np.zeros(len(monthly_data_pct))
    for i, col in enumerate(order):
        ax.bar(x_labels, monthly_data_pct[col], bottom=bottom, label=col, color=COLORS['age_groups'][i], width=0.6)
        bottom += monthly_data_pct[col]
        
    ax.set_title('Evolução Proporcional Mensal dos Atendimentos por Faixa Etária (2025 - 2026)', pad=20, fontweight='bold')
    ax.set_ylabel('Percentual dos Atendimentos (%)')
    ax.set_ylim(0, 100)
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', frameon=True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
    return fig

def plot_quantitativo_atendimentos(df_25_26, output_path=None):
    """Gera gráfico do volume absoluto mensal de atendimentos."""
    monthly_counts = df_25_26.groupby('year_month').size()
    x_labels = [datetime.strptime(str(p), '%Y-%m').strftime('%b/%y') for p in monthly_counts.index]
    
    fig, ax = plt.subplots(figsize=(11, 5))
    bars = ax.bar(x_labels, monthly_counts.values, color=COLORS['primary'], width=0.55)
    
    # Adiciona rótulos de valores no topo das barras
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + (yval * 0.01), f'{int(yval):,}', 
                ha='center', va='bottom', fontsize=9, color='#2C3E50', fontweight='semibold')
                
    # Adiciona uma linha de média mensal
    mean_val = monthly_counts.mean()
    ax.axhline(mean_val, color=COLORS['danger'], linestyle='--', linewidth=1.5, 
               label=f'Média Mensal: {int(mean_val):,}')
               
    ax.set_title('Volume Mensal de Atendimentos Realizados (2025 - 2026)', pad=20, fontweight='bold')
    ax.set_ylabel('Número de Atendimentos')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='upper right')
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
    return fig

def plot_pessoas_unicas(df_25_26, output_path=None):
    """Gera gráfico comparativo entre Volume Total de Atendimentos vs Pessoas Únicas por mês."""
    monthly_total = df_25_26.groupby('year_month').size()
    monthly_unique = df_25_26.groupby('year_month')['paciente_upper'].nunique()
    
    x_labels = [datetime.strptime(str(p), '%Y-%m').strftime('%b/%y') for p in monthly_total.index]
    x_indexes = np.arange(len(x_labels))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(11, 5))
    
    bars_total = ax.bar(x_indexes - width/2, monthly_total.values, width, label='Atendimentos Totais', color=COLORS['secondary'])
    bars_unique = ax.bar(x_indexes + width/2, monthly_unique.values, width, label='Pacientes Únicos', color=COLORS['success'])
    
    ax.set_title('Atendimentos Totais vs. Pacientes Únicos por Mês (2025 - 2026)', pad=20, fontweight='bold')
    ax.set_ylabel('Quantidade')
    ax.set_xticks(x_indexes)
    ax.set_xticklabels(x_labels, rotation=45)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend()
    
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
    return fig

def plot_idosos_pizza(df_elderly, output_path=None):
    """Gera gráfico de pizza da distribuição de idosos por subfaixas."""
    def categorize_elderly(age):
        if age <= 70: return '60-70 anos'
        elif age <= 80: return '71-80 anos'
        elif age <= 90: return '81-90 anos'
        else: return '91+ anos'
        
    df = df_elderly.copy()
    df['elderly_group'] = df['age'].apply(categorize_elderly)
    
    counts = df['elderly_group'].value_counts()
    order = ['60-70 anos', '71-80 anos', '81-90 anos', '91+ anos']
    counts = counts.reindex(order).fillna(0)
    
    fig, ax = plt.subplots(figsize=(7, 7))
    wedges, texts, autotexts = ax.pie(
        counts.values, 
        labels=counts.index, 
        autopct='%1.1f%%',
        startangle=140, 
        colors=COLORS['elderly_groups'],
        wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2) # Gráfico Donut
    )
    
    # Melhoria na legibilidade dos textos internos do gráfico
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(10)
        autotext.set_weight('bold')
        
    ax.set_title('Distribuição Geral dos Atendimentos a Idosos (2025-2026)', pad=20, fontweight='bold')
    
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
    return fig

def plot_idosos_temporal(df_elderly, output_path=None):
    """Gera gráfico de área empilhada da evolução dos atendimentos de idosos por subfaixas."""
    def categorize_elderly(age):
        if age <= 70: return '60-70'
        elif age <= 80: return '71-80'
        elif age <= 90: return '81-90'
        else: return '91+'
        
    df = df_elderly.copy()
    df['elderly_group'] = df['age'].apply(categorize_elderly)
    
    monthly_data = df.groupby(['year_month', 'elderly_group']).size().unstack(fill_value=0)
    order = ['60-70', '71-80', '81-90', '91+']
    monthly_data = monthly_data.reindex(columns=order).fillna(0)
    
    # Rótulos para o eixo X
    x_labels = [datetime.strptime(str(p), '%Y-%m').strftime('%Y-%m') for p in monthly_data.index]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Área empilhada
    ax.stackplot(
        x_labels, 
        monthly_data['60-70'], monthly_data['71-80'], monthly_data['81-90'], monthly_data['91+'],
        labels=[f'{g} anos' for g in order],
        colors=COLORS['elderly_groups'],
        alpha=0.85
    )
    
    ax.set_title('Evolução Mensal de Atendimentos a Idosos por Subfaixa Etária (2025-2026)', pad=20, fontweight='bold')
    ax.set_ylabel('Número de Atendimentos')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Configura rótulos do eixo X — no biênio 2025-2026 o número de meses é reduzido
    step = max(1, len(x_labels) // 12)
    ax.set_xticks(range(0, len(x_labels), step))
    ax.set_xticklabels([x_labels[i] for i in range(0, len(x_labels), step)], rotation=45)
    
    ax.legend(loc='upper left', frameon=True)
    
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
    return fig

# =====================================================================
# NOVAS FUNÇÕES PARA TAXA DE RETORNO
# =====================================================================

def plot_retorno_faixas_gerais(df_25_26, output_path=None):
    """Gera gráfico da Taxa Média de Retorno por Faixa Etária Geral (2025-2026)."""
    def categorize_age(age):
        if pd.isna(age): return 'Não Informado'
        if age <= 14: return 'Crianças (0-14)'
        elif age <= 29: return 'Jovens (15-29)'
        elif age <= 59: return 'Adultos (30-59)'
        else: return 'Idosos (60+)'
        
    df = df_25_26.copy()
    df['age_group'] = df['age'].apply(categorize_age)
    
    order = ['Crianças (0-14)', 'Jovens (15-29)', 'Adultos (30-59)', 'Idosos (60+)']
    ratios = []
    
    for grp in order:
        sub = df[df['age_group'] == grp]
        atend = len(sub)
        unicos = sub['paciente_upper'].nunique()
        ratio = atend / unicos if unicos > 0 else 0
        ratios.append(ratio)
        
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(order, ratios, color=COLORS['age_groups'])
    
    # Adiciona valores no final das barras
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 0.1, bar.get_y() + bar.get_height()/2, 
                f'{width:.2f}x', 
                va='center', ha='left', fontsize=10, color='#2C3E50', fontweight='semibold')
                
    ax.set_title('Taxa Média de Retorno por Faixa Etária Geral (2025 - 2026)', pad=20, fontweight='bold')
    ax.set_xlabel('Média de Atendimentos por Paciente Único')
    ax.set_xlim(0, max(ratios) + 2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.xaxis.grid(True, linestyle='--', alpha=0.5)
    ax.yaxis.grid(False)
    
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
    return fig

def plot_retorno_faixas_idosos(df_elderly, output_path=None):
    """Gera gráfico da Taxa Média de Retorno por Subfaixa de Idosos."""
    def categorize_elderly(age):
        if age <= 70: return '60-70 anos'
        elif age <= 80: return '71-80 anos'
        elif age <= 90: return '81-90 anos'
        else: return '91+ anos'
        
    df = df_elderly.copy()
    df['elderly_group'] = df['age'].apply(categorize_elderly)
    
    order = ['60-70 anos', '71-80 anos', '81-90 anos', '91+ anos']
    ratios = []
    
    for grp in order:
        sub = df[df['elderly_group'] == grp]
        atend = len(sub)
        unicos = sub['paciente_upper'].nunique()
        ratio = atend / unicos if unicos > 0 else 0
        ratios.append(ratio)
        
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(order, ratios, color=COLORS['elderly_groups'])
    
    # Adiciona valores no final das barras
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 0.1, bar.get_y() + bar.get_height()/2, 
                f'{width:.2f}x', 
                va='center', ha='left', fontsize=10, color='#2C3E50', fontweight='semibold')
                
    ax.set_title('Taxa Média de Retorno por Subfaixa de Pacientes Idosos', pad=20, fontweight='bold')
    ax.set_xlabel('Média de Atendimentos por Paciente Único')
    ax.set_xlim(0, max(ratios) + 2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.xaxis.grid(True, linestyle='--', alpha=0.5)
    ax.yaxis.grid(False)
    
    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
    return fig

# =====================================================================
# FUNÇÃO PRINCIPAL DE EXPORTAÇÃO
# =====================================================================

def main():
    db_path = 'coleta_esus.db'
    output_dir = 'graficos_analise'
    
    print("Carregando e preparando dados do banco de dados...")
    try:
        df = load_data(db_path)
    except Exception as e:
        print(f"Erro ao carregar dados: {e}")
        return
        
    # Garante que a pasta de saída exista
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Diretório '{output_dir}' criado com sucesso.")
        
    df_25_26 = df[df['year'].isin([2025, 2026])].copy()
    df_elderly = df[(df['age'] >= 60) & df['year'].isin([2025, 2026])].copy()
    
    print(f"Total registros carregados: {len(df)}")
    print(f"Registros 2025-2026: {len(df_25_26)}")
    print(f"Registros Idosos (2025-2026): {len(df_elderly)}")
    
    # 1. Profissionais
    print("Gerando gráfico: 1_agrupamento_profissionais.png...")
    plot_profissionais(df_25_26, os.path.join(output_dir, '1_agrupamento_profissionais.png'))
    
    # 2. Faixa Etária
    print("Gerando gráfico: 2_faixa_etaria_mensal_percentual.png...")
    plot_faixa_etaria_mensal(df_25_26, os.path.join(output_dir, '2_faixa_etaria_mensal_percentual.png'))
    
    # 3. Quantitativo
    print("Gerando gráfico: 3_quantitativo_atendimentos.png...")
    plot_quantitativo_atendimentos(df_25_26, os.path.join(output_dir, '3_quantitativo_atendimentos.png'))
    
    # 4. Pessoas Únicas
    print("Gerando gráfico: 4_pessoas_unicas_atendidas.png...")
    plot_pessoas_unicas(df_25_26, os.path.join(output_dir, '4_pessoas_unicas_atendidas.png'))
    
    # 5. Idosos Pizza
    print("Gerando gráfico: 5_distribuicao_idosos_geral.png...")
    plot_idosos_pizza(df_elderly, os.path.join(output_dir, '5_distribuicao_idosos_geral.png'))
    
    # 6. Idosos Temporal
    print("Gerando gráfico: 6_evolucao_idosos_temporal.png...")
    plot_idosos_temporal(df_elderly, os.path.join(output_dir, '6_evolucao_idosos_temporal.png'))
    
    # 7. Retorno Faixas Gerais
    print("Gerando gráfico: 7_retorno_faixas_gerais.png...")
    plot_retorno_faixas_gerais(df_25_26, os.path.join(output_dir, '7_retorno_faixas_gerais.png'))
    
    # 8. Retorno Faixas Idosos
    print("Gerando gráfico: 8_retorno_faixas_idosos.png...")
    plot_retorno_faixas_idosos(df_elderly, os.path.join(output_dir, '8_retorno_faixas_idosos.png'))
    
    print("\n[SUCESSO] Todos os gráficos foram salvos na pasta 'graficos_analise/'.")

if __name__ == "__main__":
    main()
