import json
import pandas as pd
from src.common.schema import Fragmento
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException


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
        indice = 0
        df = pd.read_excel(datos["ruta_final"])

        for indice, fila in df.iterrows():

            if "title" in df.columns and "journal" in df.columns:
                texto = fila["title"]
                autores = fila["journal"]

                if isinstance(texto, pd.Series):
                    texto = texto.iloc[0]

                if isinstance(autores, pd.Series):
                    autores = autores.iloc[0]

            else:
                partes = []

                for columna, valor in fila.items():

                    if isinstance(valor, pd.Series):
                        for valor_individual in valor:
                            if pd.isna(valor_individual):
                                continue

                            valor_individual = str(valor_individual).strip()

                            if valor_individual:
                                partes.append(
                                    f"{columna}: {valor_individual}"
                                )

                        continue

                    if pd.isna(valor):
                        continue

                    valor = str(valor).strip()

                    if not valor:
                        continue

                    partes.append(f"{columna}: {valor}")

                texto = ", ".join(partes)
                autores = None

            if pd.isna(texto):
                continue

            texto = str(texto).strip()

            if len(texto) <= 30:
                continue

            try:
                idioma = detect(texto)

                if idioma not in ("es", "en", "pt"):
                    idioma = "en"

            except LangDetectException:
                idioma = "en"

            fragmento = Fragmento(
                doc_id=doc_id,
                chunk_id=f"{doc_id}_chunk_{indice}",
                fuente=datos["nombre_archivo"],
                formato="xlsx",
                fenomeno=datos["fenomeno"],
                posicion=indice,
                num_tokens=len(texto.split()),
                texto=texto,
                idioma=idioma,
                url=None,
                fecha_publicacion=None,
                autores=autores,
                tags=None,
            )

            with open("data/processed/fragments.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(fragmento.__dict__, ensure_ascii=False) + "\n")

    except Exception as e:
        print(f"Error al abrir {doc_id}: {e}")


print(f"Total de archivos Excel procesados: {total_excel}")