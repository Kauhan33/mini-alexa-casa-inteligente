"""
Mini-Alexa de Casa Inteligente — ponto de entrada.

Uso:
    python main.py            -> modo interativo (digitado)
    python main.py --voz      -> já entra direto no modo de voz contínuo
    python main.py --demo     -> roda uma lista de comandos de exemplo (inclui erros propositais)

No modo digitado, digite "voz" (ou "ouvir"/"falar") a qualquer momento para
entrar no modo de voz contínuo: a Alexa fica ouvindo o microfone o tempo
todo, mas só reage a frases que começam com a palavra-chave "Alexa" (ex.:
"Alexa, ligar a luz da sala") — qualquer outra fala captada é ignorada em
silêncio, sem nenhuma resposta. Toda resposta é falada em áudio (pt-BR,
quando disponível) além de impressa na tela, até você dizer OU digitar
"sair" (digitar continua funcionando nesse modo — roda em paralelo, numa
thread separada, então não é preciso esperar a escuta para poder sair; e
não precisa da palavra-chave, já que digitar já é um ato deliberado).
"""

from __future__ import annotations

import sys
import threading
import unicodedata

from lexer import analisar_lexico
from semantic import CasaInteligente, interpretar
from voice import STT_DISPONIVEL, ErroReconhecimento, OuvidorContinuo, falar

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
PALAVRA_CHAVE = "alexa"


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


def _sem_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def _extrair_comando_apos_palavra_chave(frase: str) -> str | None:
    """
    Filtro da palavra-chave: só devolve algo se `frase` começar com "Alexa"
    (sem diferenciar maiúsculas/acentos/pontuação). Nesse caso, devolve o
    restante da frase (o comando de fato). Caso contrário, devolve None —
    o chamador deve ignorar a frase por completo, sem responder nada.
    """
    partes = frase.strip().split(maxsplit=1)
    if not partes:
        return None
    primeira_palavra = _sem_acentos(partes[0]).lower().strip(",.!?;:")
    if primeira_palavra != PALAVRA_CHAVE:
        return None
    return partes[1].strip(" ,.!?;:") if len(partes) > 1 else ""


def _thread_teclado(evento_parar: threading.Event, casa: CasaInteligente, trava: threading.Lock) -> None:
    """Roda em paralelo ao loop de voz: deixa digitar comandos (ou "sair")
    sem precisar esperar o microfone, e sem precisar da palavra-chave (digitar
    já é um ato deliberado). Só existe enquanto o modo de voz contínuo
    estiver ativo (thread daemon: encerra sozinha com o programa)."""
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
    """Fica ouvindo o microfone repetidamente. Só reage a frases que
    começam com a palavra-chave "Alexa" — para os demais, a Alexa não dá
    nenhuma resposta (nem em texto, nem em áudio), embora a transcrição
    apareça na tela como "(ignorado)", útil para depurar o reconhecimento.
    Cada comando válido é processado e respondido em texto + áudio, até
    "sair" ser dito (depois de "Alexa") ou digitado. Ao encerrar, termina
    o programa inteiro."""
    print("Modo de voz contínuo: comece o comando com a palavra-chave 'Alexa'")
    print("(ex.: \"Alexa, ligar a luz da sala\"). Fala sem essa palavra é ignorada.")
    print("Diga 'Alexa, sair' ou digite 'sair' a qualquer momento para encerrar.\n")
    falar("Modo de voz ativado. Pode falar comigo dizendo Alexa antes do comando.")

    try:
        ouvidor = OuvidorContinuo()
    except ErroReconhecimento as erro:
        print(f"Alexa: {erro}")
        sys.exit(1)

    evento_parar = threading.Event()
    trava = threading.Lock()  # protege o estado da casa contra voz e teclado ao mesmo tempo
    threading.Thread(target=_thread_teclado, args=(evento_parar, casa, trava), daemon=True).start()

    while not evento_parar.is_set():
        try:
            frase_ouvida = ouvidor.ouvir(timeout=5.0)
        except ErroReconhecimento as erro:
            # silêncio (ninguém falou dentro do timeout) é normal aqui —
            # só tenta ouvir de novo, sem poluir a tela com esse aviso
            if "Ninguém falou" not in str(erro):
                print(f"Alexa: {erro}")
            continue

        comando = _extrair_comando_apos_palavra_chave(frase_ouvida)
        if comando is None:
            print(f"Você (voz): {frase_ouvida}  (ignorado: sem a palavra-chave 'Alexa')")
            continue

        print(f"Você (voz): {frase_ouvida}")

        if not comando:
            resposta = "Diga um comando depois de 'Alexa'."
            print(f"Alexa: {resposta}")
            falar(resposta)
            continue

        if comando.lower() in COMANDOS_SAIR:
            evento_parar.set()
            break

        with trava:
            resposta = processar(comando, casa, verboso=False)
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
