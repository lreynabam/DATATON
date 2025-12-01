import json
import os
import pandas as pd
from sklearn.ensemble import IsolationForest
from joblib import load

###################---RUTAS DE ARCHIVOS------------------------------------##################
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)
MODELS_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)
MODELO_PATH = os.path.join(MODELS_DIR, "iso_patrimonial.joblib")
TRAMOS_TRAIN_CSV = os.path.join(DATA_DIR, "panel_tramos_entrenamiento.csv")

###################--FUNCIONES DE PRE PROCESAMIENTO Y LIMPIEZA DE DATOS ---######################
def num_from_valor(v):
    if isinstance(v, dict):
        if "$numberDecimal" in v:
            return float(v["$numberDecimal"])
        if "valor" in v:
            return num_from_valor(v["valor"])
    try:
        return float(v)
    except:
        return 0.0

def suma_lista(lista, campos_posibles):
    total = 0.0
    if not isinstance(lista, list):
        return 0.0
    for item in lista:
        if not isinstance(item, dict):
            continue
        for campo in campos_posibles:
            if campo in item:
                total += float(num_from_valor(item[campo]))
                break
    return total

def extraer_campos_s1(obj):
    metadata = obj.get("metadata", {})
    declaracion = obj.get("declaracion", {})
    sitp = declaracion.get("situacionPatrimonial", {})
    fecha_act = metadata.get("actualizacion")
    try:
        anio = pd.to_datetime(fecha_act).year
    except:
        anio = None

    institucion = metadata.get("institucion", "")
    tipo_declaracion = metadata.get("tipo", "")
    datos_gen = sitp.get("datosGenerales", {})
    nombre = datos_gen.get("nombre", "")
    primer_ap = datos_gen.get("primerApellido", "")
    segundo_ap = datos_gen.get("segundoApellido", "")
    id_persona = f"{nombre} {primer_ap} {segundo_ap}".strip()
    ingresos = sitp.get("ingresos", {})
    ingreso_neto = num_from_valor(
        ingresos.get("ingresoAnualNetoDeclarante", {}).get("valor", 0)
    )
    total_ingresos_anuales = num_from_valor(
        ingresos.get("totalIngresosAnualesNetos", {}).get("valor", 0)
    )
    if total_ingresos_anuales < 0:
        total_ingresos_anuales = 0
    if ingreso_neto < 0:
        ingreso_neto = 0
    if total_ingresos_anuales == 0 and ingreso_neto > 0:
        total_ingresos_anuales = ingreso_neto

    bienes = sitp.get("bienesInmuebles", {}).get("bienInmueble", [])
    bienes_val = suma_lista(bienes, ["valorAdquisicion"])
    muebles = sitp.get("bienesMuebles", {}).get("bienMueble", [])
    muebles_val = suma_lista(muebles, ["valorAdquisicion"])
    vehiculos = sitp.get("vehiculos", {}).get("vehiculo", [])
    vehiculos_val = suma_lista(vehiculos, ["valorAdquisicion"])
    inversiones = sitp.get("inversiones", {}).get("inversion", [])
    inversiones_val = suma_lista(inversiones, ["saldo", "montoOriginal"])
    activos_totales = bienes_val + muebles_val + inversiones_val + vehiculos_val
    adeudos = sitp.get("adeudos", {}).get("adeudo", [])
    pasivos_totales = suma_lista(adeudos, ["montoOriginal"])
    interes = declaracion.get("interes", {})
    fideicomisos = interes.get("fideicomisos", {})
    tiene_fideicomisos = int(not fideicomisos.get("ninguno", True))
    num_fideicomisos = 0
    
    if isinstance(fideicomisos.get("fideicomiso"), list):
        num_fideicomisos = len(fideicomisos["fideicomiso"])
    tiene_adeudos = int(len(adeudos) > 0)
    tiene_inversiones = int(len(inversiones) > 0)
    return {
        "id_persona": id_persona,
        "anio": anio,
        "institucion": institucion,
        "tipo_declaracion": tipo_declaracion,
        "ingreso_neto": ingreso_neto,
        "total_ingresos_anuales": total_ingresos_anuales,
        "activos_totales": activos_totales,
        "pasivos_totales": pasivos_totales,
        "tiene_fideicomisos": tiene_fideicomisos,
        "num_fideicomisos": num_fideicomisos,
        "tiene_adeudos": tiene_adeudos,
        "tiene_inversiones": tiene_inversiones,
    }

def procesar_json(path_json):
    print("Leyendo JSON:", path_json)
    with open(path_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    registros = []
    for obj in data:
        try:
            reg = extraer_campos_s1(obj)
            if reg["anio"] is not None and reg["id_persona"]:
                registros.append(reg)
        except Exception as e:
            print("  Error en registro:", e)
    df = pd.DataFrame(registros)
    print("Registros extraídos:", df.shape)
    return df

def construir_tramos(df_panel):
    df = df_panel.sort_values(["id_persona", "anio"]).copy()
    df["anio_prev"] = df.groupby("id_persona")["anio"].shift(1)
    df["patrimonio_neto"] = df["activos_totales"] - df["pasivos_totales"]
    df["patrimonio_prev"] = df.groupby("id_persona")["patrimonio_neto"].shift(1)
    df["delta_patrimonio"] = df["patrimonio_neto"] - df["patrimonio_prev"]
    df["ingresos_prev"] = df.groupby("id_persona")["total_ingresos_anuales"].shift(1)
    df["ingresos_acumulados"] = df["total_ingresos_anuales"] + df["ingresos_prev"].fillna(0)
    df["residuo"] = df["delta_patrimonio"] - df["ingresos_acumulados"]
    df_tramos = df.dropna(subset=["anio_prev"]).copy()
    print("Tramos construidos:", df_tramos.shape)
    return df_tramos

FEATURES = [
    "delta_patrimonio",
    "ingresos_acumulados",
    "residuo",
    "patrimonio_neto",
    "patrimonio_prev",
    "pasivos_totales",
    "tiene_fideicomisos",
    "num_fideicomisos",
    "tiene_adeudos",
    "tiene_inversiones"
]

def pipeline_json_a_anomalias(json_path, model_path, salida_tramos_json, salida_personas_json=None):
    df_panel = procesar_json(json_path)
    
    if df_panel.empty:
        print("Panel vacío; no se pudo extraer información.")
        return None
    df_tramos = construir_tramos(df_panel)
    
    if df_tramos.empty:
        print("No hay tramos (solo una declaración por persona).")
        return None
    iso = load(model_path)
    X = df_tramos[FEATURES].fillna(0)
    df_tramos["anomalia_score"] = iso.decision_function(X) #que tan anómalo es el registro 
    pred = iso.predict(X)
    df_tramos["es_anomalo"] = pred
    df_tramos.to_json(salida_tramos_json, orient="records", force_ascii=False, indent=2)
    print("Tramos (con es_anomalo) guardados en:", salida_tramos_json)

    if salida_personas_json is not None:
        df_anom = df_tramos[df_tramos["es_anomalo"] == -1].copy()
        if df_anom.empty:
            print("No hay tramos anómalos; no se genera resumen por persona.")
        else:
            resumen_personas = (
                df_anom
                .groupby("id_persona")
                .agg({
                    "institucion": lambda x: sorted(set(x)),
                    "anio_prev": "min",
                    "anio": "max",
                    "es_anomalo": "count",
                    "anomalia_score": "mean",
                    "delta_patrimonio": "sum",
                    "ingresos_acumulados": "sum"
                })
                .reset_index()
                .rename(columns={
                    "es_anomalo": "num_tramos_anomalos",
                    "anio_prev": "primer_anio_observado",
                    "anio": "ultimo_anio_observado",
                    "anomalia_score": "score_promedio"
                })
            )
            resumen_personas.to_json(salida_personas_json, orient="records", force_ascii=False, indent=2)
            print("Resumen de servidores anómalos guardado en:", salida_personas_json)

    return df_tramos
