import json
import nltk
from transformers import AutoTokenizer

try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab")

# Funciones Auxiliares
tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-m3")
limite_tokens = 500

diccionario_idiomas = {
    "es": "spanish",
    "en": "english",
    "pt": "portuguese",
}

def contar_tokens(texto: str):
    return len(tokenizer.encode(texto, add_special_tokens=False))

def contar_tokens_batch(textos: list[str]) -> list[int]:
    if not textos:
        return []

    tokens = tokenizer(textos, add_special_tokens=False, padding=False, truncation=False)["input_ids"]

    return [len(token) for token in tokens]

def segmentar_oraciones(texto: str, idioma: str) -> list[str]:
    idioma_chunk = diccionario_idiomas.get(idioma)

    if not texto or not texto.strip():
        return []

    try:
        if idioma_chunk:
            oraciones = nltk.sent_tokenize(texto, language=idioma_chunk)
        else:
            oraciones = nltk.sent_tokenize(texto)

    except Exception as e:
        print(
            f"Error segmentando texto en idioma '{idioma}': {e}"
        )
        return [texto.strip()]

    return [oracion.strip() for oracion in oraciones if oracion.strip()]

def almacenar_oraciones(oraciones: list[str]) -> tuple[list[tuple[str, int]], int]:
    chunks = []
    chunk_actual = []
    tokens_actuales = 0
    oraciones_sobre_limite = 0

    if not oraciones:
        return [], 0

    tokens_oraciones = contar_tokens_batch(oraciones)

    for oracion, tokens_oracion in zip(oraciones, tokens_oraciones):

        # Si una sola oración supera el límite, NO se corta.
        if tokens_oracion > limite_tokens:
            oraciones_sobre_limite += 1

            if chunk_actual:
                chunks.append((" ".join(chunk_actual), tokens_actuales))
                chunk_actual = []
                tokens_actuales = 0

            chunks.append((oracion, tokens_oracion))
            continue

        # Si la oración cabe en el chunk actual, se agrega.
        if tokens_actuales + tokens_oracion <= limite_tokens:
            chunk_actual.append(oracion)
            tokens_actuales += tokens_oracion

        # Si no cabe, se cierra el chunk y la oración
        else:
            if chunk_actual:
                chunks.append((" ".join(chunk_actual), tokens_actuales))

            chunk_actual = [oracion]
            tokens_actuales = tokens_oracion

    if chunk_actual:
        chunks.append((" ".join(chunk_actual), tokens_actuales))

    return chunks, oraciones_sobre_limite


# Cargar fragmentos extraídos
fragmentos_iniciales = []

with open("data/processed/fragments.jsonl", "r", encoding="utf-8") as f:
    for linea in f:
        if linea.strip():
            fragmentos_iniciales.append(json.loads(linea))

chunks_finales = []
fragmentos_sin_chunking = 0
fragmentos_con_chunking = 0
fragmentos_vacios = 0
oraciones_sobre_limite = 0
posicion_por_documento = {}

for i, fragmento in enumerate(fragmentos_iniciales, start=1):
    doc_id = fragmento["doc_id"]
    posicion_por_documento.setdefault(doc_id, 0)

    if i % 1000 == 0:
        print(f"Procesando fragmento {i}/{len(fragmentos_iniciales)}")

    texto = fragmento.get("texto", "")

    if not texto or not texto.strip():
        fragmentos_vacios += 1
        continue

    if fragmento["formato"] == "pbf":
        nuevo_chunk = dict(fragmento)
        posicion = posicion_por_documento[doc_id]
        nuevo_chunk["posicion"] = posicion
        nuevo_chunk["chunk_id"] = (f"{doc_id}_chunk_{posicion}")
        nuevo_chunk["num_tokens"] = contar_tokens(texto)
        chunks_finales.append(nuevo_chunk)
        posicion_por_documento[doc_id] += 1
        fragmentos_sin_chunking += 1
        continue

    oraciones = segmentar_oraciones(texto, fragmento.get("idioma", ""))

    if not oraciones:
        fragmentos_vacios += 1
        continue

    porciones, sobre_limite = almacenar_oraciones(oraciones)

    oraciones_sobre_limite += sobre_limite

    for porcion, num_tokens in porciones:
        nuevo_chunk = dict(fragmento)
        posicion = posicion_por_documento[doc_id]
        nuevo_chunk["texto"] = porcion
        nuevo_chunk["posicion"] = posicion
        nuevo_chunk["chunk_id"] = (f"{doc_id}_chunk_{posicion}")
        nuevo_chunk["num_tokens"] = num_tokens

        chunks_finales.append(nuevo_chunk)
        posicion_por_documento[doc_id] += 1

    fragmentos_con_chunking += 1

with open("data/processed/chunks.jsonl", "w", encoding="utf-8") as f_out:
    for chunk in chunks_finales:
        f_out.write(json.dumps(chunk, ensure_ascii=False) + "\n")

print(f"fragmentos procesados: {len(fragmentos_iniciales)}")
print(f"fragmentos sin chunking: {fragmentos_sin_chunking}")
print(f"fragmentos con chunking: {fragmentos_con_chunking}")
print(f"fragmentos vacios: {fragmentos_vacios}")
print(f"oraciones sobre limite: {oraciones_sobre_limite}")
print(f"total de chunks generados: {len(chunks_finales)}")