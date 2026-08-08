import json
import pandas as pd
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from src.common.schema import Fragmento

def detectar_idioma_documento(df, columnas_texto, muestra=20):
    """Detecta el idioma concatenando varias filas como muestra."""
    textos_muestra = []
    for _, row in df.head(muestra).iterrows():
        texto_fila = ", ".join(
            f"{col}: {row[col]}" for col in columnas_texto if pd.notna(row[col])
        )
        textos_muestra.append(texto_fila)
    
    texto_concatenado = " ".join(textos_muestra)
    
    try:
        return detect(texto_concatenado)
    except LangDetectException:
        print(f"{doc_id}: no se pudo detectar idioma")


def construir_fragmento_publicaciones(row, columnas, doc_id, indice, datos, idioma_doc):
    texto = ", ".join(f"{col}: {row[col]}" for col in columnas if pd.notna(row[col]))

    return Fragmento(
        doc_id=doc_id,
        chunk_id=f"{doc_id}_chunk_{indice}",
        fuente=datos["nombre_archivo"],
        formato="csv",
        fenomeno=datos["fenomeno"],
        posicion=indice,
        num_tokens=len(texto.split()),
        texto=texto,
        idioma=idioma_doc,
        url=row["url"] if pd.notna(row["url"]) else None,
        fecha_publicacion=row["fecha"] if pd.notna(row["fecha"]) else None,
        autores=None,  # ninguna de las dos fuentes trae columna de autor
        tags=row["fenomeno"] if pd.notna(row["fenomeno"]) else None,
    )


def construir_fragmento_aiindex_clinicaltrials(row, columnas, doc_id, indice, datos, idioma_doc):

    texto = ", ".join(f"{col}: {row[col]}" for col in columnas if pd.notna(row[col]))

    return Fragmento(
        doc_id=doc_id,
        chunk_id=f"{doc_id}_chunk_{indice}",
        fuente=datos["nombre_archivo"],
        formato="csv",
        fenomeno=datos["fenomeno"],
        posicion=indice,
        num_tokens=len(texto.split()),
        texto=texto,
        idioma=idioma_doc,
        url=row["URL"] if pd.notna(row["URL"]) else None,
        fecha_publicacion=row["Start Date"] if pd.notna(row["Start Date"]) else None,
        autores=row["Sponsor/Collaborators"] if pd.notna(row["Sponsor/Collaborators"]) else None,
        tags=row["Conditions"] if pd.notna(row["Conditions"]) else None,
    )


def construir_fragmento_aiindex_pubmed_detalle(row, columnas, doc_id, indice, datos, idioma_doc):
    # descarta la columna índice residual ("Unnamed: 0") presente en algunos archivos
    columnas_validas = [c for c in columnas if not c.startswith("Unnamed")]

    texto = ", ".join(f"{col}: {row[col]}" for col in columnas_validas if pd.notna(row[col]))

    url = f"https://pubmed.ncbi.nlm.nih.gov/{int(row['PMID'])}/" if pd.notna(row["PMID"]) else None

    return Fragmento(
        doc_id=doc_id,
        chunk_id=f"{doc_id}_chunk_{indice}",
        fuente=datos["nombre_archivo"],
        formato="csv",
        fenomeno=datos["fenomeno"],
        posicion=indice,
        num_tokens=len(texto.split()),
        texto=texto,
        idioma=idioma_doc,
        url=url,
        fecha_publicacion=row["Publication Year"] if pd.notna(row["Publication Year"]) else None,
        autores=row["Authors"] if pd.notna(row["Authors"]) else None,
        tags=row["Journal/Book"] if pd.notna(row["Journal/Book"]) else None,
    )


def construir_fragmento_aiindex_pubmed_timeline(row, columnas, doc_id, indice, datos, idioma_doc):
    texto = ", ".join(f"{col}: {row[col]}" for col in columnas if pd.notna(row[col]))

    return Fragmento(
        doc_id=doc_id,
        chunk_id=f"{doc_id}_chunk_{indice}",
        fuente=datos["nombre_archivo"],
        formato="csv",
        fenomeno=datos["fenomeno"],
        posicion=indice,
        num_tokens=len(texto.split()),
        texto=texto,
        idioma=idioma_doc,
        url=None,
        fecha_publicacion=row["Year"] if pd.notna(row["Year"]) else None,
        autores=None,
        tags=None,
    )


def construir_fragmento_daio(row, columnas, doc_id, indice, datos, idioma_doc):
    texto = ", ".join(f"{col}: {row[col]}" for col in columnas if pd.notna(row[col]))
    return Fragmento(
        doc_id=doc_id, chunk_id=f"{doc_id}_chunk_{indice}",
        fuente=datos["nombre_archivo"], formato="csv", fenomeno=datos["fenomeno"],
        posicion=indice, num_tokens=len(texto.split()), texto=texto, idioma=idioma_doc,
        url=row["url_pdf"] if pd.notna(row["url_pdf"]) else (row["url_page"] if pd.notna(row["url_page"]) else None),
        fecha_publicacion=row["year"] if pd.notna(row["year"]) else None,
        autores=row["authors"] if pd.notna(row["authors"]) else None,
        tags=row["country"] if pd.notna(row["country"]) else None,
    )


def construir_fragmento_rutan(row, columnas, doc_id, indice, datos, idioma_doc):
    texto = ", ".join(f"{col}: {row[col]}" for col in columnas if pd.notna(row[col]))
    return Fragmento(
        doc_id=doc_id, chunk_id=f"{doc_id}_chunk_{indice}",
        fuente=datos["nombre_archivo"], formato="csv", fenomeno=datos["fenomeno"],
        posicion=indice, num_tokens=len(texto.split()), texto=texto, idioma=idioma_doc,
        url=row["url"] if pd.notna(row["url"]) else None,
        fecha_publicacion=None,  # no trae fecha de publicación, solo "scraped_at" (fecha de scraping)
        autores=None,
        tags=row["fenomeno"] if pd.notna(row["fenomeno"]) else None,
    )


def construir_fragmento_csis(row, columnas, doc_id, indice, datos, idioma_doc):
    texto = ", ".join(f"{col}: {row[col]}" for col in columnas if pd.notna(row[col]))
    return Fragmento(
        doc_id=doc_id, chunk_id=f"{doc_id}_chunk_{indice}",
        fuente=datos["nombre_archivo"], formato="csv", fenomeno=datos["fenomeno"],
        posicion=indice, num_tokens=len(texto.split()), texto=texto, idioma=idioma_doc,
        url=row["pdf_url"] if pd.notna(row["pdf_url"]) else (row["page_url"] if pd.notna(row["page_url"]) else None),
        fecha_publicacion=row["año"] if pd.notna(row["año"]) else None,
        autores=None,
        tags=row["fenomeno"] if pd.notna(row["fenomeno"]) else None,
    )


def construir_fragmento_mappoea(row, columnas, doc_id, indice, datos, idioma_doc):
    texto = ", ".join(f"{col}: {row[col]}" for col in columnas if pd.notna(row[col]))
    return Fragmento(
        doc_id=doc_id, chunk_id=f"{doc_id}_chunk_{indice}",
        fuente=datos["nombre_archivo"], formato="csv", fenomeno=datos["fenomeno"],
        posicion=indice, num_tokens=len(texto.split()), texto=texto, idioma=idioma_doc,
        url=row["url"] if pd.notna(row["url"]) else None,
        fecha_publicacion=row["year"] if pd.notna(row["year"]) else None,
        autores=None,
        tags=None,  # la columna "idioma" del CSV es el idioma del PDF (ENG/ESP), no un tema/tag
    )


def construir_fragmento_resdal(row, columnas, doc_id, indice, datos, idioma_doc):
    texto = ", ".join(f"{col}: {row[col]}" for col in columnas if pd.notna(row[col]))
    return Fragmento(
        doc_id=doc_id, chunk_id=f"{doc_id}_chunk_{indice}",
        fuente=datos["nombre_archivo"], formato="csv", fenomeno=datos["fenomeno"],
        posicion=indice, num_tokens=len(texto.split()), texto=texto, idioma=idioma_doc,
        url=row["url"] if pd.notna(row["url"]) else None,
        fecha_publicacion=row["year"] if pd.notna(row["year"]) else None,
        autores=None,
        tags=row["category"] if pd.notna(row["category"]) else None,
    )
registros = {}

with open("data/processed/doc_registry.jsonl", "r", encoding="utf-8") as f:
    for linea in f:
        dato = json.loads(linea)
        registros[dato["doc_id"]] = dato

total_csvs = 0
descartados_por_idioma = 0
errores=0

for doc_id, datos in registros.items():
    if datos["tipo_archivo"] != "csv":
        continue
    
    total_csvs += 1
    
    contenido = pd.read_csv(datos["ruta_final"],encoding="utf-8",on_bad_lines="skip",sep=None,engine="python",)
    idioma_doc = detectar_idioma_documento(contenido, contenido.columns) 

    if idioma_doc not in ("en", "es", "pt"):
        descartados_por_idioma += 1
        continue

    codigo = datos["codigo_observatorio"]
    nombre_archivo = datos["nombre_archivo"]


    if codigo == "AIINDEX" and "timeline" in nombre_archivo:
        construir_fragmento = construir_fragmento_aiindex_pubmed_timeline
    elif codigo == "AIINDEX" and "pubmed" in nombre_archivo:
        construir_fragmento = construir_fragmento_aiindex_pubmed_detalle
    elif codigo == "AIINDEX" and "clinicaltrials" in nombre_archivo:
        construir_fragmento = construir_fragmento_aiindex_clinicaltrials
    elif "publicaciones" in nombre_archivo:
        construir_fragmento = construir_fragmento_publicaciones
    elif codigo == "DAIO":
        construir_fragmento = construir_fragmento_daio
    elif codigo == "RUTAN":
        construir_fragmento = construir_fragmento_rutan
    elif codigo == "CSIS":
        construir_fragmento = construir_fragmento_csis
    elif codigo == "MAPPOEA":
        construir_fragmento = construir_fragmento_mappoea
    elif codigo == "RESDAL":
        construir_fragmento = construir_fragmento_resdal
    else:
        print(f"{doc_id}: sin constructor definido todavía, se omite")
        continue


    try:
        print("documento numero", total_csvs,"impreso")
        # debug rápido — mirá qué campos tiene un registro cualquiera
        #print(list(registros.values())[0].keys())
        #print("contenido:", contenido)

        for index, fila in contenido.iterrows():
            fragmento = construir_fragmento(fila, contenido.columns, doc_id, index, datos, idioma_doc)
            #print(fila['nombre_columna'])
            print(fragmento)

            with open("data/processed/fragments.jsonl", "a", encoding="utf-8") as f_out:
               f_out.write(json.dumps(fragmento.__dict__, ensure_ascii=False) + "\n")

    except Exception as e:
        errores += 1
        print(f"{doc_id}: error - {e}")

