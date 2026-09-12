"""Testes de portabilidade: o programa tem que funcionar em qualquer
computador, mesmo sem microfone, sem as bibliotecas de voz instaladas e
sem internet.

A análise léxica e a análise semântica — o coração do exercício — usam
apenas a biblioteca padrão do Python. Tudo relacionado a voz é opcional e
degrada em silêncio, nunca derrubando o programa.

Rodar com:  python -m unittest test_sem_dependencias.py -v
"""

import unittest
from unittest.mock import patch

import main
import voice
from lexer import analisar_lexico
from semantic import CasaInteligente, interpretar


class TestNucleoSemDependencias(unittest.TestCase):
    """lexer.py e semantic.py não importam nada além da biblioteca padrão."""

    def test_lexer_e_semantic_usam_apenas_biblioteca_padrao(self):
        import lexer
        import semantic

        for modulo in (lexer, semantic):
            with self.subTest(modulo=modulo.__name__):
                with open(modulo.__file__, encoding="utf-8") as arquivo:
                    fonte = arquivo.read()
                for pacote in ("speech_recognition", "pyttsx3", "gtts", "playsound", "pyaudio"):
                    self.assertNotIn(pacote, fonte)

    def test_pipeline_funciona_sem_nenhuma_lib_de_voz(self):
        with patch.object(voice, "STT_DISPONIVEL", False), \
             patch.object(voice, "TTS_LOCAL_DISPONIVEL", False), \
             patch.object(voice, "TTS_ONLINE_DISPONIVEL", False):
            casa = CasaInteligente()
            resposta = interpretar(analisar_lexico("ligar a luz da sala"), casa)
            self.assertIn("ligando", resposta.lower())


class TestVozOpcional(unittest.TestCase):
    def test_falar_sem_nenhum_motor_nao_quebra(self):
        with patch.object(voice, "TTS_LOCAL_DISPONIVEL", False), \
             patch.object(voice, "TTS_ONLINE_DISPONIVEL", False):
            voice.falar("qualquer coisa")  # não deve levantar exceção

    def test_falar_nao_propaga_erro_de_audio(self):
        """Mesmo que os dois motores estourem exceção, falar() não quebra o
        programa — só registra o aviso."""
        with patch.object(voice, "TTS_LOCAL_DISPONIVEL", True), \
             patch.object(voice, "_falar_local", side_effect=RuntimeError("sem placa de som")), \
             patch.object(voice, "TTS_ONLINE_DISPONIVEL", True), \
             patch.object(voice, "_falar_online_pt_br", side_effect=OSError("sem internet")), \
             patch.object(voice, "_aviso_falha_audio_mostrado", False):
            voice.falar("teste")  # não deve levantar exceção

    def test_sem_stt_cai_para_modo_texto(self):
        with patch.object(main, "STT_DISPONIVEL", False), \
             patch.object(main, "rodar_modo_texto") as modo_texto_mock:
            main.rodar_interativo(usar_voz=True)
        modo_texto_mock.assert_called_once()

    def test_sem_microfone_cai_para_modo_texto(self):
        erro = main.ErroReconhecimento("Não encontrei um microfone disponível.")
        with patch.object(main, "STT_DISPONIVEL", True), \
             patch.object(main, "OuvidorContinuo", side_effect=erro), \
             patch.object(main, "rodar_modo_texto") as modo_texto_mock:
            main.rodar_interativo(usar_voz=True)
        modo_texto_mock.assert_called_once()


class TestDiagnostico(unittest.TestCase):
    def test_relatorio_sempre_gera_texto(self):
        relatorio = voice.diagnosticar()
        self.assertIn("Diagnóstico de voz", relatorio)

    def test_relatorio_avisa_quando_nada_esta_disponivel(self):
        with patch.object(voice, "STT_DISPONIVEL", False), \
             patch.object(voice, "TTS_LOCAL_DISPONIVEL", False), \
             patch.object(voice, "TTS_ONLINE_DISPONIVEL", False):
            relatorio = voice.diagnosticar()
        self.assertIn("indisponíveis", relatorio)
        self.assertIn("--texto", relatorio)


if __name__ == "__main__":
    unittest.main()
