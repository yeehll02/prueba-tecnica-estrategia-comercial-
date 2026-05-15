# Prueba Técnica – Analítico Estrategia Comercial Personas

## Instalación

```bash
pip install -r requirements.txt
```

## Cómo correr

**1. Pipeline ETL** — limpia, cruza las 4 fuentes y genera los archivos listos para análisis:

```bash
python pipeline_datos.py
```

Exporta los datos procesados en `output/`. Adicionalmente los carga en PostgreSQL (`hechos_ventas`) como mecanismo de persistencia — requiere una base de datos `analitica_comercial` corriendo en `localhost:5432`.

**2. Dashboard** — el tablero consume directamente desde `output/hechos_ventas.csv`, no requiere base de datos:

```bash
streamlit run dashboard.py
```

Se abre automáticamente en `http://localhost:8501`.




## Estructura

```
├── pipeline_datos.py     # ETL: ingesta, limpieza, transformación y carga
├── dashboard.py          # Tablero interactivo (Streamlit + Plotly)
├── requirements.txt
├── clientes.csv          #fuente
├── ventas.csv            #fuente
├── ciudades.csv          #fuente
├── sucursales.csv        #fuente
└── output/               # Generado por pipeline_datos.py
    ├── hechos_ventas.csv
    ├── dim_clientes.csv
    ├── dim_ciudades.csv
    └── dim_sucursales.csv
```
