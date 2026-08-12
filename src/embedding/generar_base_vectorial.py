import json
import os
import numpy as np
import faiss
from FlagEmbedding import BGEM3FlagModel

chunks = []

with open("data/processed/chunks.jsonl", "r", encoding="utf-8") as f:
    for linea in f:
        if linea.strip():
            chunks.append(json.loads(linea))

print(f"Chunks cargados: {len(chunks)}")

print("Cargando modelo BGE-M3 (puede tardar la primera vez)...")
modelo = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)

textos = [chunk["texto"] for chunk in chunks]

print("Generando embeddings (esto puede tardar bastante)...")

batch_size = 32
indice = None

for inicio in range(0, len(textos), batch_size):
    fin = min(inicio + batch_size, len(textos))
    textos_lote = textos[inicio:fin]

    resultado = modelo.encode(
        textos_lote,
        batch_size=batch_size,
        max_length=512,
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    )

    vectores = resultado["dense_vecs"]

    normas = np.linalg.norm(vectores, axis=1, keepdims=True)

    if not np.allclose(normas, 1.0, atol=1e-3):
        vectores = vectores / np.maximum(normas,1e-12)

    if indice is None:
        dimension = vectores.shape[1]
        indice = faiss.IndexFlatIP(dimension)

    indice.add(vectores.astype("float32"))

    print(f"Procesados {fin}/{len(textos)} chunks")

print(f"Indice FAISS construido con {indice.ntotal} vectores.")

RUTA_SALIDA = "entrega/base_vectorial/encoder_bge-m3"
os.makedirs(RUTA_SALIDA, exist_ok=True)

faiss.write_index(indice, f"{RUTA_SALIDA}/index.faiss")

print(f"Indice guardado en {RUTA_SALIDA}/index.faiss")

with open(f"{RUTA_SALIDA}/metadata.jsonl", "w", encoding="utf-8") as f:
    for chunk in chunks:
        f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

print(f"Metadata guardado en {RUTA_SALIDA}/metadata.jsonl")
print("\nProceso completo.")