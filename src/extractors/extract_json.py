"""
Extractor de texto para los 954 documentos tipo JSON del corpus CODEFEST.

CONTEXTO IMPORTANTE (descubierto explorando archivos reales):
Los archivos JSON del corpus NO tienen una unica estructura. Se dividen
en tres formas distintas segun el tipo de contenido en la raiz del archivo:

1. DICCIONARIO (la mayoria, articulos de noticias/blogs de observatorios)
    Campos comunes: url, title, body_paragraphs, y a veces body_text,
    date, authors, excerpt, tags/topics.
    OJO: no todos tienen los mismos campos. Ejemplo real:
        - ATLCOUNCIL: tiene body_text Y body_paragraphs
        - ALERTAS (defensoria): NO tiene body_text, solo body_paragraphs,
        y tiene un campo extra "alerta_meta" con info geografica valiosa
        - CSIS (algunos articulos viejos): body_text casi vacio, el
        contenido real esta en un PDF externo referenciado en pdf_links

2. LISTA con contenido tematico real (catalogos de estudios/informes)
    Ejemplo: DAIO_catalog-2.json, MAPPOEA_mapp-catalog.json,
    RUTAN_catalog-2.json, CSIS_catalog-2.json, RESDAL_catalog-2.json
    Cada elemento de la lista es como una "fila de tabla": tiene campos
    tematicos (title/titulo/nombre, year/anio, country, authors, idioma)
    Y un campo de estado de descarga que varia por observatorio:
        - DAIO, MAPPOEA, RESDAL: status como NUMERO (200 = exito, 404/503 = fallo)
        - RUTAN, CSIS: status como TEXTO "ok" (no hay ejemplo de fallo visto)
    Se debe generar un chunk por elemento, PERO SOLO si el status indica
    que el archivo referenciado se descargo con exito. Si no, ese elemento
    no representa contenido real disponible.

3. LISTA que es solo metadata de scraper (SIN contenido tematico)
    Ejemplo: AMAZONUW_tiles-index.json (indice de cache de teselas de mapa,
    campos: tile, zoom, x, y, status, size_bytes - nada de texto legible)
    Ejemplo: DEFENSA21_catalog-2.json (registro de feeds RSS, todos con
    status "error" y 0 entries)
    Estos NO producen chunks. El contenido real de estos observatorios
    (si existe) vive en otro tipo de archivo (ej: los .pbf de Amazon
    Underworld se procesan aparte, en extract_pbf.py)

4. LISTA VACIA []
    Ejemplo: DEFENSA21_articulos-2.json
    0 chunks.
"""
import json
from src.common.schema import Fragmento
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

#Funciones auxiliares para normalizar y comparar textos, para evitar duplicados.
def _texto_normalizado(t: str) -> str:
    return " ".join(t.split()).strip().lower()

def _son_redundantes(texto_a: str, texto_b: str, umbral: float = 0.8) -> bool:
    palabras_a = set(_texto_normalizado(texto_a).split())
    palabras_b = set(_texto_normalizado(texto_b).split())
    if not palabras_a or not palabras_b:
        return False
    interseccion = palabras_a & palabras_b
    mas_corto = min(len(palabras_a), len(palabras_b))
    return (len(interseccion) / mas_corto) >= umbral

def _a_lista(valor):
    if valor is None:
        return []
    if isinstance(valor, list):
        return [str(v).strip() for v in valor if str(v).strip()]
    return [str(valor).strip()] if str(valor).strip() else []

# Cargar el registro ya guardado
registros = {}
contador_lista = 0
campos_tematicos = {"title", "titulo", "nombre", "edition", "study_id"}
campos_metadata = {"feed", "entries", "tile", "zoom", "content_type", "from_cache"}
status_exito = {200, "ok"}
body_text_minimo = 50

with open("data/processed/doc_registry.jsonl", "r", encoding="utf-8") as f:
    for linea in f:
        dato = json.loads(linea)
        registros[dato["doc_id"]] = dato

for doc_id, datos in registros.items():
    if datos["tipo_archivo"] != "json":
        continue
    
    try:
        with open(datos["ruta_final"], "r", encoding="utf-8") as archivo_abierto:
            contenido = json.load(archivo_abierto)

        if isinstance(contenido, dict):
            url = contenido.get("url")
            fecha_publicacion = contenido.get("date")
            autores = contenido.get("authors")
            tags = contenido.get("tags") or contenido.get("topics")

            body_text = contenido.get("body_text", "")
            body_paragraphs = "\n".join(contenido.get("body_paragraphs")) if contenido.get("body_paragraphs") else ""
            
            tiene_body_text = bool(body_text) and len(body_text.strip()) >= body_text_minimo
            tiene_parrafos = bool(body_paragraphs) and len(body_paragraphs.strip()) >= body_text_minimo

            if tiene_body_text and tiene_parrafos:
                if _son_redundantes(body_text, body_paragraphs):
                    texto_extraido = [body_paragraphs]
                else:
                    texto_extraido = [body_paragraphs, body_text]
            elif tiene_parrafos:
                texto_extraido = [body_paragraphs]
            elif tiene_body_text:
                texto_extraido = [body_text]
            elif body_text:
                texto_extraido = [body_text]

            elif "abstract" in contenido:
                texto_extraido = [contenido["abstract"]]
            elif "sections" in contenido and len(contenido["sections"]) > 0:
                secciones = contenido["sections"]
                texto_extraido = ["\n".join("\n".join(s.get("paragraphs", [])) for s in secciones)]
            elif "content" in contenido and "sections" in contenido["content"]:
                texto_extraido = ["\n".join(contenido["content"]["sections"].values())]
            else:
                texto_extraido = []

        elif isinstance(contenido, list):
            if len(contenido) == 0:
                texto_extraido = []

            elif contenido[0].keys()&campos_tematicos:
                texto_extraido = []
                campos_a_excluir = {"url", "size_bytes", "path", "scraped_at", "status"}

                for elemento in contenido:
                    status = elemento.get("status")
                    if status not in status_exito:
                        continue

                    partes_texto = []
                    for campo, valor in elemento.items():
                        if campo in campos_a_excluir:
                            continue
                        partes_texto.append(f"{campo}: {valor}")

                    texto_elemento = ". ".join(partes_texto)
                    texto_extraido.append(texto_elemento)

            elif contenido[0].keys()&campos_metadata:
                texto_extraido = []
        for indice, texto in enumerate(texto_extraido):
            if len(texto)>30: 
                try:
                    idioma = detect(texto)
                    if idioma not in ("es", "en", "pt"):
                        idioma = "es"
                except LangDetectException:
                    idioma = "es"

                fragmento = Fragmento(
                    doc_id=doc_id,
                    chunk_id=f"{doc_id}_chunk_{indice}",
                    fuente=datos["nombre_archivo"],
                    formato="json",
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
                with open("data/processed/fragments.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps(fragmento.__dict__, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"Error al abrir {doc_id}: {e}")