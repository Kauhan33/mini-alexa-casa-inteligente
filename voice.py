"""
Módulo de reconhecimento de voz do Mini-Alexa de Casa Inteligente.

Usa a biblioteca SpeechRecognition para capturar áudio do microfone e
transcrevê-lo em texto (via Google Web Speech API, que não exige chave para
uso limitado). O texto transcrito é devolvido como uma string comum, para
ser processado pelo mesmo pipeline de análise léxica/semântica usado no
modo digitado — ou seja, a voz é só outra forma de "digitar" a frase.
"""

from __future__ import annotations

try:
    import speech_recognition as sr
    DISPONIVEL = True
except ImportError:
    sr = None  # type: ignore[assignment]
    DISPONIVEL = False


class ErroReconhecimento(Exception):
    """Erro ao tentar ouvir ou transcrever um comando de voz."""


def ouvir_comando(idioma: str = "pt-BR", timeout: float = 5.0, limite_frase: float = 8.0) -> str:
    """
    Grava um comando pelo microfone padrão e devolve o texto transcrito.

    Levanta ErroReconhecimento (com mensagem amigável, em português) se:
    - a biblioteca não estiver instalada;
    - não houver microfone disponível;
    - ninguém falar dentro do tempo limite;
    - a fala não puder ser entendida;
    - não houver internet para consultar o serviço de reconhecimento.
    """
    if not DISPONIVEL:
        raise ErroReconhecimento(
            "Reconhecimento de voz não está instalado. Rode: pip install -r requirements.txt"
        )

    reconhecedor = sr.Recognizer()
    try:
        with sr.Microphone() as fonte:
            reconhecedor.adjust_for_ambient_noise(fonte, duration=0.5)
            print("(ouvindo... fale agora)")
            audio = reconhecedor.listen(fonte, timeout=timeout, phrase_time_limit=limite_frase)
    except OSError as exc:
        raise ErroReconhecimento(
            "Não encontrei um microfone disponível neste computador."
        ) from exc
    except sr.WaitTimeoutError as exc:
        raise ErroReconhecimento("Ninguém falou a tempo.") from exc

    try:
        return reconhecedor.recognize_google(audio, language=idioma)
    except sr.UnknownValueError as exc:
        raise ErroReconhecimento("Não consegui entender o que foi falado.") from exc
    except sr.RequestError as exc:
        raise ErroReconhecimento(
            "Não consegui contatar o serviço de reconhecimento de voz "
            "(verifique sua conexão com a internet)."
        ) from exc
