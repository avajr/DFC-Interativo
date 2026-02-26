# ============================================================
# 📘 SISTEMA DFC INTERATIVA — APLICATIVO PRINCIPAL
# ------------------------------------------------------------
# Este arquivo controla:
#   - Inicialização do sistema
#   - Carregamento das tabelas
#   - Interface de gerenciamento das contas contábeis
# ============================================================


import os
import pandas as pd
import streamlit as st
from io import BytesIO
import pandas as pd

from modules.database import importar_contas_excel, criar_tabelas
from modules.contas import (
    carregar_contas,
    inserir_conta,
    editar_conta,
    excluir_conta
)

from modules.classificacao import carregar_lancamentos

st.set_page_config(
    page_title="💰 Sistema",
    page_icon="💰",   # ícone do saco de dinheiro
    layout="wide"
)

# 🚨 Verifica login
if "logado" not in st.session_state or not st.session_state["logado"]:
    st.warning("⚠️ Você precisa fazer login primeiro na página inicial.")
    st.stop()

# Se chegou aqui, já está logado
permissao = st.session_state.get("permissao", "visualizador")

# ============================================================
# 🔹 Função utilitária para exportar DataFrame em Excel
# ============================================================
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Lançamentos")
    processed_data = output.getvalue()
    return processed_data

# ============================================================
# 🔹 CONFIGURAÇÃO INICIAL DO STREAMLIT
# ============================================================

st.set_page_config(page_title="DFC Interativa", layout="wide")
st.title("💰 Sistema de Fluxo de Caixa Interativo")

# Criar tabelas no banco (se não existirem)
criar_tabelas()

# Mensagem temporária moderna
st.toast("Sistema inicializado com sucesso!", icon="🎉")

# 🔥 Carregar contas ANTES de qualquer aba
if "contas_atualizadas" in st.session_state and st.session_state["contas_atualizadas"]:
    df_contas = carregar_contas()
    st.session_state["contas_atualizadas"] = False
else:
    df_contas = carregar_contas()


# ============================================================
# 🔹 ABAS DO SISTEMA
# ============================================================

if permissao in ["visualizador", "visitante"]:
    # Usuário só pode ver o Dashboard
    aba_dashboard, = st.tabs(["📊 Dashboard"])
    with aba_dashboard:
        st.subheader("📊 Dashboard Financeiro")

        # 🔹 Funções de formatação (válidas apenas dentro do Dashboard)
        def formatar_data(data):
            if pd.isnull(data):
                return ""
            return pd.to_datetime(data).strftime("%d/%m/%Y")

        def formatar_valor(valor):
            if valor is None:
                return "R$ 0,00"
            return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        def formatar_percentual(pct):
            if pct is None:
                return "0%"
            return f"{pct:.2f}%"

        # 🔹 Carregar lançamentos classificados
        df_lanc = carregar_lancamentos()
        df_contas = carregar_contas()

        # Juntar lançamentos com contas
        df_lanc = df_lanc.merge(df_contas, left_on="conta_registro", right_on="registro", how="left")

        # ============================================================
        # 🎛️ Filtros (na sidebar)
        # ============================================================
        st.sidebar.markdown("### 🎛️ Filtros")
        
        # Converter coluna para datetime, ignorando erros
        df_lanc["data"] = pd.to_datetime(df_lanc["data"], errors="coerce")
        
        # Remover valores nulos
        datas_validas = df_lanc["data"].dropna()
        
        # Definir valores padrão seguros
        if len(datas_validas) > 0:
            data_inicial_padrao = datas_validas.min().date()
            data_final_padrao = datas_validas.max().date()
        else:
            hoje = pd.Timestamp.today().date()
            data_inicial_padrao = hoje
            data_final_padrao = hoje
        
        # Usar no date_input
        data_inicio = st.sidebar.date_input("Data inicial", value=data_inicial_padrao)
        data_fim = st.sidebar.date_input("Data final", value=data_final_padrao)
        
        # Filtros de Mestre, Subchave e Registro
        mestres_opcoes = sorted(df_lanc["mestre"].dropna().unique(), key=lambda x: float(x))
        mestre_sel = st.sidebar.multiselect("Filtrar por Mestre", options=mestres_opcoes)
        
        subchaves_opcoes = sorted(df_lanc["subchave"].dropna().unique(), key=lambda x: float(x))
        subchave_sel = st.sidebar.multiselect("Filtrar por Subchave", options=subchaves_opcoes)
        
        registros_opcoes = sorted(df_lanc["registro"].dropna().unique(), key=lambda x: float(x.replace(".", "")))
        registro_sel = st.sidebar.multiselect("Filtrar por Registro", options=registros_opcoes)

        # ============================================================
        # 🔹 Aplicar filtros
        # ============================================================
        df_filtrado = df_lanc.copy()
        
        # Aqui você já converteu df_lanc["data"] para datetime com errors="coerce"
        # Então pode usar direto sem reconverter
        df_filtrado = df_filtrado[
            (df_filtrado["data"].dt.date >= data_inicio) &
            (df_filtrado["data"].dt.date <= data_fim)
        ]
        
        if mestre_sel:
            df_filtrado = df_filtrado[df_filtrado["mestre"].isin(mestre_sel)]
        if subchave_sel:
            df_filtrado = df_filtrado[df_filtrado["subchave"].isin(subchave_sel)]
        if registro_sel:
            df_filtrado = df_filtrado[df_filtrado["registro"].isin(registro_sel)]


        # ============================================================
        # 🔹 Drill-down e gráficos
        # ============================================================
        if df_filtrado.empty:
            st.info("Nenhum dado encontrado para os filtros selecionados.")
        else:
            mestres_ordenados = sorted(df_filtrado["mestre"].unique(), key=lambda x: float(x))

            for mestre in mestres_ordenados:
                df_mestre = df_filtrado[df_filtrado["mestre"] == mestre]
                if not df_mestre.empty:
                    nome_mestre = df_mestre["nome_mestre"].iloc[0]
                    soma_mestre = df_mestre["valor"].sum()
                else:
                    nome_mestre = "(sem nome)"
                    soma_mestre = 0

                with st.expander(f"{mestre} - {nome_mestre} | Total: {formatar_valor(soma_mestre)}"):
                    subchaves_ordenadas = sorted(df_mestre["subchave"].unique(), key=lambda x: float(x))
                    for subchave in subchaves_ordenadas:
                        df_sub = df_mestre[df_mestre["subchave"] == subchave]
                        if not df_sub.empty:
                            nome_sub = df_sub["nome_subchave"].iloc[0]
                            soma_sub = df_sub["valor"].sum()
                        else:
                            nome_sub = "(sem nome)"
                            soma_sub = 0

                        with st.expander(f"{subchave} - {nome_sub} | Total: {formatar_valor(soma_sub)}"):
                            registros_ordenados = sorted(df_sub["registro"].unique(), key=lambda x: float(x.replace(".", "")))
                            for registro in registros_ordenados:
                                df_reg = df_sub[df_sub["registro"] == registro]
                                if not df_reg.empty:
                                    nome_reg = df_reg["nome_registro"].iloc[0]
                                    soma_reg = df_reg["valor"].sum()
                                else:
                                    nome_reg = "(sem nome)"
                                    soma_reg = 0

                                with st.expander(f"{registro} - {nome_reg} | Total: {formatar_valor(soma_reg)}"):
                                    st.dataframe(
                                        df_reg[["data", "valor", "historico"]].assign(
                                            data=df_reg["data"].apply(formatar_data),
                                            valor=df_reg["valor"].apply(formatar_valor)
                                        ),
                                        use_container_width=True
                                    )
    
            # 📥 Botão geral para todos os lançamentos filtrados
            st.download_button(
                label="📥 Baixar todos os lançamentos filtrados",
                data=to_excel(df_filtrado),
                file_name="lancamentos_filtrados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
  
            total_geral = df_filtrado["valor"].sum()
            st.markdown(f"### 💰 Total Geral: {formatar_valor(total_geral)}")

            st.markdown("### 🥧 Distribuição por Grupo")
            df_pizza = df_filtrado.groupby(["mestre", "nome_mestre"])["valor"].sum().reset_index()
            df_pizza["valor"] = df_pizza["valor"].abs()
            df_pizza = df_pizza[df_pizza["mestre"] != "6"]

            import plotly.express as px
            fig = px.pie(
                df_pizza,
                names="nome_mestre",
                values="valor",
                title="Distribuição dos Valores por Grupo",
                hole=0.3
            )
            st.plotly_chart(fig, use_container_width=True)

else:
    # Usuário com permissão total vê todas as abas
    aba_contas, aba_importacao, aba_classificacao, aba_dashboard = st.tabs(
        ["📚 Contas", "📥 Importação", "🧾 Classificação", "📊 Dashboard"]
    )

    # ============================================================
    # 📚 GERENCIAMENTO DE CONTAS CONTÁBEIS
    # ============================================================
    with aba_contas:
        st.subheader("📚 Gerenciamento de Contas Contábeis")

        # Recarregar sempre que entrar na aba
        df_contas = carregar_contas()

        # ============================================================
        # 📥 IMPORTAR PLANO DE CONTAS VIA EXCEL
        # ============================================================
        st.markdown("### 📥 Importar plano de contas do Excel")

        arquivo = st.file_uploader("Selecione o arquivo Excel", type=["xlsx"], key="upload_excel")

        if arquivo is not None:
            importar_contas_excel(arquivo)
            st.success("Contas importadas com sucesso!")
            st.session_state["contas_atualizadas"] = True

        # ============================================================
        # ➕ FORMULÁRIO PARA CRIAR NOVA CONTA
        # ============================================================
        st.markdown("### ➕ Criar nova conta contábil")

        with st.form("form_criar_conta"):
            col1, col2, col3 = st.columns(3)

            mestre = col1.text_input("Código Mestre (ex: 1)")
            nome_mestre = col1.text_input("Nome do Mestre (ex: RECEITAS)")

            subchave = col2.text_input("Código Subchave (ex: 1.0)")
            nome_subchave = col2.text_input("Nome da Subchave (ex: RECEITA OPERACIONAL)")

            registro = col3.text_input("Código Registro (ex: 1.0.1)")
            nome_registro = col3.text_input("Nome do Registro (ex: VENDA DE MERCADORIAS)")

            submitted = st.form_submit_button("Salvar Conta")

            if submitted:
                if mestre and subchave and registro:
                    inserir_conta(
                        mestre, subchave, registro,
                        nome_mestre, nome_subchave, nome_registro
                    )
                    st.success("Conta criada com sucesso!")
                    st.rerun()
                else:
                    st.error("Preencha todos os códigos (mestre, subchave e registro).")

        # ============================================================
        # ✏️ EDIÇÃO DE CONTAS EM MATRIZ EDITÁVEL
        # ============================================================
        st.markdown("### ✏️ Editar Contas Contábeis")

        # Resetar índice para alinhar com editor
        df_contas = df_contas.reset_index(drop=True)

        # Adicionar coluna auxiliar para exclusão
        df_contas["excluir"] = False

        # 🔍 Filtros
        col1, col2, col3 = st.columns(3)

        filtro_mestre = col1.selectbox(
            "Filtrar por Mestre",
            options=["Todos"] + sorted(df_contas["mestre"].unique()),
            key="filtro_mestre"
        )

        filtro_subchave = col2.selectbox(
            "Filtrar por Subchave",
            options=["Todos"] + sorted(df_contas["subchave"].unique()),
            key="filtro_subchave"
        )

        filtro_registro = col3.selectbox(
            "Filtrar por Registro",
            options=["Todos"] + sorted(df_contas["registro"].unique()),
            key="filtro_registro"
        )

        # Aplicar filtros
        df_filtrado = df_contas.copy()
        if filtro_mestre != "Todos":
            df_filtrado = df_filtrado[df_filtrado["mestre"] == filtro_mestre]
        if filtro_subchave != "Todos":
            df_filtrado = df_filtrado[df_filtrado["subchave"] == filtro_subchave]
        if filtro_registro != "Todos":
            df_filtrado = df_filtrado[df_filtrado["registro"] == filtro_registro]

        # Matriz editável
        edited_df = st.data_editor(
            df_filtrado,
            num_rows="fixed",
            use_container_width=True,
            key="editor_contas",
            column_config={
                "mestre": st.column_config.TextColumn("Mestre", disabled=True),
                "subchave": st.column_config.TextColumn("Subchave", disabled=True),
                "registro": st.column_config.TextColumn("Registro", disabled=True),
                "nome_mestre": st.column_config.TextColumn("Nome Mestre"),
                "nome_subchave": st.column_config.TextColumn("Nome Subchave"),
                "nome_registro": st.column_config.TextColumn("Nome Registro"),
                "excluir": st.column_config.CheckboxColumn("Excluir"),
            }
        )

        # Botão para salvar alterações
        if st.button("💾 Salvar alterações nas contas", key="save_contas"):
            for _, row in edited_df.iterrows():
                editar_conta(
                    row["mestre"], row["subchave"], row["registro"],
                    row["nome_mestre"], row["nome_subchave"], row["nome_registro"]
                )
            st.toast("Conta(s) atualizada(s) com sucesso!✅")
            st.rerun()

        # Botão para excluir registros marcados
        if st.button("🗑️ Excluir contas selecionadas", key="delete_contas"):
            for _, row in edited_df.iterrows():
                if row["excluir"]:
                    excluir_conta(row["mestre"], row["subchave"], row["registro"])
            st.warning("Conta(s) excluída(s) com sucesso!")
            st.rerun()



        # ============================================================
        # 📂 EXIBIR ESTRUTURA HIERÁRQUICA DAS CONTAS
        # ============================================================
        st.markdown("### 📂 Estrutura de Contas Contábeis")

        if df_contas.empty:
            st.info("Nenhuma conta cadastrada ainda.")
        else:
            for mestre in df_contas["mestre"].unique():
                df_mestre = df_contas[df_contas["mestre"] == mestre]
                nome_mestre = df_mestre["nome_mestre"].iloc[0]

                st.markdown(f"## **{mestre} — {nome_mestre}**")

                for subchave in df_mestre["subchave"].unique():
                    df_sub = df_mestre[df_mestre["subchave"] == subchave]
                    nome_sub = df_sub["nome_subchave"].iloc[0]

                    st.markdown(f"### 🔸 {subchave} — {nome_sub}")

                    for _, row in df_sub.iterrows():
                        st.markdown(f"- **{row['registro']} — {row['nome_registro']}**")

        # ============================================================
        # 📥 IMPORTAÇÃO DE ARQUIVOS OFX
        # ============================================================
        with aba_importacao:
            st.subheader("📥 Importação de Arquivos OFX")
        
            from modules.ofx_reader import ler_ofx, importar_ofx
            from modules.classificacao import (
                salvar_lancamentos,
                carregar_lancamentos,
                classificar_lancamento
            )
        
            uploaded_file = st.file_uploader("Selecione um arquivo OFX", type=["ofx"], key="upload_ofx")
        
            if uploaded_file:
                lancamentos = ler_ofx(uploaded_file)
                st.session_state["lancamentos_ofx"] = lancamentos
        
                # 🚨 Verificação imediata logo após upload
                if len(lancamentos) == 0:
                    st.warning("Nenhum lançamento encontrado no arquivo.")
                else:
                    st.info(f"{len(lancamentos)} lançamentos encontrados no arquivo.")
        
                if st.button("Importar lançamentos"):
                    inseridos, ignorados = importar_ofx(uploaded_file)
                    if inseridos == 0 and ignorados > 0:
                        st.warning("Nenhum lançamento novo adicionado.")
                    else:
                        st.success(f"{inseridos} lançamentos importados. {ignorados} ignorados.")

    # ============================================================
    # 🧾 CLASSIFICAÇÃO DOS LANÇAMENTOS
    # ============================================================
    with aba_classificacao:
        st.subheader("🧾 Classificação dos Lançamentos")

        df_contas = carregar_contas()
        df_lanc = carregar_lancamentos()

        # ============================================================
        # 🔍 Lançamentos pendentes de classificação
        # ============================================================
        df_nao_classificados = df_lanc[df_lanc["conta_registro"].isna()]

        if df_nao_classificados.empty:
            st.info("Todos os lançamentos já foram classificados.")
        else:
            st.markdown("### 🔍 Lançamentos pendentes de classificação")

            for _, row in df_nao_classificados.iterrows():
                with st.expander(f"{row['data']} — R$ {row['valor']} — {row['historico']}"):
                    st.write("### Selecionar conta contábil")

                    opcoes = df_contas["registro"] + " - " + df_contas["nome_registro"]
                    reg_sel_formatado = st.selectbox(
                        "Selecione a conta contábil",
                        options=opcoes,
                        key=f"select_{row['id']}"
                    )
                    reg_sel = reg_sel_formatado.split(" - ")[0]

                    if st.button("Classificar", key=f"class_{row['id']}"):
                        classificar_lancamento(row["id"], reg_sel)
                        st.success("Lançamento classificado com sucesso!", icon="📌")


        # ============================================================
        # 📄 LANÇAMENTOS IMPORTADOS
        # ============================================================
        st.markdown("### 📄 Lançamentos Importados")

        if df_lanc.empty:
            st.info("Nenhum lançamento importado ainda.")
        else:
            # Juntar lançamentos com plano de contas para trazer o nome
            df_lanc = df_lanc.merge(
                df_contas[["registro", "nome_registro"]],
                left_on="conta_registro",
                right_on="registro",
                how="left"
            )

            # 🔍 Filtros acima da matriz
            col1, col2, col3 = st.columns(3)

            filtro_data = col1.selectbox(
                "Filtrar por Data",
                options=["Todos"] + sorted(df_lanc["data"].astype(str).unique()),
                key="filtro_data"
            )

            filtro_historico = col2.selectbox(
                "Filtrar por Histórico",
                options=["Todos"] + sorted(df_lanc["historico"].unique()),
                key="filtro_historico"
            )

            # Criar coluna formatada para exibir código + nome
            df_lanc["conta_formatada"] = df_lanc["conta_registro"].astype(str) + " - " + df_lanc["nome_registro"].fillna("")

            filtro_conta = col3.selectbox(
                "Filtrar por Conta Registro",
                options=["Todos"] + sorted(df_lanc["conta_formatada"].unique()),
                key="filtro_conta"
            )

            # Aplicar filtros
            df_filtrado = df_lanc.copy()
            if filtro_data != "Todos":
                df_filtrado = df_filtrado[df_filtrado["data"].astype(str) == filtro_data]
            if filtro_historico != "Todos":
                df_filtrado = df_filtrado[df_filtrado["historico"] == filtro_historico]
            if filtro_conta != "Todos":
                cod_sel = filtro_conta.split(" - ")[0]
                df_filtrado = df_filtrado[df_filtrado["conta_registro"].astype(str) == cod_sel]

            # Paginação sobre o df_filtrado
            page_size = 100
            total_pages = (len(df_filtrado) // page_size) + (1 if len(df_filtrado) % page_size else 0)

            if "page_import" not in st.session_state:
                st.session_state.page_import = 1

            col_prev, col_page, col_next = st.columns([1, 2, 1])
            if col_prev.button("⬅️ Anterior") and st.session_state.page_import > 1:
                st.session_state.page_import -= 1
            col_page.write(f"Página {st.session_state.page_import} de {total_pages}")
            if col_next.button("Próximo ➡️") and st.session_state.page_import < total_pages:
                st.session_state.page_import += 1

            start = (st.session_state.page_import - 1) * page_size
            end = start + page_size
            df_page = df_filtrado.iloc[start:end]

            # Selecionar apenas as colunas desejadas
            df_page = df_page[["id", "data", "valor", "historico", "conta_registro", "nome_registro"]]

            # Torna a matriz editável
            edited_df = st.data_editor(
                df_page,
                num_rows="fixed",
                use_container_width=True,
                key="editor_import",
                column_config={
                    "conta_registro": st.column_config.TextColumn("Conta Registro"),
                    "nome_registro": st.column_config.TextColumn("Nome da Conta"),
                    "data": st.column_config.TextColumn("Data", disabled=True),
                    "valor": st.column_config.NumberColumn("Valor", disabled=True),
                    "historico": st.column_config.TextColumn("Histórico", disabled=True),
                    }
            )

            # Botão para salvar alterações
            if st.button("💾 Salvar alterações", key="save_import"):
                for i, row in edited_df.iterrows():
                    original = df_page.loc[i]
                    if row["conta_registro"] != original["conta_registro"]:
                        classificar_lancamento(row["id"], row["conta_registro"])
                st.toast("Alterações salvas e lançamentos reclassificados com sucesso!✅")

                # Recarregar dados para refletir nomes atualizados
                df_lanc = carregar_lancamentos()
                st.rerun()


    # ============================================================
    # 📊 DASHBOARD
    # ============================================================
    with aba_dashboard:
        st.subheader("📊 Dashboard Financeiro")

        # 🔹 Funções de formatação
        def formatar_data(data):
            if pd.isnull(data):
                return ""
            return pd.to_datetime(data).strftime("%d/%m/%Y")

        def formatar_valor(valor):
            if valor is None:
                return "R$ 0,00"
            return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        def formatar_percentual(pct):
            if pct is None:
                return "0%"
            return f"{pct:.2f}%"

        # 🔹 Carregar lançamentos classificados
        df_lanc = carregar_lancamentos()
        df_contas = carregar_contas()

        # Juntar lançamentos com contas
        df_lanc = df_lanc.merge(df_contas, left_on="conta_registro", right_on="registro", how="left")

        # ============================================================
        # 🎛️ Filtros (na sidebar)
        # ============================================================
        st.sidebar.markdown("### 🎛️ Filtros")
        
        # Converter coluna para datetime, ignorando erros
        df_lanc["data"] = pd.to_datetime(df_lanc["data"], errors="coerce")
        
        # Remover valores nulos
        datas_validas = df_lanc["data"].dropna()
        
        # Definir valores padrão seguros
        if len(datas_validas) > 0:
            data_inicial_padrao = datas_validas.min().date()
            data_final_padrao = datas_validas.max().date()
        else:
            hoje = pd.Timestamp.today().date()
            data_inicial_padrao = hoje
            data_final_padrao = hoje
        
        # Usar no date_input (apenas uma vez)
        data_inicio = st.sidebar.date_input("Data inicial", value=data_inicial_padrao)
        data_fim = st.sidebar.date_input("Data final", value=data_final_padrao)
        
        # Filtros de Mestre, Subchave e Registro
        mestres_opcoes = sorted(df_lanc["mestre"].dropna().unique(), key=lambda x: float(x))
        mestre_sel = st.sidebar.multiselect("Filtrar por Mestre", options=mestres_opcoes)
        
        subchaves_opcoes = sorted(df_lanc["subchave"].dropna().unique(), key=lambda x: float(x))
        subchave_sel = st.sidebar.multiselect("Filtrar por Subchave", options=subchaves_opcoes)
        
        registros_opcoes = sorted(df_lanc["registro"].dropna().unique(), key=lambda x: float(x.replace(".", "")))
        registro_sel = st.sidebar.multiselect("Filtrar por Registro", options=registros_opcoes)

        # ============================================================
        # 🔹 Aplicar filtros
        # ============================================================
        df_filtrado = df_lanc.copy()
        df_filtrado = df_filtrado[
            (pd.to_datetime(df_filtrado["data"]).dt.date >= data_inicio) &
            (pd.to_datetime(df_filtrado["data"]).dt.date <= data_fim)
        ]

        if mestre_sel:
            df_filtrado = df_filtrado[df_filtrado["mestre"].isin(mestre_sel)]
        if subchave_sel:
            df_filtrado = df_filtrado[df_filtrado["subchave"].isin(subchave_sel)]
        if registro_sel:
            df_filtrado = df_filtrado[df_filtrado["registro"].isin(registro_sel)]

        # ============================================================
        # 🔹 Drill-down e gráficos
        # ============================================================
        if df_filtrado.empty:
            st.info("Nenhum dado encontrado para os filtros selecionados.")
        else:
            mestres_ordenados = sorted(df_filtrado["mestre"].unique(), key=lambda x: float(x))

            for mestre in mestres_ordenados:
                df_mestre = df_filtrado[df_filtrado["mestre"] == mestre]
                if not df_mestre.empty:
                    nome_mestre = df_mestre["nome_mestre"].iloc[0]
                    soma_mestre = df_mestre["valor"].sum()
                else:
                    nome_mestre = "(sem nome)"
                    soma_mestre = 0

                with st.expander(f"{mestre} - {nome_mestre} | Total: {formatar_valor(soma_mestre)}"):
                    subchaves_ordenadas = sorted(df_mestre["subchave"].unique(), key=lambda x: float(x))
                    for subchave in subchaves_ordenadas:
                        df_sub = df_mestre[df_mestre["subchave"] == subchave]
                        if not df_sub.empty:
                            nome_sub = df_sub["nome_subchave"].iloc[0]
                            soma_sub = df_sub["valor"].sum()
                        else:
                            nome_sub = "(sem nome)"
                            soma_sub = 0

                        with st.expander(f"{subchave} - {nome_sub} | Total: {formatar_valor(soma_sub)}"):
                            registros_ordenados = sorted(df_sub["registro"].unique(), key=lambda x: float(x.replace(".", "")))
                            for registro in registros_ordenados:
                                df_reg = df_sub[df_sub["registro"] == registro]
                                if not df_reg.empty:
                                    nome_reg = df_reg["nome_registro"].iloc[0]
                                    soma_reg = df_reg["valor"].sum()
                                else:
                                    nome_reg = "(sem nome)"
                                    soma_reg = 0

                                with st.expander(f"{registro} - {nome_reg} | Total: {formatar_valor(soma_reg)}"):
                                    st.dataframe(
                                        df_reg[["data", "valor", "historico"]].assign(
                                            data=df_reg["data"].apply(formatar_data),
                                            valor=df_reg["valor"].apply(formatar_valor)
                                        ),
                                        use_container_width=True
                                    )

            # 📥 Botão geral para todos os lançamentos filtrados
            st.download_button(
                label="📥 Baixar todos os lançamentos filtrados",
                data=to_excel(df_filtrado),
                file_name="lancamentos_filtrados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            total_geral = df_filtrado["valor"].sum()
            st.markdown(f"### 💰 Total Geral: {formatar_valor(total_geral)}")

            st.markdown("### 🥧 Distribuição por Grupo")
            df_pizza = df_filtrado.groupby(["mestre", "nome_mestre"])["valor"].sum().reset_index()
            df_pizza["valor"] = df_pizza["valor"].abs()
            df_pizza = df_pizza[df_pizza["mestre"] != "6"]

            import plotly.express as px
            fig = px.pie(
                df_pizza,
                names="nome_mestre",
                values="valor",
                title="Distribuição dos Valores por Grupo",
                hole=0.3
            )
            st.plotly_chart(fig, use_container_width=True)
