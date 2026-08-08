import json
import logging
import mapbox_vector_tile
from src.common.schema import Fragmento
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

logging.getLogger("mapbox_vector_tile").setLevel(logging.ERROR)

# Prefijo ISO de pais
PAIS_A_IDIOMA = {
    "BR": "pt",
    "PE": "es", "BO": "es", "CO": "es", "EC": "es", "VE": "es",
    "PA": "es", "CR": "es", "HN": "es", "GT": "es", "MX": "es",
    "SR": "pt",
    "GY": "en",
}

def idioma_por_codigo_pais(propiedades: dict) -> str | None:
    codigo = propiedades.get("b_ADM1_PCODE") or propiedades.get("b_ADM2_PCODE") or ""
    prefijo = str(codigo)[:2].upper()
    return PAIS_A_IDIOMA.get(prefijo)

def normalizar_nombre_campo(campo: str) -> str:
    return campo.strip().replace(". ", "_").replace(" ", "_").rstrip(".")

def informacion_a_texto(info: dict) -> str:
    secciones = [
        f"{normalizar_nombre_campo(clave)}: {valor}"
        for clave, valor in info.items()
        if valor not in (None, "")
    ]
    return ", ".join(secciones)

def clave_de_duplicacion(nombre_capa: str, propiedades: dict) -> str:
    id_estable = propiedades.get("au_ID_concatenated") or propiedades.get("b_ID_concatenated")
    if id_estable:
        return f"{nombre_capa}::{id_estable}"
    items_ordenados = tuple(sorted(propiedades.items()))
    return f"{nombre_capa}::{items_ordenados}"

registros = {}
with open("data/processed/doc_registry.jsonl", "r", encoding="utf-8") as f:
    for linea in f:
        dato = json.loads(linea)
        registros[dato["doc_id"]] = dato

total_pbfs = 0
errores = 0
elementos_duplicados_omitidos = 0
elementos_sin_contenido_analitico = 0
idioma_por_pais_usado = 0
idioma_por_langdetect_usado = 0
vistos_globalmente = set()

for doc_id, datos in registros.items():
    if datos["tipo_archivo"] != "pbf":
        continue

    total_pbfs += 1

    try:
        with open(datos["ruta_final"], "rb") as f_pbf:
            data = f_pbf.read()

        tile = mapbox_vector_tile.decode(data)

        indice = 0
        for nombre_capa, capa in tile.items():
            for feature in capa.get("features", []):
                propiedades = feature.get("properties", {})
                if not propiedades:
                    continue

                if "au_country" not in propiedades:
                    elementos_sin_contenido_analitico += 1
                    continue

                clave = clave_de_duplicacion(nombre_capa, propiedades)
                if clave in vistos_globalmente:
                    elementos_duplicados_omitidos += 1
                    continue
                vistos_globalmente.add(clave)

                texto = informacion_a_texto(propiedades)

                if len(texto.strip()) <= 30:
                    continue

                idioma = idioma_por_codigo_pais(propiedades)
                if idioma:
                    idioma_por_pais_usado += 1
                else:
                    #Fallback a langdetect si no se puede determinar por codigo de pais
                    try:
                        idioma_detectado = detect(texto)
                        idioma = idioma_detectado if idioma_detectado in ("es", "en", "pt") else "es"
                    except LangDetectException:
                        idioma = "es"
                    idioma_por_langdetect_usado += 1

                fragmento = Fragmento(
                    doc_id=doc_id,
                    chunk_id=f"{doc_id}_chunk_{indice}",
                    fuente=datos["nombre_archivo"],
                    formato="pbf",
                    fenomeno=datos["fenomeno"],
                    posicion=indice,
                    num_tokens=len(texto.split()),
                    texto=texto,
                    idioma=idioma,
                    url=None,
                    fecha_publicacion=None,
                    autores=None,
                    tags=[nombre_capa],
                )

                with open("data/processed/fragments.jsonl", "a", encoding="utf-8") as f_out:
                    f_out.write(json.dumps(fragmento.__dict__, ensure_ascii=False) + "\n")

                indice += 1

    except Exception as e:
        errores += 1
        print(f"\n{datos['nombre_archivo']}")
        print(f"   {e}")

print(f"\nFinalizado.")
print(f"Total de PBF analizados: {total_pbfs}")
print(f"PBF leídos con éxito: {total_pbfs - errores}")
print(f"PBF con error: {errores}")
print(f"Elementos duplicados omitidos: {elementos_duplicados_omitidos}")
print(f"Elementos sin contenido analítico (descartados): {elementos_sin_contenido_analitico}")
print(f"Idioma resuelto por código de país: {idioma_por_pais_usado}")
print(f"Idioma resuelto por langdetect (fallback): {idioma_por_langdetect_usado}")