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

# Cargar archivo
archivo = st.file_uploader("📥 Carga tu archivo Excel", type=["xlsx"])

if archivo is not None:
    df = pd.read_excel(archivo)
    df.columns = df.columns.str.strip().str.lower()

    # Fechas
    fechas = [
        "fecha de apertura", "fecha de asignacion", "fecha en curso",
        "fecha en pausa", "fecha termino pausa", "fecha de finalizacion"
    ]
    for col in fechas:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    # Horas hábiles
    business_hours = CustomBusinessHour(start="09:00", end="18:00", weekmask='Mon Tue Wed Thu Fri')

    def en_horario(dt):
        return pd.notna(dt) and dt.weekday() < 5 and time(9, 0) <= dt.time() <= time(18, 0)

    def calcular_horas_real(row):
        inicio = row.get("fecha en curso")
        fin = row.get("fecha de finalizacion")
        pausa_ini = row.get("fecha en pausa")
        pausa_fin = row.get("fecha termino pausa")

        if pd.isna(inicio) or pd.isna(fin):
            return None

        total_horas = 0
        if pd.isna(pausa_ini):
            if en_horario(inicio) and en_horario(fin):
                total_horas = len(pd.date_range(start=inicio, end=fin, freq=business_hours))
        elif not pd.isna(pausa_ini) and not pd.isna(pausa_fin):
            if en_horario(inicio) and en_horario(pausa_ini):
                total_horas += len(pd.date_range(start=inicio, end=pausa_ini, freq=business_hours))
            if en_horario(pausa_fin) and en_horario(fin):
                total_horas += len(pd.date_range(start=pausa_fin, end=fin, freq=business_hours))
        elif not pd.isna(pausa_ini) and pd.isna(pausa_fin):
            if en_horario(inicio) and en_horario(pausa_ini):
                total_horas = len(pd.date_range(start=inicio, end=pausa_ini, freq=business_hours))

        return total_horas if total_horas > 0 else None

    # Cálculo de horas resolución real
    df["horas resolución real (hábiles)"] = df.apply(calcular_horas_real, axis=1)

    # Agregar columnas de alerta y prioridad visual
    df["Alerta"] = np.where(df["horas resolución real (hábiles)"] > 16, "🔴 Más de 16h", "🟢 Dentro del límite")
    colores_prioridad = {'Alta': '🔴 Alta', 'Media': '🟠 Media', 'Baja': '🟢 Baja'}
    df["Prioridad Visual"] = df["priodidad confianza"].map(colores_prioridad)

    # Columnas temporales para filtros
    df["mes_finalizacion"] = df["fecha de finalizacion"].dt.strftime("%B")
    df["mes"] = df["fecha de finalizacion"].dt.strftime('%b')

    # Filtros
    st.sidebar.header("🔍 Filtros")
    mes_sel = st.sidebar.multiselect("📆 Mes de Finalización", df["mes_finalizacion"].dropna().unique(), default=df["mes_finalizacion"].dropna().unique())
    estado = st.sidebar.multiselect("Estado", df["estado"].dropna().unique(), default=df["estado"].dropna().unique())
    responsable = st.sidebar.multiselect("Responsable", df["responsable"].dropna().unique(), default=df["responsable"].dropna().unique())
    dificultad = st.sidebar.multiselect("Dificultad", df["dificultad"].dropna().unique(), default=df["dificultad"].dropna().unique())
    prioridad = st.sidebar.multiselect("Prioridad Confianza", df["priodidad confianza"].dropna().unique(), default=df["priodidad confianza"].dropna().unique())

    df = df[df["mes_finalizacion"].isin(mes_sel) & df["estado"].isin(estado) &
            df["responsable"].isin(responsable) & df["dificultad"].isin(dificultad) &
            df["priodidad confianza"].isin(prioridad)]

    # KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("📌 Tickets Resueltos", df[df["estado"].str.lower() == "resuelto"].shape[0])
    col2.metric("⏱ Prom. Resolución real (hrs)", f"{df['horas resolución real (hábiles)'].mean():.1f}")
    col3.metric("🧑‍💼 Técnicos únicos", df["responsable"].nunique())

    # 📊 Tickets por Estado y Mes
    orden_meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    df["mes"] = pd.Categorical(df["mes"], categories=orden_meses, ordered=True)
    resumen = df.groupby(['mes', 'estado']).size().reset_index(name='Cantidad')
    resumen = resumen.sort_values(by='mes')
    fig = px.bar(resumen, x='mes', y='Cantidad', color='estado', barmode='group',
                 title="📅 Tickets por Estado y Mes de Finalización")
    fig.update_layout(plot_bgcolor='#0e1117', paper_bgcolor='#0e1117', font_color='white')
    st.plotly_chart(fig, use_container_width=True)

    # ⏱ Resolución por Prioridad
    st.subheader("📉 Promedio de Horas de Resolución por Prioridad Confianza")
    resolucion = df.groupby("priodidad confianza")["horas resolución real (hábiles)"].mean().reset_index()
    fig2 = px.bar(resolucion, x="priodidad confianza", y="horas resolución real (hábiles)",
                  color="priodidad confianza", text_auto=".1f",
                  title="⏱️ Resolución Promedio por Prioridad Confianza")
    fig2.update_layout(plot_bgcolor='#0e1117', paper_bgcolor='#0e1117', font_color='white')
    st.plotly_chart(fig2, use_container_width=True)

    # 📈 Tickets resueltos por Semana
    st.subheader("📊 Tickets Resueltos por Semana del Mes")
    df_sem = df[df["estado"].str.lower() == "resuelto"].copy()
    df_sem["mes_anio"] = df_sem["fecha de finalizacion"].dt.strftime("%Y-%m")
    df_sem["nro_semana_mes"] = df_sem.groupby("mes_anio")["fecha de finalizacion"].transform(
        lambda x: (x.dt.day - 1) // 7 + 1
    )
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
        xaxis=dict(
            tickmode='array',
            tickvals=grafico["semana_num"],
            ticktext=grafico["semana_mes_label"]
        )
    )
    st.plotly_chart(fig3, use_container_width=True)

    # 📄 Tabla y descarga
    st.subheader("🗂️ Datos Filtrados con Alertas")
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
    st.info("📂 Carga un archivo Excel con columnas como 'fecha en curso', 'fecha en pausa', 'fecha de finalizacion'.")
