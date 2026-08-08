import json
import os
import re
import unicodedata
from PIL import Image
import pytesseract
from src.common.schema import Fragmento
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

TEXTO_MINIMO_INFORMATIVO = 40
RUTA_FRAGMENTS = "data/processed/fragments.jsonl"

def limpiar_ocr(texto: str) -> str:
    texto = unicodedata.normalize("NFKC", texto)
    lineas_utiles = []
    for linea in texto.split("\n"):
        letras = re.findall(r"[A-Za-zÀ-ÿ]", linea)
        if len(letras) >= 3 or linea.strip() == "":
            lineas_utiles.append(linea)
    texto = "\n".join(lineas_utiles)
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()

def es_informativa(texto_limpio: str) -> bool:
    palabras_reales = re.findall(r"[A-Za-zÀ-ÿ]{3,}", texto_limpio)
    return len(texto_limpio) >= TEXTO_MINIMO_INFORMATIVO and len(palabras_reales) >= 5

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

total_imgs = 0
informativas = 0
descartadas_decorativas = 0
errores = 0

for doc_id, datos in registros.items():
    if datos["tipo_archivo"] != "imagen":
        continue

    total_imgs += 1

    try:
        imagen = Image.open(datos["ruta_final"])
        texto_ocr = pytesseract.image_to_string(imagen, lang="spa+eng+por")
        texto = limpiar_ocr(texto_ocr)

        if not es_informativa(texto):
            descartadas_decorativas += 1
            print(f"[Descartada, decorativa] {datos['nombre_archivo']}")
            continue

        informativas += 1

        idioma = None
        try:
            idioma_detectado = detect(texto)
            idioma = idioma_detectado if idioma_detectado in ("es", "en", "pt") else "en"
        except LangDetectException:
            idioma = "en"

        chunk_id = f"{doc_id}_chunk_0"

        fragmento = Fragmento(
            doc_id=doc_id,
            chunk_id=chunk_id,
            fuente=datos["nombre_archivo"],
            formato="imagen",
            fenomeno=datos["fenomeno"],
            posicion=0,
            num_tokens=len(texto.split()),
            texto=texto,
            idioma=idioma,
            url=None,
            fecha_publicacion=None,
            autores=None,
            tags=["ocr"],
        )

        fragmentos_por_chunk_id[chunk_id] = fragmento.__dict__

        print(f"[Informativa] {datos['nombre_archivo']}")

    except Exception as e:
        errores += 1
        print(f"Error con {datos['nombre_archivo']}: {e}")

with open(RUTA_FRAGMENTS, "w", encoding="utf-8") as f_out:
    for chunk_id, dato in fragmentos_por_chunk_id.items():
        f_out.write(json.dumps(dato, ensure_ascii=False) + "\n")

print(f"\nTotal imagenes: {total_imgs}")
print(f"Informativas (con OCR aplicado): {informativas}")
print(f"Descartadas por decorativas: {descartadas_decorativas}")
print(f"Errores: {errores}")
print(f"Total fragmentos en el archivo tras esta corrida: {len(fragmentos_por_chunk_id)}")