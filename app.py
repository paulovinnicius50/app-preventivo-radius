import streamlit as st
import pandas as pd
import re
import os
from datetime import date

# Configuração Inicial e CSS customizado para os Cards
st.set_page_config(page_title="Dashboard Preventivo RADIUS", page_icon="📡", layout="wide", initial_sidebar_state="expanded")

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
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2885/2885412.png", width=60)
st.sidebar.title("Configurações")
st.sidebar.markdown("---")

# NOVIDADE: CALENDÁRIO DE DATA DE CORTE
st.sidebar.subheader("📅 Data de Corte")
data_corte = st.sidebar.date_input(
    "Selecione a data limite da análise:", 
    value=date.today(),
    help="O sistema considerará apenas os logs até esta data selecionada."
)

st.sidebar.markdown("---")

st.sidebar.subheader("⚙️ Regra Diária (Elegibilidade)")
limite_elegivel = st.sidebar.number_input(
    "Logs diários para (Visita):", 
    min_value=1, 
    value=2, 
    help="Define o gatilho para cliente Elegível em um único dia."
)

st.sidebar.markdown("---")

st.sidebar.subheader("🔥 Alerta Crítico (Frequência)")
janela_dias = st.sidebar.number_input(
    "Janela de análise (Últimos X Dias):", 
    min_value=1, value=5, 
    help="Quantos dias recentes a partir da data de corte o sistema vai olhar."
)
logs_critico = st.sidebar.number_input(
    "Meta de logs POR DIA:", 
    min_value=1, value=10, 
    help="O cliente precisa bater essa quantidade de logs em um dia para que aquele dia seja considerado 'crítico'."
)
dias_necessarios = st.sidebar.number_input(
    "Dias necessários com essa meta:", 
    min_value=1, value=3, 
    help="Em quantos dias DIFERENTES o cliente precisa ter atingido a meta de logs acima para disparar o alerta."
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
        df_bruto = pd.concat(lista_dfs, ignore_index=True)
        
        # Agrupamento diário individual
        df_diario = df_bruto.groupby(['username', 'Data_do_Log'], as_index=False)['c_username'].sum()
        
        # ==========================================================
        # FILTRAGEM PELO CALENDÁRIO DE CORTE
        # ==========================================================
        df_diario['Data_Datetime'] = pd.to_datetime(df_diario['Data_do_Log'], errors='coerce', dayfirst=True)
        
        # Converte a data de corte do calendário para o formato comparável
        data_corte_dt = pd.to_datetime(data_corte)
        
        # Mantém apenas os logs cujas datas sejam MENORES OU IGUAIS à data de corte selecionada
        df_diario = df_diario[df_diario['Data_Datetime'] <= data_corte_dt]
        
        if df_diario.empty:
            st.warning("⚠️ Nenhum registro encontrado para datas anteriores ou iguais à data de corte selecionada.")
        else:
            # 1. Resumo Geral considerando o corte
            df_resumo = df_diario.groupby('username').agg(
                Total_Desconexoes=('c_username', 'sum'),
                Dias_com_Evento=('Data_do_Log', 'nunique'),
                Pico_Logs_Diario=('c_username', 'max') 
            ).reset_index()

            # 2. Inteligência do Alerta Crítico baseada na janela a partir da data de corte
            df_datas = df_diario[['Data_do_Log', 'Data_Datetime']].drop_duplicates()
            df_datas = df_datas.sort_values(by='Data_Datetime', ascending=False)
            ultimas_datas = df_datas['Data_do_Log'].head(janela_dias).tolist()

            df_janela = df_diario[df_diario['Data_do_Log'].isin(ultimas_datas)]
            df_janela_critico = df_janela[df_janela['c_username'] >= logs_critico]
            
            contagem_critica = df_janela_critico.groupby('username')['Data_do_Log'].nunique().reset_index()
            contagem_critica.rename(columns={'Data_do_Log': 'Qtd_Dias_Alerta'}, inplace=True)

            df_resumo = pd.merge(df_resumo, contagem_critica, on='username', how='left')
            df_resumo['Qtd_Dias_Alerta'] = df_resumo['Qtd_Dias_Alerta'].fillna(0)
            
            df_resumo['🔥 Alerta Crítico'] = df_resumo['Qtd_Dias_Alerta'].apply(
                lambda x: "Sim" if x >= dias_necessarios else "Não"
            )
            
            # 3. Histórico Diário Textual
            df_diario['Detalhe_Dia'] = df_diario['Data_do_Log'] + ": " + df_diario['c_username'].astype(str)
            df_detalhes = df_diario.groupby('username')['Detalhe_Dia'].apply(lambda x: ' | '.join(x)).reset_index()
            df_detalhes = df_detalhes.rename(columns={'Detalhe_Dia': 'Registros_Diários'})
            
            df_final = pd.merge(df_resumo, df_detalhes, on='username')
            
            # 4. Definição do Status de Cor
            def definir_status(row):
                if row['Pico_Logs_Diario'] >= limite_elegivel:
                    return '🔴 Elegível (Visita)'
                elif row['Dias_com_Evento'] >= 2:
                    return '🟡 Requer Análise'
                else:
                    return '🟢 Monitoramento'
                    
            df_final['Status'] = df_final.apply(definir_status, axis=1)
            df_final = df_final[~df_final['username'].isin(lista_ignorados)]
            
            # Ordenação
            df_final['Ordem_Status'] = df_final['Status'].map({'🔴 Elegível (Visita)': 1, '🟡 Requer Análise': 2, '🟢 Monitoramento': 3})
            df_final['Peso_Alerta'] = df_final['🔥 Alerta Crítico'].map({'Sim': 1, 'Não': 2})
            df_final = df_final.sort_values(by=['Ordem_Status', 'Peso_Alerta', 'Pico_Logs_Diario'], ascending=[True, True, False])
            df_final = df_final.drop(columns=['Ordem_Status', 'Peso_Alerta', 'Qtd_Dias_Alerta']).reset_index(drop=True)

            if not df_final.empty:
                with aba_relatorio:
                    qtd_elegivel = len(df_final[df_final['Status'] == '🔴 Elegível (Visita)'])
                    qtd_analise = len(df_final[df_final['Status'] == '🟡 Requer Análise'])
                    qtd_monitoramento = len(df_final[df_final['Status'] == '🟢 Monitoramento'])
                    qtd_total = len(df_final)
                    qtd_alerta = len(df_final[df_final['🔥 Alerta Crítico'] == 'Sim'])

                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("🔴 Elegíveis (Visitas)", qtd_elegivel)
                    col2.metric("🔥 Alertas Críticos", qtd_alerta)
                    col3.metric("🟡 Requer Análise", qtd_analise)
                    col4.metric("🟢 Em Monitoramento", qtd_monitoramento)
                    col5.metric("👥 Total de Clientes", qtd_total)
                    
                    st.markdown("---")

                    col_filtro, col_vazia = st.columns([3, 1])
                    with col_filtro:
                        filtro_exibicao = st.radio(
                            "Filtro de visualização:", 
                            ["🔴 Elegíveis", "🔥 Apenas Alertas Críticos", "🟡 Análise", "Todos os Status"],
                            horizontal=True
                        )
                    
                    if filtro_exibicao == "🔴 Elegíveis":
                        df_exibicao = df_final[df_final['Status'] == '🔴 Elegível (Visita)']
                    elif filtro_exibicao == "🔥 Apenas Alertas Críticos":
                        df_exibicao = df_final[df_final['🔥 Alerta Crítico'] == 'Sim']
                    elif filtro_exibicao == "🟡 Análise":
                        df_exibicao = df_final[df_final['Status'] == '🟡 Requer Análise']
                    else:
                        df_exibicao = df_final
                    
                    colunas_exibir = ['username', 'Status', '🔥 Alerta Crítico', 'Pico_Logs_Diario', 'Total_Desconexoes', 'Dias_com_Evento', 'Registros_Diários']
                    
                    st.dataframe(
                        df_exibicao[colunas_exibir], 
                        use_container_width=True,
                        height=500,
                        hide_index=True 
                    )
            else:
                with aba_relatorio:
                    st.success("Todos os clientes desta planilha já estão arquivados/em atendimento.")
else:
    with aba_relatorio:
        st.info("👈 Faça o upload dos arquivos na aba 'Importar Dados' para gerar o relatório.")
