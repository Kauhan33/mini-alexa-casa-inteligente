"""
Mini-Alexa de Casa Inteligente — ponto de entrada.

Uso:
    python main.py            -> modo interativo
    python main.py --demo     -> roda uma lista de comandos de exemplo (inclui erros propositais)
"""

from __future__ import annotations

import sys

from lexer import analisar_lexico
from semantic import CasaInteligente, interpretar

COMANDOS_DEMO = [
    "Ligar a luz da sala",
    "Acender a luz do quarto",
    "Aumentar o ventilador da sala para 60",
    "Abrir a porta da garagem",
    "Abrir a luz da sala",     # incompatível -> erro semântico
    "Diminuir o ar condicionado do quarto",
    "Fechar a cortina da sala",
    "Ligar o forno",           # dispositivo desconhecido -> erro semântico
]


def processar(frase: str, casa: CasaInteligente, verboso: bool = True) -> str:
    tokens = analisar_lexico(frase)
    if verboso:
        print(f"  tokens: {tokens}")
    return interpretar(tokens, casa)


def rodar_demo() -> None:
    casa = CasaInteligente()
    for frase in COMANDOS_DEMO:
        print(f"\nVocê: {frase}")
        print(f"Alexa: {processar(frase, casa)}")


def rodar_interativo() -> None:
    casa = CasaInteligente()
    print("Mini-Alexa de Casa Inteligente (digite 'sair' para encerrar)\n")
    while True:
        try:
            frase = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not frase:
            continue
        if frase.lower() in ("sair", "exit", "quit"):
            print("Alexa: Até logo!")
            break
        print(f"Alexa: {processar(frase, casa, verboso=False)}")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        rodar_demo()
    else:
        rodar_interativo()
