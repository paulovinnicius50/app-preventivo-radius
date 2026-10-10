import streamlit as st
import pandas as pd
import re
import os
from datetime import date, timedelta

# Configuração Inicial e CSS
st.set_page_config(page_title="Dashboard Preventivo RADIUS", page_icon="📡", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border: 1px solid #e0e0e0;
        padding: 5% 5% 5% 10%;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# FUNÇÕES DE BANCO DE DADOS
# ==========================================
ARQUIVO_TRATADOS = 'clientes_tratados.csv'
ARQUIVO_OCULTOS = 'pppoes_ocultos.csv'

# --- Funções para Visitas (Operacional) ---
def carregar_tratados():
    if os.path.exists(ARQUIVO_TRATADOS):
        try:
            df = pd.read_csv(ARQUIVO_TRATADOS)
            if 'visita_aberta' not in df.columns:
                df['visita_aberta'] = 'Não'
            if 'visita_realizada' not in df.columns:
                df['visita_realizada'] = 'Não'
            return df
        except:
            pass
    return pd.DataFrame(columns=['username', 'visita_aberta', 'visita_realizada'])

def adicionar_tratado(novo_username, v_aberta, v_realizada):
    df = carregar_tratados()
    df = df[df['username'] != novo_username]
    novo_dado = pd.DataFrame({'username': [novo_username], 'visita_aberta': [v_aberta], 'visita_realizada': [v_realizada]})
    df = pd.concat([df, novo_dado], ignore_index=True)
    df.to_csv(ARQUIVO_TRATADOS, index=False)

def limpar_tratados(username_remover):
    df = carregar_tratados()
    df = df[df['username'] != username_remover]
    df.to_csv(ARQUIVO_TRATADOS, index=False)

# --- Funções para PPPoEs Ocultos ---
def carregar_ocultos():
    if os.path.exists(ARQUIVO_OCULTOS):
        try:
            return pd.read_csv(ARQUIVO_OCULTOS)['username'].tolist()
        except:
            pass
    return []

def adicionar_oculto(novo_username):
    lista_atual = carregar_ocultos()
    if novo_username not in lista_atual:
        lista_atual.append(novo_username)
        pd.DataFrame({'username': lista_atual}).to_csv(ARQUIVO_OCULTOS, index=False)
        return True
    return False

def remover_oculto(username_remover):
    lista_atual = carregar_ocultos()
    if username_remover in lista_atual:
        lista_atual.remove(username_remover)
        pd.DataFrame({'username': lista_atual}).to_csv(ARQUIVO_OCULTOS, index=False)

# ==========================================
# INTERFACE LATERAL
# ==========================================
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2885/2885412.png", width=60)
st.sidebar.title("Configurações")
st.sidebar.markdown("---")

st.sidebar.subheader("📅 Data de Corte")
data_corte = st.sidebar.date_input("Data limite da análise:", value=date.today())

st.sidebar.markdown("---")

st.sidebar.subheader("⚙️ Regra Diária (Elegibilidade)")
limite_elegivel = st.sidebar.number_input("Logs diários para (Visita):", min_value=1, value=2)

st.sidebar.markdown("---")

st.sidebar.subheader("🔥 Alerta Crítico (Frequência)")
janela_dias = st.sidebar.number_input("Janela de análise (Últimos X Dias):", min_value=1, value=5)
logs_critico = st.sidebar.number_input("Meta de logs POR DIA:", min_value=1, value=8)
dias_necessarios = st.sidebar.number_input("Dias necessários com essa meta:", min_value=1, value=3)

st.sidebar.markdown("---")

# ==========================================
# NOVO: CONTROLE DE PPPoEs OCULTOS
# ==========================================
st.sidebar.subheader("👁️ Ocultar PPPoEs")
st.sidebar.caption("Ignorar PPPoEs do sistema (ex: default)")

pppoe_oculto = st.sidebar.text_input("Nome do PPPoE para ocultar:")
if st.sidebar.button("Ocultar PPPoE", use_container_width=True):
    if pppoe_oculto:
        if adicionar_oculto(pppoe_oculto.lower()):
            st.sidebar.success("PPPoE ocultado das análises!")
        else:
            st.sidebar.warning("Este PPPoE já está oculto.")

lista_pppoes_ocultos = carregar_ocultos()
if lista_pppoes_ocultos:
    st.sidebar.caption("PPPoEs Ocultos Atualmente:")
    pppoe_remover = st.sidebar.selectbox("Selecionar para reexibir:", lista_pppoes_ocultos, label_visibility="collapsed")
    if st.sidebar.button("Reexibir PPPoE", use_container_width=True):
        remover_oculto(pppoe_remover)
        st.sidebar.success("PPPoE reexibido!")
        st.rerun()

st.sidebar.markdown("---")

# ==========================================
# CONTROLE OPERACIONAL (VISITAS)
# ==========================================
st.sidebar.subheader("🛠️ Controle Operacional")
st.sidebar.caption("Gerenciar Status da Visita")

cliente_tratado = st.sidebar.text_input("Username do cliente:")
col_v1, col_v2 = st.sidebar.columns(2)
status_aberta = col_v1.selectbox("Aberta?", ["Não", "Sim"])
status_realizada = col_v2.selectbox("Realizada?", ["Não", "Sim"])

if st.sidebar.button("Salvar Status", use_container_width=True):
    if cliente_tratado:
        adicionar_tratado(cliente_tratado.lower(), status_aberta, status_realizada)
        st.sidebar.success("Status atualizado!")

df_tratados = carregar_tratados()
if not df_tratados.empty:
    st.sidebar.caption("Clientes com Status Manual:")
    cliente_remover_visita = st.sidebar.selectbox("Selecionar para remover:", df_tratados['username'].tolist(), label_visibility="collapsed", key="combo_visita")
    if st.sidebar.button("Remover Status Manual", use_container_width=True):
        limpar_tratados(cliente_remover_visita)
        st.sidebar.success("Removido!")
        st.rerun()

# ==========================================
# TELA PRINCIPAL
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
            if match_data:
                data_str = match_data.group()
                try:
                    if data_str.startswith('20'): 
                        data_formatada = pd.to_datetime(data_str, format='%Y-%m-%d').date()
                    else: 
                        data_formatada = pd.to_datetime(data_str, format='%d-%m-%Y').date()
                except:
                    data_formatada = None 
            else:
                data_formatada = None
            
            if data_formatada and data_formatada <= data_corte:
                df['Data_do_Log'] = data_formatada
                lista_dfs.append(df)

    if lista_dfs:
        df_bruto = pd.concat(lista_dfs, ignore_index=True)
        
        # =========================================================
        # A MÁGICA DA EXCLUSÃO ACONTECE AQUI
        # =========================================================
        # Remove completamente os PPPoEs da lista de ocultos antes de qualquer cálculo
        lista_ocultos_ativos = carregar_ocultos()
        df_bruto = df_bruto[~df_bruto['username'].isin(lista_ocultos_ativos)]
        
        # Agrupamento diário
        df_diario = df_bruto.groupby(['username', 'Data_do_Log'], as_index=False)['c_username'].sum()
        
        if df_diario.empty:
            st.warning("⚠️ Não há dados a exibir após os filtros (ou não há logs até a data de corte).")
        else:
            df_resumo = df_diario.groupby('username').agg(
                Total_Desconexoes=('c_username', 'sum'),
                Dias_com_Evento=('Data_do_Log', 'nunique'),
                Pico_Logs_Diario=('c_username', 'max') 
            ).reset_index()

            # Inteligência do Alerta Crítico
            datas_janela = [(data_corte - timedelta(days=i)) for i in range(janela_dias)]
            df_janela = df_diario[df_diario['Data_do_Log'].isin(datas_janela)]
            
            df_janela_critico = df_janela[df_janela['c_username'] >= logs_critico]
            contagem_critica = df_janela_critico.groupby('username')['Data_do_Log'].nunique().reset_index()
            contagem_critica.rename(columns={'Data_do_Log': 'Qtd_Dias_Alerta'}, inplace=True)

            df_resumo = pd.merge(df_resumo, contagem_critica, on='username', how='left')
            df_resumo['Qtd_Dias_Alerta'] = df_resumo['Qtd_Dias_Alerta'].fillna(0)
            df_resumo['🔥 Alerta Crítico'] = df_resumo['Qtd_Dias_Alerta'].apply(lambda x: "Sim" if x >= dias_necessarios else "Não")
            
            # Matriz Rápida para Registros Diários
            datas_exibicao = sorted(datas_janela) 
            df_pivot = df_diario.pivot(index='username', columns='Data_do_Log', values='c_username').fillna(0)
            
            registros_list = []
            for cliente in df_resumo['username']:
                historico = []
                if cliente in df_pivot.index:
                    for dia_alvo in datas_exibicao:
                        qtd = int(df_pivot.at[cliente, dia_alvo]) if dia_alvo in df_pivot.columns else 0
                        dia_str = dia_alvo.strftime("%d/%m")
                        if qtd >= logs_critico:
                            historico.append(f"{dia_str}: 🔴 {qtd}")
                        else:
                            historico.append(f"{dia_str}: 🟢 {qtd}")
                registros_list.append(' | '.join(historico))
                
            df_resumo['Registros_Diários'] = registros_list
            df_final = df_resumo.copy()
            
            # Definição do Status Base
            def definir_status(row):
                if row['Pico_Logs_Diario'] >= limite_elegivel:
                    return '🔴 Elegível (Visita)'
                elif row['Dias_com_Evento'] >= 2:
                    return '🟡 Requer Análise'
                else:
                    return '🟢 Monitoramento'
                    
            df_final['Status'] = df_final.apply(definir_status, axis=1)
            
            # Inserção das Colunas de Visita
            df_final = pd.merge(df_final, df_tratados, on='username', how='left')
            df_final['visita_aberta'] = df_final['visita_aberta'].fillna('Não')
            df_final['visita_realizada'] = df_final['visita_realizada'].fillna('Não')
            df_final.rename(columns={'visita_aberta': 'Visita Aberta', 'visita_realizada': 'Visita Realizada'}, inplace=True)
            
            # Ordenação Final
            df_final['Ordem_Status'] = df_final['Status'].map({'🔴 Elegível (Visita)': 1, '🟡 Requer Análise': 2, '🟢 Monitoramento': 3})
            df_final['Peso_Alerta'] = df_final['🔥 Alerta Crítico'].map({'Sim': 1, 'Não': 2})
            df_final = df_final.sort_values(by=['Ordem_Status', 'Peso_Alerta', 'Pico_Logs_Diario'], ascending=[True, True, False])
            
            if not df_final.empty:
                with aba_relatorio:
                    qtd_alerta = len(df_final[df_final['🔥 Alerta Crítico'] == 'Sim'])
                    
                    col_espaco1, col_card, col_espaco2 = st.columns([1, 2, 1])
                    with col_card:
                        st.metric("🔥 Clientes em Alerta Crítico", qtd_alerta)
                    
                    st.markdown("---")

                    col_filtro, col_vazia = st.columns([3, 1])
                    with col_filtro:
                        filtro_exibicao = st.radio(
                            "Filtro de visualização:", 
                            ["🔥 Apenas Alertas Críticos", "🔴 Elegíveis", "🟡 Análise", "Todos os Status"],
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
                    
                    colunas_exibir = [
                        'username', 'Status', '🔥 Alerta Crítico', 
                        'Visita Aberta', 'Visita Realizada', 
                        'Pico_Logs_Diario', 'Total_Desconexoes', 'Dias_com_Evento', 'Registros_Diários'
                    ]
                    
                    st.dataframe(
                        df_exibicao[colunas_exibir], 
                        use_container_width=True,
                        height=600,
                        hide_index=True 
                    )
            else:
                with aba_relatorio:
                    st.warning("Nenhum dado encontrado para a data de corte selecionada.")
else:
    with aba_relatorio:
        st.info("👈 Faça o upload dos arquivos na aba 'Importar Dados' para gerar o relatório.")
