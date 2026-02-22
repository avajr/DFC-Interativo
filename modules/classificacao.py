# ============================================================
# 📘 MÓDULO: CLASSIFICAÇÃO E IMPORTAÇÃO DE LANÇAMENTOS
# ------------------------------------------------------------
# Responsável por:
#   - Salvar lançamentos OFX no banco
#   - Evitar duplicidade
#   - Listar lançamentos importados
# ============================================================

import streamlit as st
import pandas as pd
from modules.database import conectar


# ============================================================
# 🔹 SALVAR LANÇAMENTOS NO BANCO (EVITANDO DUPLICIDADE)
# ============================================================

def salvar_lancamentos(lancamentos):
    conn = conectar()
    cur = conn.cursor()

    inseridos = 0
    ignorados = 0

    for lanc in lancamentos:
        try:
            cur.execute("""
                INSERT INTO lancamentos (
                    data, valor, banco, historico, conta_registro
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                str(pd.to_datetime(lanc["data"]).date()),
                float(lanc["valor"]),
                lanc["banco"],
                lanc["historico"],
                None    # conta_registro
            ))

            inseridos += 1

        except Exception as e:
            st.error(f"ERRO AO INSERIR: {e}")
            ignorados += 1

    conn.commit()
    conn.close()

    return inseridos, ignorados


# ============================================================
# 🔹 CARREGAR LANÇAMENTOS
# ============================================================

def carregar_lancamentos():
    conn = conectar()
    query = """
        SELECT 
            l.id,
            l.data,
            l.valor,
            l.historico,
            l.conta_registro,
            c.mestre || ' - ' || c.nome_mestre AS mestre_nome,
            c.subchave || ' - ' || c.nome_subchave AS subchave_nome,
            c.registro || ' - ' || c.nome_registro AS registro_nome
        FROM lancamentos l
        LEFT JOIN contas c
            ON l.conta_registro = c.registro
        ORDER BY l.data DESC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


# ============================================================
# 🔹 SALVAR CLASSIFICAÇÃO DE UM LANÇAMENTO
# ============================================================

def classificar_lancamento(id_lancamento, conta_registro):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        UPDATE lancamentos
        SET conta_registro = ?
        WHERE id = ?
    """, (conta_registro, id_lancamento))

    conn.commit()
    conn.close()
