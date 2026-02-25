import psycopg2
import streamlit as st
import pandas as pd
from modules.database import executar_query

# Função de conexão com Supabase/Postgres
def conectar():
    conn = psycopg2.connect(
        host=st.secrets["PGHOST"],
        port=st.secrets["PGPORT"],
        dbname=st.secrets["PGDATABASE"],
        user=st.secrets["PGUSER"],
        password=st.secrets["PGPASSWORD"]
    )
    return conn

# Criar tabelas no banco Supabase
def criar_tabelas():
    conn = conectar()
    cur = conn.cursor()

    # Tabela de lançamentos
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lancamentos (
            id SERIAL PRIMARY KEY,
            data TEXT,
            valor REAL,
            banco TEXT,
            historico TEXT,
            conta_registro TEXT,
            arquivo_origem TEXT,
            fitid TEXT,
            checknum TEXT,
            assinatura TEXT,
            UNIQUE (fitid, checknum, banco, arquivo_origem),
            UNIQUE (assinatura, banco)
        )
    """)

    # Índices únicos (já garantidos pelos UNIQUE, mas deixei explícito)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_lanc_unico_fitid
        ON lancamentos (fitid, checknum, banco, arquivo_origem)
    """)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_lanc_unico_assinatura
        ON lancamentos (assinatura, banco)
    """)

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
    conn.close()

# Importar contas de um Excel para Supabase
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
    conn.close()

# Atualizar lançamentos
def atualizar_lancamentos(id_lancamentos, registro):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE lancamentos
        SET conta_registro = %s
        WHERE id = %s
    """, (registro, id_lancamentos))
    conn.commit()
    conn.close()

