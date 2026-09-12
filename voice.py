"""
Módulo de voz do Mini-Alexa de Casa Inteligente: reconhecimento (fala -> texto)
e síntese (texto -> fala).

- Reconhecimento: SpeechRecognition + microfone, transcrito via Google Web
  Speech API (pt-BR, não exige chave para uso limitado).
- Síntese: pyttsx3, que usa o motor de voz do próprio sistema operacional
  (SAPI5 no Windows) — funciona offline.

O texto transcrito é devolvido como uma string comum, para ser processado
pelo mesmo pipeline de análise léxica/semântica usado no modo digitado — ou
seja, a voz é só outra forma de "digitar" a frase, e a resposta em áudio é
só outra forma de "imprimir" a resposta.
"""

from __future__ import annotations

try:
    import speech_recognition as sr
    STT_DISPONIVEL = True
except ImportError:
    sr = None  # type: ignore[assignment]
    STT_DISPONIVEL = False

try:
    import pyttsx3
    TTS_DISPONIVEL = True
except ImportError:
    pyttsx3 = None  # type: ignore[assignment]
    TTS_DISPONIVEL = False


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
    if not STT_DISPONIVEL:
        raise ErroReconhecimento(
            "Reconhecimento de voz não está instalado. Rode: pip install -r requirements.txt"
        )

    reconhecedor = sr.Recognizer()
    try:
        with sr.Microphone() as fonte:
            reconhecedor.adjust_for_ambient_noise(fonte, duration=0.5)
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


_motor_tts = None  # instância única do motor de síntese (lazy init)


def _obter_motor_tts():
    global _motor_tts
    if _motor_tts is None:
        _motor_tts = pyttsx3.init()
        _selecionar_voz_em_portugues(_motor_tts)
    return _motor_tts


def _selecionar_voz_em_portugues(motor) -> None:
    """Procura, entre as vozes instaladas no sistema, uma em português e a
    ativa. Se não encontrar nenhuma, mantém a voz padrão do sistema (em
    inglês, na maioria das instalações do Windows sem pacote de idioma)."""
    for voz in motor.getProperty("voices"):
        idiomas = " ".join(str(v) for v in (getattr(voz, "languages", None) or []))
        pistas = f"{voz.id} {voz.name} {idiomas}".lower()
        if "pt-br" in pistas or "pt_br" in pistas or "portuguese" in pistas or "português" in pistas:
            motor.setProperty("voice", voz.id)
            return


def falar(texto: str) -> None:
    """Lê o texto em voz alta, se a síntese de voz estiver disponível.

    Uma falha aqui (lib ausente, sem driver de áudio etc.) nunca derruba o
    programa: a resposta já foi impressa na tela de qualquer forma, então o
    áudio é tratado como um "bônus" best-effort.
    """
    if not TTS_DISPONIVEL or not texto:
        return
    try:
        motor = _obter_motor_tts()
        motor.say(texto)
        motor.runAndWait()
    except Exception:
        pass
