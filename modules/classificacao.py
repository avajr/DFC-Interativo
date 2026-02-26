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
def salvar_lancamento(lanc):
    query = """
        INSERT INTO lancamentos (data, valor, historico, banco, arquivo_origem, fitid, checknum, assinatura)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (fitid, banco, arquivo_origem) DO NOTHING
    """
    executar_query(query, (
        str(lanc["data"]) if lanc["data"] else None,
        float(lanc["valor"]) if lanc["valor"] is not None else None,
        lanc["historico"],
        lanc["banco"],
        lanc["arquivo_origem"],
        lanc["fitid"],
        lanc["checknum"],
        lanc["assinatura"]
    ))

            if cur.rowcount > 0:
                inseridos += 1
            else:
                ignorados += 1

        except Exception as e:
            st.error(f"ERRO AO INSERIR: {e}")
            ignorados += 1

    conn.commit()
    cur.close()
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
        SET conta_registro = %s
        WHERE id = %s
    """, (conta_registro, id_lancamento))

    conn.commit()
    cur.close()
    conn.close()
