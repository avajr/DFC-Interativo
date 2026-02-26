import psycopg2
import streamlit as st
import pandas as pd

# ------------------------------------------------------------
# 🔹 Conexão com Supabase/Postgres
# ------------------------------------------------------------
def conectar():
    return psycopg2.connect(
        host=st.secrets["PGHOST"],
        port=st.secrets["PGPORT"],
        dbname=st.secrets["PGDATABASE"],
        user=st.secrets["PGUSER"],
        password=st.secrets["PGPASSWORD"]
    )

# ------------------------------------------------------------
# 🔹 Função genérica para executar queries
# ------------------------------------------------------------
def executar_query(query, params=None, fetch=False):
    conn = conectar()
    cur = conn.cursor()
    cur.execute(query, params or ())
    result = None
    if fetch:
        try:
            result = cur.fetchall()
        except psycopg2.ProgrammingError:
            result = None
    conn.commit()
    cur.close()
    conn.close()
    return result

# ------------------------------------------------------------
# 🔹 Criar tabelas no banco Supabase
# ------------------------------------------------------------
def criar_tabelas():
    conn = conectar()
    cur = conn.cursor()

    # Tabela de lançamentos
DROP TABLE IF EXISTS lancamentos;
CREATE TABLE lancamentos (
    id SERIAL PRIMARY KEY,
    data DATE,
    valor NUMERIC(12,2),
    banco TEXT,
    historico TEXT,
    conta_registro TEXT,
    arquivo_origem TEXT,
    UNIQUE (data, valor, historico)
);

    # Tabela de contas contábeis
    cur.execute("""
        CREATE TABLE IF NOT EXISTS contas (
            mestre TEXT,
            subchave TEXT,
            registro TEXT,
            nome_mestre TEXT,
            nome_subchave TEXT,
            nome_registro TEXT,
            PRIMARY KEY (mestre, subchave, registro)
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

# ------------------------------------------------------------
# 🔹 Importar contas de um Excel para Supabase
# ------------------------------------------------------------
def importar_contas_excel(arquivo):
    conn = conectar()
    df = pd.read_excel(arquivo)
    df = df.rename(columns={
        "MESTRE": "mestre",
        "NOME MESTRE": "nome_mestre",
        "SUBCHAVE": "subchave",
        "NOME SUBCHAVE": "nome_subchave",
        "REGISTRO": "registro",
        "NOME REGISTRO": "nome_registro"
    })

    cur = conn.cursor()
    for _, row in df.iterrows():
        cur.execute("""
            INSERT INTO contas (mestre, nome_mestre, subchave, nome_subchave, registro, nome_registro)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (mestre, subchave, registro)
            DO UPDATE SET
                nome_mestre = EXCLUDED.nome_mestre,
                nome_subchave = EXCLUDED.nome_subchave,
                nome_registro = EXCLUDED.nome_registro
        """, (
            str(row["mestre"]),
            str(row["nome_mestre"]),
            str(row["subchave"]),
            str(row["nome_subchave"]),
            str(row["registro"]),
            str(row["nome_registro"])
        ))

    conn.commit()
    cur.close()
    conn.close()

# ------------------------------------------------------------
# 🔹 Atualizar lançamentos (classificação)
# ------------------------------------------------------------
def atualizar_lancamentos(id_lancamentos, registro):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE lancamentos
        SET conta_registro = %s
        WHERE id = %s
    """, (registro, id_lancamentos))
    conn.commit()
    cursor.close()
    conn.close()

