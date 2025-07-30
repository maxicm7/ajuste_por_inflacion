import streamlit as st
import pandas as pd
import datetime

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Calculadora de Ajuste por Inflación",
    page_icon="🇦🇷",
    layout="wide"
)

# --- SOLUCIÓN: Embeber el contenido del CSV directamente en el código ---
# Ahora la app no necesita ningún archivo externo para funcionar.
ipc_csv_string = """fecha,ipc_valor
2016-12-01,100.0000
2017-01-01,101.3000
2017-02-01,103.8285
2017-03-01,106.3195
2017-04-01,109.1678
2017-05-01,110.6903
2017-06-01,112.0185
2017-07-01,113.9129
2017-08-01,115.4851
2017-09-01,117.7949
2017-10-01,119.5318
2017-11-01,121.2482
2017-12-01,125.0494
2018-01-01,127.3000
2018-02-01,130.3632
2018-03-01,133.4111
2018-04-01,137.0322
2018-05-01,139.9110
2018-06-01,145.1011
2018-07-01,149.6994
2018-08-01,155.6280
2018-09-01,165.8078
2018-10-01,174.7563
2018-11-01,180.3252
2018-12-01,184.9727
2019-01-01,189.9219
2019-02-01,197.1389
2019-03-01,206.5916
2019-04-01,213.6231
2019-05-01,220.2702
2019-06-01,226.2166
2019-07-01,231.1891
2019-08-01,240.4367
2019-09-01,254.7410
2019-10-01,263.1425
2019-11-01,274.2415
2019-12-01,283.4414
2020-01-01,289.8973
2020-02-01,295.6953
2020-03-01,305.4593
2020-04-01,310.0381
2020-05-01,314.7186
2020-06-01,321.6738
2020-07-01,327.7852
2020-08-01,336.5700
2020-09-01,346.0606
2020-10-01,359.1830
2020-11-01,370.2978
2020-12-01,385.1097
2021-01-01,400.5141
2021-02-01,414.9286
2021-03-01,434.8252
2021-04-01,452.6529
2021-05-01,467.6252
2021-06-01,482.1213
2021-07-01,496.5850
2021-08-01,508.9996
2021-09-01,527.2286
2021-10-01,545.6238
2021-11-01,559.2643
2021-12-01,582.4137
2022-01-01,605.1278
2022-02-01,633.5684
2022-03-01,675.8943
2022-04-01,716.4480
2022-05-01,752.6391
2022-06-01,792.1765
2022-07-01,851.3598
2022-08-01,910.9550
2022-09-01,968.3442
2022-10-01,1028.3619
2022-11-01,1078.6515
2022-12-01,1134.4100
2023-01-01,1202.4744
2023-02-01,1281.8329
2023-03-01,1380.6400
2023-04-01,1496.4100
2023-05-01,1613.1490
2023-06-01,1711.5600
2023-07-01,1819.5800
2023-08-01,2044.4100
2023-09-01,2308.2000
2023-10-01,2500.2000
2023-11-01,2819.2000
2023-12-01,3539.1000
2024-01-01,4266.3000
2024-02-01,4835.4000
2024-03-01,5366.5000
2024-04-01,5833.6000
2024-05-01,6073.7000
2024-06-01,6351.7000
2024-07-01,6607.7000
2024-08-01,6883.4000
2024-09-01,7122.2000
2024-10-01,7314.0000
2024-11-01,7491.4000
2024-12-01,7694.0000
2025-01-01,7864.1000
2025-02-01,8053.0000
2025-03-01,8353.3000
2025-04-01,8585.6000
2025-05-01,8714.5000
2025-06-01,8855.6000
"""

# --- Funciones Auxiliares ---

@st.cache_data
def procesar_ipc_cargado(uploaded_file):
    """Carga y procesa los datos del IPC desde un archivo subido por el usuario."""
    try:
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
        return None

def ajustar_dataframe(df, fecha_cierre, df_ipc):
    """Aplica el ajuste por inflación al DataFrame proporcionado por el usuario."""
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
Esta herramienta te permite ajustar partidas por inflación según el **IPC Nacional (base Diciembre 2016)**. Es una demostración del mecanismo de reexpresión, útil para entender el impacto de la inflación.
**Importante:** Esto no reemplaza el cálculo completo y legal del Ajuste por Inflación Impositivo o Contable.
""")

df_ipc = None

with st.sidebar:
    st.header("1. Carga los datos de Inflación")
    
    ipc_file = st.file_uploader(
        "Sube el archivo CSV con los índices IPC",
        type=["csv"]
    )
    
    # --- CÓDIGO MODIFICADO PARA ELIMINAR EL ERROR ---
    # En lugar de abrir un archivo, usamos el string que definimos arriba.
    st.download_button(
        label="📥 Descargar plantilla IPC",
        data=ipc_csv_string.encode('utf-8'), # Pasamos el string codificado
        file_name="ipc_data_plantilla.csv",
        mime="text/csv"
    )
    
    st.markdown("---")

    if ipc_file is not None:
        df_ipc = procesar_ipc_cargado(ipc_file)
    
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

else:
    if df_ipc is None:
        st.info("⬅️ Sube el archivo CSV con los datos del IPC desde el panel lateral para comenzar.")
    else:
        st.info("⬅️ Ahora, sube tu archivo con las partidas a ajustar.")
