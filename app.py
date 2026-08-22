import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import requests
from io import StringIO

# Configuración de Pantalla Completa (CRÍTICO)
st.set_page_config(page_title="Dashboard Rendimiento", layout="wide")

# Inyección CSS (Tipografia institucional y filtros limpios)
st.markdown("""
<style>
/* Tipografia global responsive */
html, body, [class*="st-"] { 
    font-size: 14px !important;
    font-family: 'Agency FB', sans-serif !important; 
}

h1 { 
    font-size: 2rem !important;
    color: #2E7D32 !important; 
    text-align: center; 
}

/* Eliminacion forzada del fondo de color en todas las variantes de multiselect */
[data-testid="stMultiSelect"] [data-baseweb="tag"],
[data-testid="stMultiSelect"] span[data-baseweb="tag"],
[data-testid="stMultiSelectTag"],
span[data-baseweb="tag"],
div[data-baseweb="tag"] {
    background-color: transparent !important;
    background: transparent !important;
    border: 1px solid #94A3B8 !important;
    box-shadow: none !important;
    padding: 2px 8px !important;
}

/* Texto oscuro y nitido en las pastillas */
[data-testid="stMultiSelect"] [data-baseweb="tag"] span,
[data-testid="stMultiSelectTag"] span,
span[data-baseweb="tag"] span,
div[data-baseweb="tag"] span {
    color: #0F172A !important;
    font-weight: 700 !important;
    font-size: 15px !important;
}

/* Ocultar la cruz y los botones de eliminar */
[data-testid="stMultiSelect"] [data-baseweb="tag"] svg,
[data-testid="stMultiSelectTag"] svg,
span[data-baseweb="tag"] svg,
div[data-baseweb="tag"] svg,
[data-baseweb="tag"] button,
[data-baseweb="tag"] [role="presentation"] {
    display: none !important;
}

/* Forzar aparición de la barra de scroll en los dropdowns */
div[role="listbox"] {
    max-height: 400px !important;
    overflow-y: auto !important;
}

div[role="listbox"]::-webkit-scrollbar {
    width: 10px !important;
    display: block !important;
    background-color: #F8FAFC !important;
}

div[role="listbox"]::-webkit-scrollbar-thumb {
    background-color: #CBD5E1 !important;
    border-radius: 5px !important;
}

div[role="listbox"]::-webkit-scrollbar-thumb:hover {
    background-color: #94A3B8 !important;
}

li[role="option"] { font-size: 14px !important; padding: 8px !important; }

/* Main canvas styling */
.main {
    background-color: #F0F2F5 !important;
}

/* Card containers */
[data-testid="stVerticalBlock"] > [style*="flex-direction: column"] > [data-testid="stVerticalBlock"] {
    background-color: white !important;
    padding: 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05) !important;
    margin-bottom: 12px !important;
    border: 1px solid #E5E7EB !important;
}

/* Tab styling */
[data-testid="stTabs"] [data-testid="stTab"] {
    background-color: #F9FAFB !important;
    border-radius: 8px 8px 0 0 !important;
    padding: 10px 16px !important;
    font-size: 14px !important;
    font-family: 'Agency FB', sans-serif !important;
    color: #6B7280 !important;
    font-weight: bold !important;
    border: 1px solid #E5E7EB !important;
    border-bottom: none !important;
}

[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"] {
    background-color: #2E7D32 !important;
    color: #FFFFFF !important;
    border-color: #2E7D32 !important;
}

/* Radio button styling */
[data-testid="stRadio"] > div > div > div {
    background-color: #F9FAFB !important;
    border-radius: 8px !important;
    padding: 8px !important;
    border: 1px solid #E5E7EB !important;
}

/* Selectbox styling */
[data-testid="stSelectbox"] > div > div > div {
    background-color: #F9FAFB !important;
    border-radius: 8px !important;
    border: 1px solid #E5E7EB !important;
}

/* Remove sidebar */
[data-testid="stSidebar"] {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# Definición de la Lista Maestra de Métricas (Global)
METRICAS_ESPERADAS = [
    "Altura (cm)", "Peso (kg.)", "Masa Muscular (%)", "Masa Adiposa (%)", 
    "BroadJump", "BroadJump Distancia en mts", "SaltoSJ Altura (cm)", 
    "SaltoSJ Fza. Pico (+)", "SaltoSJ Relativa (N/kg)", "SaltoCMJ Altura (cm)", 
    "SaltoCMJ Braking Impulse (N·s/kg)", "SaltoCMJ Fza. Pico (+)", 
    "SaltoCMJ Relativa (N/kg)", "SaltoCMJ RSI-mod.", "SaltoCMJR Altura (cm)", 
    "SaltoCMJR GCT", "SaltoCMJR PASSIVE", "SaltoCMJR ACTIVE", 
    "Nordic IZQ.", "Nordic DER.", "Nordic débil/ fuerte dif.%", 
    "Iso30 IZQ.", "Iso30 DER.", "Iso30 dif.%", "IMTP Fza. Pico", 
    "IMTP Relativa (N/kg)", "IMTP DSI", "Velocidad Máxima (km/h)", 
    "Máx. ACC (m/s²)", "5m-10m-5m", "CMAS", "UNCa VFA (km/h)", "UNCa METROS"
]

# Función de normalización de columnas
def normalizar_columnas(df):
    """Normaliza los nombres de columnas para robustez"""
    df.columns = df.columns.str.strip()
    return df


def limpiar_datos_grafico(df, columnas_valor):
    """Elimina valores no finitos para que Plotly no renderice etiquetas NaN."""
    columnas_existentes = [col for col in columnas_valor if col in df.columns]
    if not columnas_existentes:
        return df.iloc[0:0].copy()
    datos = df.replace([np.inf, -np.inf], np.nan).copy()
    return datos.dropna(subset=columnas_existentes, how='all')

# Función para cargar datos desde Google Sheets
@st.cache_data(ttl=3600)
def cargar_datos_google_sheets():
    """Carga datos desde Google Sheets con manejo robusto de errores"""
    url = "https://docs.google.com/spreadsheets/d/1PiZ_kV-z0L0qxqZN1W6Re7woWN-5dM82Q8vWCCS3L84/export?format=csv&gid=1085591943"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        df = pd.read_csv(StringIO(response.text))
        
        # Normalizar encabezados y convertir todas las métricas con locale español.
        df.columns = df.columns.astype(str).str.strip()
        for metrica in METRICAS_ESPERADAS:
            if metrica in df.columns:
                df[metrica] = (
                    df[metrica]
                    .astype(str)
                    .str.strip()
                    .str.replace(',', '.', regex=False)
                )
                df[metrica] = pd.to_numeric(df[metrica], errors='coerce')
            else:
                df[metrica] = np.nan
        
        return df
    
    except Exception as e:
        st.error(f"Error al cargar datos desde Google Sheets: {str(e)}")
        return None

# Logo centrado
col1, col2, col3 = st.columns([3, 1, 3])
with col2:
    try:
        st.image("logo.jpeg", use_container_width=True)
    except:
        pass  # Si no existe el logo, continuar sin error

# Título Principal
st.markdown('<h1 style="text-align: center; color: #2E7D32;">MONITORIZACIÓN INSTITUCIONAL</h1>', unsafe_allow_html=True)

# Cargar datos
df = cargar_datos_google_sheets()

# REESTRUCTURACIÓN DEL PANEL DE FILTROS (Solo Fila 1)
if df is not None and not df.empty:
    columnas = df.columns.tolist()
    
    # Identificar columnas clave
    posibles_categorias = [col for col in columnas if 'categor' in col.lower() or 'categoria' in col.lower()]
    columna_categoria = posibles_categorias[0] if posibles_categorias else columnas[0] if len(columnas) > 0 else None
    
    posibles_meses = [col for col in columnas if 'mes' in col.lower() or 'month' in col.lower()]
    columna_mes = posibles_meses[0] if posibles_meses else columnas[1] if len(columnas) > 1 else None
    
    posibles_jugadores = [col for col in columnas if 'futbol' in col.lower() or 'jugador' in col.lower() or 'player' in col.lower() or 'atleta' in col.lower()]
    columna_jugador = posibles_jugadores[0] if posibles_jugadores else columnas[2] if len(columnas) > 2 else None

    if columna_jugador:
        df[columna_jugador] = df[columna_jugador].astype('string').str.strip()
    
    # Usar la lista maestra de métricas para los selectores
    metricas_disponibles = [m for m in METRICAS_ESPERADAS if m in df.columns]
    
    # FILA 1: 3 Columnas (Categoría, Mes, Futbolista)
    col_cat, col_mes, col_jug = st.columns(3)
    
    with col_cat:
        if columna_categoria:
            categorias_unicas = df[columna_categoria].dropna().unique().tolist()
            if categorias_unicas:
                categorias_opciones = ['TODAS'] + [str(cat) for cat in categorias_unicas]
                categoria_seleccionada = st.multiselect(
                    "Categoría",
                    categorias_opciones,
                    default=['TODAS']
                )
                
                if 'TODAS' not in categoria_seleccionada and categoria_seleccionada:
                    df = df[df[columna_categoria].isin(categoria_seleccionada)]
    
    with col_mes:
        if columna_mes:
            meses_unicos = df[columna_mes].dropna().unique().tolist()
            if meses_unicos:
                meses_opciones = ['TODOS'] + [str(mes) for mes in meses_unicos]
                mes_seleccionado = st.multiselect(
                    "Mes de registro",
                    meses_opciones,
                    default=['TODOS']
                )
                
                if 'TODOS' not in mes_seleccionado and mes_seleccionado:
                    df = df[df[columna_mes].isin(mes_seleccionado)]
    
    with col_jug:
        if columna_jugador:
            jugadores_unicos = df[columna_jugador].dropna().unique().tolist()
            if jugadores_unicos:
                jugadores_opciones = ['TODOS'] + [str(jug) for jug in jugadores_unicos]
                jugadores_seleccionados = st.multiselect(
                    "Futbolista",
                    jugadores_opciones,
                    default=['TODOS']
                )
                
                if 'TODOS' not in jugadores_seleccionados and jugadores_seleccionados:
                    df = df[df[columna_jugador].isin(jugadores_seleccionados)]
    
    # Métricas de Rendimiento (con opción TODAS)
    if metricas_disponibles:
        metricas_opciones = ['TODAS'] + metricas_disponibles
        metricas_seleccionadas = st.multiselect(
            "Métricas de Rendimiento",
            metricas_opciones,
            default=['TODAS']
        )
        
        # Lógica TODAS
        if 'TODAS' in metricas_seleccionadas:
            metricas_seleccionadas = metricas_disponibles
        else:
            metricas_seleccionadas = [m for m in metricas_seleccionadas if m in metricas_disponibles]
    else:
        metricas_seleccionadas = []
    
    st.markdown("---")
    
    # Limpieza y Coerción de Datos (Data Cleaning)
    if metricas_seleccionadas:
        for col in metricas_seleccionadas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

else:
    st.info("Cargando datos desde Google Sheets...")
    metricas_seleccionadas = []
    columna_jugador = None
    columna_categoria = None
    columna_mes = None
    jugadores_seleccionados = ['TODOS']
    categoria_seleccionada = ['TODAS']
    mes_seleccionado = ['TODOS']

# PESTAÑAS
if df is not None and not df.empty and metricas_seleccionadas and columna_jugador:
    tab1, tab2 = st.tabs(["Métricas", "Z-Score"])
    
    # PESTAÑA 1: MÉTRICAS - Motor de Doble Eje
    with tab1:
        # Tipo de Gráfico (DENTRO de Tab 1)
        tipo_grafico = st.selectbox(
            "Tipo de Gráfico",
            ["Gráfico de Barras Simple", "Gráfico Combinado (Barras y Líneas)"]
        )
        
        if tipo_grafico == "Gráfico de Barras Simple":
            # Lógica actual: Gráficos de barras simples
            for metrica in metricas_seleccionadas:
                if metrica in df.columns and columna_jugador in df.columns:
                    df_metrica = df.groupby(columna_jugador)[metrica].mean(numeric_only=True).reset_index()
                    df_metrica = limpiar_datos_grafico(df_metrica, [metrica])
                    df_metrica = df_metrica.sort_values(by=metrica, ascending=False)

                    if df_metrica.empty:
                        continue
                    
                    # Convertir columna Futbolista a string estrictamente
                    df_metrica[columna_jugador] = df_metrica[columna_jugador].astype(str)
                    
                    fig = px.bar(
                        df_metrica,
                        x=columna_jugador,
                        y=metrica,
                        color=columna_jugador,
                        color_discrete_sequence=px.colors.qualitative.Alphabet
                    )
                    
                    # Configurar las etiquetas (Textos gigantes)
                    fig.update_traces(
                        texttemplate='%{y:.2f}',
                        textposition='outside',
                        textfont=dict(size=12, color='black', family='Arial Black'),
                        cliponaxis=False
                    )
                    
                    # Configuración Plotly con barras ultra gruesas
                    fig.update_layout(
                        height=600,
                        bargap=0.1,
                        bargroupgap=0.0,
                        showlegend=False,
                        margin=dict(t=80, b=120),
                        title=dict(text=f"<b>{metrica}</b>", x=0.5, font=dict(size=18, color="#1E293B")),
                        xaxis_title="Futbolista",
                        yaxis_title=metrica,
                        font=dict(family='Agency FB', size=14)
                    )
                    
                    # Eje X (Futbolistas) - CRÍTICO: categórico con tickmode='linear'
                    fig.update_xaxes(type='category', tickmode='linear', tickangle=-45, tickfont=dict(size=12, family="Agency FB", color="black"))
                    
                    # Eje Y (Métrica)
                    fig.update_yaxes(tickfont=dict(size=12))
                    
                    # Grosor nuclear de barras
                    fig.update_traces(width=0.75, selector=dict(type='bar'))
                    
                    st.plotly_chart(
                        fig, 
                        use_container_width=True,
                        config={'displayModeBar': False}
                    )
                else:
                    continue
        
        else:
            # Gráfico Combinado (Barras y Líneas) - Motor de Doble Eje
            # Selectores de Eje Primario/Secundario
            col_prim, col_sec = st.columns(2)
            
            with col_prim:
                metricas_primarias = st.multiselect(
                    "Métricas Eje Primario (Barras)",
                    metricas_disponibles,
                    default=metricas_disponibles[:1] if len(metricas_disponibles) >= 1 else metricas_disponibles
                )
            
            with col_sec:
                metricas_secundarias = st.multiselect(
                    "Métricas Eje Secundario (Líneas)",
                    metricas_disponibles,
                    default=metricas_disponibles[1:2] if len(metricas_disponibles) >= 2 else []
                )
            
            if metricas_primarias or metricas_secundarias:
                # Preparar datos agrupados por futbolista
                df_agrupado = df.groupby(columna_jugador).mean(numeric_only=True).reset_index()
                metricas_combinadas = metricas_primarias + metricas_secundarias
                df_agrupado = limpiar_datos_grafico(df_agrupado, metricas_combinadas)
                df_agrupado[columna_jugador] = df_agrupado[columna_jugador].astype(str)
                
                # Crear subplots con doble eje Y
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                # Eje Y Primario (Barras) - COLOR VERDE FIJO
                for idx, metrica in enumerate(metricas_primarias):
                    if metrica in df_agrupado.columns:
                        fig.add_trace(
                            go.Bar(
                                x=df_agrupado[columna_jugador],
                                y=df_agrupado[metrica],
                                name=metrica,
                                text=df_agrupado[metrica].where(df_agrupado[metrica].notna(), None),
                                textposition='outside',
                                marker_color='#22C55E',
                                textfont=dict(size=12, color='black', family='Arial Black')
                            ),
                            secondary_y=False
                        )
                
                # Eje Y Secundario (Líneas) - COLOR DORADO FUERTE
                for idx, metrica in enumerate(metricas_secundarias):
                    if metrica in df_agrupado.columns:
                        fig.add_trace(
                            go.Scatter(
                                x=df_agrupado[columna_jugador],
                                y=df_agrupado[metrica],
                                name=metrica,
                                mode='lines+markers+text',
                                text=df_agrupado[metrica].where(df_agrupado[metrica].notna(), None),
                                textposition='bottom center',
                                line=dict(color='#F59E0B', width=3),
                                marker=dict(size=8, line=dict(width=1, color='black')),
                                textfont=dict(size=12, color='#B45309', family='Arial Black'),
                                texttemplate='<b>%{text:.2f}</b>'
                            ),
                            secondary_y=True
                        )
                
                # Configuración del gráfico combinado
                fig.update_layout(
                    title=dict(text="Gráfico Combinado: Barras y Líneas", x=0.5, y=0.98, xanchor='center', yanchor='top', font=dict(size=18, color="#1E293B")),
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.08,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=12, family='Agency FB')
                    ),
                    bargap=0.15,
                    margin=dict(t=150, b=100, l=80, r=80),
                    xaxis_title="Futbolista",
                    font=dict(family='Agency FB', size=14),
                    height=700
                )
                
                # Eje X categórico - COLOR NEGRO
                fig.update_xaxes(type='category', tickangle=-45, tickfont=dict(color='black', size=12))
                
                # Ejes Y - COLOR NEGRO
                fig.update_yaxes(tickfont=dict(color='black', size=12), title_text="Eje Primario (Barras)", secondary_y=False)
                fig.update_yaxes(tickfont=dict(color='black', size=12), title_text="Eje Secundario (Líneas)", secondary_y=True)
                
                # Grosor nuclear de barras
                fig.update_traces(width=0.75, selector=dict(type='bar'))
                
                st.plotly_chart(
                    fig, 
                    use_container_width=True,
                    config={'displayModeBar': False}
                )
            else:
                st.warning("Selecciona al menos una métrica para el Eje Primario o Secundario")
    
    # PESTAÑA 2: Z-SCORE
    with tab2:
        if metricas_seleccionadas and columna_jugador:
            # Toggle para elegir vista
            vista_zscore = st.radio(
                "Seleccione la vista de análisis:",
                ["Perfil Comparativo (Agrupado)", "Ranking por Métrica (Horizontal)"],
                horizontal=True
            )
            
            # Guardar las selecciones actuales
            df_original = cargar_datos_google_sheets()
            
            if df_original is not None and isinstance(df_original, pd.DataFrame):
                # Filtrar df_poblacion por Categoría y Mes seleccionados
                df_poblacion = df_original.copy()
                
                if columna_categoria and 'categoria_seleccionada' in locals() and 'TODAS' not in categoria_seleccionada:
                    df_poblacion = df_poblacion[df_poblacion[columna_categoria].isin(categoria_seleccionada)]
                
                if columna_mes and 'mes_seleccionado' in locals() and 'TODOS' not in mes_seleccionado:
                    df_poblacion = df_poblacion[df_poblacion[columna_mes].isin(mes_seleccionado)]
                
                # Filtrar df_jugadores (si TODOS, igual a df_poblacion)
                if 'jugadores_seleccionados' in locals() and 'TODOS' not in jugadores_seleccionados:
                    df_jugadores = df_poblacion[df_poblacion[columna_jugador].isin(jugadores_seleccionados)].copy()
                else:
                    df_jugadores = df_poblacion.copy()
                
                # Calcular Z-Scores con la lógica especificada
                z_scores_data = []
                
                for metrica in metricas_seleccionadas:
                    if metrica in df_poblacion.columns:
                        # Calcular media y desviación de la población
                        media = df_poblacion[metrica].mean(numeric_only=True)
                        desviacion = df_poblacion[metrica].std(numeric_only=True)
                        
                        # Evitar división por cero y manejo de NaNs
                        if desviacion == 0 or pd.isna(desviacion):
                            desviacion = 1
                        if pd.isna(media):
                            media = 0
                        
                        # Calcular Z-Score para cada jugador seleccionado
                        for _, fila in df_jugadores.iterrows():
                            if metrica in fila and pd.notna(fila[metrica]):
                                z_val = (fila[metrica] - media) / desviacion
                                z_scores_data.append({
                                    'Futbolista': fila[columna_jugador],
                                    'Métrica': metrica,
                                    'Z-Score': z_val
                                })
                
                # Crear DataFrame de Z-Scores
                if z_scores_data:
                    df_zscore = pd.DataFrame(z_scores_data)
                    df_zscore['Z-Score'] = pd.to_numeric(df_zscore['Z-Score'], errors='coerce')
                    df_zscore = df_zscore.replace([np.inf, -np.inf], np.nan).dropna(subset=['Futbolista', 'Métrica', 'Z-Score'])
                    
                    if vista_zscore == "Ranking por Métrica (Horizontal)":
                        # LADO A: Ranking por Métrica - Horizontal
                        for metrica in metricas_seleccionadas:
                            # Filtrar df_zscore para esa métrica específica
                            df_metrica = df_zscore[df_zscore['Métrica'] == metrica].copy()
                            
                            if not df_metrica.empty:
                                # Ordenar los datos (mejor Z-Score arriba)
                                df_metrica = df_metrica.sort_values(by='Z-Score', ascending=True)
                                
                                # Crear color dinámico según Z-Score
                                colors = ['#22C55E' if x > 0 else '#EF4444' for x in df_metrica['Z-Score']]
                                
                                # Crear gráfico de barras horizontales SIN color
                                fig = px.bar(
                                    df_metrica,
                                    x='Z-Score',
                                    y='Futbolista',
                                    orientation='h'
                                )
                                
                                # Aplicar color DESPUÉS
                                fig.update_traces(
                                    marker_color=colors,
                                    texttemplate='%{x:.2f}',
                                    textposition='outside',
                                    textfont=dict(size=16, color='black')
                                )
                                
                                # Configuración Plotly Z-Score
                                fig.update_layout(
                                    height=max(400, len(df_metrica)*40),
                                    showlegend=False,
                                    title=dict(text=f"<b>Z-Score: {metrica}</b>", x=0.5, font=dict(size=20, color="#1E293B")),
                                    xaxis_title="Z-Score",
                                    yaxis_title="",
                                    margin=dict(t=80, b=80, l=150, r=80),
                                    font=dict(family='Agency FB', size=16),
                                    bargap=0.2
                                )
                                
                                # Ancho de barras uniforme
                                fig.update_traces(width=0.5)
                                
                                # Línea base poblacional
                                fig.add_vline(x=0, line_width=3, line_dash="dash", line_color="black")
                                
                                # Tamaño de nombres de jugadores en Eje Y
                                fig.update_yaxes(tickfont=dict(size=16, family="Agency FB", color="black"))
                                
                                # Eje X
                                fig.update_xaxes(tickfont=dict(size=18, family="Agency FB", color="black"))
                                
                                st.plotly_chart(
                                    fig, 
                                    use_container_width=True,
                                    config={'displayModeBar': False}
                                )
                    
                    else:
                        # LADO B: Perfil Comparativo - Agrupado
                        fig = px.bar(
                            df_zscore,
                            x='Métrica',
                            y='Z-Score',
                            color='Futbolista',
                            color_discrete_sequence=px.colors.qualitative.Alphabet,
                            barmode='group'
                        )
                        
                        # Línea negra en Y=0
                        fig.add_hline(y=0, line_width=2, line_dash="dash", line_color="black")
                        
                        # Configuración del gráfico agrupado
                        fig.update_layout(
                            title=dict(text="Z-Score por Métrica y Futbolista", y=0.95, x=0.5, xanchor='center', yanchor='top', font=dict(size=20, color="#1E293B")),
                            showlegend=True,
                            legend=dict(
                                title_text='',
                                font=dict(size=16),
                                orientation="h",
                                yanchor="bottom",
                                y=1.20,
                                xanchor="center",
                                x=0.5
                            ),
                            bargap=0.15,
                            bargroupgap=0.05,
                            margin=dict(t=250, b=100, l=60, r=60),
                            xaxis_title="Métrica",
                            yaxis_title="Z-Score",
                            font=dict(family='Agency FB', size=16),
                            height=700
                        )
                        
                        # Textos de datos
                        fig.update_traces(
                            texttemplate='%{y:.2f}',
                            textposition='outside',
                            textfont=dict(size=16, color='black', family='Arial Black'),
                            cliponaxis=False
                        )

                        fig.update_xaxes(
                            tickangle=-45,
                            tickfont=dict(size=18, family="Agency FB", color="black"),
                            automargin=True
                        )
                        
                        st.plotly_chart(
                            fig, 
                            use_container_width=True,
                            config={'displayModeBar': False}
                        )
                else:
                    st.warning("No se pudieron calcular los Z-Scores con los datos disponibles")
            else:
                st.warning("Error al cargar datos para cálculo de Z-Score")
        else:
            st.warning("Selecciona métricas y asegúrate de que hay datos de futbolistas disponibles")

elif df is not None and df.empty:
    st.warning("El DataFrame está vacío después de aplicar los filtros. Intenta con otros criterios.")
else:
    st.info("Los datos se están cargando desde Google Sheets. Por favor, espera unos segundos...")
