import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta, time

st.set_page_config(layout="wide")
st.title("📊 Dashboard de Mesa de Ayuda - Confianza Colombia")

# 📁 Cargar archivo
archivo = st.file_uploader("Sube el archivo Excel", type=["xlsx"])

@st.cache_data
def cargar_datos(file):
    df = pd.read_excel(file)

    # Convertir columnas a fechas
    columnas_fecha = [
        'fecha de apertura', 'fecha de asignacion', 'fecha en curso',
        'fecha en pausa', 'fecha termino pausa', 'fecha de finalizacion'
    ]
    for col in columnas_fecha:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Calcular horas hábiles entre fechas
    def calcular_horas_habiles(row):
        inicio = row['fecha en curso']
        fin = row['fecha de finalizacion']
        pausa_ini = row.get('fecha en pausa')
        pausa_fin = row.get('fecha termino pausa')
        if pd.isnull(inicio) or pd.isnull(fin):
            return np.nan

        rangos = [(inicio, fin)]
        if not pd.isnull(pausa_ini):
            if not pd.isnull(pausa_fin):
                rangos = [(inicio, pausa_ini), (pausa_fin, fin)]
            else:
                rangos = [(inicio, pausa_ini)]

        total = 0
        for inicio_rango, fin_rango in rangos:
            current = inicio_rango
            while current < fin_rango:
                if current.weekday() < 5:
                    inicio_hora = max(current, datetime.combine(current.date(), time(9, 0)))
                    fin_hora = min(fin_rango, datetime.combine(current.date(), time(18, 0)))
                    delta = (fin_hora - inicio_hora).total_seconds() / 3600
                    if delta > 0:
                        total += delta
                current += timedelta(days=1)
        return round(total, 2)

    df["horas resolución real (hábiles)"] = df.apply(calcular_horas_habiles, axis=1)

    # Alertas SLA
    df["alerta"] = df["horas resolución real (hábiles)"].apply(
        lambda x: "🔴 Más de 16h" if x > 16 else "🟢 Dentro del límite"
    )

    # Visual de prioridad
    df["prioridad visual"] = df["priodidad confianza"].map({
        "Alta": "🔴 Alta", "Mediana": "🟠 Media", "Baja": "🟢 Baja"
    }).fillna(df["priodidad confianza"])

    # Columnas para filtros y gráficos
    df["mes"] = df["fecha de finalizacion"].dt.strftime("%Y-%m")
    df["semana"] = df["fecha de finalizacion"].dt.strftime("%Y-%W")
    df["cumple_sla"] = np.where(df["horas resolución real (hábiles)"] <= 16, "✅ Cumple SLA", "❌ No Cumple")

    return df

# 🚀 Si hay archivo cargado
if archivo:
    df = cargar_datos(archivo)
    st.dataframe(df)

    # 📊 Gráfico 1: Tickets por estado y mes de finalización
    fig_estado_mes = px.bar(
        df.groupby(["mes", "estado"]).size().reset_index(name="Cantidad"),
        x="mes", y="Cantidad", color="estado", barmode="group",
        title="📅 Tickets por Estado y Mes de Finalización"
    )
    st.plotly_chart(fig_estado_mes, use_container_width=True)

    # 📊 Gráfico 2: Promedio resolución por prioridad
    fig_resolucion = px.bar(
        df.groupby("prioridad visual")["horas resolución real (hábiles)"].mean().reset_index(),
        x="prioridad visual", y="horas resolución real (hábiles)",
        color="prioridad visual", title="⏱ Promedio de Resolución por Prioridad de Confianza"
    )
    st.plotly_chart(fig_resolucion, use_container_width=True)

    # 📊 Gráfico 3: Tickets por responsable
    fig_responsables = px.bar(
        df["responsable"].value_counts().reset_index(),
        x="index", y="responsable",
        labels={"index": "Responsable", "responsable": "Cantidad de Tickets"},
        title="👨‍💻 Tickets por Responsable"
    )
    st.plotly_chart(fig_responsables, use_container_width=True)

    # 📊 Gráfico 4: Distribución por dificultad
    fig_dificultad = px.pie(
        df["dificultad"].value_counts().reset_index(),
        names="index", values="dificultad",
        title="📊 Distribución por Dificultad"
    )
    st.plotly_chart(fig_dificultad, use_container_width=True)

    # 📊 Gráfico 5: Tickets por semana y estado
    st.subheader("📆 Tickets por Semana y Estado")
    fig_estado_semanal = px.bar(
        df.groupby(["semana", "estado"]).size().reset_index(name="Cantidad"),
        x="semana", y="Cantidad", color="estado",
        category_orders={"semana": sorted(df["semana"].unique())}
    )
    st.plotly_chart(fig_estado_semanal, use_container_width=True)

    # 📊 Gráfico 6: Cumplimiento de SLA por semana
    st.subheader("✅ Cumplimiento de SLA (<16h) por Semana")
    fig_sla = px.bar(
        df.groupby(["semana", "cumple_sla"]).size().reset_index(name="Cantidad"),
        x="semana", y="Cantidad", color="cumple_sla", barmode="group",
        category_orders={"semana": sorted(df["semana"].unique())}
    )
    st.plotly_chart(fig_sla, use_container_width=True)
