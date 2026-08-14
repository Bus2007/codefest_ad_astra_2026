import json
import os
import re
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from src.common.schema import Fragmento

RUTA_FRAGMENTS = "data/processed/fragments.jsonl"


def extraer_metadata_txt(lineas):
    """Saca SOURCE y SCRAPED del encabezado y devuelve donde empieza el cuerpo real."""
    url = None
    scraped_at = None
    inicio_cuerpo = 0

    for i, linea in enumerate(lineas):
        if linea.startswith("SOURCE:"):
            url = linea.replace("SOURCE:", "").strip()
        elif linea.startswith("SCRAPED:"):
            scraped_at = linea.replace("SCRAPED:", "").strip()
        elif linea.startswith("=" * 10):
            inicio_cuerpo = i + 1
            break

    return url, scraped_at, inicio_cuerpo


def saltar_estructura_inicial(cuerpo: str) -> str:
    oraciones = re.split(r'(?<=[.!?])\s+', cuerpo)
    for i in range(len(oraciones) - 2):
        if all(len(oraciones[i + k]) >= 40 for k in range(3)):
            return " ".join(oraciones[i:])
    return cuerpo


def detectar_idioma_texto(texto, muestra_chars=2000):
    try:
        return detect(texto[:muestra_chars])
    except LangDetectException:
        return None


def construir_fragmento_txt(doc_id, datos):
    with open(datos["ruta_final"], "r", encoding="utf-8") as f:
        lineas = f.read().splitlines()

    url, scraped_at, inicio_cuerpo = extraer_metadata_txt(lineas)
    cuerpo = "\n".join(l for l in lineas[inicio_cuerpo:] if l.strip())
    cuerpo = saltar_estructura_inicial(cuerpo)

    if len(cuerpo.strip()) <= 30:
        return None, None

    idioma_doc = detectar_idioma_texto(cuerpo)
    if idioma_doc not in ("en", "es", "pt"):
        return None, idioma_doc

    # Un solo fragmento de extraccion por documento (igual que JSON con
    # body_text, o PDF con una pagina) - la segmentacion por oraciones
    # final la hace chunker.py, no este extractor.
    fragmento = Fragmento(
        doc_id=doc_id,
        chunk_id=f"{doc_id}_chunk_0",
        fuente=datos["nombre_archivo"],
        formato="texto",
        fenomeno=datos["fenomeno"],
        posicion=0,
        num_tokens=len(cuerpo.split()),
        texto=cuerpo,
        idioma=idioma_doc,
        url=url,
        fecha_publicacion=None,
        autores=None,
        tags=None,
    )
    return fragmento, idioma_doc

fragmentos_por_chunk_id = {}
if os.path.exists(RUTA_FRAGMENTS):
    with open(RUTA_FRAGMENTS, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            dato = json.loads(linea)
            fragmentos_por_chunk_id[dato["chunk_id"]] = dato

registros = {}
with open("data/processed/doc_registry.jsonl", "r", encoding="utf-8") as f:
    for linea in f:
        dato = json.loads(linea)
        registros[dato["doc_id"]] = dato

total_txts = 0
descartados_por_idioma = 0
descartados_por_longitud = 0
errores = 0

for doc_id, datos in registros.items():
    if datos["tipo_archivo"] != "texto":
        continue

    total_txts += 1
    try:
        fragmento, idioma_doc = construir_fragmento_txt(doc_id, datos)

        if fragmento is None:
            if idioma_doc is None or idioma_doc not in ("en", "es", "pt"):
                descartados_por_idioma += 1
            else:
                descartados_por_longitud += 1
            continue

        fragmentos_por_chunk_id[fragmento.chunk_id] = fragmento.__dict__

    except Exception as e:
        errores += 1
        print(f"{doc_id}: error - {e}")

with open(RUTA_FRAGMENTS, "w", encoding="utf-8") as f_out:
    for chunk_id, dato in fragmentos_por_chunk_id.items():
        f_out.write(json.dumps(dato, ensure_ascii=False) + "\n")

print(f"total_txts={total_txts}, descartados_por_idioma={descartados_por_idioma}, "f"descartados_por_longitud={descartados_por_longitud}, errores={errores}")
print(f"total fragmentos en el archivo tras esta corrida: {len(fragmentos_por_chunk_id)}")