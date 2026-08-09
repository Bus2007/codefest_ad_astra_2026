import json
import pandas as pd
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from src.common.schema import Fragmento


def extraer_metadata_txt(lineas):
    """Saca SOURCE y SCRAPED del encabezado y devuelve dónde empieza el cuerpo real."""
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


def dividir_en_fragmentos_texto(texto, tamano_objetivo=200):
    """Divide el cuerpo del texto en bloques de ~tamano_objetivo palabras."""
    palabras = texto.split()
    return [
        " ".join(palabras[i:i + tamano_objetivo])
        for i in range(0, len(palabras), tamano_objetivo)
    ]


def detectar_idioma_texto(texto, muestra_chars=2000):
    try:
        return detect(texto[:muestra_chars])
    except LangDetectException:
        return None


def construir_fragmentos_txt(doc_id, datos):
    with open(datos["ruta_final"], "r", encoding="utf-8") as f:
        lineas = f.read().splitlines()

    url, scraped_at, inicio_cuerpo = extraer_metadata_txt(lineas)
    cuerpo = "\n".join(l for l in lineas[inicio_cuerpo:] if l.strip())

    idioma_doc = detectar_idioma_texto(cuerpo)
    if idioma_doc not in ("en", "es", "pt"):
        return [], idioma_doc

    trozos = dividir_en_fragmentos_texto(cuerpo)

    fragmentos = []
    for indice, texto in enumerate(trozos):
        fragmentos.append(Fragmento(
            doc_id=doc_id,
            chunk_id=f"{doc_id}_chunk_{indice}",
            fuente=datos["nombre_archivo"],
            formato="texto",
            fenomeno=datos["fenomeno"],
            posicion=indice,
            num_tokens=len(texto.split()),
            texto=texto,
            idioma=idioma_doc,
            url=url,
            fecha_publicacion=None,
            autores=None,
            tags=None,
        ))
    return fragmentos, idioma_doc


registros = {}
with open("data/processed/doc_registry.jsonl", "r", encoding="utf-8") as f:
    for linea in f:
        dato = json.loads(linea)
        registros[dato["doc_id"]] = dato

total_txts = 0
descartados_por_idioma = 0
errores = 0

for doc_id, datos in registros.items():
    if datos["tipo_archivo"] != "texto":
        continue

    total_txts += 1
    try:
        fragmentos, idioma_doc = construir_fragmentos_txt(doc_id, datos)

        if idioma_doc not in ("en", "es", "pt"):
            descartados_por_idioma += 1
            continue
        print(fragmentos)

        with open("data/processed/fragments.jsonl", "a", encoding="utf-8") as f_out:
            for fragmento in fragmentos:
                f_out.write(json.dumps(fragmento.__dict__, ensure_ascii=False) + "\n")
    
    except Exception as e:
        errores += 1
        print(f"{doc_id}: error - {e}")

print(f"total_txts={total_txts}, descartados_por_idioma={descartados_por_idioma}, errores={errores}")