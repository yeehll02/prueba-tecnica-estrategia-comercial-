import os
import ftfy
import pandas as pd
from sqlalchemy import create_engine

# ── Configuración ──────────────────────────────────────────────────────────────
RUTA_DATOS = os.path.dirname(os.path.abspath(__file__))

CONFIGURACION_BD = {
    "host":     "localhost",
    "puerto":   5432,
    "base":     "analitica_comercial",
    "usuario":  "postgres",
    "clave":    "admin",
}


# ── Pipeline ───────────────────────────────────────────────────────────────────

class PipelineDatos:
    """
    Pipeline ETL end-to-end para la prueba técnica de Estrategia Comercial.
    Flujo: Ingesta → Limpieza → Transformación → Enriquecimiento → Carga
    """

    def __init__(self, ruta_datos, config_bd):
        self.ruta_datos  = ruta_datos
        self.config_bd   = config_bd
        self.ruta_output = os.path.join(ruta_datos, "output")
        self.clientes    = None
        self.ventas      = None
        self.ciudades    = None
        self.sucursales  = None
        self.dataset     = None
        os.makedirs(self.ruta_output, exist_ok=True)

    # ── 1. Ingesta ─────────────────────────────────────────────────────────────

    def ingestar(self):
        """Carga los 4 archivos CSV desde disco."""
        print("\n=== INGESTA ===")
        self.clientes   = self._cargar_csv("clientes.csv")
        self.ventas     = self._cargar_csv("ventas.csv")
        self.ciudades   = self._cargar_csv("ciudades.csv")
        self.sucursales = self._cargar_csv("sucursales.csv")

    def _cargar_csv(self, archivo):
        ruta = os.path.join(self.ruta_datos, archivo)
        df = pd.read_csv(ruta, encoding="latin-1")
        df.columns = df.columns.str.strip().str.lower()
        for col in df.select_dtypes(include="str").columns:
            df[col] = df[col].apply(lambda x: ftfy.fix_text(x) if isinstance(x, str) else x)
        print(f"  [OK] {archivo}: {len(df):,} filas cargadas")
        return df

    # ── 2. Limpieza ────────────────────────────────────────────────────────────

    def limpiar(self):
        """Elimina duplicados, corrige tipos de dato y normaliza texto."""
        print("\n=== LIMPIEZA ===")

        self.clientes = (
            self.clientes
            .drop_duplicates(subset="id")
            .assign(
                segmento=self.clientes["segmento"].str.strip().str.lower(),
                cliente_estrategico=self.clientes["cliente_estrategico"].fillna(0).astype(int)
            )
        )

        self.ventas = (
            self.ventas
            .drop_duplicates()
            .assign(
                fecha=pd.to_datetime(self.ventas["fecha"], dayfirst=True, errors="coerce"),
                monto=pd.to_numeric(self.ventas["monto"], errors="coerce"),
                ganancia=pd.to_numeric(self.ventas["ganancia"], errors="coerce"),
                rentabilidad_tasa=pd.to_numeric(self.ventas["rentabilidad_tasa"], errors="coerce"),
            )
            .dropna(subset=["id_cliente", "monto", "fecha"])
        )

        # Renombrar para evitar conflictos en el cruce
        self.ciudades = (
            self.ciudades
            .drop_duplicates(subset="id_ciudad")
            .rename(columns={"ciudad": "nombre_ciudad"})
        )

        self.sucursales = (
            self.sucursales
            .drop_duplicates(subset="id_sucursal")
            .rename(columns={"sucursal": "nombre_sucursal", "ciudad": "ciudad_sucursal_id"})
        )

        # Corrección de valores corruptos identificados en los datos fuente
        for df in [self.clientes, self.ventas, self.ciudades, self.sucursales]:
            for col in df.select_dtypes(include="str").columns:
                df[col] = (
                    df[col]
                    .str.replace("Bogot+a", "Bogotá", regex=False)
                    .str.replace(r"Rodri.guez", "Rodríguez", regex=True)
                )

        print("  [OK] Limpieza completada en las 4 fuentes")

    # ── 3. Transformación (cruce de fuentes) ───────────────────────────────────

    def transformar(self):
        """Une las 4 fuentes en un único dataset analítico."""
        print("\n=== TRANSFORMACIÓN ===")

        df = (
            self.ventas
            .merge(self.clientes,   left_on="id_cliente",    right_on="id",         how="left")
            .merge(self.ciudades,   left_on="ciudad",         right_on="id_ciudad",  how="left")
            .merge(self.sucursales, left_on="sucursal_venta", right_on="id_sucursal",how="left")
            .drop(columns=["id", "id_ciudad", "id_sucursal", "ciudad_sucursal_id"], errors="ignore")
        )

        print(f"  [OK] Cruce completado: {len(df):,} filas | {len(df.columns)} columnas")
        self.dataset = df

    # ── 4. Enriquecimiento ─────────────────────────────────────────────────────

    def enriquecer(self):
        """Agrega variables derivadas que enriquecen el análisis."""
        print("\n=== ENRIQUECIMIENTO ===")
        df = self.dataset

        # Tipo de producto: Crédito vs Inversión
        credito = ["libre inversion", "hipotecario", "libranza", "tarjeta credito"]
        df["tipo_producto"] = df["producto"].apply(
            lambda x: "Crédito" if x in credito else "Inversión"
        )

        # Tipo de monto: segmentación por percentiles Q1 y Q3
        q1 = df["monto"].quantile(0.25)
        q3 = df["monto"].quantile(0.75)
        df["tipo_monto"] = pd.cut(
            df["monto"],
            bins=[0, q1, q3, float("inf")],
            labels=["Bajo", "Medio", "Alto"]
        ).astype(str)

        # Diferencial de rentabilidad vs promedio del producto
        media_por_producto = df.groupby("producto")["rentabilidad_tasa"].transform("mean")
        df["rentabilidad_diferencial"] = df["rentabilidad_tasa"] - media_por_producto

        # Variables temporales para análisis y forecasting
        df["anio"]      = df["fecha"].dt.year
        df["mes"]       = df["fecha"].dt.month
        df["trimestre"] = df["fecha"].dt.quarter
        df["semana"]    = df["fecha"].dt.isocalendar().week.astype(int)

        self.dataset = df
        print("  [OK] Variables agregadas: tipo_producto, tipo_monto, rentabilidad_diferencial, anio, mes, trimestre, semana")

    # ── 5. Carga ───────────────────────────────────────────────────────────────

    def cargar(self):
        """Exporta el dataset final a PostgreSQL y a CSV."""
        print("\n=== CARGA ===")
        cfg = self.config_bd
        url = (
            f"postgresql+psycopg2://{cfg['usuario']}:{cfg['clave']}"
            f"@{cfg['host']}:{cfg['puerto']}/{cfg['base']}"
        )
        motor = create_engine(url)

        # Tabla principal: hechos de venta desnormalizados para análisis y dashboard
        self.dataset.to_sql("hechos_ventas", motor, if_exists="replace", index=False)
        print("  [OK] Tabla 'hechos_ventas' cargada en PostgreSQL")

        # Tablas de dimensiones limpias para consultas relacionales
        self.clientes.to_sql("dim_clientes",   motor, if_exists="replace", index=False)
        self.ciudades.to_sql("dim_ciudades",   motor, if_exists="replace", index=False)
        self.sucursales.to_sql("dim_sucursales", motor, if_exists="replace", index=False)
        print("  [OK] Tablas de dimensiones cargadas: dim_clientes, dim_ciudades, dim_sucursales")

        # Exportar todos los datasets a la carpeta output/
        salidas = {
            "hechos_ventas.csv":   self.dataset,
            "dim_clientes.csv":    self.clientes,
            "dim_ciudades.csv":    self.ciudades,
            "dim_sucursales.csv":  self.sucursales,
        }
        for nombre, df in salidas.items():
            ruta = os.path.join(self.ruta_output, nombre)
            df.to_csv(ruta, index=False, encoding="utf-8-sig")
            print(f"  [OK] output/{nombre} exportado")

    # ── Ejecución completa ─────────────────────────────────────────────────────

    def ejecutar(self):
        self.ingestar()
        self.limpiar()
        self.transformar()
        self.enriquecer()
        self.cargar()
        print(f"\n=== PIPELINE COMPLETADO ===")
        print(f"  Filas: {len(self.dataset):,} | Columnas: {list(self.dataset.columns)}")
        return self.dataset


# ── Ejecución ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    pipeline = PipelineDatos(RUTA_DATOS, CONFIGURACION_BD)
    df_final = pipeline.ejecutar()
    # print("\n", df_final.head(3).to_string())
