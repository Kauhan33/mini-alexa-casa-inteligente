"""
Módulo de voz do Mini-Alexa de Casa Inteligente: reconhecimento (fala -> texto)
e síntese (texto -> fala).

- Reconhecimento: SpeechRecognition + microfone, transcrito via Google Web
  Speech API (pt-BR, não exige chave para uso limitado).
- Síntese: tenta primeiro pyttsx3 (motor de voz do próprio sistema
  operacional — offline, mas só fala em português se o Windows tiver um
  pacote de voz pt-BR instalado). Quando nenhuma voz em português é
  encontrada, cai para gTTS (Google Text-to-Speech, online, sempre em
  pt-BR) — assim a resposta sai em português mesmo em computadores sem
  pacote de voz instalado.

O texto transcrito é devolvido como uma string comum, para ser processado
pelo mesmo pipeline de análise léxica/semântica usado no modo digitado — ou
seja, a voz é só outra forma de "digitar" a frase, e a resposta em áudio é
só outra forma de "imprimir" a resposta.
"""

from __future__ import annotations

import os
import tempfile
import uuid

try:
    import speech_recognition as sr
    STT_DISPONIVEL = True
except ImportError:
    sr = None  # type: ignore[assignment]
    STT_DISPONIVEL = False

try:
    import pyttsx3
    TTS_LOCAL_DISPONIVEL = True
except ImportError:
    pyttsx3 = None  # type: ignore[assignment]
    TTS_LOCAL_DISPONIVEL = False

try:
    from gtts import gTTS
    from playsound import playsound
    TTS_ONLINE_DISPONIVEL = True
except ImportError:
    gTTS = None  # type: ignore[assignment]
    playsound = None  # type: ignore[assignment]
    TTS_ONLINE_DISPONIVEL = False


class ErroReconhecimento(Exception):
    """Erro ao tentar ouvir ou transcrever um comando de voz."""


def ouvir_comando(idioma: str = "pt-BR", timeout: float = 5.0, limite_frase: float = 8.0) -> str:
    """
    Grava um único comando pelo microfone padrão (abre, calibra o ruído
    ambiente e escuta) e devolve o texto transcrito. Para escuta repetida
    (vários comandos seguidos), prefira a classe OuvidorContinuo — que
    calibra uma vez só, em vez de recalibrar (e arriscar perder o começo da
    fala) a cada comando.
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

    return _transcrever(reconhecedor, audio, idioma)


class OuvidorContinuo:
    """
    Mantém o microfone aberto e calibrado uma única vez (no construtor), para
    ser reaproveitado em loops de escuta contínua. Recalibrar o ruído
    ambiente a cada comando (como ouvir_comando faz) custa ~0.5s por vez e,
    se a pessoa já começar a falar durante essa calibração, a primeira
    palavra (geralmente a palavra-chave "Alexa") pode ser cortada.
    """

    def __init__(self, idioma: str = "pt-BR") -> None:
        if not STT_DISPONIVEL:
            raise ErroReconhecimento(
                "Reconhecimento de voz não está instalado. Rode: pip install -r requirements.txt"
            )
        self._idioma = idioma
        self._reconhecedor = sr.Recognizer()
        try:
            self._microfone = sr.Microphone()
            with self._microfone as fonte:
                self._reconhecedor.adjust_for_ambient_noise(fonte, duration=1.0)
        except OSError as exc:
            raise ErroReconhecimento(
                "Não encontrei um microfone disponível neste computador."
            ) from exc

    def ouvir(self, timeout: float = 5.0, limite_frase: float = 8.0) -> str:
        try:
            with self._microfone as fonte:
                audio = self._reconhecedor.listen(fonte, timeout=timeout, phrase_time_limit=limite_frase)
        except OSError as exc:
            raise ErroReconhecimento(
                "Não encontrei um microfone disponível neste computador."
            ) from exc
        except sr.WaitTimeoutError as exc:
            raise ErroReconhecimento("Ninguém falou a tempo.") from exc

        return _transcrever(self._reconhecedor, audio, self._idioma)


def _transcrever(reconhecedor, audio, idioma: str) -> str:
    try:
        return reconhecedor.recognize_google(audio, language=idioma)
    except sr.UnknownValueError as exc:
        raise ErroReconhecimento("Não consegui entender o que foi falado.") from exc
    except sr.RequestError as exc:
        raise ErroReconhecimento(
            "Não consegui contatar o serviço de reconhecimento de voz "
            "(verifique sua conexão com a internet)."
        ) from exc


# --------------------------------------------------------------------------
# Síntese de voz (texto -> áudio)
# --------------------------------------------------------------------------

_motor_tts_local = None  # instância única do motor pyttsx3 (lazy init)
_motor_tem_voz_pt = False
_aviso_sem_voz_pt_mostrado = False


def _obter_motor_tts_local():
    """Inicializa (uma única vez) o motor de voz local e tenta selecionar
    uma voz em português. Devolve o motor e se uma voz pt foi encontrada."""
    global _motor_tts_local, _motor_tem_voz_pt, _aviso_sem_voz_pt_mostrado
    if _motor_tts_local is None:
        _motor_tts_local = pyttsx3.init()
        _motor_tem_voz_pt = _selecionar_voz_em_portugues(_motor_tts_local)
        if not _motor_tem_voz_pt and not _aviso_sem_voz_pt_mostrado:
            if TTS_ONLINE_DISPONIVEL:
                print(
                    "(nenhuma voz em português encontrada neste computador; "
                    "usando o Google Text-to-Speech (online) para responder em pt-BR.)"
                )
            else:
                print(
                    "(nenhuma voz em português encontrada neste computador; usando a voz "
                    "padrão do sistema, em outro idioma. Para instalar uma voz pt-BR no "
                    "Windows: Configurações -> Hora e Idioma -> Voz -> Adicionar vozes.)"
                )
            _aviso_sem_voz_pt_mostrado = True
    return _motor_tts_local, _motor_tem_voz_pt


def _selecionar_voz_em_portugues(motor) -> bool:
    """Procura, entre as vozes instaladas no sistema, uma em português do
    Brasil e a ativa; na falta dela, aceita qualquer português. Devolve True
    se encontrou e selecionou alguma, False se manteve a voz padrão."""
    vozes = motor.getProperty("voices")

    for voz in vozes:
        idiomas = " ".join(str(v) for v in (getattr(voz, "languages", None) or []))
        pistas = f"{voz.id} {voz.name} {idiomas}".lower()
        if any(p in pistas for p in ("pt-br", "pt_br", "brazil", "brasil")):
            motor.setProperty("voice", voz.id)
            return True

    for voz in vozes:
        idiomas = " ".join(str(v) for v in (getattr(voz, "languages", None) or []))
        pistas = f"{voz.id} {voz.name} {idiomas}".lower()
        if "portuguese" in pistas or "português" in pistas or "pt-pt" in pistas:
            motor.setProperty("voice", voz.id)
            return True

    return False


def _falar_local(texto: str) -> None:
    motor, _ = _obter_motor_tts_local()
    motor.say(texto)
    motor.runAndWait()


def _falar_online_pt_br(texto: str) -> None:
    caminho = os.path.join(tempfile.gettempdir(), f"mini_alexa_{uuid.uuid4().hex}.mp3")
    try:
        gTTS(text=texto, lang="pt", tld="com.br").save(caminho)
        playsound(caminho)
    finally:
        try:
            os.remove(caminho)
        except OSError:
            pass


def falar(texto: str) -> None:
    """
    Lê o texto em voz alta, em português. Prioridades:
    1. pyttsx3 com uma voz pt-BR/pt instalada no sistema (offline, rápido);
    2. gTTS + playsound (online, mas sempre em pt-BR, mesmo sem nenhuma voz
       instalada no sistema);
    3. nada — se nenhuma das duas estiver disponível ou ambas falharem, a
       função simplesmente não faz nada. A resposta em áudio é um bônus
       best-effort: a resposta já foi impressa na tela de qualquer forma,
       então um problema de áudio nunca derruba o programa.
    """
    if not texto:
        return

    if TTS_LOCAL_DISPONIVEL:
        try:
            _, tem_voz_pt = _obter_motor_tts_local()
            if tem_voz_pt:
                _falar_local(texto)
                return
        except Exception:
            pass

    if TTS_ONLINE_DISPONIVEL:
        try:
            _falar_online_pt_br(texto)
            return
        except Exception:
            pass

    if TTS_LOCAL_DISPONIVEL:
        try:
            _falar_local(texto)
        except Exception:
            pass
