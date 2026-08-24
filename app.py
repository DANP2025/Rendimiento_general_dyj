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

# Inyección de estilos CSS compacto
st.markdown("""<style>
* { font-family: 'Agency FB', sans-serif !important; }
header[data-testid="stHeader"] { display: none !important; }
[data-testid="stAppViewContainer"] { overflow-y: auto !important; overflow-x: hidden !important; scroll-behavior: smooth !important; }
div[data-testid="stTabs"] button p, [data-baseweb="tab"] p, [data-baseweb="tab"] div, [data-baseweb="tab"] span, [data-baseweb="tab"] { font-size: 22px !important; font-family: 'Agency FB', sans-serif !important; font-weight: 800 !important; letter-spacing: 0.5px !important; }
div[data-testid="stTabs"] button[aria-selected="true"] p, [data-baseweb="tab"][aria-selected="true"] p { color: #2E7D32 !important; }
div[data-testid="stTabs"] button[aria-selected="true"] { border-bottom: 3px solid #2E7D32 !important; }
[data-testid="stWidgetLabel"] p, label p, .stMultiSelect label p, .stSelectbox label p, .stRadio label p { font-size: 22px !important; font-family: 'Agency FB', sans-serif !important; font-weight: 800 !important; color: #0F172A !important; }
[data-baseweb="select"] > div { border: 2px solid #2E7D32 !important; border-radius: 8px !important; background-color: #FFFFFF !important; min-height: 44px !important; box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important; }
[data-baseweb="select"] > div:hover, [data-baseweb="select"] > div:focus-within { border-color: #1B5E20 !important; box-shadow: 0 0 8px rgba(46, 125, 50, 0.4) !important; }
[data-baseweb="select"] div, [data-baseweb="select"] span { font-size: 20px !important; font-family: 'Agency FB', sans-serif !important; font-weight: 700 !important; color: #0F172A !important; }
[data-baseweb="tag"], [data-baseweb="tag"] * { background-color: transparent !important; background: transparent !important; border: none !important; box-shadow: none !important; }
[data-baseweb="tag"] span { color: #0F172A !important; font-size: 20px !important; font-weight: 800 !important; font-family: 'Agency FB', sans-serif !important; }
[data-baseweb="tag"] svg, [data-baseweb="tag"] button { display: none !important; width: 0 !important; height: 0 !important; }
[data-testid="stRadio"] div[role="radiogroup"] * { font-size: 20px !important; font-family: 'Agency FB', sans-serif !important; font-weight: 700 !important; color: #0F172A !important; }
[data-testid="stRadio"] input[type="radio"]:checked + div { background-color: #2E7D32 !important; border-color: #2E7D32 !important; }
.btn-flotante-arriba { position: fixed !important; bottom: 75px !important; right: 20px !important; background-color: #2E7D32 !important; color: #FFFFFF !important; padding: 10px 20px !important; border-radius: 30px !important; font-family: 'Agency FB', sans-serif !important; font-size: 18px !important; font-weight: bold !important; text-decoration: none !important; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important; z-index: 999999 !important; display: flex !important; align-items: center !important; gap: 6px !important; transition: all 0.2s ease-in-out !important; }
.btn-flotante-arriba:hover { background-color: #1B5E20 !important; transform: translateY(-3px) !important; color: #FFFFFF !important; }
</style>""", unsafe_allow_html=True)

# Ancla al inicio absoluto
st.markdown('<div id="inicio-pagina" style="scroll-margin-top: 50px;"></div>', unsafe_allow_html=True)

# Botón flotante
st.markdown('<a href="#inicio-pagina" class="btn-flotante-arriba">⬆ Subir a Filtros</a>', unsafe_allow_html=True)

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
def cargar_datos_google_sheets(cache_buster=""):
    """Carga datos desde Google Sheets con manejo robusto de errores"""
    url = (
        "https://docs.google.com/spreadsheets/d/1PiZ_kV-z0L0qxqZN1W6Re7woWN-5dM82Q8vWCCS3L84/"
        f"export?format=csv&gid=1085591943&_={cache_buster}"
    )
    
    try:
        response = requests.get(
            url,
            headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
            timeout=30
        )
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
        st.image("logo.jpeg", width=140)
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
    
    # FILA 1: 4 Columnas (Categoría, Mes, Futbolista, Métricas)
    contenedor_filtros = st.container()
    with contenedor_filtros:
        st.markdown('<div id="marcador-filtros"></div>', unsafe_allow_html=True)

        col_cat, col_mes, col_jug, col_met = st.columns(4)
        df_cat = df

        with col_cat:
            if columna_categoria:
                st.markdown("<p style='font-family: Agency FB; font-size: 18px; font-weight: 700; color: #0F172A; margin-bottom: 2px;'>CATEGORÍA</p>", unsafe_allow_html=True)
                opciones_cat = ['TODAS'] + sorted([str(x) for x in df[columna_categoria].dropna().unique()])
                categoria_seleccionada = st.multiselect("CATEGORÍA", opciones_cat, default=['TODAS'], label_visibility="collapsed")
                if 'TODAS' not in categoria_seleccionada and categoria_seleccionada:
                    df_cat = df[df[columna_categoria].astype(str).isin(categoria_seleccionada)]
                df = df_cat
    
        df_mes = df_cat
        with col_mes:
            if columna_mes:
                st.markdown("<p style='font-family: Agency FB; font-size: 18px; font-weight: 700; color: #0F172A; margin-bottom: 2px;'>MES DE REGISTRO</p>", unsafe_allow_html=True)
                opciones_mes = ['TODOS'] + sorted([str(x) for x in df_cat[columna_mes].dropna().unique()])
                mes_seleccionado = st.multiselect("MES DE REGISTRO", opciones_mes, default=['TODOS'], label_visibility="collapsed")
                if 'TODOS' not in mes_seleccionado and mes_seleccionado:
                    df_mes = df_cat[df_cat[columna_mes].astype(str).isin(mes_seleccionado)]
                df = df_mes
    
        df_filtrado = df_mes
        with col_jug:
            if columna_jugador:
                st.markdown("<p style='font-family: Agency FB; font-size: 18px; font-weight: 700; color: #0F172A; margin-bottom: 2px;'>FUTBOLISTA</p>", unsafe_allow_html=True)
                opciones_jug = ['TODOS'] + sorted([str(x) for x in df_mes[columna_jugador].dropna().unique()])
                jugadores_seleccionados = st.multiselect("FUTBOLISTA", opciones_jug, default=['TODOS'], label_visibility="collapsed")
                if 'TODOS' not in jugadores_seleccionados and jugadores_seleccionados:
                    df_filtrado = df_mes[df_mes[columna_jugador].astype(str).isin(jugadores_seleccionados)]
                df = df_filtrado
    
        with col_met:
            st.markdown("<p style='font-family: Agency FB; font-size: 18px; font-weight: 700; color: #0F172A; margin-bottom: 2px;'>MÉTRICAS DE RENDIMIENTO</p>", unsafe_allow_html=True)
            opciones_met = ['TODAS'] + metricas_disponibles
            sel_met = st.multiselect("MÉTRICAS DE RENDIMIENTO", opciones_met, default=['TODAS'], label_visibility="collapsed")
            metricas_seleccionadas = metricas_disponibles if ('TODAS' in sel_met or not sel_met) else [m for m in sel_met if m in metricas_disponibles]
    
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
        # Selector de tipo y ejes en una sola fila.
        col_tipo, col_eje1, col_eje2 = st.columns([1.2, 1.4, 1.4])

        with col_tipo:
            st.markdown("<p style='font-family: Agency FB; font-size: 22px; font-weight: 800; color: #0F172A; margin-bottom: 2px;'>TIPO DE GRÁFICO</p>", unsafe_allow_html=True)
            tipo_grafico = st.selectbox(
                "TIPO DE GRÁFICO",
                ["GRÁFICO DE BARRAS SIMPLE", "GRÁFICO COMBINADO (BARRAS Y LÍNEAS)"],
                label_visibility="collapsed"
            )

        if tipo_grafico == "GRÁFICO COMBINADO (BARRAS Y LÍNEAS)":
            with col_eje1:
                st.markdown("<p style='font-family: Agency FB; font-size: 22px; font-weight: 800; color: #0F172A; margin-bottom: 2px;'>MÉTRICAS EJE PRIMARIO (BARRAS)</p>", unsafe_allow_html=True)
                metrica_primaria = st.selectbox("EJE PRIMARIO", metricas_disponibles, index=0, label_visibility="collapsed")

            with col_eje2:
                st.markdown("<p style='font-family: Agency FB; font-size: 22px; font-weight: 800; color: #0F172A; margin-bottom: 2px;'>MÉTRICAS EJE SECUNDARIO (LÍNEAS)</p>", unsafe_allow_html=True)
                idx_sec = 1 if len(metricas_disponibles) > 1 else 0
                metrica_secundaria = st.selectbox("EJE SECUNDARIO", metricas_disponibles, index=idx_sec, label_visibility="collapsed")

            st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
        
        if tipo_grafico == "GRÁFICO DE BARRAS SIMPLE":
            # Lógica actual: Gráficos de barras simples
            for metrica in metricas_seleccionadas:
                if metrica in df.columns and columna_jugador in df.columns:
                    df_metrica = df.groupby(columna_jugador)[metrica].mean(numeric_only=True).reset_index()
                    df_metrica = limpiar_datos_grafico(df_metrica, [metrica])

                    if df_metrica.empty:
                        continue
                    
                    # Convertir columna Futbolista a string estrictamente
                    df_metrica[columna_jugador] = df_metrica[columna_jugador].astype(str)
                    df_metrica = df_metrica.sort_values(
                        by=columna_jugador,
                        key=lambda nombres: nombres.str.casefold(),
                        ascending=True
                    )
                    
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
                        margin=dict(t=80, b=120, l=20, r=20),
                        title=dict(text=f"<b>{metrica}</b>", x=0.5, font=dict(size=18, color="#1E293B")),
                        xaxis_title="Futbolista",
                        yaxis_title=metrica,
                        font=dict(family='Agency FB', size=14)
                    )
                    
                    # Eje X (Futbolistas) - CRÍTICO: categórico con tickmode='linear'
                    fig.update_xaxes(
                        type='category',
                        range=[-0.5, len(df_metrica) - 0.5],
                        tickmode='linear',
                        tickangle=-45,
                        tickfont=dict(size=12, family="Agency FB", color="black")
                    )
                    
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
            metricas_primarias = [metrica_primaria]
            metricas_secundarias = [metrica_secundaria]
            
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
                    margin=dict(t=150, b=100, l=20, r=20),
                    xaxis_title="Futbolista",
                    font=dict(family='Agency FB', size=14),
                    height=700
                )
                
                # Eje X categórico - COLOR NEGRO
                fig.update_xaxes(
                    type='category',
                    range=[-0.5, len(df_agrupado) - 0.5],
                    tickangle=-45,
                    tickfont=dict(color='black', size=12)
                )
                
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
                                # Filtrar y ordenar alfabéticamente de la A a la Z por Futbolista
                                df_plot = df_metrica.dropna(subset=['Z-Score']).sort_values(
                                    by='Futbolista', ascending=True
                                )

                                # Generar colores sincronizados con el DataFrame ordenado
                                colores = [
                                    '#22C55E' if val >= 0 else '#EF4444'
                                    for val in df_plot['Z-Score']
                                ]

                                if df_plot.empty:
                                    continue

                                # Crear el gráfico horizontal
                                fig = px.bar(
                                    df_plot,
                                    x='Z-Score',
                                    y='Futbolista',
                                    orientation='h'
                                )
                                
                                # Asignar colores, etiquetas y estilos a las barras
                                fig.update_traces(
                                    marker_color=colores,
                                    texttemplate='%{x:.2f}',
                                    textposition='outside',
                                    cliponaxis=False,
                                    textfont=dict(size=16, color='#0F172A', family='Agency FB')
                                )

                                fig.update_yaxes(
                                    type='category',
                                    categoryorder='category descending',
                                    tickfont=dict(size=16, color='#0F172A', family='Agency FB')
                                )

                                fig.update_xaxes(
                                    tickfont=dict(size=14, color='#0F172A'),
                                    title_text="Z-Score",
                                    title_font=dict(size=16, color='#0F172A', family='Agency FB')
                                )
                                
                                # Configuración Plotly Z-Score
                                fig.update_layout(
                                    height=max(350, len(df_plot) * 40),
                                    showlegend=False,
                                    title=dict(text=f"<b>Z-Score: {metrica}</b>", x=0.5, font=dict(size=20, color="#1E293B")),
                                    yaxis_title="",
                                    margin=dict(t=60, b=50, l=150, r=60),
                                    font=dict(family='Agency FB', size=16),
                                    bargap=0.2
                                )
                                
                                # Ancho de barras uniforme
                                fig.update_traces(width=0.5)
                                
                                # Línea base poblacional
                                fig.add_vline(x=0, line_width=2, line_dash="dash", line_color="#0F172A")
                                
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
