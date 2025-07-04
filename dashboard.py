import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from PIL import Image
from io import BytesIO
from datetime import time
from pandas.tseries.offsets import CustomBusinessHour

st.set_page_config(layout="wide", page_title="Dashboard Confianza Colombia")

# Logo
logo = Image.open("logo_confianza.png")
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.image(logo, width=100)
with col_title:
    st.markdown("<h1 style='color:white;'>Dashboard de Tickets – Confianza Colombia</h1>", unsafe_allow_html=True)

# Selector de página
pagina = st.sidebar.radio("📂 Selecciona una página", ["📊 Resumen Ejecutivo", "📈 Análisis Detallado"])

# Cargar archivo
archivo = st.file_uploader("📅 Carga tu archivo Excel", type=["xlsx"])

if archivo is not None:
    df = pd.read_excel(archivo)
    df.columns = df.columns.str.strip().str.lower()

    columnas_necesarias = ["fecha de apertura", "fecha en curso", "fecha en pausa",
                           "fecha termino pausa", "fecha de finalizacion", "estado",
                           "responsable", "priodidad confianza", "descripcion",
                           "n° ticket", "solicitante"]

    for col in columnas_necesarias:
        if col not in df.columns:
            st.error(f"❌ Falta la columna requerida: '{col}'")
            st.stop()

    fechas = ["fecha de apertura", "fecha en curso", "fecha en pausa", "fecha termino pausa", "fecha de finalizacion"]
    for col in fechas:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    business_hours = CustomBusinessHour(start="09:00", end="18:00", weekmask='Mon Tue Wed Thu Fri')

    def calcular_horas_real(row):
        inicio = row["fecha en curso"]
        fin = row["fecha de finalizacion"]
        pausa_ini = row["fecha en pausa"]
        pausa_fin = row["fecha termino pausa"]

        if pd.isna(inicio) or pd.isna(fin):
            return None

        total_horas = 0
        if pd.isna(pausa_ini):
            total_horas = len(pd.date_range(start=inicio, end=fin, freq=business_hours))
        elif not pd.isna(pausa_ini) and not pd.isna(pausa_fin):
            total_horas += len(pd.date_range(start=inicio, end=pausa_ini, freq=business_hours))
            total_horas += len(pd.date_range(start=pausa_fin, end=fin, freq=business_hours))
        elif not pd.isna(pausa_ini) and pd.isna(pausa_fin):
            total_horas = len(pd.date_range(start=inicio, end=pausa_ini, freq=business_hours))

        return total_horas if total_horas > 0 else None

    df["horas resolución real (hábiles)"] = df.apply(calcular_horas_real, axis=1)

    # Reemplazar "Media" por "Mediana"
    df["priodidad confianza"] = df["priodidad confianza"].replace({"Media": "Mediana"})

    colores_prioridad = {'Alta': '🔴 Alta', 'Mediana': '🟠 Mediana', 'Baja': '🟢 Baja', 'Muy Urgente': '🔴 Muy Urgente'}
    df["Prioridad Visual"] = df["priodidad confianza"].map(colores_prioridad)

    # SLA según prioridad
    sla_map = {
        'Muy Urgente': 2,
        'Alta': 4,
        'Mediana': 8,
        'Baja': 16
    }
    df["SLA Prioridad"] = df["priodidad confianza"].map(lambda x: f"{sla_map.get(x, '?')} Horas")

    # Nueva alerta basada en SLA
    df["Alerta"] = df.apply(
        lambda row: "🟢 Dentro del SLA" if pd.notna(row["horas resolución real (hábiles)"]) and row["horas resolución real (hábiles)"] <= sla_map.get(row["priodidad confianza"], 0)
        else ("🔴 Fuera del SLA" if pd.notna(row["horas resolución real (hábiles)"]) else None),
        axis=1
    )

    df["mes_finalizacion"] = df["fecha de finalizacion"].dt.strftime("%B")
    df["mes"] = df["fecha de finalizacion"].dt.strftime('%b')

    st.sidebar.header("🔍 Filtros")
    mes_sel = st.sidebar.multiselect("📆 Mes de Finalización", df["mes_finalizacion"].dropna().unique(), default=df["mes_finalizacion"].dropna().unique())
    estado = st.sidebar.multiselect("Estado", df["estado"].dropna().unique(), default=df["estado"].dropna().unique())
    responsable = st.sidebar.multiselect("Responsable", df["responsable"].dropna().unique(), default=df["responsable"].dropna().unique())
    dificultad = st.sidebar.multiselect("Dificultad", df["dificultad"].dropna().unique() if "dificultad" in df.columns else [], default=None)
    prioridad = st.sidebar.multiselect("Prioridad Confianza", df["priodidad confianza"].dropna().unique(), default=df["priodidad confianza"].dropna().unique())

    df = df[df["mes_finalizacion"].isin(mes_sel) & df["estado"].isin(estado) &
            df["responsable"].isin(responsable) & df["priodidad confianza"].isin(prioridad)]

    orden_meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    df["mes"] = pd.Categorical(df["mes"], categories=orden_meses, ordered=True)

    if pagina == "📊 Resumen Ejecutivo":
        col1, col2, col3 = st.columns(3)
        col1.metric("📌 Tickets Resueltos", df[df["estado"].str.lower() == "resuelto"].shape[0])
        col2.metric("⏱ Prom. Resolución real (hrs)", f"{df['horas resolución real (hábiles)'].mean():.1f}")
        col3.metric("🧑‍💼 Técnicos únicos", df["responsable"].nunique())

        df_resueltos = df[df["estado"].str.lower() == "resuelto"].copy()
        if not df_resueltos.empty:
            total_tickets = df_resueltos.shape[0]
            dias_unicos = df_resueltos["fecha de finalizacion"].dt.date.nunique()
            responsables_unicos = df_resueltos["responsable"].nunique()
            tickets_dia_responsable = total_tickets / dias_unicos / responsables_unicos if dias_unicos > 0 and responsables_unicos > 0 else 0

        col4, col5 = st.columns(2)
        with col4:
            resumen = df.groupby(['mes', 'estado']).size().reset_index(name='Cantidad').sort_values(by='mes')
            fig = px.bar(resumen, x='mes', y='Cantidad', color='estado', barmode='group',
                         title="📅 Tickets por Estado y Mes de Finalización")
            fig.update_layout(plot_bgcolor='#0e1117', paper_bgcolor='#0e1117', font_color='white')
            st.plotly_chart(fig, use_container_width=True)

        with col5:
            resolucion = df.groupby("priodidad confianza")["horas resolución real (hábiles)"].mean().reset_index()
            fig2 = px.bar(resolucion, x="priodidad confianza", y="horas resolución real (hábiles)",
                          color="priodidad confianza", text_auto=".1f",
                          title="⏱️ Resolución Promedio por Prioridad Confianza")
            fig2.update_layout(plot_bgcolor='#0e1117', paper_bgcolor='#0e1117', font_color='white')
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("""
            <div style='display: flex; justify-content: center; margin-top: 30px;'>
                <div style='background-color: #1c1c1c; padding: 20px; border-radius: 12px; box-shadow: 0 0 10px rgba(255,255,255,0.1); width: 300px; text-align: center;'>
                    <h4 style='color: white;'>📅 Tickets/día/responsable</h4>
                    <p style='font-size: 36px; color: #00d4ff; margin: 0;'>
                        {0:.2f}
                    </p>
                </div>
            </div>
        """.format(tickets_dia_responsable), unsafe_allow_html=True)

    elif pagina == "📈 Análisis Detallado":
        st.subheader("📄 Tabla de Tickets con Alerta")
        columnas_tabla = [
            "n° ticket", "solicitante", "fecha de apertura", "fecha en curso", "fecha en pausa",
            "fecha termino pausa", "fecha de finalizacion", "estado", "responsable",
            "priodidad confianza", "SLA Prioridad", "Prioridad Visual", "horas resolución real (hábiles)", "Alerta", "descripcion"
        ]
        st.dataframe(df[columnas_tabla])

        def convertir_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Filtrados')
            return output.getvalue()

        st.download_button("📄 Descargar Excel", convertir_excel(df), file_name="reporte_confianza.xlsx")

else:
    st.info("📂 Carga un archivo Excel con columnas como 'fecha en curso', 'fecha de finalizacion', 'responsable', etc.")
