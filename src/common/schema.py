from dataclasses import dataclass

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
    
    def __post_init__(self):
        if self.fenomeno not in (1,2,3):
            raise ValueError("fenomeno debe ser 1, 2 o 3")
        if self.num_tokens < 0:
            raise ValueError("num_tokens debe ser no negativo")
        if self.idioma not in ("en", "es", "pt"):
            raise ValueError("idioma debe ser en(ingles), es(español) o pt(portugues)")
