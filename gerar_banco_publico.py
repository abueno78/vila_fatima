"""
gerar_banco_publico.py
======================
Script de ETL para geração do banco de dados público higienizado.

Transformações aplicadas:
    1. Filtra APENAS registros com year IN (2025, 2026) da tabela
       atendimentos_padronizados.
    2. Anonimiza a coluna 'nome_completo' com tokens sequenciais únicos
       (ex: PAC_000001), preservando a cardinalidade (mesma pessoa sempre
       recebe o mesmo token → nunique() e taxas de retorno continuam válidos).
    3. Remove tabelas com dados pessoais sensíveis (conteudo, atendimentos
       brutos, saude_idoso, cidadaos_vinculados).
    4. Mantém a tabela classificacao_profissionais intacta (sem dados pessoais).
    5. Comprime o resultado em coleta_esus.db.gz via gzip.

Uso:
    python gerar_banco_publico.py

Saída:
    coleta_esus.db.gz  (sobrescreve o arquivo existente)
"""

import os
import re
import gzip
import shutil
import sqlite3
import tempfile
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_ORIGEM = os.path.join(BASE_DIR, 'coleta_esus.db')
DB_PUBLICO_TEMP = os.path.join(BASE_DIR, 'coleta_esus_publico.db')
GZ_DESTINO = os.path.join(BASE_DIR, 'coleta_esus.db.gz')
ANOS_PUBLICOS = (2025, 2026)


def parse_year(data_hora_str: str) -> int | None:
    """Extrai o ano de uma string no formato 'DD/MM/YYYY - HH:MM'."""
    if not data_hora_str:
        return None
    m = re.search(r'(\d{2})/(\d{2})/(\d{4})', data_hora_str)
    if m:
        return int(m.group(3))
    return None


def gerar_banco_higienizado():
    # ── Validação ──────────────────────────────
    if not os.path.exists(DB_ORIGEM):
        raise FileNotFoundError(
            f"Banco de origem não encontrado: {DB_ORIGEM}\n"
            "Execute o script a partir do diretório do projeto."
        )

    if os.path.exists(DB_PUBLICO_TEMP):
        os.remove(DB_PUBLICO_TEMP)

    print(f"[ETL] Conectando ao banco de origem: {DB_ORIGEM}")
    conn_origem = sqlite3.connect(DB_ORIGEM)
    conn_origem.row_factory = sqlite3.Row

    # ── Leitura e filtro dos atendimentos ──────
    print(f"[ETL] Carregando atendimentos de {ANOS_PUBLICOS}...")
    cur_origem = conn_origem.cursor()
    cur_origem.execute("""
        SELECT id, atendimento_original_id, data_hora, status_atendimento,
               nome_completo, idade, tudo_feito_unidade, profissional_atendimento
        FROM atendimentos_padronizados
    """)
    todas_linhas = cur_origem.fetchall()

    # Filtra pelo ano extraído do campo data_hora
    linhas_filtradas = [
        row for row in todas_linhas
        if parse_year(row['data_hora']) in ANOS_PUBLICOS
    ]

    print(f"[ETL] Total no banco de origem: {len(todas_linhas):,}")
    print(f"[ETL] Registros de {ANOS_PUBLICOS}: {len(linhas_filtradas):,}")

    # ── Anonimização (preservando cardinalidade) ─
    print("[ETL] Anonimizando pacientes (tokens PAC_XXXXXX)...")
    mapa_pacientes: dict[str, str] = {}
    contador = 1

    for row in linhas_filtradas:
        chave = str(row['nome_completo']).upper().strip() if row['nome_completo'] else ''
        if chave and chave not in mapa_pacientes:
            mapa_pacientes[chave] = f"PAC_{contador:06d}"
            contador += 1

    print(f"[ETL] Pacientes únicos identificados: {len(mapa_pacientes):,}")

    # ── Leitura da tabela de profissionais ─────
    cur_origem.execute(
        "SELECT nome_profissional, area_profissional, area_geral "
        "FROM classificacao_profissionais"
    )
    profissionais = cur_origem.fetchall()
    conn_origem.close()

    # ── Construção do banco público ────────────
    print(f"[ETL] Criando banco público em: {DB_PUBLICO_TEMP}")
    conn_pub = sqlite3.connect(DB_PUBLICO_TEMP)
    cur_pub = conn_pub.cursor()

    # Tabela principal (anonimizada)
    cur_pub.execute("""
        CREATE TABLE atendimentos_padronizados (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            atendimento_original_id INTEGER,
            data_hora               TEXT,
            status_atendimento      TEXT,
            nome_completo           TEXT,   -- token PAC_XXXXXX (anonimizado)
            idade                   TEXT,
            tudo_feito_unidade      TEXT,
            profissional_atendimento TEXT
        )
    """)

    # Insere linhas anonimizadas
    registros_pub = []
    for row in linhas_filtradas:
        chave = str(row['nome_completo']).upper().strip() if row['nome_completo'] else ''
        token = mapa_pacientes.get(chave, 'PAC_ANONIMO')
        registros_pub.append((
            row['atendimento_original_id'],
            row['data_hora'],
            row['status_atendimento'],
            token,
            row['idade'],
            row['tudo_feito_unidade'],
            row['profissional_atendimento'],
        ))

    cur_pub.executemany("""
        INSERT INTO atendimentos_padronizados
            (atendimento_original_id, data_hora, status_atendimento, nome_completo,
             idade, tudo_feito_unidade, profissional_atendimento)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, registros_pub)

    # Tabela de profissionais (sem dados pessoais)
    cur_pub.execute("""
        CREATE TABLE classificacao_profissionais (
            nome_profissional TEXT PRIMARY KEY,
            area_profissional TEXT,
            area_geral        TEXT
        )
    """)
    cur_pub.executemany(
        "INSERT INTO classificacao_profissionais VALUES (?, ?, ?)",
        [(r['nome_profissional'], r['area_profissional'], r['area_geral'])
         for r in profissionais]
    )

    conn_pub.commit()

    # ── Verificação pós-inserção ───────────────
    cur_pub.execute("SELECT COUNT(*) FROM atendimentos_padronizados")
    total_pub = cur_pub.fetchone()[0]
    cur_pub.execute("SELECT COUNT(DISTINCT nome_completo) FROM atendimentos_padronizados")
    unicos_pub = cur_pub.fetchone()[0]
    cur_pub.execute("SELECT COUNT(*) FROM classificacao_profissionais")
    total_prof = cur_pub.fetchone()[0]

    conn_pub.close()

    print(f"[ETL] Banco público criado com sucesso:")
    print(f"      - Atendimentos: {total_pub:,}")
    print(f"      - Pacientes únicos anonimizados: {unicos_pub:,}")
    print(f"      - Profissionais na tabela de classificação: {total_prof}")

    # ── Compressão ─────────────────────────────
    print(f"[ETL] Comprimindo para: {GZ_DESTINO}")
    with open(DB_PUBLICO_TEMP, 'rb') as f_in:
        with gzip.open(GZ_DESTINO, 'wb', compresslevel=9) as f_out:
            shutil.copyfileobj(f_in, f_out)

    # Remove o arquivo temporário descomprimido
    os.remove(DB_PUBLICO_TEMP)

    # Tamanhos para conferência
    gz_size_mb = os.path.getsize(GZ_DESTINO) / (1024 * 1024)
    print(f"[ETL] Arquivo gerado: {GZ_DESTINO} ({gz_size_mb:.1f} MB)")
    print("[ETL] ✅ ETL concluído com sucesso! Banco pronto para deploy público.")


if __name__ == '__main__':
    inicio = datetime.now()
    gerar_banco_higienizado()
    print(f"[ETL] Tempo total: {(datetime.now() - inicio).seconds}s")
