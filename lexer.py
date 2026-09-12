"""
Analisador léxico do Mini-Alexa de Casa Inteligente.

Responsável por transformar uma frase em linguagem natural em uma lista de
tokens classificados (ação, dispositivo, local, valor numérico etc.),
exatamente como a fase léxica de um compilador transforma código-fonte em
uma sequência de tokens.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum, auto


class TipoToken(Enum):
    ACAO = auto()
    DISPOSITIVO = auto()
    LOCAL = auto()
    VALOR = auto()
    CONECTIVO = auto()
    DESCONHECIDO = auto()


@dataclass
class Token:
    tipo: TipoToken
    valor: str   # forma canônica (ex.: "LIGAR", "ar_condicionado", "22")
    lexema: str  # texto original reconhecido (ex.: "acender", "ar condicionado")

    def __repr__(self) -> str:
        return f"<{self.tipo.name}:{self.valor}>"


# --------------------------------------------------------------------------
# Vocabulário reconhecido pelo analisador
# --------------------------------------------------------------------------

ACOES: dict[str, str] = {
    "ligar": "LIGAR", "acender": "LIGAR", "ativar": "LIGAR", "iniciar": "LIGAR",
    "desligar": "DESLIGAR", "apagar": "DESLIGAR", "desativar": "DESLIGAR", "parar": "DESLIGAR",
    "abrir": "ABRIR",
    "fechar": "FECHAR",
    "aumentar": "AUMENTAR", "subir": "AUMENTAR",
    "diminuir": "DIMINUIR", "baixar": "DIMINUIR", "reduzir": "DIMINUIR",
}

# cada dispositivo pode ter vários sinônimos, inclusive compostos por mais de uma palavra
DISPOSITIVOS: dict[str, list[str]] = {
    "luz": ["luz", "luzes", "lampada", "lampadas"],
    "ventilador": ["ventilador", "ventiladores"],
    "ar_condicionado": ["ar condicionado", "ar-condicionado"],
    "tv": ["tv", "televisao"],
    "porta": ["porta", "portas"],
    "portao": ["portao"],
    "cortina": ["cortina", "cortinas"],
    "tomada": ["tomada", "tomadas"],
    "alarme": ["alarme"],
}

LOCAIS = {
    "sala", "quarto", "cozinha", "banheiro", "quintal", "garagem", "escritorio", "varanda",
}

# palavras sem significado próprio para a análise semântica (artigos,
# preposições, unidades de medida...), mas que fazem parte da frase
PALAVRAS_IGNORADAS = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "para", "pra", "por",
    "favor", "no", "na", "nos", "nas", "grau", "graus", "porcento",
}


def _normalizar(texto: str) -> str:
    """Minúsculas, sem acentuação e sem pontuação — facilita o casamento léxico."""
    texto = texto.lower().strip()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    texto = re.sub(r"[^\w\s%]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def analisar_lexico(frase: str) -> list[Token]:
    """
    Percorre a frase palavra a palavra (com lookahead de 2 palavras para
    reconhecer dispositivos compostos, como "ar condicionado") e devolve a
    lista de tokens classificados.
    """
    palavras = _normalizar(frase).split(" ") if frase.strip() else []
    tokens: list[Token] = []

    i = 0
    while i < len(palavras):
        palavra = palavras[i]
        duas_palavras = " ".join(palavras[i:i + 2]) if i + 1 < len(palavras) else None

        # 1) dispositivo composto (2 palavras), ex.: "ar condicionado"
        casado = False
        if duas_palavras:
            for canonico, sinonimos in DISPOSITIVOS.items():
                if duas_palavras in sinonimos:
                    tokens.append(Token(TipoToken.DISPOSITIVO, canonico, duas_palavras))
                    i += 2
                    casado = True
                    break
        if casado:
            continue

        # 2) ação
        if palavra in ACOES:
            tokens.append(Token(TipoToken.ACAO, ACOES[palavra], palavra))
            i += 1
            continue

        # 3) dispositivo de uma palavra só
        encontrado = None
        for canonico, sinonimos in DISPOSITIVOS.items():
            if palavra in sinonimos:
                encontrado = canonico
                break
        if encontrado:
            tokens.append(Token(TipoToken.DISPOSITIVO, encontrado, palavra))
            i += 1
            continue

        # 4) local
        if palavra in LOCAIS:
            tokens.append(Token(TipoToken.LOCAL, palavra, palavra))
            i += 1
            continue

        # 5) valor numérico (ex.: "22", "50%")
        if re.fullmatch(r"\d+%?", palavra):
            tokens.append(Token(TipoToken.VALOR, palavra.rstrip("%"), palavra))
            i += 1
            continue

        # 6) palavra sem valor semântico (artigo, preposição, unidade...)
        if palavra in PALAVRAS_IGNORADAS:
            tokens.append(Token(TipoToken.CONECTIVO, palavra, palavra))
            i += 1
            continue

        # 7) nada reconhecido
        tokens.append(Token(TipoToken.DESCONHECIDO, palavra, palavra))
        i += 1

    return tokens
