# ============================================================
# 📘 MÓDULO: CONTAS CONTÁBEIS
# ------------------------------------------------------------
# Responsável por:
#   - Criar, editar e excluir contas contábeis
#   - Carregar contas do banco de dados
#   - Garantir a estrutura hierárquica:
#         Mestre → Subchave → Registro
#   - Validar códigos e nomes
#   - Servir como base para classificação de lançamentos
# ============================================================

import pandas as pd
from modules.database import conectar

# ============================================================
# 🔹 1. CARREGAMENTO DAS CONTAS
# ============================================================

def carregar_contas():
    conn = conectar()
    df = pd.read_sql("""
        SELECT *
        FROM contas
        ORDER BY mestre, subchave, registro
    """, conn)
    conn.close()
    return df

# ============================================================
# 🔹 2. INSERÇÃO DE NOVA CONTA
# ============================================================

def inserir_conta(mestre, subchave, registro,
                  nome_mestre, nome_subchave, nome_registro):

    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO contas (
            mestre, subchave, registro,
            nome_mestre, nome_subchave, nome_registro
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (mestre, subchave, registro,
          nome_mestre, nome_subchave, nome_registro))

    conn.commit()
    cur.close()
    conn.close()

# ============================================================
# 🔹 3. EDIÇÃO DE CONTA EXISTENTE
# ============================================================

def editar_conta(mestre, subchave, registro,
                 nome_mestre, nome_subchave, nome_registro):

    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        UPDATE contas
        SET nome_mestre = %s,
            nome_subchave = %s,
            nome_registro = %s
        WHERE mestre = %s
          AND subchave = %s
          AND registro = %s
    """, (nome_mestre, nome_subchave, nome_registro,
          mestre, subchave, registro))

    conn.commit()
    cur.close()
    conn.close()

# ============================================================
# 🔹 4. EXCLUSÃO DE CONTA
# ============================================================

def excluir_conta(mestre, subchave, registro):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM contas
        WHERE mestre = %s
          AND subchave = %s
          AND registro = %s
    """, (mestre, subchave, registro))

    conn.commit()
    cur.close()
    conn.close()

# ============================================================
# 🔹 5. FUNÇÕES AUXILIARES
# ============================================================

def validar_codigo(codigo):
    # TODO: implementar validação de formato
    return True
