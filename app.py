import streamlit as st
import pandas as pd
import re
import os

# 1. Configuração Inicial e CSS customizado para os Cards
st.set_page_config(page_title="Dashboard Preventivo RADIUS", page_icon="📡", layout="wide", initial_sidebar_state="expanded")

# Pequeno truque de estilo para deixar os cartões mais bonitos
st.markdown("""
    <style>
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border: 1px solid #e0e0e0;
        padding: 5% 5% 5% 10%;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# FUNÇÕES DE BANCO DE DADOS (Lista de Tratados)
# ==========================================
ARQUIVO_TRATADOS = 'clientes_tratados.csv'

def carregar_tratados():
    if os.path.exists(ARQUIVO_TRATADOS):
        return pd.read_csv(ARQUIVO_TRATADOS)['username'].tolist()
    return []

def adicionar_tratado(novo_username):
    lista_atual = carregar_tratados()
    if novo_username not in lista_atual:
        lista_atual.append(novo_username)
        pd.DataFrame({'username': lista_atual}).to_csv(ARQUIVO_TRATADOS, index=False)
        return True
    return False

def limpar_tratados(username_remover):
    lista_atual = carregar_tratados()
    if username_remover in lista_atual:
        lista_atual.remove(username_remover)
        pd.DataFrame({'username': lista_atual}).to_csv(ARQUIVO_TRATADOS, index=False)

# ==========================================
# INTERFACE LATERAL (SIDEBAR PROFISSIONAL)
# ==========================================
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2885/2885412.png", width=60) # Ícone de antena
st.sidebar.title("Configurações")
st.sidebar.markdown("---")

st.sidebar.subheader("⚙️ Regra de Negócio")
limite_elegivel = st.sidebar.number_input(
    "Logs diários para (Visita):", 
    min_value=1, 
    value=2, 
    help="Define o gatilho para cliente Elegível."
)

st.sidebar.markdown("---")

st.sidebar.subheader("🛠️ Controle Operacional")
st.sidebar.caption("Ocultar clientes com OS aberta")

cliente_tratado = st.sidebar.text_input("Username do cliente:")
if st.sidebar.button("Salvar Exceção", use_container_width=True):
    if cliente_tratado:
        if adicionar_tratado(cliente_tratado.lower()):
            st.sidebar.success("Cliente arquivado!")
        else:
            st.sidebar.warning("Já arquivado.")

lista_ignorados = carregar_tratados()
if lista_ignorados:
    st.sidebar.caption("Lista de Exceções:")
    cliente_remover = st.sidebar.selectbox("Selecionar:", lista_ignorados, label_visibility="collapsed")
    if st.sidebar.button("Remover da Exceção", use_container_width=True):
        limpar_tratados(cliente_remover)
        st.sidebar.success("Removido!")
        st.rerun()

# ==========================================
# TELA PRINCIPAL (DASHBOARD)
# ==========================================
st.title("Painel Analítico - RADIUS Preventivo")
st.markdown("Monitoramento inteligente de instabilidade de conexão")

# Separando a tela em Abas para ficar mais limpo
aba_relatorio, aba_dados = st.tabs(["📊 Relatório Consolidado", "📁 Importar Dados"])

with aba_dados:
    st.info("Suba os arquivos diários do RADIUS aqui para atualizar o Dashboard.")
    arquivos_upload = st.file_uploader("Arraste as planilhas (Excel ou CSV):", type=["csv", "xlsx"], accept_multiple_files=True)

if arquivos_upload:
    lista_dfs = []
    
    for arquivo in arquivos_upload:
        try:
            df = pd.read_excel(arquivo)
        except:
            try:
                df = pd.read_csv(arquivo)
            except:
                df = pd.read_csv(arquivo, sep=';')
                
        df.columns = df.columns.str.lower()
        
        if 'username' in df.columns and 'c_username' in df.columns:
            match_data = re.search(r'\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2}', arquivo.name)
            data_log = match_data.group() if match_data else arquivo.name[:10]
            df['Data_do_Log'] = data_log
            lista_dfs.append(df)

    if lista_dfs:
        df_consolidado = pd.concat(lista_dfs, ignore_index=True)
        
        df_resumo = df_consolidado.groupby('username').agg(
            Total_Desconexoes=('c_username', 'sum'),
            Dias_com_Evento=('Data_do_Log', 'nunique'),
            Pico_Logs_Diario=('c_username', 'max') 
        ).reset_index()
        
        df_consolidado['Detalhe_Dia'] = df_consolidado['Data_do_Log'] + ": " + df_consolidado['c_username'].astype(str)
        df_detalhes = df_consolidado.groupby('username')['Detalhe_Dia'].apply(lambda x: ' | '.join(x)).reset_index()
        df_detalhes = df_detalhes.rename(columns={'Detalhe_Dia': 'Registros_Diários'})
        
        df_final = pd.merge(df_resumo, df_detalhes, on='username')
        
        def definir_status(row):
            if row['Pico_Logs_Diario'] >= limite_elegivel:
                return '🔴 Elegível (Visita)'
            elif row['Dias_com_Evento'] >= 2:
                return '🟡 Requer Análise'
            else:
                return '🟢 Monitoramento'
                
        df_final['Status'] = df_final.apply(definir_status, axis=1)
        df_final = df_final[~df_final['username'].isin(lista_ignorados)]
        
        df_final['Ordem_Status'] = df_final['Status'].map({'🔴 Elegível (Visita)': 1, '🟡 Requer Análise': 2, '🟢 Monitoramento': 3})
        df_final = df_final.sort_values(by=['Ordem_Status', 'Pico_Logs_Diario', 'Dias_com_Evento'], ascending=[True, False, False])
        df_final = df_final.drop(columns=['Ordem_Status']).reset_index(drop=True)

        if not df_final.empty:
            
            with aba_relatorio:
                # 1. CARDS DE RESUMO (O visual de Dashboard!)
                # Contando quantos estão em cada status
                qtd_elegivel = len(df_final[df_final['Status'] == '🔴 Elegível (Visita)'])
                qtd_analise = len(df_final[df_final['Status'] == '🟡 Requer Análise'])
                qtd_monitoramento = len(df_final[df_final['Status'] == '🟢 Monitoramento'])
                qtd_total = len(df_final)

                # Desenhando as colunas no topo da tela
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("🔴 Elegíveis (Visitas)", qtd_elegivel)
                col2.metric("🟡 Requer Análise", qtd_analise)
                col3.metric("🟢 Em Monitoramento", qtd_monitoramento)
                col4.metric("👥 Total de Clientes", qtd_total)
                
                st.markdown("---")

                # 2. TABELA E FILTROS ALINHADOS
                col_filtro, col_vazia = st.columns([2, 1])
                with col_filtro:
                    filtro_exibicao = st.radio(
                        "Filtro de visualização:", 
                        ["🔴 Elegíveis", "🟡 Análise", "Todos os Status"],
                        horizontal=True
                    )
                
                if filtro_exibicao == "🔴 Elegíveis":
                    df_exibicao = df_final[df_final['Status'] == '🔴 Elegível (Visita)']
                elif filtro_exibicao == "🟡 Análise":
                    df_exibicao = df_final[df_final['Status'] == '🟡 Requer Análise']
                else:
                    df_exibicao = df_final
                
                colunas_exibir = ['username', 'Status', 'Pico_Logs_Diario', 'Total_Desconexoes', 'Dias_com_Evento', 'Registros_Diários']
                
                st.dataframe(
                    df_exibicao[colunas_exibir], 
                    use_container_width=True,
                    height=500,
                    hide_index=True # Oculta aquele número inútil (0, 1, 2) da primeira coluna
                )
        else:
            with aba_relatorio:
                st.success("Todos os clientes desta planilha já estão arquivados/em atendimento.")
else:
    with aba_relatorio:
        st.info("👈 Faça o upload dos arquivos na aba 'Importar Dados' para gerar o relatório.")