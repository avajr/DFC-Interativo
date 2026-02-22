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
# ------------------------------------------------------------
# Função responsável por buscar todas as contas cadastradas
# no banco de dados, já ordenadas pela hierarquia.
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
# ------------------------------------------------------------
# Insere uma nova conta contábil na estrutura hierárquica.
# Parâmetros:
#   mestre        → nível 1  (ex: "1")
#   subchave      → nível 2  (ex: "1.0")
#   registro      → nível 3  (ex: "1.0.1")
#   nome_mestre   → nome do nível 1
#   nome_subchave → nome do nível 2
#   nome_registro → nome do nível 3
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
        VALUES (?, ?, ?, ?, ?, ?)
    """, (mestre, subchave, registro,
          nome_mestre, nome_subchave, nome_registro))

    conn.commit()
    conn.close()



# ============================================================
# 🔹 3. EDIÇÃO DE CONTA EXISTENTE
# ------------------------------------------------------------
# Permite alterar os nomes de uma conta já cadastrada.
# A estrutura (mestre, subchave, registro) NÃO deve ser alterada,
# pois ela é a chave primária da tabela.
# ============================================================

def editar_conta(mestre, subchave, registro,
                 nome_mestre, nome_subchave, nome_registro):

    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        UPDATE contas
        SET nome_mestre = ?,
            nome_subchave = ?,
            nome_registro = ?
        WHERE mestre = ?
          AND subchave = ?
          AND registro = ?
    """, (nome_mestre, nome_subchave, nome_registro,
          mestre, subchave, registro))

    conn.commit()
    conn.close()



# ============================================================
# 🔹 4. EXCLUSÃO DE CONTA
# ------------------------------------------------------------
# Remove uma conta contábil da estrutura.
# IMPORTANTE:
#   - Antes de excluir, o sistema deve verificar se existem
#     lançamentos OFX classificados nessa conta.
#   - Essa verificação será feita no módulo de classificação.
# ============================================================

def excluir_conta(mestre, subchave, registro):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM contas
        WHERE mestre = ?
          AND subchave = ?
          AND registro = ?
    """, (mestre, subchave, registro))

    conn.commit()
    conn.close()



# ============================================================
# 🔹 5. FUNÇÕES AUXILIARES (A SEREM IMPLEMENTADAS)
# ------------------------------------------------------------
# Aqui vamos adicionar futuramente:
#
#   ✔ validar_formato_mestre()
#   ✔ validar_formato_subchave()
#   ✔ validar_formato_registro()
#   ✔ gerar_proximo_codigo()
#   ✔ montar_hierarquia()
#
# Essas funções vão ajudar:
#   - a criar códigos automaticamente
#   - validar se o usuário digitou "1.0.1" corretamente
#   - montar a árvore hierárquica para exibir no Streamlit
# ============================================================

# Exemplo de placeholder:
def validar_codigo(codigo):
    # TODO: implementar validação de formato
    return True