import os
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Bibliotecas do ReportLab para geração de PDF
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# =========================================================================
# GERAÇÃO DOS GRÁFICOS COMPLEMENTARES CENSO 2022
# =========================================================================
def generate_census_charts():
    output_dir = 'graficos_analise'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 1. Pirâmide Etária
    categories_pyr = ['0-4 Anos/Y', '5-9 Anos/Y', '10-14 Anos/Y', '15-19 Anos/Y', '20-24 Anos/Y', 
                      '25-29 Anos/Y', '30-39 Anos/Y', '40-49 Anos/Y', '50-59 Anos/Y', '60-69 Anos/Y', '70+ Anos/Y']
    male_values = [303, 380, 280, 280, 380, 290, 500, 460, 330, 230, 150]
    female_values = [275, 330, 335, 310, 380, 350, 606, 510, 420, 340, 260]

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.barh(categories_pyr, [-val for val in male_values], color='#5DADE2', label='Masculino / Male')
    ax.barh(categories_pyr, female_values, color='#F1948A', label='Feminino / Female')
    ax.set_xticks([-600, -300, 0, 300, 600])
    ax.set_xticklabels(['600', '300', '0', '300', '600'])
    ax.axvline(0, color='#2C3E50', linewidth=0.8, linestyle='-')
    ax.set_title('Pirâmide Etária / Population Pyramid (Censo 2022)', fontsize=11, fontweight='bold', pad=10)
    ax.legend(loc='lower right', frameon=True, fontsize=8)
    ax.xaxis.grid(True, linestyle='--', alpha=0.5)
    ax.yaxis.grid(False)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'pyramid_census.png'), dpi=300, bbox_inches='tight')
    plt.close()

    # 2. Raça/Cor
    raca_labels = ['Branca\nWhite', 'Preta\nBlack', 'Parda\nMixed', 'Amarela\nAsian', 'Indígena\nIndig.']
    male_pct = [42.47, 31.84, 25.68, 0.00, 0.00]
    female_pct = [43.01, 33.43, 23.32, 0.00, 0.00]

    x = np.arange(len(raca_labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(6, 4.2))
    ax.bar(x - width/2, male_pct, width, label='Masculino / Male', color='#5DADE2')
    ax.bar(x + width/2, female_pct, width, label='Feminino / Female', color='#F1948A')
    ax.set_xticks(x)
    ax.set_xticklabels(raca_labels, fontsize=9)
    ax.set_ylabel('Proporção / Proportion (%)')
    ax.set_title('Autodeclaração Raça/Cor / Race & Color (%)', fontsize=11, fontweight='bold', pad=10)
    ax.legend(loc='upper right', frameon=True, fontsize=8)
    ax.xaxis.grid(False)
    ax.yaxis.grid(True, linestyle='--', alpha=0.5)
    ax.set_ylim(0, 50)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'raca_census.png'), dpi=300, bbox_inches='tight')
    plt.close()


# =========================================================================
# CLASSE DE CANVAS PERSONALIZADA PARA SLIDES HORIZONTAIS
# =========================================================================
class SlideCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = []
        
    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()
        
    def save(self):
        num_pages = len(self.pages)
        for page in self.pages:
            self.__dict__.update(page)
            self.draw_slide_decorations(num_pages)
            super().showPage()
        super().save()
        
    def draw_slide_decorations(self, total_pages):
        self.saveState()
        
        # Cor institucional PUCRS: Azul #00508B, Dourado #EBB700
        pucrs_blue = colors.HexColor('#00508B')
        pucrs_gold = colors.HexColor('#EBB700')
        
        # Ignora decorações no slide de capa (página 1)
        if self._pageNumber > 1:
            # 1. Barra de Cabeçalho (Header Strip)
            self.setFillColor(pucrs_blue)
            self.rect(0, 555, 842.27, 40, fill=True, stroke=False)
            
            # Detalhe dourado abaixo do cabeçalho
            self.setFillColor(pucrs_gold)
            self.rect(0, 552, 842.27, 3, fill=True, stroke=False)
            
            # Texto do Cabeçalho
            self.setFillColor(colors.white)
            self.setFont("Helvetica-Bold", 12)
            self.drawString(30, 569, "UNIDADE DE SAÚDE VILA FÁTIMA  •  APS PUCRS / SMS")
            
            # 2. Rodapé (Footer)
            self.setStrokeColor(colors.HexColor('#BDC3C7'))
            self.setLineWidth(0.5)
            self.line(30, 40, 812.27, 40)
            
            self.setFillColor(colors.HexColor('#7F8C8D'))
            self.setFont("Helvetica", 8)
            self.drawString(30, 25, "Escola de Medicina PUCRS • Porto Alegre, RS, Brasil • Relatório e Perfil Demográfico")
            
            # Número da Página
            page_str = f"Slide {self._pageNumber} / {total_pages}"
            self.drawRightString(812.27, 25, page_str)
            
        self.restoreState()


# =========================================================================
# CONTRUÇÃO DO DOCUMENTO PDF (16:9)
# =========================================================================
def build_pdf(filename, lang='pt'):
    # Tamanho A4 Landscape: 842.27 x 595.27 pontos
    doc = SimpleDocTemplate(
        filename,
        pagesize=landscape(A4),
        leftMargin=30,
        rightMargin=30,
        topMargin=65,    # margem folgada por causa do header
        bottomMargin=55  # margem folgada por causa do rodapé
    )
    
    styles = getSampleStyleSheet()
    
    # Cores de texto
    text_color = colors.HexColor('#2C3E50')
    pucrs_blue = colors.HexColor('#00508B')
    
    # Estilos customizados
    title_style = ParagraphStyle(
        'SlideTitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=pucrs_blue,
        spaceAfter=15,
        spaceBefore=0
    )
    
    bullet_style = ParagraphStyle(
        'SlideBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        textColor=text_color,
        leading=16,
        leftIndent=15,
        firstLineIndent=-12,
        spaceAfter=8
    )
    
    story = []
    
    # Textos traduzíveis
    texts = {
        'pt': {
            'cover_title': "Unidade de Saúde Vila Fátima",
            'cover_sub': "Perfil Operacional e Demográfico do Território\n(Dados do Censo 2022 e Atendimentos 2025-2026)",
            'cover_audience': "Público-alvo: Visitantes e Professores Estrangeiros",
            'cover_inst': "Escola de Medicina PUCRS • Porto Alegre, RS",
            's1_title': "1. Contexto Territorial e Socioeconômico",
            's1_b1': "• <b>População Residente:</b> O território do censo compreende <b>4.891 moradores</b>.",
            's1_b2': "• <b>Vulnerabilidade Social:</b> A área de comunidades urbanas / favela representa <b>69,18%</b> da extensão territorial total (0,5135 km²).",
            's1_b3': "• <b>Perfil de Renda Familiar:</b> A renda mediana mensal é de <b>R$ 1.212,00</b> (exatamente 1 salário mínimo da época do censo), indicando que 50% dos chefes de família vivem sob renda de subsistência.",
            's1_b4': "• <b>Dispersão e Média:</b> A renda média familiar mensal é de <b>R$ 1.721,14</b> com desvio padrão de R$ 378,07, refletindo homogeneidade na baixa renda local.",
            's2_title': "2. Pirâmide Etária Residente (Censo 2022)",
            's2_b1': "• <b>Base Jovem Robusta:</b> Grande contingente de crianças e jovens de 0 a 24 anos, demandando acompanhamento constante de pediatria, puericultura e saúde nas escolas.",
            's2_b2': "• <b>Faixa Adulta Ativa:</b> Expressivo grupo de adultos na faixa produtiva de 30 a 49 anos.",
            's2_b3': "• <b>Transição Geriátrica:</b> Faixa de idosos (60+) relevante, exigindo atenção focada em agravos crônicos de saúde.",
            's3_title': "3. Composição de Raça e Cor no Território",
            's3_b1': "• <b>População Autodeclarada:</b> A comunidade é caracterizada por expressiva diversidade étnico-racial.",
            's3_b2': "• <b>Brancos e Pretos/Pardos:</b> Cerca de <b>43%</b> autodeclaram-se brancos, enquanto mais de <b>55%</b> identificam-se como pretos ou pardos (negros).",
            's3_b3': "• <b>Diferencial Municipal:</b> A proporção de população negra na Vila Fátima supera significativamente a média geral do município de Porto Alegre.",
            's4_title': "4. Indicadores de Atendimento e Alcance (2025-2026)",
            's4_b1': "• <b>Acompanhamento Contínuo:</b> Alta consistência no volume mensal de consultas.",
            's4_b2': "• <b>Cobertura e Vínculo:</b> O gráfico de Atendimentos vs. Pacientes Únicos demonstra a relação de vínculo: os mesmos pacientes são atendidos múltiplas vezes no ano.",
            's4_b3': "• <b>Continuidade do Cuidado:</b> Essencial para a efetividade de programas de saúde da família e controle epidemiológico.",
            's5_title': "5. Equipe Multidisciplinar e Áreas de Atuação",
            's5_b1': "• <b>Top Profissionais:</b> Gráfico demonstra o volume acumulado de consultas por profissionais da unidade (Top 15).",
            's5_b2': "• <b>Equipe de Saúde da Família (ESF):</b> Atuação integrada de médicos, enfermeiros, cirurgiões-dentistas e técnicos.",
            's5_b3': "• <b>Enfermagem Protagonista:</b> Alta participação de enfermeiros e técnicos no acolhimento, imunização e consultas preventivas.",
            's6_title': "6. Evolução Proporcional dos Atendimentos por Faixa Etária",
            's6_b1': "• <b>Perfil de Demanda:</b> Distribuição proporcional estável dos atendimentos de 2025 ao início de 2026.",
            's6_b2': "• <b>Adultos e Idosos na Frente:</b> As consultas de adultos (30-59 anos) e idosos (60+) lideram o volume mensal.",
            's6_b3': "• <b>Estabilidade:</b> A consistência percentual reflete a rotina organizada de agendamentos e acompanhamento de saúde da unidade.",
            's7_title': "7. Frequência Média de Consultas por Faixa Etária",
            's7_b1': "• <b>Taxa de Retorno:</b> Avaliação de quantas vezes um paciente único retorna ao serviço no período.",
            's7_b2': "• <b>Cuidado Geriátrico Intenso:</b> Idosos (60+) possuem a maior taxa de retorno geral, com média elevada de reconsultas.",
            's7_b3': "• <b>Vínculo Infantil:</b> Crianças (0-14) também mantêm visitas recorrentes, associadas a consultas de puericultura e vacinação.",
            's8_title': "8. Perfil e Intensidade da Atenção Geriátrica (60+)",
            's8_b1': "• <b>Estrutura do Grupo:</b> O grupo de 60-70 anos constitui a maior fatia dos idosos atendidos na unidade.",
            's8_b2': "• <b>Fator da Idade Avançada:</b> A frequência de visitas aumenta substancialmente nos idosos mais velhos. O grupo de 81-90 anos registra média recorde de <b>17,42 visitas por paciente</b>.",
            's8_b3': "• <b>Complexidade Clínica:</b> Pacientes muito idosos exigem retornos frequentes para controle polifarmácia e comorbidades.",
            's9_title': "9. Conclusões e Impacto Institucional",
            's9_b1': "• <b>Integração Ensino-Serviço:</b> A cooperação entre a Escola de Medicina da PUCRS e a SMS Porto Alegre qualifica a assistência local, servindo de campo de ensino de excelência.",
            's9_b2': "• <b>Vínculo e Resolutividade:</b> As altas taxas de retorno demonstram sucesso no acompanhamento longitudinal, vital para a Atenção Primária.",
            's9_b3': "• <b>Vulnerabilidade Territorial:</b> O modelo de saúde atende de forma coordenada e eficaz uma população de elevada vulnerabilidade social.",
            's9_b4': "• <b>Decisões Baseadas em Dados:</b> O monitoramento dinâmico otimiza a alocação de recursos médicos e de enfermagem no território."
        },
        'en': {
            'cover_title': "Vila Fátima Primary Health Unit",
            'cover_sub': "Territorial Operational & Demographic Profile\n(Census 2022 & 2025-2026 Consultation Data)",
            'cover_audience': "Target Audience: Academic Visitors & International Professors",
            'cover_inst': "PUCRS School of Medicine • Porto Alegre, Brazil",
            's1_title': "1. Territorial & Socioeconomic Context",
            's1_b1': "• <b>Resident Population:</b> The census sector covers a total of <b>4,891 residents</b>.",
            's1_b2': "• <b>Social Vulnerability:</b> Informal urban community sectors (Favelas) represent <b>69.18%</b> of the total territorial area (0.5135 km²).",
            's1_b3': "• <b>Household Income Profile:</b> The median monthly income is <b>R$ 1,212.00</b> (1 minimum wage in 2022), showing that 50% of families live on subsistence thresholds.",
            's1_b4': "• <b>Income Distribution:</b> The average monthly family income is <b>R$ 1,721.14</b> with a low standard deviation of R$ 378.07, demonstrating generalized low-income status.",
            's2_title': "2. Resident Population Structure (Census 2022)",
            's2_b1': "• <b>Broad Base:</b> Significant proportion of children and youth (0-24 years), demanding constant pediatric and family monitoring.",
            's2_b2': "• <b>Active Adults:</b> Robust concentration of working-age adults between 30 and 49 years.",
            's2_b3': "• <b>Geriatric Transition:</b> Emerging elderly cohorts (60+) highlight the rising demand for chronic disease management.",
            's3_title': "3. Racial & Ethnic Composition of the Territory",
            's3_b1': "• <b>Self-Declared Identity:</b> The community exhibits high ethnic-racial diversity.",
            's3_b2': "• <b>Demographic Breakdowns:</b> White residents account for approximately <b>43%</b>, while Black & Pardo (Mixed) residents total over <b>55%</b>.",
            's3_b3': "• <b>Comparison:</b> The proportion of self-declared Black and Mixed residents is significantly higher than Porto Alegre's municipal average.",
            's4_title': "4. Healthcare Operational Metrics (2025-2026)",
            's4_b1': "• <b>Consultation Flow:</b> Excellent operational stability in monthly consultation volume.",
            's4_b2': "• <b>Reach vs. Retention:</b> Total consultations versus unique patients reveal strong patient bonding, with patients returning for continuous monitoring.",
            's4_b3': "• <b>Continuity of Care:</b> Vital for effective chronic disease prevention and community health strategy.",
            's5_title': "5. Multidisciplinary Team & Consultations Volume",
            's5_b1': "• <b>Top Professionals:</b> Visualizes the cumulative consultation volume by professional name (Top 15).",
            's5_b2': "• <b>ESF Team Integration:</b> Combined efforts of physicians, nurses, dentists, and technical staff.",
            's5_b3': "• <b>Active Nursing Role:</b> Highlights the central role of nurses and techs in patient reception, pre-natal care, and immunization.",
            's6_title': "6. Proportional Consultations by Age Group",
            's6_b1': "• <b>Demographic Demands:</b> Shows stable proportional distribution of consultations by age group from 2025 to 2026.",
            's6_b2': "• <b>Adults and Elderly First:</b> Adult (30-59) and elderly (60+) consultation volumes lead the monthly share.",
            's6_b3': "• <b>Stability:</b> Consistency indicates organized programmatic care and stable community demand.",
            's7_title': "7. Average Visit Frequency by Age Group",
            's7_b1': "• <b>Return Rate:</b> Indicates how many times a unique patient visits the health unit in the period.",
            's7_b2': "• <b>Geriatric Care Demands:</b> Elderly patients (60+) show the highest return rate, highlighting complex geriatric care needs.",
            's7_b3': "• <b>Pediatric bonding:</b> Children (0-14) maintain solid returns, linked to developmental monitoring and vaccinations.",
            's8_title': "8. Elderly Cohorts Distribution and Return Rates (60+)",
            's8_b1': "• <b>Geriatric Makeup:</b> The 60-70 cohort represents the largest absolute share of elderly visits.",
            's8_b2': "• <b>Advanced Age Intensity:</b> Visit frequency rises sharply with age. The 81-90 cohort registers a record average of <b>17.42 visits</b> per patient.",
            's8_b3': "• <b>Clinical Complexity:</b> Frail elderly patients require frequent visits for multi-morbidity and polypharmacy control.",
            's9_title': "9. Strategic & Institutional Conclusions",
            's9_b1': "• <b>Education-Service Integration:</b> The partnership between PUCRS School of Medicine and SMS Porto Alegre elevates local clinical practice and serves as an academic center of excellence.",
            's9_b2': "• <b>Continuity of Care:</b> Excellent patient return rates show active longitudinal care, a pillar of Primary Health Care.",
            's9_b3': "• <b>Territorial Care Model:</b> The team coordinates highly effective care in a socially vulnerable neighborhood (69.18% urban communities).",
            's9_b4': "• <b>Data-Driven Health Management:</b> Continuous monitoring allows optimization of resource allocation on the field."
        }
    }

    t = texts[lang]
    
    # -----------------------------------------------------------------
    # SLIDE 1: COVER PAGE
    # -----------------------------------------------------------------
    # Layout centralizado
    cover_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=30,
        textColor=pucrs_blue,
        alignment=1, # Centralizado
        spaceAfter=15,
        leading=38
    )
    
    cover_sub_style = ParagraphStyle(
        'CoverSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=14,
        textColor=colors.HexColor('#7F8C8D'),
        alignment=1,
        spaceAfter=40,
        leading=20
    )
    
    cover_info_style = ParagraphStyle(
        'CoverInfo',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=11,
        textColor=colors.HexColor('#2C3E50'),
        alignment=1,
        spaceAfter=8
    )
    
    story.append(Spacer(1, 100))
    # Insere logo PUCRS se disponível localmente, senão apenas texto
    story.append(Paragraph(t['cover_title'].upper(), cover_style))
    story.append(Paragraph(t['cover_sub'], cover_sub_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph(t['cover_audience'], cover_info_style))
    story.append(Paragraph(t['cover_inst'], cover_info_style))
    story.append(PageBreak())
    
    # -----------------------------------------------------------------
    # SLIDE 2: TERRITORIAL CONTEXT (6 KPIs)
    # -----------------------------------------------------------------
    story.append(Paragraph(t['s1_title'], title_style))
    
    # Tabela de KPIs (2 linhas x 3 colunas)
    kpi_style_lbl = ParagraphStyle('KPILbl', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#7F8C8D'), alignment=1)
    kpi_style_val = ParagraphStyle('KPIVal', fontName='Helvetica-Bold', fontSize=22, textColor=colors.HexColor('#00508B'), alignment=1)
    
    kpi_labels = {
        'pt': [
            ["POPULAÇÃO RESIDENTE", "ÁREA TERRITORIAL", "FAVELA / COMUNIDADE"],
            ["4.891 Pessoas", "0,5135 km²", "69,18% da área"],
            ["RENDA FAMILIAR MÉDIA", "RENDA FAMILIAR MEDIANA", "DESVIO PADRÃO RENDA"],
            ["R$ 1.721,14", "R$ 1.212,00", "R$ 378,07"]
        ],
        'en': [
            ["RESIDENT POPULATION", "TERRITORIAL AREA", "INFORMAL COMMUNITY (FAVELA)"],
            ["4,891 Residents", "0.5135 km²", "69.18% of area"],
            ["MEAN MONTHLY INCOME", "MEDIAN MONTHLY INCOME", "INCOME STD. DEVIATION"],
            ["R$ 1,721.14", "R$ 1,212.00", "R$ 378.07"]
        ]
    }
    
    k_lbls_row1 = [Paragraph(kpi_labels[lang][0][i], kpi_style_lbl) for i in range(3)]
    k_vals_row1 = [Paragraph(kpi_labels[lang][1][i], kpi_style_val) for i in range(3)]
    k_lbls_row2 = [Paragraph(kpi_labels[lang][2][i], kpi_style_lbl) for i in range(3)]
    k_vals_row2 = [Paragraph(kpi_labels[lang][3][i], kpi_style_val) for i in range(3)]
    
    kpi_table_data = [
        k_lbls_row1,
        k_vals_row1,
        [Spacer(1, 15), Spacer(1, 15), Spacer(1, 15)],
        k_lbls_row2,
        k_vals_row2
    ]
    
    kpi_table = Table(kpi_table_data, colWidths=[250, 250, 250])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F9FA')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#ECF0F1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ECF0F1')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    story.append(kpi_table)
    story.append(Spacer(1, 20))
    story.append(Paragraph(t['s1_b1'], bullet_style))
    story.append(Paragraph(t['s1_b2'], bullet_style))
    story.append(Paragraph(t['s1_b3'], bullet_style))
    story.append(Paragraph(t['s1_b4'], bullet_style))
    story.append(PageBreak())
    
    # Funções auxiliares para slides de duas colunas (Texto na Esquerda, Gráfico na Direita)
    def make_two_col_slide(slide_title, bullet_texts, image_path, image_width=320, image_height=220):
        story.append(Paragraph(slide_title, title_style))
        
        # Coluna da esquerda (textos)
        left_flowables = []
        for txt in bullet_texts:
            left_flowables.append(Paragraph(txt, bullet_style))
            
        # Coluna da direita (imagem)
        right_flowables = []
        if os.path.exists(image_path):
            right_flowables.append(Image(image_path, width=image_width, height=image_height))
        else:
            right_flowables.append(Paragraph(f"<i>[Grafico indisponível: {image_path}]</i>", bullet_style))
            
        # Tabela de duas colunas
        two_col_table = Table([[left_flowables, right_flowables]], colWidths=[400, 360])
        two_col_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(two_col_table)
        story.append(PageBreak())

    # -----------------------------------------------------------------
    # SLIDE 3: CENSUS DEMOGRAPHIC PYRAMID
    # -----------------------------------------------------------------
    make_two_col_slide(
        t['s2_title'],
        [t['s2_b1'], t['s2_b2'], t['s2_b3']],
        'graficos_analise/pyramid_census.png',
        image_width=350, image_height=250
    )

    # -----------------------------------------------------------------
    # SLIDE 4: RACIAL COMPOSITION
    # -----------------------------------------------------------------
    make_two_col_slide(
        t['s3_title'],
        [t['s3_b1'], t['s3_b2'], t['s3_b3']],
        'graficos_analise/raca_census.png',
        image_width=350, image_height=250
    )

    # -----------------------------------------------------------------
    # SLIDE 5: OPERATIONAL REACH (ATENDIMENTOS VS UNICOS)
    # -----------------------------------------------------------------
    make_two_col_slide(
        t['s4_title'],
        [t['s4_b1'], t['s4_b2'], t['s4_b3']],
        'graficos_analise/4_pessoas_unicas_atendidas.png',
        image_width=350, image_height=210
    )

    # -----------------------------------------------------------------
    # SLIDE 6: TOP PROFESSIONALS VOLUME
    # -----------------------------------------------------------------
    make_two_col_slide(
        t['s5_title'],
        [t['s5_b1'], t['s5_b2'], t['s5_b3']],
        'graficos_analise/1_agrupamento_profissionais.png',
        image_width=340, image_height=240
    )

    # -----------------------------------------------------------------
    # SLIDE 7: MONTHLY AGE PROPORTION
    # -----------------------------------------------------------------
    make_two_col_slide(
        t['s6_title'],
        [t['s6_b1'], t['s6_b2'], t['s6_b3']],
        'graficos_analise/2_faixa_etaria_mensal_percentual.png',
        image_width=345, image_height=210
    )

    # -----------------------------------------------------------------
    # SLIDE 8: RETURN RATIO AGE GROUPS
    # -----------------------------------------------------------------
    make_two_col_slide(
        t['s7_title'],
        [t['s7_b1'], t['s7_b2'], t['s7_b3']],
        'graficos_analise/7_retorno_faixas_gerais.png',
        image_width=350, image_height=210
    )

    # -----------------------------------------------------------------
    # SLIDE 9: ELDERLY ATTENDANCE DONUT & RETORNO COHORTS
    # -----------------------------------------------------------------
    # Layout de 3 colunas (Texto na Esquerda, Donut no meio, Barra na Direita)
    story.append(Paragraph(t['s8_title'], title_style))
    
    left_flow = [Paragraph(t['s8_b1'], bullet_style), Paragraph(t['s8_b2'], bullet_style), Paragraph(t['s8_b3'], bullet_style)]
    
    mid_flow = []
    if os.path.exists('graficos_analise/5_distribuicao_idosos_geral.png'):
        mid_flow.append(Image('graficos_analise/5_distribuicao_idosos_geral.png', width=195, height=195))
        
    right_flow = []
    if os.path.exists('graficos_analise/8_retorno_faixas_idosos.png'):
        right_flow.append(Image('graficos_analise/8_retorno_faixas_idosos.png', width=240, height=155))
        
    three_col_table = Table([[left_flow, mid_flow, right_flow]], colWidths=[330, 205, 245])
    three_col_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(three_col_table)
    story.append(PageBreak())

    # -----------------------------------------------------------------
    # SLIDE 10: CONCLUSIONS
    # -----------------------------------------------------------------
    story.append(Paragraph(t['s9_title'], title_style))
    story.append(Paragraph(t['s9_b1'], bullet_style))
    story.append(Paragraph(t['s9_b2'], bullet_style))
    story.append(Paragraph(t['s9_b3'], bullet_style))
    story.append(Paragraph(t['s9_b4'], bullet_style))
    
    # Constrói o documento com o canvas de dois passos
    doc.build(story, canvasmaker=SlideCanvas)
    print(f"PDF Slide deck gerado com sucesso em '{filename}'")

def main():
    print("Gerando gráficos auxiliares...")
    generate_census_charts()
    
    print("Gerando PDFs das apresentações...")
    build_pdf('apresentacao_vila_fatima_pt.pdf', 'pt')
    build_pdf('apresentacao_vila_fatima_en.pdf', 'en')

if __name__ == '__main__':
    main()
