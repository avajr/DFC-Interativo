import psycopg2
import streamlit as st
import hashlib

def get_connection():
    conn = psycopg2.connect(
        host=st.secrets["PGHOST"],
        port=st.secrets["PGPORT"],
        dbname=st.secrets["PGDATABASE"],
        user=st.secrets["PGUSER"],
        password=st.secrets["PGPASSWORD"]
    )
    return conn

try:
    conn = get_connection()
    conn.close()
    st.success("✅ Conexão com Supabase funcionando!")
except Exception as e:
    st.error(f"Erro de conexão: {e}")

def criar_tabela_usuarios():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            login TEXT UNIQUE,
            senha TEXT,
            permissao TEXT
        )
    """)
    conn.commit()

    # Criar super admin se não existir
    cur.execute("SELECT * FROM usuarios WHERE login = %s", ("AVANDO",))
    if not cur.fetchone():
        senha_hash = hashlib.sha256("Ubewd.4500".encode()).hexdigest()
        cur.execute(
            "INSERT INTO usuarios (login, senha, permissao) VALUES (%s, %s, %s)",
            ("AVANDO", senha_hash, "super_admin")
        )
        conn.commit()
    conn.close()

def validar_login(login, senha):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT senha, permissao FROM usuarios WHERE login = %s", (login.upper(),))
    row = cur.fetchone()
    conn.close()
    if row:
        senha_hash, permissao = row
        if senha_hash == hashlib.sha256(senha.encode()).hexdigest():
            return True, permissao
    return False, None

def cadastrar_usuario(login, senha):
    conn = get_connection()
    cur = conn.cursor()
    try:
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        cur.execute(
            "INSERT INTO usuarios (login, senha, permissao) VALUES (%s, %s, %s)",
            (login.upper(), senha_hash, "visitante")
        )
        conn.commit()
        st.success("Usuário cadastrado com sucesso! ✅")
    except psycopg2.Error:
        st.error("Esse login já existe ou houve erro!")
    finally:
        conn.close()

# Configuração da página de login
st.set_page_config(page_title="Login DFC", layout="centered")
st.title("🔑 Login no Sistema DFC")

criar_tabela_usuarios()

# Selectbox para escolher ação
acao = st.selectbox("Selecione uma opção:", ["Login", "Cadastrar novo usuário"])

if acao == "Login":
    login = st.text_input("Usuário").upper()
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        valido, permissao = validar_login(login, senha)
        if valido:
            st.session_state["usuario"] = login
            st.session_state["permissao"] = permissao
            st.session_state["logado"] = True
            st.success("Login realizado com sucesso! Redirecionando...")
            # 🚀 Aqui você pode usar st.switch_page("sistema")
        else:
            st.error("Usuário ou senha inválidos!")

elif acao == "Cadastrar novo usuário":
    novo_login = st.text_input("Novo Usuário").upper()
    nova_senha = st.text_input("Nova Senha", type="password")

    if st.button("Cadastrar"):
        if novo_login and nova_senha:
            cadastrar_usuario(novo_login, nova_senha)
        else:
            st.warning("Preencha usuário e senha para cadastrar!")




