import os
import sqlite3
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import sys

# Bibliotecas do ReportLab para geração de PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# =====================================================================
# 1. FUNÇÕES DE TRATAMENTO E CARGA DE DADOS
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

def load_and_preprocess_data(db_path):
    """Carrega dados e realiza o pré-processamento."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Banco de dados não encontrado em {db_path}")
        
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("""
        SELECT data_hora, nome_completo, idade, profissional_atendimento 
        FROM atendimentos_padronizados
    """, conn)
    df_classificacao = pd.read_sql("SELECT nome_profissional, area_profissional, area_geral FROM classificacao_profissionais", conn)
    conn.close()
    
    # Limpeza e parsing de data
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
# 3. NUMERADOR DINÂMICO DE PÁGINAS (CANVAS CUSTOMIZADO)
# =====================================================================

class NumberedCanvas(canvas.Canvas):
    """Canvas de dois passos para calcular o total de páginas e desenhar cabeçalhos/rodapés."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        # Ignora cabeçalhos e rodapés na página de capa (Página 1)
        if self._pageNumber == 1:
            return
            
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#00508B")) # Azul PUCRS
        
        # Cabeçalho
        self.drawString(54, 802, "UNIDADE DE SAÚDE VILA FÁTIMA")
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#555555"))
        self.drawRightString(541, 802, "Relatório Analítico de Atendimentos (2025 - 2026)")
        
        # Linha do cabeçalho
        self.setStrokeColor(colors.HexColor("#009EDB")) # Azul Claro
        self.setLineWidth(0.75)
        self.line(54, 794, 541, 794)
        
        # Rodapé
        self.setStrokeColor(colors.HexColor("#E0E0E0"))
        self.setLineWidth(0.5)
        self.line(54, 50, 541, 50)
        
        page_text = f"Página {self._pageNumber} de {page_count}"
        self.setFont("Helvetica", 8)
        self.drawString(54, 38, "PUCRS / SMS Porto Alegre — Análise Científica de Atendimentos")
        self.drawRightString(541, 38, page_text)
        self.restoreState()

# =====================================================================
# 4. EXECUÇÃO DOS CÁLCULOS E GERAÇÃO DE GRÁFICOS
# =====================================================================

def main():
    print("Iniciando geração do relatório...")
    db_path = 'coleta_esus.db'
    df = load_and_preprocess_data(db_path)
    
    # Filtro estrito de período 2025-2026
    df_25_26 = df[df['year'].isin([2025, 2026])].copy()
    

    # Faixa etária
    def categorize_age(age):
        if pd.isna(age): return 'Não Informado'
        if age <= 14: return 'Crianças (0-14)'
        elif age <= 29: return 'Jovens (15-29)'
        elif age <= 59: return 'Adultos (30-59)'
        else: return 'Idosos (60+)'
        
    df_25_26['age_group'] = df_25_26['age'].apply(categorize_age)
    
    # Subfaixas idosos
    def categorize_elderly(age):
        if pd.isna(age) or age < 60: return None
        if age <= 70: return '60-70 anos'
        elif age <= 80: return '71-80 anos'
        elif age <= 90: return '81-90 anos'
        else: return '91+ anos'
        
    df_25_26['elderly_group'] = df_25_26['age'].apply(categorize_elderly)
    
    # Criar pasta temporária para imagens
    temp_dir = 'temp_pdf_charts'
    os.makedirs(temp_dir, exist_ok=True)
    
    # Configurações globais de estilo Matplotlib para os gráficos do PDF (fundo branco, elegante)
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.size': 9,
        'axes.labelsize': 10,
        'axes.titlesize': 11,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'figure.titlesize': 13,
        'axes.grid': True,
        'grid.alpha': 0.2,
        'grid.linestyle': '--',
        'figure.facecolor': '#ffffff',
        'axes.facecolor': '#ffffff'
    })
    
    # Paleta de Cores
    pucrs_blue = '#00508B'
    pucrs_light = '#009EDB'
    accent_color = '#EBB700'
    colors_faixas = ['#5DADE2', '#48C9B0', '#F4D03F', '#AF7AC5']
    colors_subid = ['#AED6F1', '#5DADE2', '#2E86C1', '#1B4F72']
    
    # -------------------------------------------------------------
    # GRÁFICO 1: Volume Geral de Atendimentos por Área Profissional
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(6, 2.5))
    area_counts = df_25_26['general_area'].value_counts().sort_values(ascending=True)
    bars = ax.barh(area_counts.index, area_counts.values, color=pucrs_light)
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 100, bar.get_y() + bar.get_height()/2, f'{int(width):,}', 
                va='center', ha='left', fontsize=8, color='#333333', fontweight='semibold')
    ax.set_title('Volume Geral de Atendimentos por Área Profissional (2025-2026)', pad=10, fontweight='bold', color=pucrs_blue)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    chart1_path = os.path.join(temp_dir, 'chart1.png')
    plt.savefig(chart1_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    # -------------------------------------------------------------
    # GRÁFICO 2: Taxa de Retorno Geral no Período por Faixa Etária Geral
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(5, 2.5))
    retorno_per_faixa = {}
    for g in ['Crianças (0-14)', 'Jovens (15-29)', 'Adultos (30-59)', 'Idosos (60+)']:
        sub = df_25_26[df_25_26['age_group'] == g]
        retorno_per_faixa[g] = len(sub) / sub['paciente_upper'].nunique() if sub['paciente_upper'].nunique() > 0 else 0
    
    bars = ax.bar(retorno_per_faixa.keys(), retorno_per_faixa.values(), color=colors_faixas, width=0.5)
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height + 0.3, f'{height:.2f}x', 
                va='bottom', ha='center', fontsize=9, color='#333333', fontweight='bold')
    ax.set_title('Taxa Média de Retorno no Período (2025-2026) por Faixa Etária', pad=10, fontweight='bold', color=pucrs_blue)
    ax.set_ylabel('Consultas por Paciente Único')
    ax.set_ylim(0, 17)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    chart2_path = os.path.join(temp_dir, 'chart2.png')
    plt.savefig(chart2_path, dpi=300, bbox_inches='tight')
    plt.close()

    # -------------------------------------------------------------
    # GRÁFICO 3: Comparativo de Taxas de Retorno (Período vs Mensal Média)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(6, 2.5))
    x = np.arange(4)
    width = 0.35
    
    r_periodo = []
    r_mensal = []
    faixas = ['Crianças (0-14)', 'Jovens (15-29)', 'Adultos (30-59)', 'Idosos (60+)']
    
    for g in faixas:
        sub = df_25_26[df_25_26['age_group'] == g]
        r_periodo.append(len(sub) / sub['paciente_upper'].nunique() if sub['paciente_upper'].nunique() > 0 else 0)
        
        m_counts = sub.groupby('year_month').size()
        m_uniq = sub.groupby('year_month')['paciente_upper'].nunique()
        r_mensal.append((m_counts / m_uniq).mean())
        
    rects1 = ax.bar(x - width/2, r_periodo, width, label='No Período (16m)', color=pucrs_blue)
    rects2 = ax.bar(x + width/2, r_mensal, width, label='Mensal Média', color=pucrs_light)
    
    for rect in rects1:
        h = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()/2, h + 0.3, f'{h:.1f}x', va='bottom', ha='center', fontsize=8, color=pucrs_blue, fontweight='bold')
    for rect in rects2:
        h = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()/2, h + 0.3, f'{h:.1f}x', va='bottom', ha='center', fontsize=8, color=pucrs_light, fontweight='bold')
        
    ax.set_xticks(x)
    ax.set_xticklabels(['Crianças', 'Jovens', 'Adultos', 'Idosos'])
    ax.set_title('Retorno Longitudinal (Período) vs. Retorno Frequente (Mensal Média)', pad=10, fontweight='bold', color=pucrs_blue)
    ax.set_ylabel('Consultas / Paciente Único')
    ax.set_ylim(0, 17)
    ax.legend(frameon=True, facecolor='#ffffff')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    chart3_path = os.path.join(temp_dir, 'chart3.png')
    plt.savefig(chart3_path, dpi=300, bbox_inches='tight')
    plt.close()

    # -------------------------------------------------------------
    # GRÁFICO 4: Proporção de Atendimentos Clínicos por Faixa Etária
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(6, 2.5))
    ct_pct = pd.crosstab(df_25_26['general_area'], df_25_26['age_group'], normalize='columns') * 100
    # Reordenar colunas
    ct_pct = ct_pct[['Crianças (0-14)', 'Jovens (15-29)', 'Adultos (30-59)', 'Idosos (60+)']]
    
    bottoms = np.zeros(4)
    areas_ordered = ct_pct.sum(axis=1).sort_values(ascending=False).index
    
    for i, area in enumerate(areas_ordered):
        vals = ct_pct.loc[area].values
        ax.bar(ct_pct.columns, vals, bottom=bottoms, label=area, alpha=0.85)
        bottoms += vals
        

    ax.set_title('Estratificação de Consultas por Área e Faixa Etária', pad=10, fontweight='bold', color=pucrs_blue)
    ax.set_ylabel('Proporção de Atendimentos (%)')
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', frameon=True, fontsize=7)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    chart4_path = os.path.join(temp_dir, 'chart4.png')
    plt.savefig(chart4_path, dpi=300, bbox_inches='tight')
    plt.close()

    # -------------------------------------------------------------
    # GRÁFICO 5: Distribuição da População Idosa por Subfaixa Etária
    # -------------------------------------------------------------
    df_eld_all = df_25_26[df_25_26['elderly_group'].notna()]
    sub_counts = df_eld_all['elderly_group'].value_counts().reindex(['60-70 anos', '71-80 anos', '81-90 anos', '91+ anos'])
    
    fig, ax = plt.subplots(figsize=(4.5, 2.5))
    wedges, texts, autotexts = ax.pie(
        sub_counts.values, 
        labels=sub_counts.index, 
        autopct='%1.1f%%', 
        colors=colors_subid, 
        startangle=90, 
        pctdistance=0.75,
        textprops=dict(color="#333333", fontsize=8),
        wedgeprops=dict(width=0.4, edgecolor='white') # Donut Chart
    )
    plt.setp(autotexts, size=8, weight="bold")
    ax.set_title('Distribuição de Consultas de Idosos por Subfaixa', pad=10, fontweight='bold', color=pucrs_blue)
    plt.tight_layout()
    chart5_path = os.path.join(temp_dir, 'chart5.png')
    plt.savefig(chart5_path, dpi=300, bbox_inches='tight')
    plt.close()

    # -------------------------------------------------------------
    # GRÁFICO 6: Comparativo de Retorno no Período por Subfaixa de Idosos
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(5, 2.5))
    r_subidos = {}
    for g in ['60-70 anos', '71-80 anos', '81-90 anos', '91+ anos']:
        sub = df_25_26[df_25_26['elderly_group'] == g]
        r_subidos[g] = len(sub) / sub['paciente_upper'].nunique() if sub['paciente_upper'].nunique() > 0 else 0
        
    bars = ax.bar(r_subidos.keys(), r_subidos.values(), color=colors_subid, width=0.45)
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.3, f'{h:.2f}x', 
                va='bottom', ha='center', fontsize=9, color='#333333', fontweight='bold')
    ax.set_title('Taxa Média de Retorno no Período por Subfaixa de Idosos', pad=10, fontweight='bold', color=pucrs_blue)
    ax.set_ylabel('Consultas por Paciente Único')
    ax.set_ylim(0, 20)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    chart6_path = os.path.join(temp_dir, 'chart6.png')
    plt.savefig(chart6_path, dpi=300, bbox_inches='tight')
    plt.close()

    # -------------------------------------------------------------
    # GRÁFICO 7: Média de Retorno (Período) por Área Profissional para Pacientes Idosos (60+)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(6, 2.5))
    df_eld_only = df_25_26[df_25_26['age_group'] == 'Idosos (60+)']
    
    area_retornos = {}
    for area in df_eld_only['professional_area'].unique():
        sub = df_eld_only[df_eld_only['professional_area'] == area]
        ratio = len(sub) / sub['paciente_upper'].nunique() if sub['paciente_upper'].nunique() > 0 else 0
        area_retornos[area] = ratio
        
    area_ret_s = pd.Series(area_retornos).sort_values(ascending=True)
    bars = ax.barh(area_ret_s.index, area_ret_s.values, color=colors_faixas[3]) # lilás para idosos
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 0.1, bar.get_y() + bar.get_height()/2, f'{width:.2f}x', 
                va='center', ha='left', fontsize=8, color='#333333', fontweight='semibold')
    ax.set_title('Taxa de Retorno por Área Profissional nos Pacientes Idosos', pad=10, fontweight='bold', color=pucrs_blue)
    ax.set_xlabel('Consultas por Paciente Único')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    chart7_path = os.path.join(temp_dir, 'chart7.png')
    plt.savefig(chart7_path, dpi=300, bbox_inches='tight')
    plt.close()

    # -------------------------------------------------------------
    # GRÁFICO 8: Evolução Temporal Mensal de Atendimentos de Idosos por Área
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(6.5, 2.5))
    df_eld_only = df_25_26[df_25_26['age_group'] == 'Idosos (60+)']
    monthly_trend = df_eld_only.groupby(['year_month', 'professional_area']).size().unstack(fill_value=0)
    # Selecionar as 3 principais áreas
    top_areas = monthly_trend.sum().sort_values(ascending=False).head(3).index.tolist()
    for area in top_areas:
        if area in monthly_trend.columns:
            trend = monthly_trend[area]
            ax.plot(trend.index.astype(str), trend.values, marker='o', label=area, linewidth=2)
            
    ax.set_title('Evolução Mensal de Atendimentos de Idosos por Área (2025-2026)', pad=10, fontweight='bold', color=pucrs_blue)
    ax.set_ylabel('Quantidade de Consultas')
    plt.xticks(rotation=45, ha='right')
    ax.legend(frameon=True, facecolor='#ffffff')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    chart8_path = os.path.join(temp_dir, 'chart8.png')
    plt.savefig(chart8_path, dpi=300, bbox_inches='tight')
    plt.close()

    print("Imagens temporárias de gráficos salvas.")

    # =====================================================================
    # 5. ESTRUTURAÇÃO DO PDF COM REPORTLAB
    # =====================================================================
    
    pdf_filename = 'Relatorio_Atendimentos_Vila_Fatima_2025_2026.pdf'
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=A4,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Customização de Estilos de Texto
    primary_color = colors.HexColor("#00508B")
    secondary_color = colors.HexColor("#009EDB")
    dark_text = colors.HexColor("#1A1A1A")
    gray_text = colors.HexColor("#555555")
    
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color,
        alignment=1, # Centralizado
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=secondary_color,
        alignment=1,
        spaceAfter=50
    )
    
    h1_style = ParagraphStyle(
        'Header1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=primary_color,
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'Header2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=secondary_color,
        spaceBefore=12,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=dark_text,
        spaceAfter=8
    )
    
    bullet_style = ParagraphStyle(
        'BulletDark',
        parent=styles['Bullet'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=dark_text,
        spaceAfter=4,
        leftIndent=15
    )
    
    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=10,
        leading=14,
        textColor=primary_color,
        alignment=1
    )
    
    table_text_style = ParagraphStyle(
        'TableText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=dark_text
    )
    
    table_header_style = ParagraphStyle(
        'TableHeaderText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )
    
    story = []
    
    # -------------------------------------------------------------
    # PÁGINA 1: CAPA
    # -------------------------------------------------------------
    story.append(Spacer(1, 100))
    
    # Logo da PUCRS (Se existir)
    logo_path = 'logo_pucrs.png'
    if os.path.exists(logo_path):
        story.append(Image(logo_path, width=2.5*inch, height=0.75*inch))
        story.append(Spacer(1, 30))
        
    story.append(Paragraph("UNIDADE DE SAÚDE VILA FÁTIMA", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Relatório Científico de Atendimentos,<br/>Estratificação Demográfica e Taxa de Retorno", title_style))
    story.append(Paragraph("Análise Consolidada dos Anos 2025 e 2026 (Período de 16 meses)", subtitle_style))
    
    # Linha decorativa na capa
    d_table = Table([[""]], colWidths=[487], rowHeights=[4])
    d_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), primary_color),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(d_table)
    story.append(Spacer(1, 150))
    
    # Metadados de rodapé da capa
    metadata_text = f"""
    <b>Parceria:</b> PUCRS - Pontifícia Universidade Católica do Rio Grande do Sul<br/>
    <b>Instituição Assistencial:</b> Secretaria Municipal de Saúde (SMS) de Porto Alegre<br/>
    <b>Data de Emissão:</b> {datetime.now().strftime('%d/%m/%Y')}<br/>
    <b>Período Analisado:</b> Janeiro de 2025 a Abril de 2026
    """
    story.append(Paragraph(metadata_text, ParagraphStyle('CapInfo', parent=body_style, fontSize=9, textColor=gray_text, alignment=1)))
    story.append(PageBreak())
    
    # -------------------------------------------------------------

    # PÁGINA 2: INTRODUÇÃO E DISTRIBUIÇÃO
    # -------------------------------------------------------------
    story.append(Paragraph("1. Introdução e Visão Geral Assistencial", h1_style))
    intro_p1 = """
    Este relatório apresenta a análise quantitativa e epidemiológica dos atendimentos realizados na 
    <b>Unidade de Saúde Vila Fátima</b> durante o ciclo operacional de 2025 e início de 2026. A análise visa 
    compreender os padrões demográficos de assistência, a distribuição macro e micro das consultas e a recorrência 
    de visitas por paciente único (Taxa de Retorno). 
    """
    story.append(Paragraph(intro_p1, body_style))
    
    total_atends = len(df_25_26)
    unicos_total = df_25_26['paciente_upper'].nunique()
    retorno_geral_periodo = total_atends / unicos_total if unicos_total > 0 else 0
    
    kpi_data = [
        [Paragraph("<b>Indicador Operacional</b>", table_header_style), Paragraph("<b>Resultado Encontrado</b>", table_header_style)],
        [Paragraph("Volume Total de Atendimentos", table_text_style), Paragraph(f"<b>{total_atends:,}</b> consultas", table_text_style)],
        [Paragraph("Pacientes Únicos Atendidos", table_text_style), Paragraph(f"<b>{unicos_total:,}</b> pessoas físicas", table_text_style)],
        [Paragraph("Taxa Média de Retorno", table_text_style), Paragraph(f"<b>{retorno_geral_periodo:.2f}x</b> consultas/paciente", table_text_style)],
    ]
    
    kpi_table = Table(kpi_data, colWidths=[240, 247])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D3D3D3")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F9F9F9")]),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Tabela 1A: Distribuição Macro (Área Geral)", h2_style))
    df_macro = df_25_26['general_area'].value_counts().reset_index()
    t1a_data = [[Paragraph("<b>Área Geral</b>", table_header_style), Paragraph("<b>Atendimentos</b>", table_header_style), Paragraph("<b>Percentual</b>", table_header_style)]]
    for _, row in df_macro.iterrows():
        pct = (row['count'] / total_atends * 100)
        t1a_data.append([Paragraph(row['general_area'], table_text_style), Paragraph(f"{row['count']:,}", table_text_style), Paragraph(f"{pct:.1f}%", table_text_style)])
        
    t1a_tbl = Table(t1a_data, colWidths=[200, 100, 100])
    t1a_tbl.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), primary_color), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D3D3D3")), ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F9F9F9")])]))
    story.append(t1a_tbl)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Tabela 1B: Distribuição Micro (Área Profissional)", h2_style))
    df_micro = df_25_26.groupby(['general_area', 'professional_area']).size().reset_index(name='Atendimentos').sort_values(by=['general_area', 'Atendimentos'], ascending=[True, False])
    t1b_data = [[Paragraph("<b>Área Geral</b>", table_header_style), Paragraph("<b>Área Profissional</b>", table_header_style), Paragraph("<b>Volume</b>", table_header_style)]]
    for _, row in df_micro.iterrows():
        t1b_data.append([Paragraph(row['general_area'], table_text_style), Paragraph(row['professional_area'], table_text_style), Paragraph(f"{row['Atendimentos']:,}", table_text_style)])
        
    t1b_tbl = Table(t1b_data, colWidths=[150, 150, 80])
    t1b_tbl.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), primary_color), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D3D3D3")), ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F9F9F9")])]))
    story.append(t1b_tbl)
    
    story.append(PageBreak())
    
    # -------------------------------------------------------------
    # PÁGINA 3: TAXA DE RETORNO E ESTRATIFICAÇÃO
    # -------------------------------------------------------------
    story.append(Paragraph("2. Taxas de Retorno Consolidadas (Período e Mensal)", h1_style))
    
    story.append(Paragraph("Tabela 2: Taxas de Retorno por Área Geral", h2_style))
    df_ret_macro = df_25_26.groupby('general_area').agg(Atendimentos=('parsed_date', 'size'), Pacientes_Unicos=('paciente_upper', 'nunique')).reset_index()
    t2_data = [[Paragraph("<b>Área Geral</b>", table_header_style), Paragraph("<b>Retorno Período</b>", table_header_style), Paragraph("<b>Retorno Mensal</b>", table_header_style)]]
    for _, row in df_ret_macro.iterrows():
        rp = row['Atendimentos'] / row['Pacientes_Unicos'] if row['Pacientes_Unicos'] > 0 else 0
        rm = rp / 16
        t2_data.append([Paragraph(row['general_area'], table_text_style), Paragraph(f"{rp:.2f}x", table_text_style), Paragraph(f"{rm:.2f}x", table_text_style)])
    
    t2_tbl = Table(t2_data, colWidths=[200, 100, 100])
    t2_tbl.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), primary_color), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D3D3D3")), ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F9F9F9")])]))
    story.append(t2_tbl)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Tabela 4A: Retorno Demográfico Cruzado por Área Geral", h2_style))
    # Para manter no A4, faremos uma tabela achatada
    t4a_data = [[Paragraph("<b>Área Geral</b>", table_header_style), Paragraph("<b>Crianças</b>", table_header_style), Paragraph("<b>Jovens</b>", table_header_style), Paragraph("<b>Adultos</b>", table_header_style), Paragraph("<b>Idosos</b>", table_header_style)]]
    df_cruz_macro = df_25_26.groupby(['general_area', 'age_group']).agg(A=('parsed_date', 'size'), U=('paciente_upper', 'nunique')).reset_index()
    df_cruz_macro['R'] = (df_cruz_macro['A'] / df_cruz_macro['U']).round(2)
    pv_m = df_cruz_macro.pivot(index='general_area', columns='age_group', values='R').fillna(0)
    for g_area in pv_m.index:
        cr = f"{pv_m.loc[g_area].get('Crianças (0-14)', 0):.2f}x"
        jv = f"{pv_m.loc[g_area].get('Jovens (15-29)', 0):.2f}x"
        ad = f"{pv_m.loc[g_area].get('Adultos (30-59)', 0):.2f}x"
        id = f"{pv_m.loc[g_area].get('Idosos (60+)', 0):.2f}x"
        t4a_data.append([Paragraph(g_area, table_text_style), Paragraph(cr, table_text_style), Paragraph(jv, table_text_style), Paragraph(ad, table_text_style), Paragraph(id, table_text_style)])

    t4a_tbl = Table(t4a_data, colWidths=[140, 80, 80, 80, 80])
    t4a_tbl.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), primary_color), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D3D3D3")), ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F9F9F9")])]))
    story.append(t4a_tbl)
    
    story.append(PageBreak())
    
    # -------------------------------------------------------------
    # PÁGINA 4: DEMOGRAFIA CRUZADA (100% Linha e Coluna)
    # -------------------------------------------------------------
    story.append(Paragraph("3. Demografia Cruzada (Tabelas 5 e 6)", h1_style))
    story.append(Paragraph("Tabela 5: Perfil da Especialidade (Soma na Linha = 100%)", h2_style))
    
    age_cols = ['Crianças (0-14)', 'Jovens (15-29)', 'Adultos (30-59)', 'Idosos (60+)']
    df_demo = df_25_26[df_25_26['age_group'].isin(age_cols)]
    
    df_cross_row = pd.crosstab([df_demo['general_area'], df_demo['professional_area']], df_demo['age_group'], normalize='index') * 100
    t5_data = [[Paragraph("<b>Área Profissional</b>", table_header_style), Paragraph("<b>Crianças</b>", table_header_style), Paragraph("<b>Jovens</b>", table_header_style), Paragraph("<b>Adultos</b>", table_header_style), Paragraph("<b>Idosos</b>", table_header_style)]]
    for idx, row in df_cross_row.iterrows():
        t5_data.append([Paragraph(idx[1], table_text_style), Paragraph(f"{row.get('Crianças (0-14)',0):.1f}%", table_text_style), Paragraph(f"{row.get('Jovens (15-29)',0):.1f}%", table_text_style), Paragraph(f"{row.get('Adultos (30-59)',0):.1f}%", table_text_style), Paragraph(f"{row.get('Idosos (60+)',0):.1f}%", table_text_style)])
        
    t5_tbl = Table(t5_data, colWidths=[140, 80, 80, 80, 80])
    t5_tbl.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), primary_color), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D3D3D3")), ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F9F9F9")])]))
    story.append(t5_tbl)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Tabela 6: Dependência do Sistema (Soma na Coluna = 100%)", h2_style))
    df_cross_col = pd.crosstab([df_demo['general_area'], df_demo['professional_area']], df_demo['age_group'], normalize='columns') * 100
    t6_data = [[Paragraph("<b>Área Profissional</b>", table_header_style), Paragraph("<b>Crianças</b>", table_header_style), Paragraph("<b>Jovens</b>", table_header_style), Paragraph("<b>Adultos</b>", table_header_style), Paragraph("<b>Idosos</b>", table_header_style)]]
    for idx, row in df_cross_col.iterrows():
        t6_data.append([Paragraph(idx[1], table_text_style), Paragraph(f"{row.get('Crianças (0-14)',0):.1f}%", table_text_style), Paragraph(f"{row.get('Jovens (15-29)',0):.1f}%", table_text_style), Paragraph(f"{row.get('Adultos (30-59)',0):.1f}%", table_text_style), Paragraph(f"{row.get('Idosos (60+)',0):.1f}%", table_text_style)])
        
    t6_tbl = Table(t6_data, colWidths=[140, 80, 80, 80, 80])
    t6_tbl.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), primary_color), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D3D3D3")), ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F9F9F9")])]))
    story.append(t6_tbl)
    
    story.append(PageBreak())
    
    # -------------------------------------------------------------
    # PÁGINA 5: DETALHAMENTO IDOSOS
    # -------------------------------------------------------------
    story.append(Paragraph("4. Análise Avançada dos Idosos (60+)", h1_style))
    eld_cols = ['60-70 anos', '71-80 anos', '81-90 anos', '91+ anos']
    df_eld_cross = df_eld_all[df_eld_all['elderly_group'].isin(eld_cols)]
    
    story.append(Paragraph("Interseção Profunda: Perfil das Áreas de Atendimento para Idosos (100% Linha)", h2_style))
    df_eld_row = pd.crosstab(df_eld_cross['professional_area'], df_eld_cross['elderly_group'], normalize='index') * 100
    te_data = [[Paragraph("<b>Área Profissional</b>", table_header_style), Paragraph("<b>60-70 anos</b>", table_header_style), Paragraph("<b>71-80 anos</b>", table_header_style), Paragraph("<b>81-90 anos</b>", table_header_style), Paragraph("<b>91+ anos</b>", table_header_style)]]
    for area, row in df_eld_row.iterrows():
        te_data.append([Paragraph(area, table_text_style), Paragraph(f"{row.get('60-70 anos',0):.1f}%", table_text_style), Paragraph(f"{row.get('71-80 anos',0):.1f}%", table_text_style), Paragraph(f"{row.get('81-90 anos',0):.1f}%", table_text_style), Paragraph(f"{row.get('91+ anos',0):.1f}%", table_text_style)])
        
    te_tbl = Table(te_data, colWidths=[140, 80, 80, 80, 80])
    te_tbl.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), primary_color), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D3D3D3")), ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F9F9F9")])]))
    story.append(te_tbl)
    
    story.append(Spacer(1, 30))
    sign_data = [
        [Paragraph("________________________________________<br/><b>Núcleo de Ciência de Dados em Saúde</b><br/>PUCRS / US Vila Fátima", ParagraphStyle('Sign1', parent=body_style, alignment=1)),
         Paragraph("________________________________________<br/><b>Coordenação de Atenção Primária</b><br/>SMS Porto Alegre", ParagraphStyle('Sign2', parent=body_style, alignment=1))]
    ]
    sign_table = Table(sign_data, colWidths=[240, 247])
    sign_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(sign_table)
    
    # Compilar documento
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Relatório PDF '{pdf_filename}' gerado com sucesso!")
    
    # Limpar arquivos de imagem temporários
    for file in os.listdir(temp_dir):
        os.remove(os.path.join(temp_dir, file))
    os.rmdir(temp_dir)
    print("Arquivos de imagem temporários excluídos.")

if __name__ == '__main__':
    main()
