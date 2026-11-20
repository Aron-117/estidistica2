# =============================================================================
# BLOQUE 1 - EXTRACCIÓN, LIMPIEZA Y MUESTRA (Rol 2: Líder de Programación)
# Proyecto: Demografía y distribución entre zonas (urbano vs. rural)
# Base: EH2025_Persona.sav
# Requiere: pandas, numpy, pyreadstat   (pip install pandas numpy pyreadstat)
# Salidas : muestra_mas.csv, poblacion_limpia.csv, control_bloque1.txt
# =============================================================================
import re
import math
import numpy as np
import pandas as pd

# -----------------------------------------------------------------------------
# 0. CONFIGURACIÓN  (lo único que debes ajustar)
# -----------------------------------------------------------------------------
RUTA_SAV   = "EH2025_Persona.sav"
SEMILLA    = 2025          # semilla fija -> la muestra se puede reproducir
E          = 0.03          # error máximo (3%)
Z          = 1.96          # 95% de confianza
P          = 0.5           # p=0.5 (máxima varianza) si no hay otro dato
N_MUESTRA  = None          # <- poner aquí el n que defina el Rol 1; si es None se calcula abajo

# Nombres de columnas en el .sav. Se rellenan en el paso 2 (con la ayuda de
# buscar_columnas). Los nombres de abajo son SUPUESTOS: confírmalos.
COL = {
    "area":    "area",     # 1 = urbano, 2 = rural
    "depto":   "depto",    # departamento
    "sexo":    "s1_02",    # sexo (S1-P2)               <- confirmar
    "edad":    "s1_03",    # edad (S1-P3)
    "estciv":  "s1_10",    # estado civil (S1-P10)      <- confirmar
    "nacio":   "s1_10a",   # nació en este lugar (S1-P10a)
    "emb":     "s2_06",    # está/estuvo embarazada (S2-P6)  <- confirmar
    "hijos":   "s2_07",    # hijos nacidos vivos (S2-P7)
}
# Códigos asumidos (verifícalos con las etiquetas del .sav, paso 2):
COD_URBANO, COD_RURAL = 1, 2
COD_MUJER             = 2
COD_EMB_SI            = 1   # "sí" en S2-P6


# -----------------------------------------------------------------------------
# 1. CARGA
# -----------------------------------------------------------------------------
def cargar_sav(ruta):
    import pyreadstat
    # formatos numéricos (sin convertir a texto) para poder operar con códigos
    df, meta = pyreadstat.read_sav(ruta, apply_value_formats=False,
                                   user_missing=False)
    df.columns = [c.lower() for c in df.columns]
    etiquetas = {c.lower(): l for c, l in zip(meta.column_names, meta.column_labels)}
    return df, meta, etiquetas


# -----------------------------------------------------------------------------
# 2. EXPLORACIÓN: ubicar columnas por palabra clave en nombre o etiqueta
# -----------------------------------------------------------------------------
def buscar_columnas(etiquetas, patron):
    """Ej.: buscar_columnas(etiquetas, 'edad|años cumplidos')"""
    rx = re.compile(patron, re.I)
    return {c: l for c, l in etiquetas.items()
            if rx.search(c) or (l and rx.search(str(l)))}


PISTAS = {
    "area":   r"^area$|[áa]rea",
    "depto":  r"depart",
    "sexo":   r"sexo",
    "edad":   r"edad|a[ñn]os cumplidos",
    "estciv": r"estado civil|casad|conviv",
    "nacio":  r"naci[óo] en|lugar de nacimiento|d[óo]nde naci",
    "emb":    r"embaraz",
    "hijos":  r"hij[oa]s.*(vivos|nacidos)|nacidos vivos",
}


def sugerir_columnas(etiquetas):
    """Imprime candidatos por variable según nombre/etiqueta. Úsalo para llenar COL."""
    print("\nCANDIDATOS (confirma y copia el nombre correcto en COL):")
    for k, patron in PISTAS.items():
        cand = buscar_columnas(etiquetas, patron)
        print(f"  {k:7s}:", dict(list(cand.items())[:6]) or "sin coincidencias")


def inspeccionar(df, meta=None):
    print("Filas x columnas:", df.shape)
    for k, c in COL.items():
        if c not in df.columns:
            print(f"  [FALTA] {k:7s} -> '{c}' no existe en la base")
            continue
        print(f"  [ok]    {k:7s} -> '{c}'  nulos={df[c].isna().sum():,}  "
              f"valores={sorted(df[c].dropna().unique())[:12]}")
    if meta is not None:
        for k in ("area", "nacio", "estciv", "emb", "sexo"):
            c = COL[k]
            if c in meta.variable_value_labels:
                print(f"  etiquetas {c}: {meta.variable_value_labels[c]}")


# -----------------------------------------------------------------------------
# 3. CONSTRUCCIÓN DE VARIABLES Y UNIVERSOS (SOBRE LA BASE TOTAL)
#    Cada variable queda en NaN fuera de su universo -> los "casos válidos"
#    de cada variable son simplemente dropna() de esa columna.
# -----------------------------------------------------------------------------
def construir_variables(df):
    d = pd.DataFrame(index=df.index)
    d["area"]  = df[COL["area"]]
    d["depto"] = df[COL["depto"]]
    d["urbano"] = (d["area"] == COD_URBANO).astype(float)
    d.loc[~d["area"].isin([COD_URBANO, COD_RURAL]), "urbano"] = np.nan

    # --- Cuantitativa 1: EDAD (universo: todas las personas) -----------------
    # 0 = menor de 1 año (valor válido). 98 = "98 o más" (tope) -> limitación.
    d["edad"] = df[COL["edad"]].where(df[COL["edad"]].between(0, 98))

    # --- Cuantitativa 2: HIJOS NACIDOS VIVOS ---------------------------------
    # Universo: mujeres de 13 a 50 años que están o estuvieron embarazadas.
    # El 0 es un cero válido. Vacíos = no pasaron por la pregunta -> NaN.
    univ_hijos = ((df[COL["sexo"]] == COD_MUJER)
                  & df[COL["edad"]].between(13, 50)
                  & (df[COL["emb"]] == COD_EMB_SI))
    d["hijos"] = df[COL["hijos"]].where(univ_hijos)
    # Valores raros: negativos o > 20 se marcan y se pasan a NaN (revisar!)
    d["hijos_raro"] = d["hijos"].notna() & ~d["hijos"].between(0, 20)
    d.loc[d["hijos_raro"], "hijos"] = np.nan

    # --- Dicotómica 1: NACIÓ EN ESTE LUGAR (universo: todas las personas) ----
    # 1 si respondió 1; 0 si respondió 2 o 3.
    n = df[COL["nacio"]]
    d["nacio_lugar"] = np.where(n == 1, 1.0, np.where(n.isin([2, 3]), 0.0, np.nan))

    # --- Dicotómica 2: VIVE EN UNIÓN (universo: 12 años o más) ---------------
    # 1 si casada/o (1) o conviviente (2); 0 si 3..6.
    ec = df[COL["estciv"]]
    en_universo = df[COL["edad"]] >= 12
    d["vive_union"] = np.where(ec.isin([1, 2]), 1.0, np.where(ec.isin([3, 4, 5, 6]), 0.0, np.nan))
    d.loc[~en_universo, "vive_union"] = np.nan

    return d


# -----------------------------------------------------------------------------
# 4. TAMAÑO DE MUESTRA (referencia; la fórmula final la fija el Rol 1)
#    n0 = Z^2 * p * (1-p) / e^2 ;  n = n0 / (1 + (n0-1)/N)   (pob. finita)
# -----------------------------------------------------------------------------
def tamano_muestra(N, e=E, z=Z, p=P):
    n0 = (z ** 2) * p * (1 - p) / e ** 2
    return math.ceil(n0 / (1 + (n0 - 1) / N))


# -----------------------------------------------------------------------------
# 5. MUESTRA ALEATORIA SIMPLE (MAS) DE TODA LA BASE
# -----------------------------------------------------------------------------
def extraer_mas(d, n, semilla=SEMILLA):
    return d.sample(n=n, replace=False, random_state=semilla)


# -----------------------------------------------------------------------------
# 6. CONTROLES (para el informe y la defensa)
# -----------------------------------------------------------------------------
def controles(d, m):
    L = []
    L.append(f"N poblacion = {len(d):,} | n muestra = {len(m):,}")
    L.append("\nCasos válidos por variable (Población | Muestra):")
    for v in ["edad", "hijos", "nacio_lugar", "vive_union"]:
        L.append(f"  {v:12s} {d[v].notna().sum():>9,} | {m[v].notna().sum():>7,}")
    L.append("\nCasos válidos por variable y área en la MUESTRA (urbano / rural):")
    for v in ["edad", "hijos", "nacio_lugar", "vive_union"]:
        u = m.loc[m["area"] == COD_URBANO, v].notna().sum()
        r = m.loc[m["area"] == COD_RURAL, v].notna().sum()
        L.append(f"  {v:12s} {u:>6,} / {r:>6,}   {'<-- OJO: <30' if min(u, r) < 30 else ''}")
    L.append("\nProporciones por área en la POBLACIÓN (deben estar ~15%-85%):")
    for v in ["nacio_lugar", "vive_union"]:
        pr = d.groupby("area")[v].mean().round(3).to_dict()
        L.append(f"  {v:12s} {pr}")
    L.append(f"\nHijos fuera de rango descartados (pob.): {int(d['hijos_raro'].sum())}")
    L.append(f"Edad == 98 (tope '98 o más') en población: {(d['edad']==98).sum():,}")
    L.append(f"\n% urbano  población={d['urbano'].mean():.4f} | muestra={m['urbano'].mean():.4f}")
    return "\n".join(L)


# -----------------------------------------------------------------------------
# 7. PROGRAMA PRINCIPAL
# -----------------------------------------------------------------------------
def main():
    df, meta, etiquetas = cargar_sav(RUTA_SAV)
    sugerir_columnas(etiquetas)              # 1) ve candidatos y ajusta COL
    inspeccionar(df, meta)                   # 2) revisa que no diga [FALTA]
    faltan = [c for c in COL.values() if c not in df.columns]
    if faltan:
        raise SystemExit(f"Corrige COL, no existen: {faltan}")
    d = construir_variables(df)

    N = len(d)
    n = N_MUESTRA or tamano_muestra(N)
    print(f"Tamaño de muestra usado: n = {n}")

    m = extraer_mas(d, n)

    d.to_csv("poblacion_limpia.csv", index=False)   # base total (Rol 3 calcula parámetros)
    m.to_csv("muestra_mas.csv", index=False)        # ENTREGABLE .csv

    txt = controles(d, m)
    print(txt)
    open("control_bloque1.txt", "w", encoding="utf-8").write(txt)


if __name__ == "__main__":
    main()
