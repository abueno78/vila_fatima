import os
import sqlite3
import re
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# Importa funções de carga do script original do projeto
from gerar_relatorio_imagens import load_data

def main():
    db_path = 'coleta_esus.db'
    print("Carregando dados para a apresentação...")
    df = load_data(db_path)
    
    # Filtros idênticos aos do dashboard
    df_25_26 = df[df['year'].isin([2025, 2026])].copy()
    df_elderly = df[(df['age'] >= 60) & (df['parsed_date'] >= datetime(2019, 11, 1))].copy()
    
    # Rótulos do eixo X formatados (ex: Jan/25)
    monthly_total = df_25_26.groupby('year_month').size()
    monthly_unique = df_25_26.groupby('year_month')['paciente_upper'].nunique()
    x_labels_pt = [datetime.strptime(str(p), '%Y-%m').strftime('%b/%y') for p in monthly_total.index]
    
    # Tradução dos meses para inglês
    months_en = {
        'jan': 'Jan', 'fev': 'Feb', 'mar': 'Mar', 'abr': 'Apr', 'mai': 'May', 'jun': 'Jun',
        'jul': 'Jul', 'ago': 'Aug', 'set': 'Sep', 'out': 'Oct', 'nov': 'Nov', 'dez': 'Dec'
    }
    x_labels_en = []
    for xl in x_labels_pt:
        parts = xl.split('/')
        month_pt = parts[0].lower()
        month_en = months_en.get(month_pt, parts[0].capitalize())
        x_labels_en.append(f"{month_en}/{parts[1]}")

    # =========================================================================
    # GERAÇÃO DOS GRÁFICOS (PT e EN)
    # =========================================================================

    # 1. Volume de Atendimentos vs Pacientes Únicos
    # Versão PT
    fig_vol_pt = go.Figure()
    fig_vol_pt.add_trace(go.Bar(x=x_labels_pt, y=monthly_total.values, name='Atendimentos Totais', marker_color='#009EDB'))
    fig_vol_pt.add_trace(go.Bar(x=x_labels_pt, y=monthly_unique.values, name='Pacientes Únicos', marker_color='#00DF89'))
    fig_vol_pt.update_layout(
        barmode='group', xaxis_title='Mês', yaxis_title='Quantidade',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(x=0.02, y=0.98, bgcolor='rgba(18,24,38,0.6)', bordercolor='rgba(255,255,255,0.1)', borderwidth=1),
        margin=dict(l=40, r=40, t=20, b=40), height=350, yaxis=dict(gridcolor='rgba(255,255,255,0.08)'), font=dict(color='#ffffff')
    )
    div_vol_pt = fig_vol_pt.to_html(include_plotlyjs=False, full_html=False)

    # Versão EN
    fig_vol_en = go.Figure()
    fig_vol_en.add_trace(go.Bar(x=x_labels_en, y=monthly_total.values, name='Total Consultations', marker_color='#009EDB'))
    fig_vol_en.add_trace(go.Bar(x=x_labels_en, y=monthly_unique.values, name='Unique Patients', marker_color='#00DF89'))
    fig_vol_en.update_layout(
        barmode='group', xaxis_title='Month', yaxis_title='Quantity',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(x=0.02, y=0.98, bgcolor='rgba(18,24,38,0.6)', bordercolor='rgba(255,255,255,0.1)', borderwidth=1),
        margin=dict(l=40, r=40, t=20, b=40), height=350, yaxis=dict(gridcolor='rgba(255,255,255,0.08)'), font=dict(color='#ffffff')
    )
    div_vol_en = fig_vol_en.to_html(include_plotlyjs=False, full_html=False)

    # 2. Áreas Profissionais
    area_mapping_pt = {
        'MEDICINA': 'Medicina', 'ENFERMAGEM': 'Enfermagem', 'ODONTOLOGIA': 'Odontologia',
        'TÉCNICO DE ENFERMAGEM': 'Téc. de Enfermagem', 'TECNICO DE ENFERMAGEM': 'Téc. de Enfermagem',
        'AUXILIAR DE SAÚDE BUCAL': 'Aux. de Saúde Bucal', 'AUXILIAR DE SAUDE BUCAL': 'Aux. de Saúde Bucal',
        'OUTROS / NÃO IDENTIFICADO': 'Outros/Não Identificado', 'RESIDENTE': 'Residente',
        'ACADÊMICO': 'Acadêmico/Estudante', 'ACADEMICO': 'Acadêmico/Estudante'
    }
    area_mapping_en = {
        'MEDICINA': 'Medicine', 'ENFERMAGEM': 'Nursing', 'ODONTOLOGIA': 'Dentistry',
        'TÉCNICO DE ENFERMAGEM': 'Nursing Tech', 'TECNICO DE ENFERMAGEM': 'Nursing Tech',
        'AUXILIAR DE SAÚDE BUCAL': 'Dental Assistant', 'AUXILIAR DE SAUDE BUCAL': 'Dental Assistant',
        'OUTROS / NÃO IDENTIFICADO': 'Others/Unidentified', 'RESIDENTE': 'Resident',
        'ACADÊMICO': 'Academic/Intern', 'ACADEMICO': 'Academic/Intern'
    }
    
    df_25_26['prof_area_pt'] = df_25_26['professional_area'].str.upper().map(area_mapping_pt).fillna('Outros/Não Identificado')
    df_25_26['prof_area_en'] = df_25_26['professional_area'].str.upper().map(area_mapping_en).fillna('Others/Unidentified')
    
    area_counts_pt = df_25_26['prof_area_pt'].value_counts()
    area_counts_en = df_25_26['prof_area_en'].value_counts()

    # Versão PT
    fig_area_pt = go.Figure()
    fig_area_pt.add_trace(go.Bar(y=area_counts_pt.index, x=area_counts_pt.values, orientation='h', marker=dict(color=area_counts_pt.values, colorscale='Blues', reversescale=True)))
    fig_area_pt.update_layout(
        xaxis_title='Volume de Atendimentos', yaxis_title='Área de Atuação',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=40, t=20, b=40), height=350, xaxis=dict(gridcolor='rgba(255,255,255,0.08)'), font=dict(color='#ffffff')
    )
    div_area_pt = fig_area_pt.to_html(include_plotlyjs=False, full_html=False)

    # Versão EN
    fig_area_en = go.Figure()
    fig_area_en.add_trace(go.Bar(y=area_counts_en.index, x=area_counts_en.values, orientation='h', marker=dict(color=area_counts_en.values, colorscale='Blues', reversescale=True)))
    fig_area_en.update_layout(
        xaxis_title='Number of Consultations', yaxis_title='Professional Domain',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=40, t=20, b=40), height=350, xaxis=dict(gridcolor='rgba(255,255,255,0.08)'), font=dict(color='#ffffff')
    )
    div_area_en = fig_area_en.to_html(include_plotlyjs=False, full_html=False)

    # 3. Evolução Etária Mensal
    def categorize_age_pt(age):
        if pd.isna(age): return 'Não Informado'
        if age <= 14: return 'Crianças (0-14)'
        elif age <= 29: return 'Jovens (15-29)'
        elif age <= 59: return 'Adultos (30-59)'
        else: return 'Idosos (60+)'

    def categorize_age_en(age):
        if pd.isna(age): return 'Unidentified'
        if age <= 14: return 'Children (0-14)'
        elif age <= 29: return 'Youth (15-29)'
        elif age <= 59: return 'Adults (30-59)'
        else: return 'Elderly (60+)'

    df_25_26['age_group_pt'] = df_25_26['age'].apply(categorize_age_pt)
    df_25_26['age_group_en'] = df_25_26['age'].apply(categorize_age_en)
    
    monthly_age_pt = df_25_26.groupby(['year_month', 'age_group_pt']).size().unstack(fill_value=0)
    monthly_age_pct_pt = monthly_age_pt.div(monthly_age_pt.sum(axis=1), axis=0) * 100
    order_pt = ['Crianças (0-14)', 'Jovens (15-29)', 'Adultos (30-59)', 'Idosos (60+)']
    monthly_age_pct_pt = monthly_age_pct_pt.reindex(columns=order_pt).fillna(0)

    monthly_age_en = df_25_26.groupby(['year_month', 'age_group_en']).size().unstack(fill_value=0)
    monthly_age_pct_en = monthly_age_en.div(monthly_age_en.sum(axis=1), axis=0) * 100
    order_en = ['Children (0-14)', 'Youth (15-29)', 'Adults (30-59)', 'Elderly (60+)']
    monthly_age_pct_en = monthly_age_pct_en.reindex(columns=order_en).fillna(0)

    colors_age = ['#5DADE2', '#48C9B0', '#F4D03F', '#AF7AC5']

    # Versão PT
    fig_age_pct_pt = go.Figure()
    for idx, col in enumerate(order_pt):
        fig_age_pct_pt.add_trace(go.Bar(x=x_labels_pt, y=monthly_age_pct_pt[col], name=col, marker_color=colors_age[idx]))
    fig_age_pct_pt.update_layout(
        barmode='stack', xaxis_title='Mês', yaxis_title='Porcentagem (%)',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(x=1.02, y=1.0, bgcolor='rgba(18,24,38,0.6)', bordercolor='rgba(255,255,255,0.1)', borderwidth=1),
        margin=dict(l=40, r=40, t=20, b=40), height=350, yaxis=dict(gridcolor='rgba(255,255,255,0.08)'), font=dict(color='#ffffff')
    )
    div_age_pct_pt = fig_age_pct_pt.to_html(include_plotlyjs=False, full_html=False)

    # Versão EN
    fig_age_pct_en = go.Figure()
    for idx, col in enumerate(order_en):
        fig_age_pct_en.add_trace(go.Bar(x=x_labels_en, y=monthly_age_pct_en[col], name=col, marker_color=colors_age[idx]))
    fig_age_pct_en.update_layout(
        barmode='stack', xaxis_title='Month', yaxis_title='Percentage (%)',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(x=1.02, y=1.0, bgcolor='rgba(18,24,38,0.6)', bordercolor='rgba(255,255,255,0.1)', borderwidth=1),
        margin=dict(l=40, r=40, t=20, b=40), height=350, yaxis=dict(gridcolor='rgba(255,255,255,0.08)'), font=dict(color='#ffffff')
    )
    div_age_pct_en = fig_age_pct_en.to_html(include_plotlyjs=False, full_html=False)

    # 4. Taxa de Retorno por Faixa Etária
    ratios_age_pt = []
    for grp in order_pt:
        sub = df_25_26[df_25_26['age_group_pt'] == grp]
        ratio = len(sub) / sub['paciente_upper'].nunique() if sub['paciente_upper'].nunique() > 0 else 0
        ratios_age_pt.append(ratio)

    ratios_age_en = []
    for grp in order_en:
        sub = df_25_26[df_25_26['age_group_en'] == grp]
        ratio = len(sub) / sub['paciente_upper'].nunique() if sub['paciente_upper'].nunique() > 0 else 0
        ratios_age_en.append(ratio)

    # Versão PT
    fig_ret_age_pt = go.Figure()
    fig_ret_age_pt.add_trace(go.Bar(x=order_pt, y=ratios_age_pt, marker_color=colors_age, text=[f'{r:.2f}x' for r in ratios_age_pt], textposition='outside'))
    fig_ret_age_pt.update_layout(
        xaxis_title='Faixa Etária', yaxis_title='Média de Atendimentos por Paciente Único',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=40, t=30, b=40), height=350, yaxis=dict(gridcolor='rgba(255,255,255,0.08)'), font=dict(color='#ffffff')
    )
    div_ret_age_pt = fig_ret_age_pt.to_html(include_plotlyjs=False, full_html=False)

    # Versão EN
    fig_ret_age_en = go.Figure()
    fig_ret_age_en.add_trace(go.Bar(x=order_en, y=ratios_age_en, marker_color=colors_age, text=[f'{r:.2f}x' for r in ratios_age_en], textposition='outside'))
    fig_ret_age_en.update_layout(
        xaxis_title='Age Group', yaxis_title='Average Consultations per Unique Patient',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=40, t=30, b=40), height=350, yaxis=dict(gridcolor='rgba(255,255,255,0.08)'), font=dict(color='#ffffff')
    )
    div_ret_age_en = fig_ret_age_en.to_html(include_plotlyjs=False, full_html=False)

    # 5. Distribuição de Idosos (Donut)
    def categorize_elderly_pt(age):
        if age <= 70: return '60-70 anos'
        elif age <= 80: return '71-80 anos'
        elif age <= 90: return '81-90 anos'
        else: return '91+ anos'

    def categorize_elderly_en(age):
        if age <= 70: return '60-70 Years'
        elif age <= 80: return '71-80 Years'
        elif age <= 90: return '81-90 Years'
        else: return '91+ Years'
        
    df_elderly['eld_group_pt'] = df_elderly['age'].apply(categorize_elderly_pt)
    df_elderly['eld_group_en'] = df_elderly['age'].apply(categorize_elderly_en)
    
    eld_counts_pt = df_elderly['eld_group_pt'].value_counts()
    eld_counts_en = df_elderly['eld_group_en'].value_counts()
    eld_order_pt = ['60-70 anos', '71-80 anos', '81-90 anos', '91+ anos']
    eld_order_en = ['60-70 Years', '71-80 Years', '81-90 Years', '91+ Years']
    
    eld_counts_pt = eld_counts_pt.reindex(eld_order_pt).fillna(0)
    eld_counts_en = eld_counts_en.reindex(eld_order_en).fillna(0)

    # Versão PT
    fig_eld_donut_pt = go.Figure()
    fig_eld_donut_pt.add_trace(go.Pie(labels=eld_counts_pt.index, values=eld_counts_pt.values, hole=0.4, marker=dict(colors=['#AED6F1', '#5DADE2', '#2E86C1', '#1B4F72']), textinfo='percent+label', textfont=dict(color='#ffffff')))
    fig_eld_donut_pt.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=20, b=20), height=350, font=dict(color='#ffffff'), showlegend=False)
    div_eld_donut_pt = fig_eld_donut_pt.to_html(include_plotlyjs=False, full_html=False)

    # Versão EN
    fig_eld_donut_en = go.Figure()
    fig_eld_donut_en.add_trace(go.Pie(labels=eld_counts_en.index, values=eld_counts_en.values, hole=0.4, marker=dict(colors=['#AED6F1', '#5DADE2', '#2E86C1', '#1B4F72']), textinfo='percent+label', textfont=dict(color='#ffffff')))
    fig_eld_donut_en.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=20, b=20), height=350, font=dict(color='#ffffff'), showlegend=False)
    div_eld_donut_en = fig_eld_donut_en.to_html(include_plotlyjs=False, full_html=False)

    # 6. Taxa de Retorno por Cohort de Idosos
    ratios_eld_pt = []
    for grp in eld_order_pt:
        sub = df_elderly[df_elderly['eld_group_pt'] == grp]
        ratio = len(sub) / sub['paciente_upper'].nunique() if sub['paciente_upper'].nunique() > 0 else 0
        ratios_eld_pt.append(ratio)

    ratios_eld_en = []
    for grp in eld_order_en:
        sub = df_elderly[df_elderly['eld_group_en'] == grp]
        ratio = len(sub) / sub['paciente_upper'].nunique() if sub['paciente_upper'].nunique() > 0 else 0
        ratios_eld_en.append(ratio)

    # Versão PT
    fig_ret_eld_pt = go.Figure()
    fig_ret_eld_pt.add_trace(go.Bar(x=eld_order_pt, y=ratios_eld_pt, marker_color=['#AED6F1', '#5DADE2', '#2E86C1', '#1B4F72'], text=[f'{r:.2f}x' for r in ratios_eld_pt], textposition='outside'))
    fig_ret_eld_pt.update_layout(
        xaxis_title='Subfaixa de Idosos', yaxis_title='Média de Atendimentos por Paciente Único',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=40, t=30, b=40), height=350, yaxis=dict(gridcolor='rgba(255,255,255,0.08)'), font=dict(color='#ffffff')
    )
    div_ret_eld_pt = fig_ret_eld_pt.to_html(include_plotlyjs=False, full_html=False)

    # Versão EN
    fig_ret_eld_en = go.Figure()
    fig_ret_eld_en.add_trace(go.Bar(x=eld_order_en, y=ratios_eld_en, marker_color=['#AED6F1', '#5DADE2', '#2E86C1', '#1B4F72'], text=[f'{r:.2f}x' for r in ratios_eld_en], textposition='outside'))
    fig_ret_eld_en.update_layout(
        xaxis_title='Elderly Age Group', yaxis_title='Average Consultations per Unique Patient',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=40, t=30, b=40), height=350, yaxis=dict(gridcolor='rgba(255,255,255,0.08)'), font=dict(color='#ffffff')
    )
    div_ret_eld_en = fig_ret_eld_en.to_html(include_plotlyjs=False, full_html=False)

    # 7. Pirâmide Etária (Censo 2022)
    categories_pyr_pt = ['0-4 Anos', '5-9 Anos', '10-14 Anos', '15-19 Anos', '20-24 Anos', '25-29 Anos', '30-39 Anos', '40-49 Anos', '50-59 Anos', '60-69 Anos', '70 Anos ou Mais']
    categories_pyr_en = ['0-4 Years', '5-9 Years', '10-14 Years', '15-19 Years', '20-24 Years', '25-29 Years', '30-39 Years', '40-49 Years', '50-59 Years', '60-69 Years', '70+ Years']
    male_pyr_values = [303, 380, 280, 280, 380, 290, 500, 460, 330, 230, 150]
    female_pyr_values = [275, 330, 335, 310, 380, 350, 606, 510, 420, 340, 260]

    # Versão PT
    fig_pyramid_pt = go.Figure()
    fig_pyramid_pt.add_trace(go.Bar(y=categories_pyr_pt, x=[-val for val in male_pyr_values], name='Masculino', orientation='h', marker=dict(color='#8ecae6'), hoverinfo='text', text=male_pyr_values, hovertemplate='<b>Masculino</b><br>Faixa: %{y}<br>População: %{text}<extra></extra>'))
    fig_pyramid_pt.add_trace(go.Bar(y=categories_pyr_pt, x=female_pyr_values, name='Feminino', orientation='h', marker=dict(color='#f1a7a1'), hoverinfo='text', text=female_pyr_values, hovertemplate='<b>Feminino</b><br>Faixa: %{y}<br>População: %{text}<extra></extra>'))
    fig_pyramid_pt.update_layout(
        barmode='overlay', bargap=0.1, bargroupgap=0,
        xaxis=dict(tickvals=[-606, -303, 0, 303, 606], ticktext=['606', '303', '0', '303', '606'], title='População', gridcolor='rgba(255,255,255,0.08)'),
        yaxis=dict(title='Faixa Etária'), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(x=0.75, y=0.98), margin=dict(l=40, r=40, t=20, b=40), height=380, font=dict(color='#ffffff')
    )
    div_pyramid_pt = fig_pyramid_pt.to_html(include_plotlyjs=False, full_html=False)

    # Versão EN
    fig_pyramid_en = go.Figure()
    fig_pyramid_en.add_trace(go.Bar(y=categories_pyr_en, x=[-val for val in male_pyr_values], name='Male', orientation='h', marker=dict(color='#8ecae6'), hoverinfo='text', text=male_pyr_values, hovertemplate='<b>Male</b><br>Age: %{y}<br>Population: %{text}<extra></extra>'))
    fig_pyramid_en.add_trace(go.Bar(y=categories_pyr_en, x=female_pyr_values, name='Female', orientation='h', marker=dict(color='#f1a7a1'), hoverinfo='text', text=female_pyr_values, hovertemplate='<b>Female</b><br>Age: %{y}<br>Population: %{text}<extra></extra>'))
    fig_pyramid_en.update_layout(
        barmode='overlay', bargap=0.1, bargroupgap=0,
        xaxis=dict(tickvals=[-606, -303, 0, 303, 606], ticktext=['606', '303', '0', '303', '606'], title='Population', gridcolor='rgba(255,255,255,0.08)'),
        yaxis=dict(title='Age Group'), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(x=0.75, y=0.98), margin=dict(l=40, r=40, t=20, b=40), height=380, font=dict(color='#ffffff')
    )
    div_pyramid_en = fig_pyramid_en.to_html(include_plotlyjs=False, full_html=False)

    # 8. Raça/Cor (Censo 2022)
    raca_df_pt = pd.DataFrame({
        'Raça/Cor': ['Branca', 'Preta', 'Parda', 'Amarela', 'Indígena'],
        'População Masculina (%)': [42.47, 31.84, 25.68, 0.00, 0.00],
        'População Feminina (%)': [43.01, 33.43, 23.32, 0.00, 0.00]
    })
    
    raca_df_en = pd.DataFrame({
        'Race/Color': ['White', 'Black', 'Mixed (Pardo)', 'Asian', 'Indigenous'],
        'Male Population (%)': [42.47, 31.84, 25.68, 0.00, 0.00],
        'Female Population (%)': [43.01, 33.43, 23.32, 0.00, 0.00]
    })

    # Versão PT
    fig_raca_pt = go.Figure()
    fig_raca_pt.add_trace(go.Bar(x=raca_df_pt['Raça/Cor'], y=raca_df_pt['População Masculina (%)'], name='Masculino', marker_color='#8ecae6'))
    fig_raca_pt.add_trace(go.Bar(x=raca_df_pt['Raça/Cor'], y=raca_df_pt['População Feminina (%)'], name='Feminino', marker_color='#f1a7a1'))
    fig_raca_pt.update_layout(
        barmode='group', xaxis_title='Raça/Cor (Autodeclarada)', yaxis_title='Proporção (%)',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(x=0.75, y=0.98), margin=dict(l=40, r=40, t=20, b=40),
        height=320, yaxis=dict(gridcolor='rgba(255,255,255,0.08)', range=[0, 50]), font=dict(color='#ffffff')
    )
    div_raca_pt = fig_raca_pt.to_html(include_plotlyjs=False, full_html=False)

    # Versão EN
    fig_raca_en = go.Figure()
    fig_raca_en.add_trace(go.Bar(x=raca_df_en['Race/Color'], y=raca_df_en['Male Population (%)'], name='Male', marker_color='#8ecae6'))
    fig_raca_en.add_trace(go.Bar(x=raca_df_en['Race/Color'], y=raca_df_en['Female Population (%)'], name='Female', marker_color='#f1a7a1'))
    fig_raca_en.update_layout(
        barmode='group', xaxis_title='Race/Color (Self-declared)', yaxis_title='Proportion (%)',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(x=0.75, y=0.98), margin=dict(l=40, r=40, t=20, b=40),
        height=320, yaxis=dict(gridcolor='rgba(255,255,255,0.08)', range=[0, 50]), font=dict(color='#ffffff')
    )
    div_raca_en = fig_raca_en.to_html(include_plotlyjs=False, full_html=False)


    # =========================================================================
    # COMPILAÇÃO DO HTML COMPLETO COM CONTROLES DE IDIOMA
    # =========================================================================
    print("Compilando código HTML bilíngue...")

    html_content = f"""<!doctype html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <title>Unidade de Saúde Vila Fátima</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    
    <!-- Estilos do Reveal.js -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.5.0/reveal.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.5.0/theme/black.min.css">
    
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- Plotly.js -->
    <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
    
    <style>
        .reveal {{
            background-color: #0b0f19;
            color: #ffffff;
            font-family: 'Outfit', 'Inter', sans-serif;
        }}
        .reveal h1, .reveal h2, .reveal h3, .reveal h4 {{
            color: #ffffff;
            font-weight: 800;
            text-transform: none;
            text-shadow: none;
        }}
        .reveal h1 {{
            font-size: 2.8rem !important;
            background: linear-gradient(135deg, #ffffff, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .reveal h2 {{
            font-size: 2.0rem !important;
            border-bottom: 2px solid #009EDB;
            padding-bottom: 8px;
            margin-bottom: 20px !important;
            display: inline-block;
        }}
        .card {{
            background: linear-gradient(145deg, #131a2d, #0d1222);
            border: 1px solid rgba(0, 158, 219, 0.18);
            border-radius: 16px;
            padding: 16px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
        }}
        .metric-val {{
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #009EDB, #00DF89);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .metric-lbl {{
            font-size: 0.8rem;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            font-weight: 600;
        }}
        .slides section {{
            height: 100%;
        }}
        /* Botão seletor de idioma flutuante */
        #lang-selector {{
            position: absolute;
            top: 20px;
            right: 20px;
            z-index: 999;
            background: rgba(18, 24, 38, 0.9);
            border: 1px solid rgba(0, 158, 219, 0.3);
            border-radius: 8px;
            padding: 6px 12px;
            font-size: 0.85rem;
            font-weight: bold;
            color: white;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            transition: all 0.2s ease;
        }}
        #lang-selector button:hover {{
            color: #009EDB;
        }}
        .hidden {{
            display: none !important;
        }}
    </style>
</head>
<body>
    <!-- Seletor de Idioma -->
    <div id="lang-selector">
        🌐 
        <button onclick="setLanguage('pt')" class="mx-1 focus:outline-none">PT</button> | 
        <button onclick="setLanguage('en')" class="mx-1 focus:outline-none">EN</button>
    </div>

    <div class="reveal">
        <div class="slides">
            
            <!-- Slide 1: Cover (Capa) -->
            <section class="flex flex-col justify-center items-center h-full text-center">
                <div class="mb-4">
                    <img src="https://logodownload.org/wp-content/uploads/2021/04/pucrs-logo.png" style="height: 60px; filter: brightness(0) invert(1);" alt="PUCRS Logo">
                </div>
                
                <!-- Português -->
                <div class="lang-pt">
                    <h1 class="mb-2">Unidade de Saúde Vila Fátima</h1>
                    <p class="text-sky-400 font-semibold text-xl mb-8">Perfil Operacional e Demográfico (Dados do Censo 2022 e Atendimentos 2025-2026)</p>
                    <div class="w-24 h-1 bg-sky-500 mb-8 mx-auto"></div>
                    <p class="text-gray-400 text-sm">Público-alvo: Professores e Visitantes Estrangeiros</p>
                    <p class="text-gray-500 text-xs mt-2">PUCRS Escola de Medicina • Porto Alegre, Brasil</p>
                </div>
                
                <!-- Inglês -->
                <div class="lang-en hidden">
                    <h1 class="mb-2">Vila Fátima Primary Health Unit</h1>
                    <p class="text-sky-400 font-semibold text-xl mb-8">An Operational & Demographic Profile (Census 2022 & 2025-2026 Data)</p>
                    <div class="w-24 h-1 bg-sky-500 mb-8 mx-auto"></div>
                    <p class="text-gray-400 text-sm">Target Audience: Academic & Institutional Visitors</p>
                    <p class="text-gray-500 text-xs mt-2">PUCRS School of Medicine • Porto Alegre, Brazil</p>
                </div>
            </section>
            
            <!-- Slide 2: Territorial Context (Contexto Territorial) -->
            <section class="px-8 text-left">
                <h2 class="lang-pt">1. Contexto Territorial e Socioeconômico</h2>
                <h2 class="lang-en hidden">1. Territorial & Socioeconomic Context</h2>
                
                <div class="grid grid-cols-3 gap-4 mb-6">
                    <div class="card text-center">
                        <div class="lang-pt">
                            <div class="metric-lbl">Área Total</div>
                            <div class="metric-val">0,5135 km²</div>
                            <div class="text-xs text-gray-400 mt-1">Setor densamente povoado</div>
                        </div>
                        <div class="lang-en hidden">
                            <div class="metric-lbl">Total Area</div>
                            <div class="metric-val">0.5135 km²</div>
                            <div class="text-xs text-gray-400 mt-1">Densely populated sector</div>
                        </div>
                    </div>
                    <div class="card text-center">
                        <div class="lang-pt">
                            <div class="metric-lbl">Comunidade Urbana (Favela)</div>
                            <div class="metric-val">69,18%</div>
                            <div class="text-xs text-gray-400 mt-1">Alta vulnerabilidade territorial</div>
                        </div>
                        <div class="lang-en hidden">
                            <div class="metric-lbl">Urban Communities (Favela)</div>
                            <div class="metric-val">69.18%</div>
                            <div class="text-xs text-gray-400 mt-1">High territorial vulnerability</div>
                        </div>
                    </div>
                    <div class="card text-center">
                        <div class="lang-pt">
                            <div class="metric-lbl">População Residente</div>
                            <div class="metric-val">4.891</div>
                            <div class="text-xs text-gray-400 mt-1">Com base no Censo 2022</div>
                        </div>
                        <div class="lang-en hidden">
                            <div class="metric-lbl">Resident Population</div>
                            <div class="metric-val">4,891</div>
                            <div class="text-xs text-gray-400 mt-1">Based on 2022 Census data</div>
                        </div>
                    </div>
                </div>
                
                <div class="grid grid-cols-3 gap-4">
                    <div class="card text-center">
                        <div class="lang-pt">
                            <div class="metric-lbl">Renda Média Mensal</div>
                            <div class="metric-val">R$ 1.721,14</div>
                            <div class="text-xs text-gray-400 mt-1">Por chefe de família</div>
                        </div>
                        <div class="lang-en hidden">
                            <div class="metric-lbl">Mean Monthly Income</div>
                            <div class="metric-val">R$ 1,721.14</div>
                            <div class="text-xs text-gray-400 mt-1">Per household head</div>
                        </div>
                    </div>
                    <div class="card text-center">
                        <div class="lang-pt">
                            <div class="metric-lbl">Renda Mediana Mensal</div>
                            <div class="metric-val">R$ 1.212,00</div>
                            <div class="text-xs text-gray-400 mt-1">Equivalente a 1 salário mínimo (2022)</div>
                        </div>
                        <div class="lang-en hidden">
                            <div class="metric-lbl">Median Monthly Income</div>
                            <div class="metric-val">R$ 1,212.00</div>
                            <div class="text-xs text-gray-400 mt-1">Equivalent to 1 minimum wage (2022)</div>
                        </div>
                    </div>
                    <div class="card text-center">
                        <div class="lang-pt">
                            <div class="metric-lbl">Desvio Padrão da Renda</div>
                            <div class="metric-val">R$ 378,07</div>
                            <div class="text-xs text-gray-400 mt-1">Variabilidade no setor do censo</div>
                        </div>
                        <div class="lang-en hidden">
                            <div class="metric-lbl">Income Standard Deviation</div>
                            <div class="metric-val">R$ 378.07</div>
                            <div class="text-xs text-gray-400 mt-1">Indicates low income disparity</div>
                        </div>
                    </div>
                </div>
            </section>
            
            <!-- Slide 3: Demographic Pyramid (Pirâmide) -->
            <section class="px-8 text-left">
                <h2 class="lang-pt">2. Estrutura da População Residente</h2>
                <h2 class="lang-en hidden">2. Resident Population Structure</h2>
                <div class="grid grid-cols-12 gap-6 items-center">
                    <div class="col-span-8 card">
                        <div class="lang-pt">{div_pyramid_pt}</div>
                        <div class="lang-en hidden">{div_pyramid_en}</div>
                    </div>
                    <div class="col-span-4 text-sm text-gray-300 space-y-4">
                        <div class="lang-pt">
                            <p class="font-bold text-sky-400 text-base">Estrutura Demográfica:</p>
                            <ul class="list-disc pl-4 space-y-2">
                                <li><strong>Base Larga:</strong> Proporção significativa de crianças e jovens (0-24 anos), apontando alta demanda materno-infantil.</li>
                                <li><strong>Adultos Consolidados:</strong> Forte presença de adultos entre 30 e 49 anos.</li>
                                <li><strong>Envelhecimento:</strong> Coorte crescente de idosos (60+), exigindo atenção voltada a doenças crônicas.</li>
                            </ul>
                        </div>
                        <div class="lang-en hidden">
                            <p class="font-bold text-sky-400 text-base">Key Demographic Findings:</p>
                            <ul class="list-disc pl-4 space-y-2">
                                <li><strong>Broad Base:</strong> Significant proportion of children and youth (0-24 years), pointing to high maternal-child healthcare demand.</li>
                                <li><strong>Consolidated Adult Cohort:</strong> Strong presence of adults aged 30-49.</li>
                                <li><strong>Aging Population:</strong> Clear elderly groups (60+), highlighting the need for chronic disease management.</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </section>
            
            <!-- Slide 4: Race and Color (Raça) -->
            <section class="px-8 text-left">
                <h2 class="lang-pt">3. Composição por Raça e Cor do Território</h2>
                <h2 class="lang-en hidden">3. Racial Composition of the Territory</h2>
                <div class="grid grid-cols-12 gap-6 items-center">
                    <div class="col-span-8 card">
                        <div class="lang-pt">{div_raca_pt}</div>
                        <div class="lang-en hidden">{div_raca_en}</div>
                    </div>
                    <div class="col-span-4 text-sm text-gray-300 space-y-4">
                        <div class="lang-pt">
                            <p class="font-bold text-sky-400 text-base">Perfil de Diversidade Racial:</p>
                            <ul class="list-disc pl-4 space-y-2">
                                <li><strong>Branca:</strong> Representa cerca de <strong>43%</strong> da população residente.</li>
                                <li><strong>Negra e Parda (Pretos/Pardos):</strong> Representam conjuntamente mais de <strong>55%</strong> dos residentes locais.</li>
                                <li><strong>Fator Diferencial:</strong> Percentual de população preta e parda significativamente superior à média geral de Porto Alegre.</li>
                            </ul>
                        </div>
                        <div class="lang-en hidden">
                            <p class="font-bold text-sky-400 text-base">Racial Diversity Profile:</p>
                            <ul class="list-disc pl-4 space-y-2">
                                <li><strong>White Cohort:</strong> Accounts for approximately <strong>43%</strong> of the population.</li>
                                <li><strong>Black & Pardo (Mixed) Cohorts:</strong> Represent more than <strong>55%</strong> of the local community.</li>
                                <li><strong>Significance:</strong> Higher percentage of Black and Mixed ethnic groups compared to the wider Porto Alegre municipal average.</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </section>
            
            <!-- Slide 5: Operational Overview (Atendimentos) -->
            <section class="px-8 text-left">
                <h2 class="lang-pt">4. Indicadores de Atendimento e Alcance (2025-2026)</h2>
                <h2 class="lang-en hidden">4. Healthcare Operational Metrics (2025-2026)</h2>
                <div class="grid grid-cols-12 gap-6 items-center">
                    <div class="col-span-8 card">
                        <div class="lang-pt">{div_vol_pt}</div>
                        <div class="lang-en hidden">{div_vol_en}</div>
                    </div>
                    <div class="col-span-4 text-sm text-gray-300 space-y-4">
                        <div class="lang-pt">
                            <p class="font-bold text-sky-400 text-base">Volume e Cobertura:</p>
                            <ul class="list-disc pl-4 space-y-2">
                                <li><strong>Volume Mensal:</strong> Fluxo contínuo e estável de atendimentos ao longo do ano.</li>
                                <li><strong>Alcance Real:</strong> Relação entre consultas e pacientes únicos indica que a mesma pessoa é acompanhada de forma longitudinal.</li>
                                <li><strong>Vínculo:</strong> Forte ligação entre a equipe de saúde e as famílias assistidas.</li>
                            </ul>
                        </div>
                        <div class="lang-en hidden">
                            <p class="font-bold text-sky-400 text-base">Attendance & Reach Analysis:</p>
                            <ul class="list-disc pl-4 space-y-2">
                                <li><strong>Consultation Stability:</strong> High monthly volume averaging consistent care throughout the period.</li>
                                <li><strong>Coverage:</strong> The comparison between total consultations and unique patients reveals a high longitudinal follow-up rate.</li>
                                <li><strong>Retention:</strong> Relies on strong family-health bonding.</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Slide 6: Professional Domain Integration (Profissionais) -->
            <section class="px-8 text-left">
                <h2 class="lang-pt">5. Integração Profissional Multidisciplinar</h2>
                <h2 class="lang-en hidden">5. Multidisciplinary Professional Care</h2>
                <div class="grid grid-cols-12 gap-6 items-center">
                    <div class="col-span-8 card">
                        <div class="lang-pt">{div_area_pt}</div>
                        <div class="lang-en hidden">{div_area_en}</div>
                    </div>
                    <div class="col-span-4 text-sm text-gray-300 space-y-4">
                        <div class="lang-pt">
                            <p class="font-bold text-sky-400 text-base">Pilares da Assistência:</p>
                            <ul class="list-disc pl-4 space-y-2">
                                <li><strong>Equipe Multiprofissional:</strong> Integração de Medicina, Enfermagem, Odontologia e Equipes Técnicas.</li>
                                <li><strong>Atuação da Enfermagem:</strong> Papel crucial e central em consultas de triagem, pré-natal e acompanhamento de crônicos.</li>
                                <li><strong>Saúde Bucal:</strong> Assistência odontológica integrada ao plano de cuidados do território.</li>
                            </ul>
                        </div>
                        <div class="lang-en hidden">
                            <p class="font-bold text-sky-400 text-base">Key Pillars of Care:</p>
                            <ul class="list-disc pl-4 space-y-2">
                                <li><strong>Multidisciplinary Structure:</strong> Integrated services spanning Medicine, Nursing, Dentistry, and Nursing Technicians.</li>
                                <li><strong>Strong Nurse-Led Care:</strong> Highlights the active role of nurses in triage, prenatal monitoring, and chronic patient control.</li>
                                <li><strong>Dentistry Access:</strong> Robust oral health integration.</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </section>
            
            <!-- Slide 7: Demographic Distribution of Consultations (Evolução Faixa Etária) -->
            <section class="px-8 text-left">
                <h2 class="lang-pt">6. Atendimentos por Faixa Etária</h2>
                <h2 class="lang-en hidden">6. Consultations by Age Group</h2>
                <div class="grid grid-cols-12 gap-6 items-center">
                    <div class="col-span-8 card">
                        <div class="lang-pt">{div_age_pct_pt}</div>
                        <div class="lang-en hidden">{div_age_pct_en}</div>
                    </div>
                    <div class="col-span-4 text-sm text-gray-300 space-y-4">
                        <div class="lang-pt">
                            <p class="font-bold text-sky-400 text-base">Dinâmica por Faixa Etária:</p>
                            <ul class="list-disc pl-4 space-y-2">
                                <li><strong>Predomínio de Adultos:</strong> Adultos representam o grupo que mais consome consultas operacionalmente.</li>
                                <li><strong>Expressividade de Idosos:</strong> Consistente volume relativo de idosos (60+), superando proporcionalmente o público infantil em todos os meses.</li>
                                <li><strong>Regularidade:</strong> Padrão de consultas estável temporalmente.</li>
                            </ul>
                        </div>
                        <div class="lang-en hidden">
                            <p class="font-bold text-sky-400 text-base">Age Group Dynamics:</p>
                            <ul class="list-disc pl-4 space-y-2">
                                <li><strong>Adult Prevalence:</strong> Adults (30-59 years) represent the highest consultation share.</li>
                                <li><strong>Geriatric Load:</strong> High relative percentage of elderly patients (60+) in every single month, outperforming children.</li>
                                <li><strong>Continuous Care:</strong> Stable distribution reflecting organized scheduled appointments.</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Slide 8: Patient Return Rate by Age Group (Retorno Geral) -->
            <section class="px-8 text-left">
                <h2 class="lang-pt">7. Frequência Média de Consultas por Faixa Etária</h2>
                <h2 class="lang-en hidden">7. Average Visit Frequency by Age Group</h2>
                <div class="grid grid-cols-12 gap-6 items-center">
                    <div class="col-span-8 card">
                        <div class="lang-pt">{div_ret_age_pt}</div>
                        <div class="lang-en hidden">{div_ret_age_en}</div>
                    </div>
                    <div class="col-span-4 text-sm text-gray-300 space-y-4">
                        <div class="lang-pt">
                            <p class="font-bold text-sky-400 text-base">Taxa de Retorno:</p>
                            <ul class="list-disc pl-4 space-y-2">
                                <li><strong>Vínculo Longitudinal:</strong> Altas taxas médias de visitas confirmam que o paciente realiza tratamentos completos, não apenas consultas isoladas.</li>
                                <li><strong>Geriatria Ativa:</strong> O público de idosos tem a maior taxa de reconsultas devido a agravos crônicos.</li>
                                <li><strong>Prevenção:</strong> Acompanhamento regular de crianças no território.</li>
                            </ul>
                        </div>
                        <div class="lang-en hidden">
                            <p class="font-bold text-sky-400 text-base">Patient Return Rate:</p>
                            <ul class="list-disc pl-4 space-y-2">
                                <li><strong>Continuous Care:</strong> Demonstrates high return rates, showing patients visit the unit multiple times.</li>
                                <li><strong>Elderly Intensity:</strong> Elderly patients have the highest average returns, indicating high chronicity and complex care tracking.</li>
                                <li><strong>Preventive Care:</strong> Consistent children follow-ups.</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Slide 9: Elderly Donut & Return Rate (Idosos Detalhado) -->
            <section class="px-8 text-left">
                <h2 class="lang-pt">8. Foco na Atenção Geriátrica (Grupo 60+)</h2>
                <h2 class="lang-en hidden">8. Geriatric Care Focus (60+ Cohort)</h2>
                <div class="grid grid-cols-12 gap-6 items-center">
                    <div class="col-span-4 card text-center">
                        <div class="font-bold text-xs text-sky-400 uppercase mb-2 lang-pt">Distribuição por Idade (60+)</div>
                        <div class="font-bold text-xs text-sky-400 uppercase mb-2 lang-en hidden">Age Distribution (60+)</div>
                        
                        <div class="lang-pt">{div_eld_donut_pt}</div>
                        <div class="lang-en hidden">{div_eld_donut_en}</div>
                    </div>
                    <div class="col-span-4 card text-center">
                        <div class="font-bold text-xs text-sky-400 uppercase mb-2 lang-pt">Taxa de Retorno por Idade</div>
                        <div class="font-bold text-xs text-sky-400 uppercase mb-2 lang-en hidden">Return Rate by Age Range</div>
                        
                        <div class="lang-pt">{div_ret_eld_pt}</div>
                        <div class="lang-en hidden">{div_ret_eld_en}</div>
                    </div>
                    <div class="col-span-4 text-sm text-gray-300 space-y-2">
                        <div class="lang-pt">
                            <p class="font-bold text-sky-400 text-base">Descobertas Gerontológicas:</p>
                            <ul class="list-disc pl-4 space-y-1 text-xs">
                                <li><strong>Volume:</strong> A faixa de 60-70 anos representa a maior fatia absoluta de idosos em atendimento.</li>
                                <li><strong>Intensidade Assistencial:</strong> O retorno cresce conforme a idade avança. O grupo de 81-90 anos exige, em média, <strong>17,42 consultas</strong> no período.</li>
                                <li><strong>Dependência da APS:</strong> Idosos frágeis requerem visitas domiciliares sistemáticas e fluxo ativo.</li>
                            </ul>
                        </div>
                        <div class="lang-en hidden">
                            <p class="font-bold text-sky-400 text-base">Key Elderly Takeaways:</p>
                            <ul class="list-disc pl-4 space-y-1 text-xs">
                                <li><strong>Distribution:</strong> The 60-70 cohort represents the largest absolute share of geriatric appointments.</li>
                                <li><strong>Extreme Continuity of Care:</strong> The oldest cohorts show extreme return rates. The 81-90 age group averages <strong>17.42 visits</strong>.</li>
                                <li><strong>Social Vulnerability:</strong> Elderly patients are heavily dependent on immediate home visits and localized Primary Care (APS).</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Slide 10: Conclusion (Conclusão) -->
            <section class="px-8 text-left">
                <h2 class="lang-pt">9. Conclusões Estratégicas Institucionais</h2>
                <h2 class="lang-en hidden">9. Strategic Institutional Conclusions</h2>
                <div class="grid grid-cols-2 gap-6">
                    
                    <!-- Box PT -->
                    <div class="card space-y-3 lang-pt">
                        <h4 class="text-sky-400 font-bold border-b border-gray-700 pb-2">🎯 Conclusões Principais</h4>
                        <ul class="list-disc pl-4 text-sm text-gray-300 space-y-2">
                            <li><strong>Modelo Territorializado:</strong> Aplicação eficiente da Estratégia de Saúde da Família (ESF) em um território com 69,18% de área de comunidades (favelas).</li>
                            <li><strong>Forte Vínculo com Pacientes:</strong> Taxas excepcionais de retorno garantem o monitoramento longitudinal de doenças crônicas e gestantes.</li>
                            <li><strong>Equipe Sincronizada:</strong> Medicina, Enfermagem e Odontologia atuando em rede única.</li>
                        </ul>
                    </div>
                    <div class="card space-y-3 lang-pt">
                        <h4 class="text-emerald-400 font-bold border-b border-gray-700 pb-2">🏫 Parceria e Impacto Acadêmico</h4>
                        <ul class="list-disc pl-4 text-sm text-gray-300 space-y-2">
                            <li><strong>Cooperação com a PUCRS:</strong> Integração ativa de residentes, acadêmicos e internos da saúde como motores de qualificação da APS municipal.</li>
                            <li><strong>Gestão Baseada em Evidências:</strong> Indicadores operacionais permitem redistribuir e focar os esforços nas equipes com maior sobrecarga geriátrica.</li>
                            <li><strong>Referência:</strong> Vila Fátima atua como modelo pedagógico e clínico de alto impacto.</li>
                        </ul>
                    </div>

                    <!-- Box EN -->
                    <div class="card space-y-3 lang-en hidden">
                        <h4 class="text-sky-400 font-bold border-b border-gray-700 pb-2">🎯 Key Summary Findings</h4>
                        <ul class="list-disc pl-4 text-sm text-gray-300 space-y-2">
                            <li><strong>Territorial Care Model:</strong> Successful implementation of the Family Health Strategy (ESF) in a high-vulnerability setting (69.18% informal community).</li>
                            <li><strong>Strong Patient Bonding:</strong> Outstanding visit return rate, particularly in chronic and elderly patients, confirming active longitudinal care.</li>
                            <li><strong>Cohesive Teamwork:</strong> Integrated flow of medicine, nursing, dentistry and tech care.</li>
                        </ul>
                    </div>
                    <div class="card space-y-3 lang-en hidden">
                        <h4 class="text-emerald-400 font-bold border-b border-gray-700 pb-2">🏫 Academic Cooperation & Impact</h4>
                        <ul class="list-disc pl-4 text-sm text-gray-300 space-y-2">
                            <li><strong>PUCRS Partnership:</strong> Serves as an academic reference, linking medical education and residency with high-impact public health service.</li>
                            <li><strong>Data-driven Decision Making:</strong> Using operational indicators allows local health managers to dynamically adapt resource allocation (e.g., reinforcing elderly-focused services).</li>
                            <li><strong>Replicability:</strong> A reference model of integration between primary care and higher education.</li>
                        </ul>
                    </div>

                </div>
                
                <div class="text-center mt-6 text-xs text-gray-500 font-semibold lang-pt">
                    Obrigado pela atenção! • Unidade de Saúde Vila Fátima / PUCRS
                </div>
                <div class="text-center mt-6 text-xs text-gray-500 font-semibold lang-en hidden">
                    Thank you for your attention! • Vila Fátima Primary Health Unit / PUCRS
                </div>
            </section>

        </div>
    </div>

    <!-- Reveal.js Script -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.5.0/reveal.min.js"></script>
    <script>
        Reveal.initialize({{
            width: 1100,
            height: 700,
            margin: 0.04,
            minScale: 0.2,
            maxScale: 2.0,
            controls: true,
            progress: true,
            history: true,
            center: true,
            transition: 'slide',
            slideNumber: 'c/t'
        }});

        function setLanguage(lang) {{
            if (lang === 'pt') {{
                document.querySelectorAll('.lang-pt').forEach(el => el.classList.remove('hidden'));
                document.querySelectorAll('.lang-en').forEach(el => el.classList.add('hidden'));
            }} else {{
                document.querySelectorAll('.lang-pt').forEach(el => el.classList.add('hidden'));
                document.querySelectorAll('.lang-en').forEach(el => el.classList.remove('hidden'));
            }}
            // Redimensiona gráficos do Plotly para ajustar aos cards após alternar visibilidade
            setTimeout(() => {{
                window.dispatchEvent(new Event('resize'));
            }}, 50);
        }}
    </script>
</body>
</html>
"""

    output_html_path = 'apresentacao_vila_fatima.html'
    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"[SUCESSO] Apresentação interativa bilíngue criada em '{output_html_path}'")

if __name__ == '__main__':
    main()
