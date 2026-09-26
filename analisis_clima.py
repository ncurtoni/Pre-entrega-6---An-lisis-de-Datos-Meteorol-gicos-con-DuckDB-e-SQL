"""
Analisis de datos meteorologicos con DuckDB.
Consulta el CSV directamente desde disco, sin cargarlo en una base de
datos tradicional ni persistir un archivo binario propio: la conexion
es en memoria (":memory:") y DuckDB lee el archivo al vuelo cada vez
que una consulta lo referencia.
"""

import time
import duckdb

RUTA_CSV = "data/clima.csv"

con = duckdb.connect(":memory:")

# Vista sobre el archivo: no copia los datos a ningun lado, es solo una
# consulta guardada que apunta al CSV. read_csv_auto detecta tipos de
# columna automaticamente (fecha como DATE, temperatura como DOUBLE, etc).
con.execute(f"""
    CREATE OR REPLACE VIEW clima AS
    SELECT * FROM read_csv_auto('{RUTA_CSV}')
""")

total_filas = con.sql("SELECT COUNT(*) AS total FROM clima").df()["total"][0]
nulos_temp = con.sql("SELECT COUNT(*) AS nulos FROM clima WHERE temperatura IS NULL").df()["nulos"][0]
print(f"Filas totales: {total_filas}")
print(f"Temperaturas nulas antes de limpiar: {nulos_temp}")

# Limpieza: los nulos de temperatura se completan con la mediana de esa
# misma estacion meteorologica (no la mediana global), porque el clima
# de Bariloche y el de Buenos Aires no son comparables. La mediana es
# mas robusta que el promedio ante dias extremos puntuales.
con.execute("""
    CREATE OR REPLACE VIEW clima_limpio AS
    WITH medianas AS (
        SELECT estacion, MEDIAN(temperatura) AS mediana_temp
        FROM clima
        GROUP BY estacion
    )
    SELECT
        c.estacion,
        c.fecha,
        COALESCE(c.temperatura, m.mediana_temp) AS temperatura,
        c.precipitacion_mm
    FROM clima c
    JOIN medianas m ON c.estacion = m.estacion
""")

nulos_despues = con.sql("SELECT COUNT(*) AS nulos FROM clima_limpio WHERE temperatura IS NULL").df()["nulos"][0]
print(f"Temperaturas nulas despues de limpiar: {nulos_despues}")


def medir(nombre, consulta):
    inicio = time.time()
    resultado = con.sql(consulta).df()
    duracion = time.time() - inicio
    print(f"\n{nombre} ({duracion*1000:.2f} ms)")
    print(resultado)
    return resultado


# 1. Promedios: temperatura promedio mensual por estacion
medir("Consulta 1: Promedio mensual de temperatura por estacion", """
    SELECT
        estacion,
        MONTH(CAST(fecha AS DATE)) AS mes,
        ROUND(AVG(temperatura), 1) AS temperatura_promedio
    FROM clima_limpio
    GROUP BY estacion, mes
    ORDER BY estacion, mes
""")

# 2. Maximos historicos por estacion
medir("Consulta 2: Temperatura maxima historica por estacion", """
    SELECT
        estacion,
        MAX(temperatura) AS temperatura_maxima,
        fecha AS fecha_del_maximo
    FROM clima_limpio
    WHERE temperatura = (
        SELECT MAX(temperatura) FROM clima_limpio c2 WHERE c2.estacion = clima_limpio.estacion
    )
    GROUP BY estacion, fecha
    ORDER BY temperatura_maxima DESC
""")

# 3. Conteo con filtrado complejo: dias de helada (temperatura < 0) por estacion
medir("Consulta 3: Dias de helada (temperatura < 0) por estacion", """
    SELECT
        estacion,
        COUNT(*) AS dias_de_helada
    FROM clima_limpio
    WHERE temperatura < 0
    GROUP BY estacion
    ORDER BY dias_de_helada DESC
""")

con.close()
