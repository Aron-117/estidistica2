"""Proyecto: Demografia y distribucion entre zonas urbano-rural.

Requisitos:
    pip install pandas numpy pyreadstat scipy

Coloca EH2025_Persona.sav en la misma carpeta que este archivo (o cambia
RUTA_SAV) y ejecuta:
    python proyecto_demografia_zonas.py

Antes de entregar, confirma los nombres y codigos de COL y COD_* con las
etiquetas que el programa imprime al iniciar.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scipy import stats
except ImportError as error:
    raise SystemExit("Falta scipy. Instala requisitos con: pip install pandas numpy pyreadstat scipy") from error


# -----------------------------------------------------------------------------
# 0. CONFIGURACION: revisar solo esta seccion antes de ejecutar
# -----------------------------------------------------------------------------
RUTA_SAV = r"C:\Users\aronc\Downloads\BD_EH2025_Persona\EH2025_Persona.sav"
CARPETA_SALIDA = "resultados_demografia"
SEMILLA = 2025
E = 0.03                         # error maximo para calcular n
Z = 1.96                         # nivel de confianza para proporciones: 95 %
P = 0.50                         # maxima variabilidad cuando p es desconocida
N_MUESTRA = 1040                # escribe aqui el n acordado por el grupo
NIVEL_CONFIANZA = 0.95

# Nombres supuestos de la EH2025. Deben coincidir con los candidatos impresos.
COL = {
    "area":   "area",
    "depto":  "depto",
    "sexo":   "s01a_02",
    "edad":   "s01a_03",
    "aestudio": "aestudio",
    "estciv":   "s01a_10",
    "nacio":    "s01b_10a",
}
COD_URBANO, COD_RURAL = 1, 2


CUANTITATIVAS = ["edad", "aestudio"]
DICOTOMICAS = ["nacio_lugar", "vive_union"]
NOMBRES = {
    "edad": "Edad en anos cumplidos",
    "aestudio": "Anios de estudio",
    "nacio_lugar": "Nacio en este lugar",
    "vive_union": "Vive en union",
}


# -----------------------------------------------------------------------------
# 1. CARGA Y EXPLORACION
# -----------------------------------------------------------------------------
def cargar_sav(ruta: str | Path):
    """Lee codigos numericos, sin sustituirlos por sus etiquetas de texto."""
    import pyreadstat

    df, meta = pyreadstat.read_sav(ruta, apply_value_formats=False, user_missing=False)
    df.columns = [str(c).lower() for c in df.columns]
    etiquetas = {
        str(c).lower(): etiqueta
        for c, etiqueta in zip(meta.column_names, meta.column_labels)
    }
    # Las etiquetas de valores permiten verificar los codigos usados arriba.
    etiquetas_valor = {
        str(c).lower(): valores
        for c, valores in meta.variable_value_labels.items()
    }
    return df, etiquetas, etiquetas_valor


PISTAS = {
    "area": r"^area$|[áa]rea",
    "depto": r"depart",
    "sexo": r"sexo",
    "edad": r"edad|a[ñn]os cumplidos",
    "aestudio": r"aestudio|a[ñn]os de estudio|instrucci[óo]n",
    "estciv": r"estado civil|casad|conviv",
    "nacio": r"naci[óo] en|lugar de nacimiento|d[óo]nde naci",
}


def buscar_columnas(etiquetas: dict, patron: str) -> dict:
    rx = re.compile(patron, re.IGNORECASE)
    return {
        columna: etiqueta
        for columna, etiqueta in etiquetas.items()
        if rx.search(columna) or (etiqueta and rx.search(str(etiqueta)))
    }


def reporte_exploracion(df: pd.DataFrame, etiquetas: dict, etiquetas_valor: dict) -> str:
    lineas = [f"Filas x columnas de la base original: {df.shape}", "", "CANDIDATOS PARA COL:"]
    for clave, patron in PISTAS.items():
        candidatos = dict(list(buscar_columnas(etiquetas, patron).items())[:8])
        lineas.append(f"  {clave}: {candidatos or 'sin coincidencias'}")

    lineas.extend(["", "COLUMNAS CONFIGURADAS:"])
    for clave, columna in COL.items():
        if columna not in df.columns:
            lineas.append(f"  [FALTA] {clave}: '{columna}' no existe")
            continue
        valores = sorted(df[columna].dropna().unique().tolist())[:15]
        lineas.append(f"  [OK] {clave}: '{columna}', nulos={df[columna].isna().sum():,}, valores={valores}")
        if columna in etiquetas_valor:
            lineas.append(f"       etiquetas: {etiquetas_valor[columna]}")
    return "\n".join(lineas)


def validar_columnas(df: pd.DataFrame) -> None:
    faltan = [columna for columna in COL.values() if columna not in df.columns]
    if faltan:
        raise SystemExit(f"Corrige COL: estas columnas no existen en la base: {faltan}")


# -----------------------------------------------------------------------------
# 2. LIMPIEZA Y DEFINICION DE UNIVERSOS
# -----------------------------------------------------------------------------
def construir_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Deja NaN fuera de cada universo: el analisis usa solo casos validos."""
    d = pd.DataFrame(index=df.index)
    d["area"] = df[COL["area"]]
    d["depto"] = df[COL["depto"]]
    d["urbano"] = np.where(d["area"] == COD_URBANO, 1.0,
                           np.where(d["area"] == COD_RURAL, 0.0, np.nan))

    # Edad: 0 significa menor de un ano; 98 es "98 o mas" y se conserva.
    d["edad"] = df[COL["edad"]].where(df[COL["edad"]].between(0, 98))

    # Anos de estudio: 0 es valido (sin instruccion formal); se excluyen negativos/NaN.
    aestudio = pd.to_numeric(df[COL["aestudio"]], errors="coerce")
    d["aestudio"] = aestudio.where(aestudio >= 0)

    # Nacio en este lugar: 1 = mismo municipio/ciudad; 0 = otro lugar o exterior.
    nacio = df[COL["nacio"]]
    d["nacio_lugar"] = np.where(
        nacio == 1, 1.0, np.where(nacio.isin([2, 3]), 0.0, np.nan)
    )

    # Vive en union: solo universo de 12 anos o mas.
    estciv = df[COL["estciv"]]
    d["vive_union"] = np.where(
        estciv.isin([1, 2]), 1.0, np.where(estciv.isin([3, 4, 5, 6]), 0.0, np.nan)
    )
    d.loc[df[COL["edad"]] < 12, "vive_union"] = np.nan
    return d


# -----------------------------------------------------------------------------
# 3. MUESTRA ALEATORIA SIMPLE
# -----------------------------------------------------------------------------
def tamano_muestra(N: int, e: float = E, z: float = Z, p: float = P) -> int:
    """Formula con correccion por poblacion finita."""
    if N < 2:
        raise ValueError("La poblacion debe tener al menos dos registros.")
    n0 = (z**2) * p * (1 - p) / (e**2)
    return min(N, math.ceil(n0 / (1 + (n0 - 1) / N)))


def extraer_mas(d: pd.DataFrame, n: int, semilla: int = SEMILLA) -> pd.DataFrame:
    if not 1 <= n <= len(d):
        raise ValueError(f"n debe estar entre 1 y {len(d):,}; se recibio {n:,}.")
    return d.sample(n=n, replace=False, random_state=semilla).copy()


# -----------------------------------------------------------------------------
# 4. ESTADISTICA DESCRIPTIVA E INTERVALOS DE CONFIANZA
# -----------------------------------------------------------------------------
def etiqueta_area(codigo) -> str:
    if codigo == COD_URBANO:
        return "Urbano"
    if codigo == COD_RURAL:
        return "Rural"
    return str(codigo)


def casos_por_area(d: pd.DataFrame, variable: str) -> dict:
    resultado = {}
    for codigo in (COD_URBANO, COD_RURAL):
        serie = d.loc[d["area"] == codigo, variable].dropna()
        resultado[codigo] = serie.astype(float)
    return resultado


def ci_media(serie: pd.Series, confianza: float = NIVEL_CONFIANZA) -> tuple[float, float]:
    n = len(serie)
    if n < 2:
        return (np.nan, np.nan)
    media = serie.mean()
    se = serie.std(ddof=1) / math.sqrt(n)
    margen = stats.t.ppf((1 + confianza) / 2, df=n - 1) * se
    return media - margen, media + margen


def resumen_cuantitativa(d: pd.DataFrame, variable: str, fuente: str, incluir_ic: bool) -> list[dict]:
    filas = []
    for codigo, serie in casos_por_area(d, variable).items():
        fila = {
            "fuente": fuente, "variable": variable, "descripcion": NOMBRES[variable],
            "tipo": "media", "area": etiqueta_area(codigo), "n_validos": len(serie),
            "estimacion": serie.mean(), "desviacion_estandar": serie.std(ddof=1),
        }
        if incluir_ic:
            fila["ic_inferior"], fila["ic_superior"] = ci_media(serie)
        filas.append(fila)
    return filas


def resumen_proporcion(d: pd.DataFrame, variable: str, fuente: str, incluir_ic: bool) -> list[dict]:
    filas = []
    for codigo, serie in casos_por_area(d, variable).items():
        n = len(serie)
        prop = serie.mean() if n else np.nan
        fila = {
            "fuente": fuente, "variable": variable, "descripcion": NOMBRES[variable],
            "tipo": "proporcion", "area": etiqueta_area(codigo), "n_validos": n,
            "estimacion": prop, "casos_si": serie.sum(),
        }
        if incluir_ic and n:
            margen = Z * math.sqrt(prop * (1 - prop) / n)
            fila["ic_inferior"] = max(0.0, prop - margen)
            fila["ic_superior"] = min(1.0, prop + margen)
        filas.append(fila)
    return filas


def diferencia_poblacion(d: pd.DataFrame, variable: str, tipo: str) -> dict:
    """Parametro descriptivo: diferencia real urbano menos rural, sin IC."""
    grupos = casos_por_area(d, variable)
    urbano, rural = grupos[COD_URBANO], grupos[COD_RURAL]
    return {
        "fuente": "poblacion", "variable": variable, "descripcion": NOMBRES[variable],
        "tipo": tipo, "comparacion": "Urbano - Rural",
        "n_urbano": len(urbano), "n_rural": len(rural),
        "estimacion": urbano.mean() - rural.mean(),
    }


def comparar_medias(muestra: pd.DataFrame, variable: str) -> dict:
    grupos = casos_por_area(muestra, variable)
    urbano, rural = grupos[COD_URBANO], grupos[COD_RURAL]
    base = {
        "fuente": "muestra", "variable": variable, "descripcion": NOMBRES[variable],
        "tipo": "diferencia_de_medias", "comparacion": "Urbano - Rural",
        "n_urbano": len(urbano), "n_rural": len(rural),
        "estimacion": urbano.mean() - rural.mean(),
    }
    if len(urbano) < 2 or len(rural) < 2:
        return base | {"metodo": "No calculable: menos de 2 casos por area"}

    prueba_levene = stats.levene(urbano, rural, center="mean")
    varianzas_iguales = prueba_levene.pvalue >= 0.05
    vu, vr = urbano.var(ddof=1), rural.var(ddof=1)
    if varianzas_iguales:
        gl = len(urbano) + len(rural) - 2
        var_agrupada = ((len(urbano) - 1) * vu + (len(rural) - 1) * vr) / gl
        se = math.sqrt(var_agrupada * (1 / len(urbano) + 1 / len(rural)))
        metodo = "t con varianzas agrupadas (Levene p >= 0.05)"
    else:
        se2 = vu / len(urbano) + vr / len(rural)
        se = math.sqrt(se2)
        gl = (se2**2) / ((vu / len(urbano))**2 / (len(urbano) - 1) + (vr / len(rural))**2 / (len(rural) - 1))
        metodo = "t de Welch (Levene p < 0.05)"
    diferencia = base["estimacion"]
    t_obs = diferencia / se if se else np.nan
    critico = stats.t.ppf((1 + NIVEL_CONFIANZA) / 2, df=gl)
    return base | {
        "metodo": metodo, "levene_p": prueba_levene.pvalue, "gl": gl,
        "error_estandar": se, "estadistico": t_obs,
        "p_valor_bilateral": 2 * stats.t.sf(abs(t_obs), df=gl),
        "ic_inferior": diferencia - critico * se,
        "ic_superior": diferencia + critico * se,
    }


def comparar_proporciones(muestra: pd.DataFrame, variable: str) -> dict:
    grupos = casos_por_area(muestra, variable)
    urbano, rural = grupos[COD_URBANO], grupos[COD_RURAL]
    nu, nr = len(urbano), len(rural)
    pu = urbano.mean() if nu else np.nan
    pr = rural.mean() if nr else np.nan
    base = {
        "fuente": "muestra", "variable": variable, "descripcion": NOMBRES[variable],
        "tipo": "diferencia_de_proporciones", "comparacion": "Urbano - Rural",
        "n_urbano": nu, "n_rural": nr, "proporcion_urbana": pu,
        "proporcion_rural": pr, "estimacion": pu - pr,
        "metodo": "IC normal de dos proporciones independientes",
    }
    if not nu or not nr:
        return base
    se = math.sqrt(pu * (1 - pu) / nu + pr * (1 - pr) / nr)
    z_obs = (pu - pr) / se if se else np.nan
    return base | {
        "error_estandar": se, "estadistico": z_obs,
        "p_valor_bilateral": 2 * stats.norm.sf(abs(z_obs)),
        "ic_inferior": (pu - pr) - Z * se,
        "ic_superior": (pu - pr) + Z * se,
    }


# -----------------------------------------------------------------------------
# 5. CONTROLES DE REPRESENTATIVIDAD
# -----------------------------------------------------------------------------
def distribucion_departamento(poblacion: pd.DataFrame, muestra: pd.DataFrame) -> pd.DataFrame:
    def distribucion(d: pd.DataFrame) -> pd.Series:
        return d["depto"].value_counts(dropna=False, normalize=True)

    tabla = pd.concat(
        [distribucion(poblacion).rename("proporcion_poblacion"),
         distribucion(muestra).rename("proporcion_muestra")],
        axis=1,
    ).fillna(0)
    tabla.index.name = "depto"
    tabla = tabla.reset_index()
    tabla["diferencia_muestra_menos_poblacion"] = tabla["proporcion_muestra"] - tabla["proporcion_poblacion"]
    return tabla.sort_values("depto", key=lambda x: x.astype(str))


def control_muestra(poblacion: pd.DataFrame, muestra: pd.DataFrame) -> str:
    lineas = [
        f"N poblacion = {len(poblacion):,} | n muestra = {len(muestra):,}",
        f"Semilla de la muestra MAS = {SEMILLA}",
        "",
        "Casos validos por variable (poblacion | muestra):",
    ]
    for variable in CUANTITATIVAS + DICOTOMICAS:
        lineas.append(f"  {variable:14s} {poblacion[variable].notna().sum():>9,} | {muestra[variable].notna().sum():>7,}")
    lineas.append("\nCasos validos por variable y area en la muestra (urbano / rural):")
    for variable in CUANTITATIVAS + DICOTOMICAS:
        urbano = muestra.loc[muestra["area"] == COD_URBANO, variable].notna().sum()
        rural = muestra.loc[muestra["area"] == COD_RURAL, variable].notna().sum()
        alerta = " <-- REVISAR: menos de 30" if min(urbano, rural) < 30 else ""
        lineas.append(f"  {variable:14s} {urbano:>6,} / {rural:>6,}{alerta}")

    p_urb = poblacion["urbano"].mean()
    m_urb = muestra["urbano"].mean()
    se = math.sqrt(m_urb * (1 - m_urb) / len(muestra))
    li, ls = max(0, m_urb - Z * se), min(1, m_urb + Z * se)
    lineas.extend([
        "",
       f"Edad igual a 98 (tope '98 o mas') en poblacion: {(poblacion['edad'] == 98).sum():,}",
        f"Años de estudio igual a 0 en poblacion: {(poblacion['aestudio'] == 0).sum():,}",
        "Limitacion: aestudio excluye valores perdidos (NaN) sin imputarlos como cero.",
        "Limitacion: edad=98 representa '98 o mas', por lo que la media de edad queda acotada.",
    ])
    return "\n".join(lineas)


# -----------------------------------------------------------------------------
# 6. EJECUCION Y ARCHIVOS DE SALIDA
# -----------------------------------------------------------------------------
def main() -> None:
    ruta = Path(RUTA_SAV)
    if not ruta.exists():
        raise SystemExit(f"No se encontro '{ruta}'. Copia la base .sav junto al script o cambia RUTA_SAV.")

    df, etiquetas, etiquetas_valor = cargar_sav(ruta)
    exploracion = reporte_exploracion(df, etiquetas, etiquetas_valor)
    print(exploracion)
    validar_columnas(df)
    poblacion = construir_variables(df)

    n = N_MUESTRA if N_MUESTRA is not None else tamano_muestra(len(poblacion))
    muestra = extraer_mas(poblacion, n)
    print(f"\nTamano de muestra usado: n = {n:,}")

    parametros = []
    estimaciones = []
    for variable in CUANTITATIVAS:
        parametros.extend(resumen_cuantitativa(poblacion, variable, "poblacion", incluir_ic=False))
        parametros.append(diferencia_poblacion(poblacion, variable, "diferencia_de_medias"))
        estimaciones.extend(resumen_cuantitativa(muestra, variable, "muestra", incluir_ic=True))
    for variable in DICOTOMICAS:
        parametros.extend(resumen_proporcion(poblacion, variable, "poblacion", incluir_ic=False))
        parametros.append(diferencia_poblacion(poblacion, variable, "diferencia_de_proporciones"))
        estimaciones.extend(resumen_proporcion(muestra, variable, "muestra", incluir_ic=True))

    comparaciones = ([comparar_medias(muestra, variable) for variable in CUANTITATIVAS]
                     + [comparar_proporciones(muestra, variable) for variable in DICOTOMICAS])
    controles = control_muestra(poblacion, muestra)
    print("\n" + controles)

    salida = Path(CARPETA_SALIDA)
    salida.mkdir(parents=True, exist_ok=True)
    poblacion.to_csv(salida / "poblacion_limpia.csv", index=False, encoding="utf-8-sig")
    muestra.to_csv(salida / "muestra_mas.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(parametros).to_csv(salida / "parametros_poblacion.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(estimaciones).to_csv(salida / "estimaciones_muestra_ic.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(comparaciones).to_csv(salida / "comparaciones_urbano_rural_ic.csv", index=False, encoding="utf-8-sig")
    distribucion_departamento(poblacion, muestra).to_csv(salida / "distribucion_departamento.csv", index=False, encoding="utf-8-sig")
    (salida / "exploracion_y_codigos.txt").write_text(exploracion, encoding="utf-8")
    (salida / "control_muestra.txt").write_text(controles, encoding="utf-8")
    print(f"\nArchivos guardados en: {salida.resolve()}")


if __name__ == "__main__":
    main()