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
archivo = st.file_uploader("📥 Carga tu archivo Excel", type=["xlsx"])

if archivo is not None:
    df = pd.read_excel(archivo)
    df.columns = df.columns.str.strip().str.lower()

    # Asegurar nombres consistentes
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

    # Cálculo de horas hábiles
    business_hours = CustomBusinessHour(start="09:00", end="18:00", weekmask='Mon Tue Wed Thu Fri')

    def en_horario(dt):
        return pd.notna(dt) and dt.weekday() < 5 and time(9, 0) <= dt.time() <= time(18, 0)

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
    df["Alerta"] = np.where(df["horas resolución real (hábiles)"] > 16, "🔴 Más de 16h", "🟢 Dentro del límite")

    # Visualización de prioridad
    colores_prioridad = {'Alta': '🔴 Alta', 'Media': '🟠 Media', 'Baja': '🟢 Baja'}
    df["Prioridad Visual"] = df["priodidad confianza"].map(colores_prioridad)

    # Mes y semana
    df["mes_finalizacion"] = df["fecha de finalizacion"].dt.strftime("%B")
    df["mes"] = df["fecha de finalizacion"].dt.strftime('%b')

    # Filtros
    st.sidebar.header("🔍 Filtros")
    mes_sel = st.sidebar.multiselect("📆 Mes de Finalización", df["mes_finalizacion"].dropna().unique(), default=df["mes_finalizacion"].dropna().unique())
    estado = st.sidebar.multiselect("Estado", df["estado"].dropna().unique(), default=df["estado"].dropna().unique())
    responsable = st.sidebar.multiselect("Responsable", df["responsable"].dropna().unique(), default=df["responsable"].dropna().unique())
    dificultad = st.sidebar.multiselect("Dificultad", df["dificultad"].dropna().unique() if "dificultad" in df.columns else [], default=None)
    prioridad = st.sidebar.multiselect("Prioridad Confianza", df["priodidad confianza"].dropna().unique(), default=df["priodidad confianza"].dropna().unique())

    df = df[df["mes_finalizacion"].isin(mes_sel) & df["estado"].isin(estado) &
            df["responsable"].isin(responsable) & df["priodidad confianza"].isin(prioridad)]

    # Gráficos comunes
    orden_meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    df["mes"] = pd.Categorical(df["mes"], categories=orden_meses, ordered=True)

    if pagina == "📊 Resumen Ejecutivo":
        col1, col2, col3 = st.columns(3)
        col1.metric("📌 Tickets Resueltos", df[df["estado"].str.lower() == "resuelto"].shape[0])
        col2.metric("⏱ Prom. Resolución real (hrs)", f"{df['horas resolución real (hábiles)'].mean():.1f}")
        col3.metric("🧑‍💼 Técnicos únicos", df["responsable"].nunique())

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

    elif pagina == "📈 Análisis Detallado":
        st.subheader("📊 Tickets Resueltos por Semana del Mes")
        df_sem = df[df["estado"].str.lower() == "resuelto"].copy()
        df_sem["mes_anio"] = df_sem["fecha de finalizacion"].dt.strftime("%Y-%m")
        df_sem["nro_semana_mes"] = df_sem.groupby("mes_anio")["fecha de finalizacion"].transform(lambda x: (x.dt.day - 1) // 7 + 1)
        df_sem["semana_mes_label"] = "Semana " + df_sem["nro_semana_mes"].astype(str)
        grafico = df_sem.groupby(["mes_anio", "semana_mes_label"]).size().reset_index(name="Cantidad de Tickets")
        grafico["semana_num"] = grafico["semana_mes_label"].str.extract(r'(\d+)').astype(int)
        grafico = grafico.sort_values(by=["mes_anio", "semana_num"])

        fig3 = px.bar(
            grafico, x="semana_num", y="Cantidad de Tickets", color="mes_anio",
            text_auto=True, barmode='group',
            title="📈 Tickets Resueltos por Semana del Mes",
            labels={"semana_num": "Semana", "Cantidad de Tickets": "Tickets"}
        )
        fig3.update_layout(
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white",
            xaxis=dict(tickmode='array', tickvals=grafico["semana_num"], ticktext=grafico["semana_mes_label"])
        )
        st.plotly_chart(fig3, use_container_width=True)

        # Gráfico por responsable
        st.subheader("👨‍💻 Tickets por Responsable")
        df_resp = df["responsable"].value_counts().reset_index()
        df_resp.columns = ["Responsable", "Tickets"]
        fig_resp = px.bar(df_resp, x="Responsable", y="Tickets", title="👨‍💻 Tickets por Responsable")
        fig_resp.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white")
        st.plotly_chart(fig_resp, use_container_width=True)

        # Tabla de datos
        st.subheader("📄 Tabla de Tickets con Alerta")
        st.dataframe(df[[
            "n° ticket", "solicitante", "fecha de apertura", "fecha en curso", "fecha en pausa",
            "fecha termino pausa", "fecha de finalizacion", "estado", "responsable",
            "priodidad confianza", "Prioridad Visual", "horas resolución real (hábiles)", "Alerta", "descripcion"
        ]])

        def convertir_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Filtrados')
            return output.getvalue()

        st.download_button("📤 Descargar Excel", convertir_excel(df), file_name="reporte_confianza.xlsx")

else:
    st.info("📂 Carga un archivo Excel con columnas como 'fecha en curso', 'fecha de finalizacion', 'responsable', etc.")
