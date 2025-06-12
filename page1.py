import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Título
st.title("📊 Dashboard de Tickets")

# Cargar archivo Excel
archivo = st.file_uploader("Carga tu archivo Excel con tickets", type=["xlsx"])

if archivo is not None:
    df = pd.read_excel(archivo)

    # Procesar fechas
    df['Fecha_Creación'] = pd.to_datetime(df['Fecha_Creación'])
    df['Fecha_Resolución'] = pd.to_datetime(df['Fecha_Resolución'])
    df['Días_Resolución'] = (df['Fecha_Resolución'] - df['Fecha_Creación']).dt.days

    # KPIs
    total = df[df['Estado'] == 'Resuelto'].shape[0]
    promedio = df['Días_Resolución'].mean()

    st.metric("✅ Tickets Resueltoss", total)
    st.metric("⏱️ Tiempo Promedio Resolución (días)", f"{promedio:.2f}")

    # Gráfico 1: Tickets por Estado
    tickets_estado = df['Estado'].value_counts()
    fig1, ax1 = plt.subplots()
    tickets_estado.plot(kind='bar', ax=ax1)
    ax1.set_title("Tickets por Estado")
    ax1.set_ylabel("Cantidad")
    st.pyplot(fig1)

    # Gráfico 2: Resoluciones por Día
    resueltos = df[df['Estado'] == 'Resuelto']
    resueltos_por_fecha = resueltos.groupby('Fecha_Resolución').size()
    fig2, ax2 = plt.subplots()
    resueltos_por_fecha.plot(ax=ax2, marker='o')
    ax2.set_title("Resoluciones por Día")
    ax2.set_ylabel("Tickets")
    st.pyplot(fig2)

    # Tabla de datos
    st.subheader("📄 Datos Procesados")
    st.dataframe(df)
