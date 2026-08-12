import json
import os
import pandas as pd
from src.common.schema import Fragmento
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

RUTA_FRAGMENTS = "data/processed/fragments.jsonl"

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

total_excel = 0

for doc_id, datos in registros.items():
    if datos["tipo_archivo"] != "excel":
        continue

    total_excel += 1

    try:
        posicion = 0
        df = pd.read_excel(datos["ruta_final"])

        for _, fila in df.iterrows():

            if "title" in df.columns and "journal" in df.columns:
                texto_titulo = fila["title"]
                journal = fila["journal"]

                if isinstance(texto_titulo, pd.Series):
                    texto_titulo = texto_titulo.iloc[0]
                if isinstance(journal, pd.Series):
                    journal = journal.iloc[0]

                if pd.isna(texto_titulo):
                    continue

                journal_txt = str(journal).strip() if not pd.isna(journal) else None
                if journal_txt:
                    texto = f"title: {str(texto_titulo).strip()}, journal: {journal_txt}"
                else:
                    texto = str(texto_titulo).strip()
                autores = None

            else:
                partes = []
                for columna, valor in fila.items():
                    if isinstance(valor, pd.Series):
                        for valor_individual in valor:
                            if pd.isna(valor_individual):
                                continue
                            valor_individual = str(valor_individual).strip()
                            if valor_individual:
                                partes.append(f"{columna}: {valor_individual}")
                        continue

                    if pd.isna(valor):
                        continue
                    valor = str(valor).strip()
                    if not valor:
                        continue
                    partes.append(f"{columna}: {valor}")

                texto = ", ".join(partes)
                autores = None

            texto = str(texto).strip()
            if len(texto) <= 30:
                continue

            try:
                idioma = detect(texto)
                if idioma not in ("es", "en", "pt"):
                    idioma = "en"
            except LangDetectException:
                idioma = "en"

            chunk_id = f"{doc_id}_chunk_{posicion}"

            fragmento = Fragmento(
                doc_id=doc_id,
                chunk_id=chunk_id,
                fuente=datos["nombre_archivo"],
                formato="xlsx",
                fenomeno=datos["fenomeno"],
                posicion=posicion,
                num_tokens=len(texto.split()),
                texto=texto,
                idioma=idioma,
                url=None,
                fecha_publicacion=None,
                autores=autores,
                tags=None,
            )

            # Reemplaza si ya existia (corrida anterior), agrega si es nuevo
            fragmentos_por_chunk_id[chunk_id] = fragmento.__dict__

            posicion += 1

    except Exception as e:
        print(f"Error al abrir {doc_id}: {e}")

with open(RUTA_FRAGMENTS, "w", encoding="utf-8") as f_out:
    for chunk_id, dato in fragmentos_por_chunk_id.items():
        f_out.write(json.dumps(dato, ensure_ascii=False) + "\n")

print(f"Total de archivos Excel procesados: {total_excel}")
print(f"Total fragmentos en el archivo tras esta corrida: {len(fragmentos_por_chunk_id)}")