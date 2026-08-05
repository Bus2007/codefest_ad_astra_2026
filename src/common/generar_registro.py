import pandas as pd
import os
import json

df = pd.read_excel("config/Indice_Datos_Codefest.xlsx", sheet_name="Inventario de Archivos")
registros = {}
duplicados = []
ruta_raw = "data/raw"

for _, fila in df.iterrows():
    doc_id = str(fila["DOC_ID"]).strip()

    if doc_id in registros:
        duplicados.append(doc_id)

    nombre_archivo = str(fila["Nombre estandarizado"]).strip()
    tipo_excel = str(fila["Tipo"]).strip().lower()

    if tipo_excel in ("otro", "otros", "nan", ""):
        extension = os.path.splitext(nombre_archivo)[1].lstrip(".").lower()
        tipo_archivo = extension if extension else tipo_excel
    else:
        tipo_archivo = tipo_excel

    registros[doc_id] = {
        "fenomeno": int(str(fila["Fenómeno"]).strip().replace("F", "")),
        "observatorio": str(fila["Observatorio"]).strip(),
        "codigo_observatorio": str(fila["Código Observatorio"]).strip(),
        "nombre_archivo": nombre_archivo,
        "carpeta": str(fila["Carpeta"]).strip(),
        "tipo_archivo": tipo_archivo,
    }

    ruta_simple = os.path.join(registros[doc_id]["carpeta"], registros[doc_id]["nombre_archivo"])
    ruta_final = os.path.join(ruta_raw, ruta_simple)
    registros[doc_id]["ruta_final"] = ruta_final.replace("\\", "/")
    registros[doc_id]["existe"] = os.path.exists(ruta_final)

    if not registros[doc_id]["existe"]:
        print(f"No se encuentra: {doc_id} -> {ruta_final}")

conteo_por_tipo_archivo = {}
for doc_id, datos in registros.items():
    tipo = datos["tipo_archivo"]
    conteo_por_tipo_archivo[tipo] = conteo_por_tipo_archivo.get(tipo, 0) + 1

print(conteo_por_tipo_archivo)

with open("data/processed/doc_registry.jsonl", "w", encoding="utf-8") as f:
    for doc_id, datos in registros.items():
        fila = {"doc_id": doc_id, **datos}
        f.write(json.dumps(fila, ensure_ascii=False) + "\n")