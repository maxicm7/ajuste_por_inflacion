import streamlit as st
import pandas as pd
import datetime

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Calculadora de Ajuste por Inflación (Simplificada)",
    page_icon="🇦🇷",
    layout="wide"
)

# --- Funciones Auxiliares ---

@st.cache_data # Usamos cache para no cargar el archivo IPC cada vez
def cargar_ipc():
    """Carga los datos del IPC desde un archivo local y los prepara."""
    try:
        # Asumimos que el archivo ipc_data.csv está en la misma carpeta
        df_ipc = pd.read_csv('ipc_data.csv')
        # La columna de fecha del IPC oficial viene en formato 'YYYY-MM-DD'
        df_ipc['fecha'] = pd.to_datetime(df_ipc['fecha'], format='%Y-%m-%d')
        df_ipc.set_index('fecha', inplace=True)
        # Nos aseguramos de que el índice esté ordenado
        df_ipc.sort_index(inplace=True)
        return df_ipc
    except FileNotFoundError:
        st.error("Error: No se encontró el archivo 'ipc_data.csv'. Asegúrate de que esté en la misma carpeta que la app.")
        return None

def ajustar_dataframe(df, fecha_cierre, df_ipc):
    """
    Aplica el ajuste por inflación al DataFrame proporcionado por el usuario.
    """
    # 1. Preparar datos y buscar IPC de cierre
    # El IPC de cierre es el del último día del mes de la fecha de cierre
    fecha_ipc_cierre = fecha_cierre.replace(day=1) - datetime.timedelta(days=1)
    fecha_ipc_cierre = fecha_ipc_cierre.replace(day=1) # Llevamos al primer día del mes para buscar en el índice
    
    try:
        ipc_cierre = df_ipc.loc[fecha_ipc_cierre, 'ipc_valor']
    except KeyError:
        st.error(f"No se encontró el IPC para la fecha de cierre ({fecha_cierre.strftime('%d-%m-%Y')}). Por favor, elige una fecha con datos disponibles.")
        return None

    # 2. Listas para almacenar los resultados
    coeficientes = []
    valores_ajustados = []
    ajustes_recpam = []
    
    # 3. Iterar por cada fila para calcular el ajuste
    for index, row in df.iterrows():
        fecha_origen = row['Fecha']
        monto_historico = row['Monto_Historico']

        # El IPC de origen es el del último día del mes ANTERIOR a la compra
        fecha_ipc_origen = fecha_origen.replace(day=1) - datetime.timedelta(days=1)
        fecha_ipc_origen = fecha_ipc_origen.replace(day=1) # Llevamos al primer día del mes para buscar
        
        try:
            ipc_origen = df_ipc.loc[fecha_ipc_origen, 'ipc_valor']
            
            # Fórmula del ajuste
            coeficiente = ipc_cierre / ipc_origen
            valor_ajustado = monto_historico * coeficiente
            ajuste_recpam = valor_ajustado - monto_historico

            coeficientes.append(coeficiente)
            valores_ajustados.append(valor_ajustado)
            ajustes_recpam.append(ajuste_recpam)
        
        except KeyError:
            # Si no hay IPC de origen, no podemos ajustar
            st.warning(f"No se encontró IPC para la fecha de origen {fecha_origen.strftime('%d-%m-%Y')} en la fila {index+1}. Se dejará sin ajustar.")
            coeficientes.append(1.0)
            valores_ajustados.append(monto_historico)
            ajustes_recpam.append(0.0)

    # 4. Agregar las nuevas columnas al DataFrame
    df_resultado = df.copy()
    df_resultado['Coeficiente'] = coeficientes
    df_resultado['Monto_Ajustado'] = valores_ajustados
    df_resultado['Ajuste_RECPAM'] = ajustes_recpam
    
    return df_resultado

# --- Interfaz de la App ---

st.title("📈 Calculadora de Ajuste por Inflación (Simplificada)")
st.markdown("""
Esta herramienta te permite ajustar partidas por inflación según el **IPC Nacional (base Diciembre 2016)**. 
Es una **demostración simplificada** del mecanismo de reexpresión, útil para entender el impacto de la inflación en bienes, activos o gastos.

**Importante:** Esto no reemplaza el cálculo completo y legal del Ajuste por Inflación Impositivo o Contable, que es mucho más complejo.
""")

# Cargar datos del IPC
df_ipc = cargar_ipc()

if df_ipc is not None:
    # --- Barra Lateral con Entradas del Usuario ---
    with st.sidebar:
        st.header("1. Carga tu archivo")
        uploaded_file = st.file_uploader(
            "Selecciona un archivo CSV o Excel",
            type=["csv", "xlsx"]
        )

        st.markdown("---")
        st.header("2. Elige la fecha de cierre")
        fecha_cierre = st.date_input(
            "¿A qué fecha quieres ajustar los valores?",
            datetime.date(2023, 12, 31),
            min_value=datetime.date(2017, 1, 1),
            max_value=datetime.date.today()
        )
    
    # --- Área Principal ---
    if uploaded_file is not None:
        try:
            # Leer el archivo subido por el usuario
            if uploaded_file.name.endswith('.csv'):
                df_usuario = pd.read_csv(uploaded_file, sep=';', decimal=',')
            else:
                df_usuario = pd.read_excel(uploaded_file)
            
            # Validar y convertir las columnas necesarias
            if not {'Fecha', 'Monto_Historico'}.issubset(df_usuario.columns):
                st.error("El archivo debe contener las columnas 'Fecha' y 'Monto_Historico'.")
            else:
                df_usuario['Fecha'] = pd.to_datetime(df_usuario['Fecha'], dayfirst=True)
                
                st.subheader("Datos Originales Cargados")
                st.dataframe(df_usuario)

                # Procesar y mostrar resultados
                with st.spinner('Calculando ajuste por inflación...'):
                    df_resultado = ajustar_dataframe(df_usuario, fecha_cierre, df_ipc)

                if df_resultado is not None:
                    st.subheader(f"📊 Resultados Ajustados al {fecha_cierre.strftime('%d/%m/%Y')}")
                    
                    # Formatear columnas para mejor visualización
                    df_display = df_resultado.style.format({
                        "Monto_Historico": "AR$ {:,.2f}",
                        "Coeficiente": "{:.4f}",
                        "Monto_Ajustado": "AR$ {:,.2f}",
                        "Ajuste_RECPAM": "AR$ {:,.2f}",
                        "Fecha": lambda x: x.strftime("%d/%m/%Y")
                    })
                    st.dataframe(df_display, use_container_width=True)

                    # Mostrar totales
                    st.subheader("Totales Generales")
                    total_historico = df_resultado['Monto_Historico'].sum()
                    total_ajustado = df_resultado['Monto_Ajustado'].sum()
                    total_recpam = df_resultado['Ajuste_RECPAM'].sum()

                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Valor Histórico", f"AR$ {total_historico:,.2f}")
                    col2.metric("Total Valor Ajustado", f"AR$ {total_ajustado:,.2f}")
                    col3.metric("Total Ajuste (RECPAM)", f"AR$ {total_recpam:,.2f}", delta=f"{((total_ajustado/total_historico - 1)*100):.2f}% de aumento")

                    # Opción para descargar
                    @st.cache_data
                    def convert_df_to_csv(df):
                        return df.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')

                    csv = convert_df_to_csv(df_resultado)
                    st.download_button(
                       label="📥 Descargar Resultados en CSV",
                       data=csv,
                       file_name=f'ajuste_inflacion_{fecha_cierre.strftime("%Y%m%d")}.csv',
                       mime='text/csv',
                    )

        except Exception as e:
            st.error(f"Ocurrió un error al procesar el archivo: {e}")
            st.info("Asegúrate de que el archivo tenga el formato correcto: columnas 'Fecha' (dd/mm/aaaa) y 'Monto_Historico' (números con coma decimal).")

    else:
        st.info("⬅️ Sube un archivo y elige una fecha de cierre para comenzar.")
        st.markdown("---")
        st.subheader("Formato del archivo de entrada:")
        st.markdown("""
        Tu archivo (CSV o Excel) debe tener al menos 3 columnas:
        - `Descripcion`: Texto que identifica la partida.
        - `Fecha`: La fecha de la compra/origen en formato **DD/MM/AAAA**.
        - `Monto_Historico`: El valor original en pesos. Usa **coma (,)** como separador decimal si es un CSV.
        
        Puedes descargar un archivo de ejemplo para usar como plantilla:
        """)
        # Crear un link de descarga para el archivo de ejemplo
        with open("ejemplo.xlsx", "rb") as file:
            st.download_button(
                label="Descargar plantilla de ejemplo (Excel)",
                data=file,
                file_name="ejemplo.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
