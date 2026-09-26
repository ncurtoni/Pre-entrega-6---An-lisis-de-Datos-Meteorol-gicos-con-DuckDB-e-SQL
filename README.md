# Analisis de datos meteorologicos con DuckDB

Analisis de un dataset de clima diario (temperatura y precipitacion) de tres
estaciones meteorologicas argentinas, consultando el archivo CSV **directamente**
con DuckDB, sin cargarlo en una base de datos tradicional ni generar ningun
archivo binario propio (la conexion de DuckDB es en memoria).

## Archivos

- `analisis_clima.py`: script principal, con las consultas SQL embebidas.
- `data/clima.csv`: dataset de clima diario (2025 completo, 3 estaciones,
  1095 filas). Es un dataset sintetico generado para este ejercicio, con
  patrones estacionales realistas del hemisferio sur (veranos calidos en
  enero, inviernos frios en julio) y un 5% de temperaturas nulas insertadas
  a proposito para poder demostrar la limpieza de datos.
- `requirements.txt`: dependencias (`duckdb`, `pandas`).

## Como ejecutar

```bash
pip install -r requirements.txt
python analisis_clima.py
```

No hace falta instalar ningun motor de base de datos aparte: DuckDB se
instala como una libreria de Python mas, y lee el CSV al vuelo.

## Como funciona (sin base de datos tradicional)

```python
con = duckdb.connect(":memory:")  # conexion en memoria, no se guarda en disco

con.execute("""
    CREATE OR REPLACE VIEW clima AS
    SELECT * FROM read_csv_auto('data/clima.csv')
""")
```

`read_csv_auto` le dice a DuckDB que lea el archivo directamente y detecte
los tipos de columna solo (fecha como `DATE`, temperatura como `DOUBLE`,
etc.). La `VIEW` no copia los datos a ningun lado: es una consulta guardada
que apunta al archivo. En ningun momento se crea una base de datos SQLite,
MySQL, ni un archivo `.duckdb` persistido en el repositorio.

## Limpieza de datos

El CSV tiene 48 temperaturas nulas (de 1095 filas). Se completan con la
**mediana de esa misma estacion meteorologica** (no una mediana global),
porque el clima de Bariloche y el de Buenos Aires no son comparables. Se
eligio la mediana por sobre el promedio por ser mas robusta ante dias
extremos puntuales.

## Consultas y hallazgos

### 1. Promedio mensual de temperatura por estacion

Confirma el patron estacional esperado del hemisferio sur: los tres promedios
mas altos de cada estacion caen en diciembre-enero-febrero, y los mas bajos
en junio-julio. Cordoba fue la mas calida en verano (26-27 grados de
promedio mensual) y Bariloche la mas fria en invierno (0.2-0.7 grados).

### 2. Temperatura maxima historica por estacion

| Estacion | Maxima | Fecha |
|---|---|---|
| Cordoba | 31.1 | 2025-01-08 |
| Buenos Aires | 30.2 | 2025-12-23 |
| Bariloche | 22.0 | 2025-01-11 |

Los tres maximos caen en pleno verano, coherente con el patron estacional.

### 3. Dias de helada (temperatura menor a 0) por estacion

Solo Bariloche registro dias de helada en este dataset: 30 dias en todo 2025
(concentrados en el invierno). Buenos Aires y Cordoba no tuvieron ningun dia
por debajo de 0 grados.

## Tiempos de respuesta observados

Con el dataset de 1095 filas (chico para los estandares de DuckDB, que esta
pensado para millones de filas), cada consulta se resolvio en menos de medio
segundo, incluyendo la lectura del CSV desde disco en cada caso:

| Consulta | Tiempo |
|---|---|
| Promedio mensual por estacion | ~170 ms |
| Maximo historico por estacion | ~360 ms |
| Dias de helada por estacion | ~190 ms |

Estos tiempos incluyen leer el archivo completo desde cero en cada consulta
(no hay ninguna tabla cacheada en memoria entre una consulta y la
siguiente), lo que confirma que DuckDB puede resolver analisis agregados
sobre un archivo plano sin necesidad de una etapa previa de carga a una
base de datos tradicional.
