"""
Detecção da palavra-chave ("Alexa") nas frases reconhecidas por voz.

O reconhecimento de fala erra bastante justamente no nome da assistente —
nos testes reais apareceram "Alexia", "Alexis", "Alex" e até "Alex eu"
(com o nome quebrado em duas palavras). Comparar a primeira palavra com
"alexa" por igualdade exata, portanto, descartaria comandos válidos.

Este módulo resolve isso em três camadas:

1. uma lista de variações já conhecidas (casamento exato, rápido);
2. similaridade aproximada (difflib), para variações não previstas — o
   limiar 0.72 foi calibrado com transcrições reais: aceita "alexeu"
   (0.727) e "alexia" (0.909), mas rejeita fala comum como "legal"
   (0.600) e "agora" (0.400);
3. tratamento de resíduo: quando o nome é transcrito em duas palavras
   ("Alex eu sair"), a segunda só é absorvida se for curta E não
   significar nada no vocabulário do lexer — assim "Alexa tv" preserva
   o "tv" (que é um dispositivo), mas "Alex eu sair" vira "sair".

Isso funciona como uma etapa *anterior* à análise léxica: filtra o que é
dirigido à assistente antes de a frase virar tokens.
"""

from __future__ import annotations

import unicodedata
from difflib import SequenceMatcher

from lexer import TipoToken, analisar_lexico

PALAVRA_CHAVE = "alexa"

# Limiar de similaridade (0 a 1) calibrado com transcrições reais.
LIMIAR_SIMILARIDADE = 0.72

# Tamanho máximo de uma palavra para ser considerada "resto" do nome mal
# transcrito (ex.: o "eu" de "Alex eu").
MAX_TAMANHO_RESIDUO = 3

# Variações já observadas ou previsíveis, garantidas independente do limiar.
VARIACOES_CONHECIDAS = {
    "alexa", "alexia", "alexis", "alexsa", "aleksa", "alexar", "alexo",
    "alex", "lexa", "lex", "elexa", "eleksa", "elexia",
    "alessa", "alexandra", "alexei", "aleixa", "aleixo", "alexeu",
}


def _normalizar(texto: str) -> str:
    """Minúsculas, sem acentuação e sem pontuação — só letras."""
    texto = texto.lower().strip()
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    return "".join(c for c in sem_acento if c.isalpha())


def parece_palavra_chave(candidato: str) -> bool:
    """True se `candidato` é a palavra-chave ou algo parecido o suficiente."""
    candidato = _normalizar(candidato)
    if not candidato:
        return False
    if candidato in VARIACOES_CONHECIDAS:
        return True
    return SequenceMatcher(None, candidato, PALAVRA_CHAVE).ratio() >= LIMIAR_SIMILARIDADE


def _e_residuo(palavra: str) -> bool:
    """True se `palavra` é curta e não significa nada no vocabulário do
    lexer — ou seja, provável sobra de uma transcrição errada do nome
    (o "eu" de "Alex eu"), e não parte do comando."""
    normalizada = _normalizar(palavra)
    if not normalizada or len(normalizada) > MAX_TAMANHO_RESIDUO:
        return False
    tokens = analisar_lexico(normalizada)
    return all(
        token.tipo in (TipoToken.DESCONHECIDO, TipoToken.CONECTIVO) for token in tokens
    )


def extrair_comando(frase: str) -> str | None:
    """
    Devolve o comando que vem depois da palavra-chave, ou None se a frase
    não for dirigida à assistente (sem palavra-chave no início).

    Devolve string vazia quando a pessoa diz só a palavra-chave, sem
    comando algum ("Alexa").

    >>> extrair_comando("Alexa ligar a luz da sala")
    'ligar a luz da sala'
    >>> extrair_comando("Alexia sair")
    'sair'
    >>> extrair_comando("Alex eu sair")
    'sair'
    >>> extrair_comando("agora tá funcionando") is None
    True
    """
    palavras = frase.strip().split()
    if not palavras:
        return None

    # Hipótese 1: o nome foi transcrito quebrado em duas palavras.
    if len(palavras) >= 2 and _e_residuo(palavras[1]):
        if parece_palavra_chave(palavras[0] + palavras[1]):
            return " ".join(palavras[2:]).strip(" ,.!?;:")

    # Hipótese 2: o nome é a primeira palavra.
    if parece_palavra_chave(palavras[0]):
        return " ".join(palavras[1:]).strip(" ,.!?;:")

    return None
