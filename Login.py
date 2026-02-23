import streamlit as st
import hashlib, sqlite3

def criar_tabela_usuarios():
    conn = sqlite3.connect("data/dfc.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE,
            senha TEXT,
            permissao TEXT
        )
    """)
    conn.commit()

    # Criar super admin se não existir
    cur.execute("SELECT * FROM usuarios WHERE login = ?", ("AVANDO",))
    if not cur.fetchone():
        senha_hash = hashlib.sha256("Ubewd.4500".encode()).hexdigest()
        cur.execute("INSERT INTO usuarios (login, senha, permissao) VALUES (?, ?, ?)",
                    ("AVANDO", senha_hash, "super_admin"))
        conn.commit()
    conn.close()

def validar_login(login, senha):
    conn = sqlite3.connect("data/dfc.db")
    cur = conn.cursor()
    cur.execute("SELECT senha, permissao FROM usuarios WHERE login = ?", (login.upper(),))
    row = cur.fetchone()
    conn.close()
    if row:
        senha_hash, permissao = row
        if senha_hash == hashlib.sha256(senha.encode()).hexdigest():
            return True, permissao
    return False, None

def cadastrar_usuario(login, senha):
    conn = sqlite3.connect("data/dfc.db")
    cur = conn.cursor()
    try:
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        cur.execute("INSERT INTO usuarios (login, senha, permissao) VALUES (?, ?, ?)",
                    (login.upper(), senha_hash, "visitante"))
        conn.commit()
        st.success("Usuário cadastrado com sucesso! ✅")
    except sqlite3.IntegrityError:
        st.error("Esse login já existe!")
    finally:
        conn.close()

# Configuração da página de login
st.set_page_config(page_title="Login DFC", layout="centered")
st.title("🔑 Login no Sistema DFC")

criar_tabela_usuarios()

login = st.text_input("Usuário").upper()
senha = st.text_input("Senha", type="password")

if st.button("Entrar"):
    valido, permissao = validar_login(login, senha)
    if valido:
        st.session_state["usuario"] = login
        st.session_state["permissao"] = permissao
        st.session_state["logado"] = True
        st.success("Login realizado com sucesso! Redirecionando...")
        
        # 🚀 Redireciona para dfc_it.py dentro da pasta pages
        st.switch_page("pages/Sistema de Fluxo de Caixa Interativo.py")
    else:
        st.error("Usuário ou senha inválidos!")

# 🔹 Formulário para cadastrar novos usuários
if acao == "Cadastrar novo usuário":
    novo_login = st.text_input("Novo Usuário").upper()
    nova_senha = st.text_input("Nova Senha", type="password")

    if st.button("Cadastrar"):
        if novo_login and nova_senha:
            cadastrar_usuario(novo_login, nova_senha)
        else:
            st.warning("Preencha usuário e senha para cadastrar!")



