"""
Mini-Alexa de Casa Inteligente — ponto de entrada.

Uso:
    python main.py            -> modo interativo (digitado)
    python main.py --voz      -> já entra direto no modo de voz contínuo
    python main.py --demo     -> roda uma lista de comandos de exemplo (inclui erros propositais)

No modo digitado, digite "voz" (ou "ouvir"/"falar") a qualquer momento para
entrar no modo de voz contínuo: a Alexa fica ouvindo o microfone o tempo
todo e responde em áudio, até você dizer OU digitar "sair" (digitar
continua funcionando nesse modo — roda em paralelo, numa thread separada,
então não é preciso esperar a escuta para poder sair).
"""

from __future__ import annotations

import sys
import threading

from lexer import analisar_lexico
from semantic import CasaInteligente, interpretar
from voice import STT_DISPONIVEL, ErroReconhecimento, falar, ouvir_comando

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

COMANDOS_SAIR = ("sair", "exit", "quit")
COMANDOS_PARA_ENTRAR_EM_VOZ = ("voz", "ouvir", "falar")


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


def _thread_teclado(evento_parar: threading.Event, casa: CasaInteligente, trava: threading.Lock) -> None:
    """Roda em paralelo ao loop de voz: deixa digitar comandos (ou "sair")
    sem precisar esperar o microfone. Só existe enquanto o modo de voz
    contínuo estiver ativo (thread daemon: encerra sozinha com o programa)."""
    while not evento_parar.is_set():
        try:
            texto = input().strip()
        except (EOFError, KeyboardInterrupt):
            evento_parar.set()
            return

        if not texto:
            continue
        if texto.lower() in COMANDOS_SAIR:
            evento_parar.set()
            return

        with trava:
            resposta = processar(texto, casa, verboso=False)
        print(f"Alexa: {resposta}")
        falar(resposta)


def rodar_modo_voz_continuo(casa: CasaInteligente) -> None:
    """Fica ouvindo o microfone repetidamente (cada comando reconhecido é
    processado e respondido em texto + áudio) até "sair" ser dito ou
    digitado. Ao encerrar, termina o programa inteiro."""
    print("Modo de voz contínuo: fale um comando quando quiser.")
    print("Diga ou digite 'sair' a qualquer momento para encerrar.\n")
    falar("Modo de voz ativado. Pode falar.")

    evento_parar = threading.Event()
    trava = threading.Lock()  # protege o estado da casa contra voz e teclado ao mesmo tempo
    threading.Thread(target=_thread_teclado, args=(evento_parar, casa, trava), daemon=True).start()

    while not evento_parar.is_set():
        try:
            frase = ouvir_comando(timeout=3.0)
        except ErroReconhecimento as erro:
            # silêncio (ninguém falou dentro do timeout) é normal aqui —
            # só tenta ouvir de novo, sem poluir a tela com esse aviso
            if "Ninguém falou" not in str(erro):
                print(f"Alexa: {erro}")
            continue

        print(f"Você (voz): {frase}")
        if frase.strip().lower() in COMANDOS_SAIR:
            evento_parar.set()
            break

        with trava:
            resposta = processar(frase, casa, verboso=False)
        print(f"Alexa: {resposta}")
        falar(resposta)

    print("Alexa: Até logo!")
    falar("Até logo!")
    sys.exit(0)


def rodar_interativo(usar_voz: bool = False) -> None:
    casa = CasaInteligente()

    if usar_voz and not STT_DISPONIVEL:
        print(
            "Aviso: reconhecimento de voz não está instalado "
            "(pip install -r requirements.txt). Continuando em modo texto.\n"
        )
        usar_voz = False

    if usar_voz:
        rodar_modo_voz_continuo(casa)  # nunca retorna: termina o programa ao sair
        return

    dica_voz = ", ou 'voz' para ativar o modo de voz contínuo" if STT_DISPONIVEL else ""
    print(f"Mini-Alexa de Casa Inteligente (digite 'sair' para encerrar{dica_voz})\n")

    while True:
        try:
            frase = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not frase:
            continue
        if frase.lower() in COMANDOS_SAIR:
            print("Alexa: Até logo!")
            break

        if frase.lower() in COMANDOS_PARA_ENTRAR_EM_VOZ:
            if not STT_DISPONIVEL:
                print(
                    "Alexa: reconhecimento de voz não está instalado. "
                    "Rode: pip install -r requirements.txt"
                )
                continue
            rodar_modo_voz_continuo(casa)  # nunca retorna: termina o programa ao sair
            continue

        print(f"Alexa: {processar(frase, casa, verboso=False)}")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        rodar_demo()
    elif "--voz" in sys.argv:
        rodar_interativo(usar_voz=True)
    else:
        rodar_interativo()
