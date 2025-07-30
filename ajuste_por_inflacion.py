import streamlit as st
import pandas as pd
import datetime
import io # _# NUEVO: Necesario para manejar los datos del IPC en memoria

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Calculadora de Ajuste por Inflación",
    page_icon="🇦🇷",
    layout="wide"
)

# --- Funciones Auxiliares ---

# _# MODIFICADO: Esta función ahora procesa un archivo subido, no uno local.
@st.cache_data
def procesar_ipc_cargado(uploaded_file):
    """Carga y procesa los datos del IPC desde un archivo subido por el usuario."""
    try:
        # Leemos el archivo CSV subido. Importante especificar separador y decimal.
        df_ipc = pd.read_csv(uploaded_file, sep=',', decimal='.')
        if 'fecha' not in df_ipc.columns or 'ipc_valor' not in df_ipc.columns:
            st.error("El archivo de IPC debe contener las columnas 'fecha' y 'ipc_valor'.")
            return None
        
        df_ipc['fecha'] = pd.to_datetime(df_ipc['fecha'], format='%Y-%m-%d')
        df_ipc.set_index('fecha', inplace=True)
        df_ipc.sort_index(inplace=True)
        return df_ipc
    except Exception as e:
        st.error(f"Error al procesar el archivo de IPC: {e}")
        st.info("Asegúrate de que el archivo CSV del IPC tenga el formato correcto: columnas 'fecha,ipc_valor' y separador decimal de punto.")
        return None

# _# Mantenemos la función de ajuste corregida
def ajustar_dataframe(df, fecha_cierre, df_ipc):
    """
    Aplica el ajuste por inflación al DataFrame proporcionado por el usuario.
    """
    # IPC de cierre es el del mes de la fecha de cierre.
    fecha_ipc_cierre = fecha_cierre.replace(day=1)
    
    try:
        ipc_cierre = df_ipc.loc[fecha_ipc_cierre, 'ipc_valor']
    except KeyError:
        st.error(f"No se encontró el IPC para el mes de cierre ({fecha_cierre.strftime('%B %Y')}). Por favor, elige una fecha de cierre anterior o actualiza tu archivo de IPC.")
        return None

    coeficientes, valores_ajustados, ajustes_recpam = [], [], []
    
    for index, row in df.iterrows():
        fecha_origen = row['Fecha']
        monto_historico = row['Monto_Historico']
        
        # IPC de origen es el del mes ANTERIOR a la compra
        fecha_ipc_origen = fecha_origen.replace(day=1) - datetime.timedelta(days=1)
        fecha_ipc_origen = fecha_ipc_origen.replace(day=1)
        
        try:
            ipc_origen = df_ipc.loc[fecha_ipc_origen, 'ipc_valor']
            
            coeficiente = ipc_cierre / ipc_origen
            valor_ajustado = monto_historico * coeficiente
            ajuste_recpam = valor_ajustado - monto_historico

            coeficientes.append(coeficiente)
            valores_ajustados.append(valor_ajustado)
            ajustes_recpam.append(ajuste_recpam)
        
        except KeyError:
            st.warning(f"No se encontró IPC para la fecha de origen {fecha_origen.strftime('%d-%m-%Y')} en la fila {index+1}. Se dejará sin ajustar.")
            coeficientes.append(1.0)
            valores_ajustados.append(monto_historico)
            ajustes_recpam.append(0.0)

    df_resultado = df.copy()
    df_resultado['Coeficiente'] = coeficientes
    df_resultado['Monto_Ajustado'] = valores_ajustados
    df_resultado['Ajuste_RECPAM'] = ajustes_recpam
    
    return df_resultado

# --- Interfaz de la App ---

st.title("📈 Calculadora de Ajuste por Inflación")
st.markdown("""
Esta herramienta te permite ajustar partidas por inflación según el **IPC Nacional (base Diciembre 2016)**. 
Es una demostración del mecanismo de reexpresión, útil para entender el impacto de la inflación.

**Importante:** Esto no reemplaza el cálculo completo y legal del Ajuste por Inflación Impositivo o Contable.
""")

df_ipc = None

# --- Barra Lateral con Entradas del Usuario ---
with st.sidebar:
    st.header("1. Carga los datos de Inflación")
    
    # _# NUEVO: Uploader para el archivo de IPC
    ipc_file = st.file_uploader(
        "Sube el archivo 'ipc_data.csv'",
        type=["csv"]
    )
    
    # Ofrecer la descarga de la plantilla del IPC
    with open("ipc_data.csv", "rb") as file:
        st.download_button(
            label="📥 Descargar plantilla IPC",
            data=file,
            file_name="ipc_data.csv",
            mime="text/csv"
        )
    
    st.markdown("---")

    if ipc_file is not None:
        # Procesamos el archivo de IPC una vez que se sube
        df_ipc = procesar_ipc_cargado(ipc_file)
    
    # _# NUEVO: Solo mostramos los siguientes pasos si el IPC se cargó correctamente
    if df_ipc is not None:
        st.header("2. Carga tus partidas")
        uploaded_file = st.file_uploader(
            "Sube tu archivo de partidas (CSV o Excel)",
            type=["csv", "xlsx"]
        )
        
        st.markdown("---")
        st.header("3. Elige la fecha de cierre")
        fecha_cierre = st.date_input(
            "¿A qué fecha quieres ajustar los valores?",
            datetime.date(2023, 12, 31),
            min_value=datetime.date(2017, 1, 1),
            max_value=datetime.date.today()
        )
    else:
        st.info("Por favor, sube primero el archivo con los datos del IPC para continuar.")

# --- Área Principal ---
# _# MODIFICADO: La lógica principal ahora depende de que ambos archivos estén cargados
if df_ipc is not None and 'uploaded_file' in locals() and uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_usuario = pd.read_csv(uploaded_file, sep=';', decimal=',')
        else:
            df_usuario = pd.read_excel(uploaded_file)
        
        if not {'Fecha', 'Monto_Historico'}.issubset(df_usuario.columns):
            st.error("Tu archivo de partidas debe contener las columnas 'Fecha' y 'Monto_Historico'.")
        else:
            df_usuario['Fecha'] = pd.to_datetime(df_usuario['Fecha'], dayfirst=True)
            
            st.subheader("Datos Originales Cargados")
            st.dataframe(df_usuario, use_container_width=True)

            with st.spinner('Calculando ajuste por inflación...'):
                df_resultado = ajustar_dataframe(df_usuario, locals().get('fecha_cierre'), df_ipc)

            if df_resultado is not None:
                st.subheader(f"📊 Resultados Ajustados al {locals().get('fecha_cierre').strftime('%d/%m/%Y')}")
                
                df_display = df_resultado.style.format({
                    "Monto_Historico": "AR$ {:,.2f}",
                    "Coeficiente": "{:.4f}",
                    "Monto_Ajustado": "AR$ {:,.2f}",
                    "Ajuste_RECPAM": "AR$ {:,.2f}",
                    "Fecha": lambda x: x.strftime("%d/%m/%Y")
                })
                st.dataframe(df_display, use_container_width=True)

                st.subheader("Totales Generales")
                total_historico = df_resultado['Monto_Historico'].sum()
                total_ajustado = df_resultado['Monto_Ajustado'].sum()
                total_recpam = df_resultado['Ajuste_RECPAM'].sum()

                col1, col2, col3 = st.columns(3)
                col1.metric("Total Valor Histórico", f"AR$ {total_historico:,.2f}")
                col2.metric("Total Valor Ajustado", f"AR$ {total_ajustado:,.2f}")
                col3.metric("Total Ajuste (RECPAM)", f"AR$ {total_recpam:,.2f}", delta=f"{((total_ajustado/total_historico - 1)*100):.2f}%" if total_historico > 0 else "0.00%")

                @st.cache_data
                def convert_df_to_csv(df):
                    return df.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')

                csv = convert_df_to_csv(df_resultado)
                st.download_button(
                   label="📥 Descargar Resultados en CSV",
                   data=csv,
                   file_name=f'ajuste_inflacion_{locals().get("fecha_cierre").strftime("%Y%m%d")}.csv',
                   mime='text/csv',
                )

    except Exception as e:
        st.error(f"Ocurrió un error al procesar el archivo de partidas: {e}")
        st.info("Asegúrate de que el archivo tenga el formato correcto: columnas 'Fecha' (dd/mm/aaaa) y 'Monto_Historico' (números).")
else:
    if df_ipc is None:
        st.info("⬅️ Sube el archivo `ipc_data.csv` desde el panel lateral para comenzar.")
    else:
        st.info("⬅️ Ahora, sube tu archivo con las partidas a ajustar.")
