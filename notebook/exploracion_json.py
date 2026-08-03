import json
from collections import Counter

# 1. Cargar el registro ya guardado
registros = {}
with open("data/processed/doc_registry.jsonl", "r", encoding="utf-8") as f:
    for linea in f:
        dato = json.loads(linea)
        registros[dato["doc_id"]] = dato

# 2. Recorrer solo los json, contando claves y detectando casos distintos
contador_claves = Counter()
archivos_con_error = []
archivos_lista = []

for doc_id, datos in registros.items():
    if datos["tipo_archivo"] != "json":
        continue

    try:
        with open(datos["ruta_final"], "r", encoding="utf-8") as archivo_abierto:
            contenido = json.load(archivo_abierto)
    except Exception as e:
        archivos_con_error.append((doc_id, str(e)))
        continue

    if isinstance(contenido, list):
        archivos_lista.append((doc_id, datos["ruta_final"]))
        continue

    if not isinstance(contenido, dict):
        # por si acaso viene algo aún más raro (numero, string suelto, etc)
        archivos_lista.append((doc_id, datos["ruta_final"]))
        continue

    contador_claves.update(contenido.keys())

# 3. Reporte
total_json = len([d for d in registros.values() if d["tipo_archivo"] == "json"])
print("Total JSON:", total_json)
print("Errores al abrir:", len(archivos_con_error))
print("Archivos que NO son un objeto {} (son lista u otro tipo):", len(archivos_lista))
print()

if archivos_lista:
    print("--- Archivos con estructura distinta ---")
    for doc_id, ruta in archivos_lista:
        print(f"{doc_id} -> {ruta}")
    print()

print("--- Conteo de claves (solo entre los que SÍ son objeto) ---")
for clave, cantidad in contador_claves.most_common():
    print(f"{clave}: {cantidad}")
