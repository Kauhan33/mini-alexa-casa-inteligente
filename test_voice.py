"""Testes automatizados do módulo de voz.

Não dependem de microfone real: cobrem apenas o comportamento de erro
quando a biblioteca de reconhecimento não está disponível, e a integração
com o pipeline de texto (lexer/semantic) usando uma transcrição simulada.

Rodar com:  python -m unittest test_voice.py -v
"""

import unittest
from unittest.mock import patch

import voice
from lexer import analisar_lexico
from semantic import CasaInteligente, interpretar


class TestVoice(unittest.TestCase):
    def test_erro_quando_biblioteca_nao_instalada(self):
        with patch.object(voice, "STT_DISPONIVEL", False):
            with self.assertRaises(voice.ErroReconhecimento):
                voice.ouvir_comando()

    def test_falar_nao_faz_nada_se_tts_indisponivel(self):
        """falar() nunca deve lançar exceção, mesmo sem TTS disponível —
        é um recurso best-effort."""
        with patch.object(voice, "TTS_DISPONIVEL", False):
            voice.falar("qualquer coisa")  # não deve levantar erro

    def test_falar_com_texto_vazio_nao_chama_motor(self):
        with patch.object(voice, "_obter_motor_tts") as motor_mock:
            voice.falar("")
            motor_mock.assert_not_called()

    def test_transcricao_simulada_segue_o_mesmo_pipeline_do_texto(self):
        """A voz não deve ter um caminho de interpretação separado: uma vez
        transcrita, a frase passa pelo mesmo lexer/semantic do modo texto."""
        casa = CasaInteligente()
        frase_transcrita = "ligar a luz da sala"  # como viria do reconhecedor
        resposta = interpretar(analisar_lexico(frase_transcrita), casa)
        self.assertIn("ligando", resposta.lower())


if __name__ == "__main__":
    unittest.main()
