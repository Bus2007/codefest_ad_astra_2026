import json
import logging
import pymupdf
import unicodedata
from src.common.schema import Fragmento
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
import re

def _limpiar_texto(t: str) -> str:
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

def _detectar_lineas_repetidas(paginas_texto, umbral=0.6):
    from collections import Counter
    contador = Counter()
    for texto in paginas_texto:
        lineas_unicas = set(l.strip() for l in texto.split("\n") if l.strip())
        contador.update(lineas_unicas)
    n_paginas = len(paginas_texto)
    return {linea for linea, freq in contador.items() if freq / n_paginas >= umbral}

def verificar_autor(valor):
    if not valor or not valor.strip():
        return None
    valor_limpio = valor.strip()
    palabras = valor_limpio.split()
    if len(palabras) <= 1 and len(valor_limpio) <= 6:
        return None
    software_conocido = {"adobe", "acrobat", "microsoft", "word", "latex", "pdfmaker"}
    if any(s in valor_limpio.lower() for s in software_conocido):
        return None
    return valor_limpio

logging.getLogger("pymupdf").setLevel(logging.ERROR)
registros = {}

with open("data/processed/doc_registry.jsonl", "r", encoding="utf-8") as f:
    for linea in f:
        dato = json.loads(linea)
        registros[dato["doc_id"]] = dato

total_pdfs = 0
errores = 0
descartados_por_idioma = 0

for doc_id, datos in registros.items():
    if datos["tipo_archivo"] != "pdf":
        continue

    total_pdfs += 1

    try:
        doc = pymupdf.open(datos["ruta_final"])
        metadata_pdf = doc.metadata
        autores = verificar_autor(metadata_pdf.get("author"))
        fecha_publicacion = metadata_pdf.get("creationDate") or None
        url = None
        tags = None

        paginas_texto = [pagina.get_text() for pagina in doc]
        lineas_repetidas = _detectar_lineas_repetidas(paginas_texto)

        indice = 0
        for texto_crudo in paginas_texto:
            lineas_limpias = [
                l for l in texto_crudo.split("\n")
                if l.strip() not in lineas_repetidas
            ]
            texto = _limpiar_texto("\n".join(lineas_limpias))

            if len(texto.strip()) <= 30:
                continue

            idioma = None
            try:
                idioma = detect(texto)
            except LangDetectException:
                print(f"{doc_id} pagina {indice}: no se pudo detectar idioma")

            if idioma not in ("en", "es", "pt"):
                descartados_por_idioma += 1
                continue

            fragmento = Fragmento(
                doc_id=doc_id,
                chunk_id=f"{doc_id}_chunk_{indice}",
                fuente=datos["nombre_archivo"],
                formato="pdf",
                fenomeno=datos["fenomeno"],
                posicion=indice,
                num_tokens=len(texto.split()),
                texto=texto,
                idioma=idioma,
                url=url,
                fecha_publicacion=fecha_publicacion,
                autores=autores,
                tags=tags,
            )

            with open("data/processed/fragments.jsonl", "a", encoding="utf-8") as f_out:
                f_out.write(json.dumps(fragmento.__dict__, ensure_ascii=False) + "\n")

            indice += 1

        doc.close()

    except Exception as e:
        errores += 1
        print(f"\n{datos['nombre_archivo']}")
        print(f"   {e}")

print(f"\nFinalizado.")
print(f"Total de PDFs analizados: {total_pdfs}")
print(f"PDFs leídos con éxito: {total_pdfs - errores}")
print(f"PDFs con error: {errores}")
print(f"Páginas descartadas por idioma fuera de es/en/pt: {descartados_por_idioma}")