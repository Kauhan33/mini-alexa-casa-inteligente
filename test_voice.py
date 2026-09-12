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

    def test_falar_nao_faz_nada_se_nenhum_tts_disponivel(self):
        """falar() nunca deve lançar exceção, mesmo sem nenhum motor de TTS
        disponível (nem local, nem online) — é um recurso best-effort."""
        with patch.object(voice, "TTS_LOCAL_DISPONIVEL", False), \
             patch.object(voice, "TTS_ONLINE_DISPONIVEL", False):
            voice.falar("qualquer coisa")  # não deve levantar erro

    def test_falar_com_texto_vazio_nao_chama_nenhum_motor(self):
        with patch.object(voice, "_obter_motor_tts_local") as motor_local_mock, \
             patch.object(voice, "_falar_online_pt_br") as online_mock:
            voice.falar("")
            motor_local_mock.assert_not_called()
            online_mock.assert_not_called()

    def test_falar_usa_gtts_quando_nao_ha_voz_local_em_portugues(self):
        """Se o motor local existe mas nenhuma voz em português foi
        encontrada, falar() deve cair para o gTTS (garante pt-BR)."""
        with patch.object(voice, "TTS_LOCAL_DISPONIVEL", True), \
             patch.object(voice, "_obter_motor_tts_local", return_value=(None, False)), \
             patch.object(voice, "TTS_ONLINE_DISPONIVEL", True), \
             patch.object(voice, "_falar_online_pt_br") as online_mock:
            voice.falar("teste")
            online_mock.assert_called_once_with("teste")

    def test_transcricao_simulada_segue_o_mesmo_pipeline_do_texto(self):
        """A voz não deve ter um caminho de interpretação separado: uma vez
        transcrita, a frase passa pelo mesmo lexer/semantic do modo texto."""
        casa = CasaInteligente()
        frase_transcrita = "ligar a luz da sala"  # como viria do reconhecedor
        resposta = interpretar(analisar_lexico(frase_transcrita), casa)
        self.assertIn("ligando", resposta.lower())


if __name__ == "__main__":
    unittest.main()
