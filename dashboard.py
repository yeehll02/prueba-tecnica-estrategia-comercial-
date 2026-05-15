import os
import numpy as np
import streamlit as st
import pandas as pd
import plotly.express as px

# ── Configuración ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Estrategia Comercial Personas",
    layout="wide",
    initial_sidebar_state="expanded"
)

MESES = {
    1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
    7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"
}

COLORES = px.colors.qualitative.Safe


# ── Helpers ────────────────────────────────────────────────────────────────────
@st.cache_data
def cargar_datos():
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "hechos_ventas.csv")
    df = pd.read_csv(ruta, parse_dates=["fecha"])
    df["nombre_mes"] = df["mes"].map(MESES)
    return df


def fmt_millones(valor):
    if valor >= 1_000_000_000:
        return f"${valor/1_000_000_000:.1f}B"
    return f"${valor/1_000_000:.1f}M"


def mostrar(fig, tickangle=None):
    """Aplica estilo común y renderiza el gráfico."""
    kw = {"xaxis_title": None}
    if tickangle:
        kw["xaxis_tickangle"] = tickangle
    fig.update_layout(**kw)
    st.plotly_chart(fig, use_container_width=True)


# ── Sidebar y filtros ──────────────────────────────────────────────────────────
df_base = cargar_datos()

with st.sidebar:
    st.title("Filtros")
    anio_sel     = st.multiselect("Año",             sorted(df_base["anio"].dropna().unique()),          default=sorted(df_base["anio"].dropna().unique()))
    region_sel   = st.multiselect("Región",           sorted(df_base["region"].dropna().unique()),        default=sorted(df_base["region"].dropna().unique()))
    segmento_sel = st.multiselect("Segmento",         sorted(df_base["segmento"].dropna().unique()),      default=sorted(df_base["segmento"].dropna().unique()))
    tipo_sel     = st.multiselect("Tipo de producto", sorted(df_base["tipo_producto"].dropna().unique()), default=sorted(df_base["tipo_producto"].dropna().unique()))
    st.divider()
    pagina = st.radio("Página", ["Resumen Ejecutivo", "Productos", "Clientes", "Geografía", "Sucursales", "Proyección"])

df = df_base[
    df_base["anio"].isin(anio_sel) &
    df_base["region"].isin(region_sel) &
    df_base["segmento"].isin(segmento_sel) &
    df_base["tipo_producto"].isin(tipo_sel)
]


# ── Página 1: Resumen Ejecutivo ────────────────────────────────────────────────
if pagina == "Resumen Ejecutivo":
    st.title("Resumen Ejecutivo")
    st.caption("Vista general del desempeño comercial")
    st.divider()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Ganancia Total",             fmt_millones(df["ganancia"].sum()))
    k2.metric("Monto Colocado / Invertido", fmt_millones(df["monto"].sum()))
    k3.metric("Rentabilidad Promedio",      f"{df['rentabilidad_tasa'].mean()*100:.2f}%")
    k4.metric("Clientes Estratégicos",      f"{df['cliente_estrategico'].sum():,}")

    st.divider()
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Ganancia por mes")
        por_mes = df.groupby(["mes","nombre_mes"])["ganancia"].sum().reset_index().sort_values("mes")
        mostrar(px.bar(por_mes, x="nombre_mes", y="ganancia",
                       color_discrete_sequence=[COLORES[0]],
                       labels={"nombre_mes":"Mes","ganancia":"Ganancia ($)"}))

    with c2:
        st.subheader("Ganancia por tipo de producto")
        por_tipo = df.groupby("tipo_producto")["ganancia"].sum().reset_index()
        st.plotly_chart(px.pie(por_tipo, names="tipo_producto", values="ganancia",
                               color_discrete_sequence=COLORES, hole=0.4),
                        use_container_width=True)
        st.caption("**Crédito:** libre inversión, hipotecario, libranza, tarjeta crédito — el banco presta dinero al cliente.  \n**Inversión:** CDT, inversión virtual — el cliente deposita dinero en el banco.")

    st.subheader("Tendencia mensual de ganancia y monto")
    tendencia = df.groupby(["mes","nombre_mes"]).agg(ganancia=("ganancia","sum"), monto=("monto","sum")).reset_index().sort_values("mes")
    mostrar(px.line(tendencia, x="nombre_mes", y=["ganancia","monto"], markers=True,
                    labels={"nombre_mes":"Mes","value":"$","variable":"Métrica"},
                    color_discrete_sequence=COLORES))


# ── Página 2: Productos ────────────────────────────────────────────────────────
elif pagina == "Productos":
    st.title("Análisis de Productos")
    st.caption("Desempeño por producto y tipo")
    st.divider()

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Ganancia por producto")
        por_prod = df.groupby("producto")["ganancia"].sum().reset_index().sort_values("ganancia")
        mostrar(px.bar(por_prod, x="ganancia", y="producto", orientation="h",
                       color_discrete_sequence=[COLORES[1]],
                       labels={"producto":"","ganancia":"Ganancia ($)"}))

    with c2:
        st.subheader("Rentabilidad promedio por producto")
        rent_prod = df.groupby("producto")["rentabilidad_tasa"].mean().reset_index().sort_values("rentabilidad_tasa")
        rent_prod["rentabilidad_pct"] = rent_prod["rentabilidad_tasa"] * 100
        mostrar(px.bar(rent_prod, x="rentabilidad_pct", y="producto", orientation="h",
                       color_discrete_sequence=[COLORES[2]],
                       labels={"producto":"","rentabilidad_pct":"Rentabilidad (%)"}))

    st.subheader("Crecimiento mensual por producto")
    crecimiento = df.groupby(["mes","nombre_mes","producto"])["ganancia"].sum().reset_index().sort_values("mes")
    mostrar(px.line(crecimiento, x="nombre_mes", y="ganancia", color="producto", markers=True,
                    color_discrete_sequence=COLORES,
                    labels={"nombre_mes":"Mes","ganancia":"Ganancia ($)","producto":"Producto"}))

    st.subheader("Ventas por tipo de producto según valor de la venta")
    q1, q3 = int(df["monto"].quantile(0.25)), int(df["monto"].quantile(0.75))
    st.caption(f"Bajo: menos de ${q1:,}  |  Medio: entre ${q1:,} y ${q3:,}  |  Alto: más de ${q3:,}")
    cruce = df.groupby(["tipo_producto","tipo_monto"])["monto"].sum().reset_index()
    mostrar(px.bar(cruce, x="tipo_producto", y="monto", color="tipo_monto", barmode="group",
                   color_discrete_sequence=COLORES,
                   labels={"tipo_producto":"Tipo de producto","monto":"Monto ($)","tipo_monto":"Valor de la venta"}))


# ── Página 3: Clientes ─────────────────────────────────────────────────────────
elif pagina == "Clientes":
    st.title("Análisis de Clientes")
    st.caption("Segmentos, rentabilidad y clientes clave")
    st.divider()

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Ganancia por segmento")
        por_seg = df.groupby("segmento")["ganancia"].sum().reset_index().sort_values("ganancia", ascending=False)
        mostrar(px.bar(por_seg, x="segmento", y="ganancia",
                       color_discrete_sequence=[COLORES[3]],
                       labels={"segmento":"Segmento","ganancia":"Ganancia ($)"}))

    with c2:
        st.subheader("Rentabilidad diferencial por segmento")
        rent_seg = df.groupby("segmento")["rentabilidad_diferencial"].mean().reset_index().sort_values("rentabilidad_diferencial", ascending=False)
        rent_seg["diferencial_pct"] = rent_seg["rentabilidad_diferencial"] * 100
        mostrar(px.bar(rent_seg, x="segmento", y="diferencial_pct",
                       color_discrete_sequence=[COLORES[4]],
                       labels={"segmento":"Segmento","diferencial_pct":"Diferencial (%)"}))

    st.subheader("Top 10 clientes por ganancia")
    top = df.nlargest(10, "ganancia")[["id_cliente","producto","segmento","monto","ganancia","rentabilidad_tasa"]].reset_index(drop=True)
    top.index += 1
    top["rentabilidad_tasa"] = (top["rentabilidad_tasa"] * 100).round(2).astype(str) + "%"
    top.columns = ["Cliente","Producto","Segmento","Monto ($)","Ganancia ($)","Tasa"]
    st.dataframe(top, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        st.subheader("Distribución por tipo de monto")
        tipo_monto = df["tipo_monto"].value_counts().reset_index()
        st.plotly_chart(px.pie(tipo_monto, names="tipo_monto", values="count",
                               color_discrete_sequence=COLORES, hole=0.4,
                               labels={"tipo_monto":"Tramo","count":"Clientes"}),
                        use_container_width=True)

    with c4:
        st.subheader("Clientes estratégicos vs no estratégicos")
        conteo = df["cliente_estrategico"].map({1:"Estratégico", 0:"No estratégico"}).value_counts().reset_index()
        st.plotly_chart(px.pie(conteo, names="cliente_estrategico", values="count",
                               color_discrete_sequence=COLORES, hole=0.4),
                        use_container_width=True)


# ── Página 4: Geografía ────────────────────────────────────────────────────────
elif pagina == "Geografía":
    st.title("Distribución Geográfica")
    st.caption("Desempeño por región, departamento y ciudad")
    st.divider()

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Ganancia por región")
        por_region = df.groupby("region")["ganancia"].sum().reset_index().sort_values("ganancia", ascending=False)
        mostrar(px.bar(por_region, x="region", y="ganancia",
                       color_discrete_sequence=[COLORES[0]],
                       labels={"region":"Región","ganancia":"Ganancia ($)"}))

    with c2:
        st.subheader("Ganancia por departamento")
        por_dept = df.groupby("departamento")["ganancia"].sum().reset_index().sort_values("ganancia")
        mostrar(px.bar(por_dept, x="ganancia", y="departamento", orientation="h",
                       color_discrete_sequence=[COLORES[1]],
                       labels={"departamento":"","ganancia":"Ganancia ($)"}))

    st.subheader("Ganancia generada por ciudad")
    st.caption("Ganancia = utilidad que deja cada operación al banco")
    por_ciudad = df.groupby("nombre_ciudad").agg(ganancia=("ganancia","sum")).reset_index().sort_values("ganancia", ascending=False)
    mostrar(px.bar(por_ciudad, x="nombre_ciudad", y="ganancia",
                   color_discrete_sequence=[COLORES[0]],
                   labels={"nombre_ciudad":"Ciudad","ganancia":"Ganancia ($)"}))

    st.subheader("Segmentos por región")
    seg_region = df.groupby(["region","segmento"])["ganancia"].sum().reset_index()
    mostrar(px.bar(seg_region, x="region", y="ganancia", color="segmento", barmode="group",
                   color_discrete_sequence=COLORES,
                   labels={"region":"Región","ganancia":"Ganancia ($)","segmento":"Segmento"}))


# ── Página 5: Sucursales ───────────────────────────────────────────────────────
elif pagina == "Sucursales":
    st.title("Desempeño de Sucursales")
    st.caption("Ranking de sucursales y gerentes por resultados comerciales")
    st.divider()

    por_suc = (
        df.groupby(["nombre_sucursal","gerente"])
        .agg(ganancia=("ganancia","sum"), monto=("monto","sum"),
             clientes=("id_cliente","count"), rentabilidad=("rentabilidad_tasa","mean"))
        .reset_index().sort_values("ganancia", ascending=False)
    )

    st.subheader("Ranking de sucursales por ganancia")
    mostrar(px.bar(por_suc, x="nombre_sucursal", y="ganancia", color="gerente",
                   color_discrete_sequence=COLORES,
                   labels={"nombre_sucursal":"Sucursal","ganancia":"Ganancia ($)","gerente":"Gerente"}),
            tickangle=-30)

    st.subheader("Tabla de desempeño por gerente")
    tabla = por_suc.copy()
    tabla["rentabilidad"] = (tabla["rentabilidad"] * 100).round(2).astype(str) + "%"
    tabla.index = range(1, len(tabla) + 1)
    tabla.columns = ["Sucursal","Gerente","Ganancia ($)","Monto ($)","Clientes","Rentabilidad"]
    st.dataframe(tabla, use_container_width=True)

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Mejor y peor mes por ganancia")
        por_mes = df.groupby(["mes","nombre_mes"])["ganancia"].sum().reset_index().sort_values("mes")
        mejor = por_mes.loc[por_mes["ganancia"].idxmax(), "nombre_mes"]
        peor  = por_mes.loc[por_mes["ganancia"].idxmin(), "nombre_mes"]
        mostrar(px.bar(por_mes, x="nombre_mes", y="ganancia",
                       color_discrete_sequence=[COLORES[0]],
                       labels={"nombre_mes":"Mes","ganancia":"Ganancia ($)"}))
        st.success(f"Mejor mes: {mejor}")
        st.error(f"Peor mes: {peor}")

    with c2:
        st.subheader("Rentabilidad promedio por sucursal")
        rent_suc = df.groupby("nombre_sucursal")["rentabilidad_tasa"].mean().reset_index().sort_values("rentabilidad_tasa")
        rent_suc["rentabilidad_pct"] = rent_suc["rentabilidad_tasa"] * 100
        mostrar(px.bar(rent_suc, x="rentabilidad_pct", y="nombre_sucursal", orientation="h",
                       color_discrete_sequence=[COLORES[2]],
                       labels={"nombre_sucursal":"","rentabilidad_pct":"Rentabilidad (%)"}))


# ── Página 6: Proyección ───────────────────────────────────────────────────────
elif pagina == "Proyección":
    st.title("Proyección de Demanda")
    st.caption("Estimación de ventas para la próxima semana — tres enfoques complementarios")
    st.divider()

    VENTANA = 4

    semanas = (
        df_base.groupby("semana")
        .agg(n_ventas=("monto","count"), ganancia=("ganancia","sum"), monto=("monto","sum"))
        .reset_index().sort_values("semana").iloc[1:-1].reset_index(drop=True)
    )
    ultimas = semanas.tail(VENTANA)

    ma_ganancia    = ultimas["ganancia"].mean()
    variacion_pct  = ultimas["ganancia"].pct_change().dropna().mean() * 100
    x, y           = semanas["semana"].values, semanas["ganancia"].values
    coef           = np.polyfit(x, y, 1)
    trend_ganancia = np.polyval(coef, x[-1] + 1)

    k1, k2, k3 = st.columns(3)
    k1.metric("Promedio Móvil (ganancia)",    f"${ma_ganancia/1e9:.2f}B",    help=f"Media de las últimas {VENTANA} semanas completas")
    k2.metric("Variación semana a semana",    f"{variacion_pct:+.2f}%",      help="Cambio promedio de ganancia de una semana a la siguiente")
    k3.metric("Regresión Lineal (ganancia)",  f"${trend_ganancia/1e9:.2f}B", help="Extrapolación por mínimos cuadrados")

    st.divider()
    st.subheader("Ganancia semanal histórica y proyección")

    df_plot = pd.concat([
        semanas[["semana","ganancia"]].assign(tipo="Histórico"),
        pd.DataFrame([{"semana": x[-1]+1, "ganancia": ma_ganancia, "tipo": "Proyección (MA)"}])
    ], ignore_index=True)

    fig = px.bar(df_plot, x="semana", y="ganancia", color="tipo",
                 color_discrete_map={"Histórico": COLORES[0], "Proyección (MA)": COLORES[3]},
                 labels={"semana":"Semana","ganancia":"Ganancia ($)","tipo":""})
    fig.add_scatter(x=semanas["semana"], y=np.polyval(coef, semanas["semana"]),
                    mode="lines", name="Tendencia lineal",
                    line=dict(color="red", dash="dash", width=2))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader(f"Últimas {VENTANA} semanas (base del pronóstico)")
    tabla = ultimas[["semana","n_ventas","ganancia","monto"]].copy()
    tabla.columns = ["Semana","N° Ventas","Ganancia ($)","Monto ($)"]
    st.dataframe(tabla.reset_index(drop=True), use_container_width=True)

    st.info(
        f"**Metodología:** Se usan las {VENTANA} semanas completas más recientes. "
        f"El promedio móvil da la estimación base, la variación semanal valida si hay aceleración o desaceleración, "
        f"y la regresión lineal detecta si existe una tendencia estructural de largo plazo."
    )
