import json
import numpy as np
import faiss
import re
import pymupdf
from sentence_transformers import SentenceTransformer

def extraer_texto_del_pdf(ruta_pdf):
    try:
        doc = pymupdf.open(ruta_pdf)
        texto_completo = ""
        for pagina in doc:
            texto_completo += pagina.get_text()
        doc.close()
        return texto_completo
    except Exception as e:
        print(f"Error al leer el PDF de consultas: {e}")
        return ""

def cargar_consultas(ruta_pdf):
    texto_sin_procesar = extraer_texto_del_pdf(ruta_pdf)
    patron = r"(q0[0-5]\d)\s+([^\n]+)"
    matches = re.findall(patron, texto_sin_procesar)
    
    consultas = {}
    for match in matches:
        q_id = match[0].strip()
        q_texto = match[1].strip()
        consultas[q_id] = q_texto
        
    if len(consultas) != 50:
        print(f"No hay 50 consultas, hay: {len(consultas)}")
    return consultas

def dividir_por_oraciones_250_palabras(texto_original):
    palabras = texto_original.split()
    if len(palabras) <= 250:
        return [texto_original]
    
    oraciones = re.split(r'(?<=[.!?])\s+', texto_original)
    
    sub_fragmentos = []
    chunk_actual = []
    conteo_actual = 0
    
    for oracion in oraciones:
        palabras_oracion = oracion.split()
        if conteo_actual + len(palabras_oracion) <= 250:
            chunk_actual.append(oracion)
            conteo_actual += len(palabras_oracion)
        else:
            if chunk_actual:
                sub_fragmentos.append(" ".join(chunk_actual))
            chunk_actual = [oracion]
            conteo_actual = len(palabras_oracion)
    
    if chunk_actual:
        sub_fragmentos.append(" ".join(chunk_actual))
    
    return sub_fragmentos

def main():
    modelo = SentenceTransformer('BAAI/bge-m3')
    index = faiss.read_index("entrega/base_vectorial/encoder_bge-m3/index.faiss")
    
    metadata_store = []
    with open("entrega/base_vectorial/encoder_bge-m3/metadata.jsonl", 'r', encoding='utf-8') as f:
        for line in f:
            metadata_store.append(json.loads(line))
    
    consultas = cargar_consultas("config/Extracto_Preguntas_50_v2.pdf")
    
    resultados_finales = []
    q_ids_ordenados = sorted(consultas.keys())
    
    for q_id in q_ids_ordenados:
        texto_consulta = consultas[q_id]
        
        q_emb = modelo.encode([texto_consulta], normalize_embeddings=True)
        q_emb = np.array(q_emb, dtype='float32')
        
        k_search = 100
        distancias, indices_faiss = index.search(q_emb, k_search)
        
        puntajes_doc = {}
        fragmentos_candidatos = []
        
        for i in range(k_search):
            index_interno = indices_faiss[0][i]
            if index_interno == -1: 
                continue
                
            score_similitud = distancias[0][i]
            meta = metadata_store[index_interno]
            doc_id = meta['doc_id']
            
            if doc_id not in puntajes_doc or score_similitud > puntajes_doc[doc_id]:
                puntajes_doc[doc_id] = score_similitud
                
            texto_limpio = meta['texto'].replace('\n', ' ')
            texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()

            fragmentos_candidatos.append({
                "chunk_id": meta['chunk_id'],
                "doc_id": doc_id,
                "text": texto_limpio
            })
        
        docs_ordenados = sorted(puntajes_doc.items(), key=lambda x: x[1], reverse=True)
        top_3_docs = docs_ordenados[:3]
        
        json_documents = [
            {"rank": rank + 1, "doc_id": d_id} 
            for rank, (d_id, _score) in enumerate(top_3_docs)
        ]
        
        json_fragments = []
        rank_frag = 1
        
        for candidato in fragmentos_candidatos:
            if rank_frag > 10:
                break
            
            sub_fragmentos = dividir_por_oraciones_250_palabras(candidato["text"])
            
            for sub_text in sub_fragmentos:
                if rank_frag > 10:
                    break
                
                json_fragments.append({
                    "rank": rank_frag,
                    "chunk_id": candidato["chunk_id"], 
                    "doc_id": candidato["doc_id"],
                    "text": sub_text
                })
                rank_frag += 1
        
        objeto_resultado = {
            "query_id": q_id,
            "documents": json_documents,
            "fragments": json_fragments
        }
        resultados_finales.append(objeto_resultado)

    with open("entrega/resultados.jsonl", 'w', encoding='utf-8') as out_f:
        for res in resultados_finales:
            out_f.write(json.dumps(res, ensure_ascii=False) + '\n')
            
    print("Archivo Generado")

if __name__ == "__main__":
    main()