"""
Mini-Alexa de Casa Inteligente — ponto de entrada.

Uso:
    python main.py              -> microfone JÁ ATIVO + teclado, ao mesmo tempo (padrão)
    python main.py --texto      -> somente teclado, sem usar o microfone
    python main.py --demo       -> roda uma lista de comandos de exemplo (inclui erros propositais)
    python main.py --diagnostico -> mostra o que esta máquina tem disponível para voz

Por padrão o programa começa ouvindo: dá para **falar** ou **digitar** o
comando, sem precisar ativar nada. A diferença entre os dois:

- **Falando**, é obrigatório começar com a palavra-chave "Alexa" (ex.:
  "Alexa, ligar a luz da sala"). Qualquer outra fala captada não recebe
  resposta — é só conversa perto do microfone. Variações comuns de
  transcrição errada do nome ("Alexia", "Alex", "Alex eu") também são
  aceitas (ver wakeword.py). A resposta sai na tela **e em áudio** (pt-BR).
- **Digitando**, não precisa da palavra-chave (digitar já é um ato
  deliberado) e a resposta sai **somente por escrito**, sem áudio.

Para encerrar: diga "Alexa, sair" ou digite "sair".

Nada disso é obrigatório para o programa funcionar: sem microfone, sem
bibliotecas de voz ou sem internet, ele continua rodando pelo teclado — a
análise léxica e semântica não dependem de nada além da biblioteca padrão.
"""

from __future__ import annotations

import sys
import threading

from lexer import analisar_lexico
from semantic import CasaInteligente, interpretar, texto_para_audio
from voice import STT_DISPONIVEL, ErroReconhecimento, OuvidorContinuo, diagnosticar, falar
from wakeword import extrair_comando

COMANDOS_DEMO = [
    "Ligar a luz da sala",
    "Ligar a luz da sala",                     # redundante -> informa o estado atual
    "Desligar a luz da sala",
    "Desligar a luz da sala",                  # redundante, no sentido oposto
    "Acender a luz do quarto",                 # outro local: estado independente
    "Aumentar o ventilador da sala para 60",
    "Aumentar o ventilador da sala para 40",   # contraditório -> informa o nível
    "Abrir a porta da garagem",
    "Abrir a porta da garagem",                # redundante
    "Abrir a luz da sala",                     # incompatível -> erro semântico
    "Ligar o forno",                           # dispositivo desconhecido
    "Estado da casa",                          # consulta: o que está ligado agora
]

COMANDOS_SAIR = ("sair", "exit", "quit")

# Marca que o microfone voltou a escutar. Reimprimir isso depois de cada
# resposta evita o problema de falar no vazio: enquanto a assistente está
# respondendo em áudio, nada é captado, e sem esse aviso não há como saber
# quando o próximo comando pode ser dito. Só ASCII, para não arriscar erro
# de codificação em terminais mais antigos.
AVISO_OUVINDO = ">> ouvindo... (pode falar ou digitar)"

AVISO_ESTADO_INICIAL = (
    "Estado inicial: todos os dispositivos comecam desligados (e portas/cortinas "
    "fechadas), em todos os locais."
)

AVISO_CONSULTAS = (
    'Consultas: diga/digite "comandos" para ver tudo que e aceito, ou '
    '"estado da casa" para saber o que esta ligado agora.'
)


def processar(frase: str, casa: CasaInteligente, verboso: bool = True) -> str:
    tokens = analisar_lexico(frase)
    if verboso:
        print(f"  tokens: {tokens}")
    return interpretar(tokens, casa)


def _responder(resposta: str, com_audio: bool) -> None:
    """Imprime a resposta e, quando `com_audio`, também a fala.

    O áudio é reservado às respostas de comandos **falados**: quem digitou o
    comando está olhando a tela, e ouvir a resposta em voz alta seria
    intrusivo. Respostas longas (a lista de comandos) são faladas em versão
    resumida, mas impressas por completo."""
    print(f"Alexa: {resposta}")
    if com_audio:
        falar(texto_para_audio(resposta))


def _avisar_ouvindo() -> None:
    """Sinaliza que o microfone está livre para o próximo comando."""
    print(AVISO_OUVINDO, flush=True)


def rodar_demo() -> None:
    casa = CasaInteligente()
    for frase in COMANDOS_DEMO:
        print(f"\nVocê: {frase}")
        print(f"Alexa: {processar(frase, casa)}")


def _thread_teclado(
    evento_parar: threading.Event, casa: CasaInteligente, trava: threading.Lock
) -> None:
    """Roda em paralelo à escuta do microfone: aceita comandos digitados
    (sem exigir a palavra-chave) e o "sair", sem precisar esperar o ciclo
    de escuta atual terminar. Thread daemon: encerra junto com o programa.

    Respostas daqui saem só por escrito — áudio é para comandos falados."""
    while not evento_parar.is_set():
        try:
            texto = input().strip()
        except EOFError:
            # stdin não é interativo (entrada redirecionada, execução sem
            # terminal...). Encerra só a leitura de teclado: a escuta por
            # voz continua funcionando normalmente.
            return
        except KeyboardInterrupt:
            evento_parar.set()
            return

        if not texto:
            continue
        if texto.lower() in COMANDOS_SAIR:
            evento_parar.set()
            return

        with trava:
            resposta = processar(texto, casa, verboso=False)
        _responder(resposta, com_audio=False)
        _avisar_ouvindo()


def rodar_modo_voz(casa: CasaInteligente, ouvidor: OuvidorContinuo) -> None:
    """Escuta o microfone continuamente, respondendo apenas às falas que
    começam com a palavra-chave, enquanto uma thread paralela aceita
    comandos digitados. Ao encerrar, termina o programa inteiro."""
    print('Microfone ativo: fale começando com "Alexa" (ex.: "Alexa, ligar a luz da sala")')
    print("ou apenas digite o comando, sem palavra-chave (ex.: ligar a luz da sala).")
    print('Para encerrar: diga "Alexa, sair" ou digite "sair".')
    print(AVISO_CONSULTAS)
    print(AVISO_ESTADO_INICIAL + "\n")
    falar("Estou ouvindo. Diga Alexa antes do comando.")

    evento_parar = threading.Event()
    # registra se a saída foi pedida por voz, para decidir se a despedida
    # também deve ser falada
    saida_por_voz = threading.Event()
    trava = threading.Lock()  # protege o estado da casa contra voz e teclado ao mesmo tempo
    threading.Thread(target=_thread_teclado, args=(evento_parar, casa, trava), daemon=True).start()

    _avisar_ouvindo()

    while not evento_parar.is_set():
        try:
            frase_ouvida = ouvidor.ouvir(timeout=5.0)
        except ErroReconhecimento as erro:
            mensagem = str(erro)
            # silêncio é o caso mais comum (o microfone fica sempre aberto):
            # o aviso de "ouvindo" já impresso continua valendo, então não
            # há nada a mostrar
            if "Ninguém falou" in mensagem:
                continue
            # já houve som, mas não deu para transcrever: vale avisar, senão
            # a pessoa fica esperando uma resposta que não vem
            if "não consegui entender" in mensagem.lower():
                print("(não entendi o que foi falado — pode repetir)")
            else:
                print(f"Alexa: {mensagem}")
            _avisar_ouvindo()
            continue

        comando = extrair_comando(frase_ouvida)
        if comando is None:
            # não era dirigido à assistente: nenhuma resposta, só o registro
            # da transcrição (ajuda a depurar o que o microfone entendeu)
            print(f"Você (voz): {frase_ouvida}  (ignorado: sem a palavra-chave 'Alexa')")
            _avisar_ouvindo()
            continue

        print(f"Você (voz): {frase_ouvida}")

        if not comando:
            _responder("Diga um comando depois de 'Alexa'.", com_audio=True)
            _avisar_ouvindo()
            continue

        if comando.lower() in COMANDOS_SAIR:
            saida_por_voz.set()
            evento_parar.set()
            break

        with trava:
            resposta = processar(comando, casa, verboso=False)
        _responder(resposta, com_audio=True)
        _avisar_ouvindo()

    _responder("Até logo!", com_audio=saida_por_voz.is_set())
    sys.exit(0)


def rodar_modo_texto(casa: CasaInteligente) -> None:
    """Modo somente teclado (sem microfone). Não exige palavra-chave e não
    responde em áudio."""
    print("Mini-Alexa de Casa Inteligente (digite 'sair' para encerrar)")
    print(AVISO_CONSULTAS)
    print(AVISO_ESTADO_INICIAL + "\n")

    while True:
        try:
            frase = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not frase:
            continue
        if frase.lower() in COMANDOS_SAIR:
            _responder("Até logo!", com_audio=False)
            break

        resposta = processar(frase, casa, verboso=False)
        _responder(resposta, com_audio=False)


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
    if "--diagnostico" in sys.argv:
        print(diagnosticar())
    elif "--demo" in sys.argv:
        rodar_demo()
    elif "--texto" in sys.argv:
        rodar_interativo(usar_voz=False)
    else:
        rodar_interativo()
