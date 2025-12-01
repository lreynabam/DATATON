from flask import Flask, render_template, request, jsonify, send_file
import os
from joblib import load
from logicaModelo import pipeline_json_a_anomalias

# =============== RUTAS BASE ===============
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # carpeta DATATON
MODELO_PATH = os.path.join(BASE_DIR, "models", "iso_patrimonial.joblib")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("DEBUG BASE_DIR:", BASE_DIR)
print("DEBUG OUTPUT_DIR:", OUTPUT_DIR)

app = Flask(__name__)


# =============== PÁGINA PRINCIPAL ===============
@app.route("/")
def index():
    return render_template("index.html")


# =============== DESCARGA DEL JSON ===============
@app.route("/descargar/servidores_anomalos")
def descargar_servidores_anomalos():
    filename = "servidores_anomalos.json"
    full_path = os.path.join(OUTPUT_DIR, filename)

    print("\n[DESCARGAR] Intentando enviar archivo...")
    print("[DESCARGAR] Ruta completa esperada:", full_path)
    print("[DESCARGAR] Archivos en OUTPUT_DIR:", os.listdir(OUTPUT_DIR))

    if not os.path.exists(full_path):
        print("[DESCARGAR] ❌ Archivo NO existe en esa ruta")
        # Aquí devolvemos un texto claro, para que lo veas también en el navegador
        return (
            f"No se encontró el archivo '{filename}' en: {full_path}. "
            "Verifica que ya se ejecutó el análisis y que el nombre coincide.",
            404,
        )

    print("[DESCARGAR] ✅ Archivo encontrado, enviando al cliente...")
    return send_file(
        full_path,
        as_attachment=True,
        download_name=filename,
        mimetype="application/json"
    )


# =============== API: DETECTAR ANOMALÍAS ===============
@app.route("/api/detectar-anomalias-archivo", methods=["POST"])
def detectar_anomalias_archivo():
    if "json_file" not in request.files:
        return jsonify({"error": "No se envió 'json_file'"}), 400

    file = request.files["json_file"]
    if file.filename == "":
        return jsonify({"error": "Archivo vacío"}), 400

    temp_path = os.path.join(OUTPUT_DIR, file.filename)
    file.save(temp_path)
    print("\n[ANALIZAR] Archivo recibido y guardado en:", temp_path)

    salida_tramos_json = os.path.join(OUTPUT_DIR, "anomalias_tramos.json")
    salida_personas_json = os.path.join(OUTPUT_DIR, "servidores_anomalos.json")
    print("[ANALIZAR] Salida tramos:", salida_tramos_json)
    print("[ANALIZAR] Salida personas:", salida_personas_json)

    df_tramos = pipeline_json_a_anomalias(
        json_path=temp_path,
        model_path=MODELO_PATH,
        salida_tramos_json=salida_tramos_json,
        salida_personas_json=salida_personas_json,
    )

    if df_tramos is None or df_tramos.empty:
        print("[ANALIZAR] ⚠ No se generaron tramos.")
        return jsonify({"mensaje": "No se generaron tramos"}), 200

    df_anom = df_tramos[df_tramos["es_anomalo"] == -1].copy()
    data = df_anom.to_dict(orient="records")

    print("[ANALIZAR] ✅ Total tramos:", len(df_tramos))
    print("[ANALIZAR] ✅ Tramos anómalos:", len(df_anom))
    print("[ANALIZAR] Archivos en OUTPUT_DIR tras análisis:", os.listdir(OUTPUT_DIR))

    return jsonify({
        "num_tramos": int(len(df_tramos)),
        "num_anomalos": int(len(df_anom)),
        "tramos_anomalos": data
    }), 200


if __name__ == "__main__":
    app.run(debug=True)
