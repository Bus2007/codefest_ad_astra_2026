from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Fragmento:
    doc_id:str
    chunk_id:str
    fuente:str
    formato:str
    fenomeno:int
    posicion:int
    num_tokens:int
    texto:str
    idioma:str
    url: Optional[str] = None
    fecha_publicacion: Optional[str] = None
    autores: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    alerta_meta: Optional[dict] = None
    
    def __post_init__(self):
        if self.fenomeno not in (1,2,3):
            raise ValueError("fenomeno debe ser 1, 2 o 3")
        if self.num_tokens < 0:
            raise ValueError("num_tokens debe ser no negativo")
        if self.idioma not in ("en", "es", "pt"):
            raise ValueError("idioma debe ser en(ingles), es(español) o pt(portugues)")
        if self.formato not in ("pdf", "html", "md", "json", "csv", "xlsx", "image", "pbf"):
            raise ValueError("formato debe ser pdf, html, md, json, csv, xlsx, image o pbf")
