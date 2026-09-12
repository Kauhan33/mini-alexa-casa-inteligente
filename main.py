"""
Mini-Alexa de Casa Inteligente — ponto de entrada.

Uso:
    python main.py            -> modo interativo (digitado)
    python main.py --voz      -> modo interativo, ouvindo o microfone a cada turno
    python main.py --demo     -> roda uma lista de comandos de exemplo (inclui erros propositais)

No modo digitado, digite "voz" (ou "ouvir"/"falar") a qualquer momento para
falar um único comando pelo microfone em vez de digitar.
"""

from __future__ import annotations

import sys

from lexer import analisar_lexico
from semantic import CasaInteligente, interpretar
from voice import DISPONIVEL as VOZ_DISPONIVEL
from voice import ErroReconhecimento, ouvir_comando

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

COMANDOS_PARA_OUVIR = ("voz", "ouvir", "falar")


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


def _capturar_frase_por_voz() -> str | None:
    """Ouve o microfone e devolve o texto transcrito, ou None se algo falhou
    (a mensagem de erro já é impressa aqui)."""
    try:
        frase = ouvir_comando()
    except ErroReconhecimento as erro:
        print(f"Alexa: {erro}")
        return None
    print(f"Você (voz): {frase}")
    return frase


def rodar_interativo(usar_voz: bool = False) -> None:
    casa = CasaInteligente()

    if usar_voz and not VOZ_DISPONIVEL:
        print(
            "Aviso: reconhecimento de voz não está instalado "
            "(pip install -r requirements.txt). Continuando em modo texto.\n"
        )
        usar_voz = False

    dica_voz = ", ou 'voz' para falar" if VOZ_DISPONIVEL and not usar_voz else ""
    print(f"Mini-Alexa de Casa Inteligente (digite 'sair' para encerrar{dica_voz})\n")

    while True:
        try:
            if usar_voz:
                frase = _capturar_frase_por_voz()
                if frase is None:
                    continue
            else:
                frase = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not frase:
            continue
        if frase.lower() in ("sair", "exit", "quit"):
            print("Alexa: Até logo!")
            break

        if not usar_voz and frase.lower() in COMANDOS_PARA_OUVIR:
            if not VOZ_DISPONIVEL:
                print(
                    "Alexa: reconhecimento de voz não está instalado. "
                    "Rode: pip install -r requirements.txt"
                )
                continue
            frase = _capturar_frase_por_voz()
            if frase is None:
                continue

        print(f"Alexa: {processar(frase, casa, verboso=False)}")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        rodar_demo()
    elif "--voz" in sys.argv:
        rodar_interativo(usar_voz=True)
    else:
        rodar_interativo()
