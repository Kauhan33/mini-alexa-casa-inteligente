"""
Mini-Alexa de Casa Inteligente — ponto de entrada.

Uso:
    python main.py            -> microfone JÁ ATIVO + teclado, ao mesmo tempo (padrão)
    python main.py --texto    -> somente teclado, sem usar o microfone
    python main.py --demo     -> roda uma lista de comandos de exemplo (inclui erros propositais)

Por padrão o programa começa ouvindo: dá para **falar** ou **digitar** o
comando, sem precisar ativar nada. A diferença entre os dois:

- **Falando**, é obrigatório começar com a palavra-chave "Alexa" (ex.:
  "Alexa, ligar a luz da sala"). Qualquer outra fala captada não recebe
  resposta — é só conversa perto do microfone. Variações comuns de
  transcrição errada do nome ("Alexia", "Alex", "Alex eu") também são
  aceitas (ver wakeword.py).
- **Digitando**, não precisa da palavra-chave: digitar já é um ato
  deliberado. Basta escrever "ligar a luz da sala".

Toda resposta é impressa na tela e falada em áudio (pt-BR). Para encerrar:
diga "Alexa, sair" ou digite "sair".
"""

from __future__ import annotations

import sys
import threading

from lexer import analisar_lexico
from semantic import CasaInteligente, interpretar
from voice import STT_DISPONIVEL, ErroReconhecimento, OuvidorContinuo, falar
from wakeword import extrair_comando

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


def processar(frase: str, casa: CasaInteligente, verboso: bool = True) -> str:
    tokens = analisar_lexico(frase)
    if verboso:
        print(f"  tokens: {tokens}")
    return interpretar(tokens, casa)


def _responder(resposta: str) -> None:
    """Imprime e fala a resposta (todo retorno ao usuário passa por aqui)."""
    print(f"Alexa: {resposta}")
    falar(resposta)


def rodar_demo() -> None:
    casa = CasaInteligente()
    for frase in COMANDOS_DEMO:
        print(f"\nVocê: {frase}")
        print(f"Alexa: {processar(frase, casa)}")


def _thread_teclado(evento_parar: threading.Event, casa: CasaInteligente, trava: threading.Lock) -> None:
    """Roda em paralelo à escuta do microfone: aceita comandos digitados
    (sem exigir a palavra-chave) e o "sair", sem precisar esperar o ciclo
    de escuta atual terminar. Thread daemon: encerra junto com o programa."""
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
        _responder(resposta)


def rodar_modo_voz(casa: CasaInteligente, ouvidor: OuvidorContinuo) -> None:
    """Escuta o microfone continuamente, respondendo apenas às falas que
    começam com a palavra-chave, enquanto uma thread paralela aceita
    comandos digitados. Ao encerrar, termina o programa inteiro."""
    print('Microfone ativo: fale começando com "Alexa" (ex.: "Alexa, ligar a luz da sala")')
    print("ou apenas digite o comando, sem palavra-chave (ex.: ligar a luz da sala).")
    print('Para encerrar: diga "Alexa, sair" ou digite "sair".\n')
    falar("Estou ouvindo. Diga Alexa antes do comando.")

    evento_parar = threading.Event()
    trava = threading.Lock()  # protege o estado da casa contra voz e teclado ao mesmo tempo
    threading.Thread(target=_thread_teclado, args=(evento_parar, casa, trava), daemon=True).start()

    while not evento_parar.is_set():
        try:
            frase_ouvida = ouvidor.ouvir(timeout=5.0)
        except ErroReconhecimento as erro:
            # silêncio ou fala inintelígivel são normais aqui (o microfone
            # está sempre aberto) — não vale poluir a tela nem responder
            if "Ninguém falou" not in str(erro) and "não consegui entender" not in str(erro).lower():
                print(f"Alexa: {erro}")
            continue

        comando = extrair_comando(frase_ouvida)
        if comando is None:
            # não era dirigido à assistente: nenhuma resposta, só o registro
            # da transcrição (ajuda a depurar o que o microfone entendeu)
            print(f"Você (voz): {frase_ouvida}  (ignorado: sem a palavra-chave 'Alexa')")
            continue

        print(f"Você (voz): {frase_ouvida}")

        if not comando:
            _responder("Diga um comando depois de 'Alexa'.")
            continue

        if comando.lower() in COMANDOS_SAIR:
            evento_parar.set()
            break

        with trava:
            resposta = processar(comando, casa, verboso=False)
        _responder(resposta)

    _responder("Até logo!")
    sys.exit(0)


def rodar_modo_texto(casa: CasaInteligente) -> None:
    """Modo somente teclado (sem microfone). Não exige palavra-chave."""
    print("Mini-Alexa de Casa Inteligente (digite 'sair' para encerrar)\n")

    while True:
        try:
            frase = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not frase:
            continue
        if frase.lower() in COMANDOS_SAIR:
            _responder("Até logo!")
            break

        resposta = processar(frase, casa, verboso=False)
        _responder(resposta)


def rodar_interativo(usar_voz: bool = True) -> None:
    casa = CasaInteligente()

    if usar_voz:
        if not STT_DISPONIVEL:
            print(
                "Aviso: reconhecimento de voz não está instalado "
                "(pip install -r requirements.txt). Continuando só com o teclado.\n"
            )
        else:
            try:
                ouvidor = OuvidorContinuo()
            except ErroReconhecimento as erro:
                print(f"Aviso: {erro} Continuando só com o teclado.\n")
            else:
                rodar_modo_voz(casa, ouvidor)  # nunca retorna: termina o programa ao sair
                return

    rodar_modo_texto(casa)


if __name__ == "__main__":
    if "--demo" in sys.argv:
        rodar_demo()
    elif "--texto" in sys.argv:
        rodar_interativo(usar_voz=False)
    else:
        rodar_interativo()
