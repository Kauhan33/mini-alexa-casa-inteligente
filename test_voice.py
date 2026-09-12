"""Testes automatizados do módulo de voz.

Não dependem de microfone, alto-falante nem internet: cobrem o
comportamento de erro, a ordem de preferência entre os motores de síntese
e a integração com o pipeline de texto, sempre com as bibliotecas externas
substituídas por dublês.

Rodar com:  python -m unittest test_voice.py -v
"""

import unittest
from unittest.mock import MagicMock, patch

import voice
from lexer import analisar_lexico
from semantic import CasaInteligente, interpretar


class TestReconhecimento(unittest.TestCase):
    def test_erro_quando_biblioteca_nao_instalada(self):
        with patch.object(voice, "STT_DISPONIVEL", False):
            with self.assertRaises(voice.ErroReconhecimento):
                voice.ouvir_comando()

    def test_ouvidor_continuo_exige_biblioteca(self):
        with patch.object(voice, "STT_DISPONIVEL", False):
            with self.assertRaises(voice.ErroReconhecimento):
                voice.OuvidorContinuo()

    def test_transcricao_simulada_segue_o_mesmo_pipeline_do_texto(self):
        """A voz não deve ter um caminho de interpretação separado: uma vez
        transcrita, a frase passa pelo mesmo lexer/semantic do modo texto."""
        casa = CasaInteligente()
        frase_transcrita = "ligar a luz da sala"  # como viria do reconhecedor
        resposta = interpretar(analisar_lexico(frase_transcrita), casa)
        self.assertIn("ligando", resposta.lower())


class TestSintese(unittest.TestCase):
    def test_texto_vazio_nao_chama_nenhum_motor(self):
        with patch.object(voice, "_falar_local") as local_mock, \
             patch.object(voice, "_falar_online_pt_br") as online_mock:
            voice.falar("")
            local_mock.assert_not_called()
            online_mock.assert_not_called()

    def test_prefere_voz_local_em_portugues(self):
        with patch.object(voice, "TTS_LOCAL_DISPONIVEL", True), \
             patch.object(voice, "_falar_local", return_value=True) as local_mock, \
             patch.object(voice, "TTS_ONLINE_DISPONIVEL", True), \
             patch.object(voice, "_falar_online_pt_br") as online_mock:
            voice.falar("teste")
            local_mock.assert_called_once_with("teste", exigir_portugues=True)
            online_mock.assert_not_called()

    def test_usa_gtts_quando_nao_ha_voz_local_em_portugues(self):
        """Sem voz pt instalada, _falar_local devolve False e a síntese deve
        cair para o gTTS — que garante pt-BR em qualquer máquina."""
        with patch.object(voice, "TTS_LOCAL_DISPONIVEL", True), \
             patch.object(voice, "_falar_local", return_value=False), \
             patch.object(voice, "TTS_ONLINE_DISPONIVEL", True), \
             patch.object(voice, "_falar_online_pt_br") as online_mock, \
             patch.object(voice, "_aviso_sem_voz_pt_mostrado", True):
            voice.falar("teste")
            online_mock.assert_called_once_with("teste")

    def test_ultimo_recurso_e_qualquer_voz_local(self):
        """Sem voz pt e sem gTTS, falar em outro idioma é melhor que silêncio."""
        chamadas = []

        def falar_local_falso(texto, exigir_portugues=True):
            chamadas.append(exigir_portugues)
            return not exigir_portugues  # só consegue falar sem exigir português

        with patch.object(voice, "TTS_LOCAL_DISPONIVEL", True), \
             patch.object(voice, "_falar_local", side_effect=falar_local_falso), \
             patch.object(voice, "TTS_ONLINE_DISPONIVEL", False), \
             patch.object(voice, "_aviso_sem_voz_pt_mostrado", True):
            voice.falar("teste")

        self.assertEqual(chamadas, [True, False])

    def test_falha_de_audio_nunca_derruba_o_programa(self):
        with patch.object(voice, "TTS_LOCAL_DISPONIVEL", True), \
             patch.object(voice, "_falar_local", side_effect=RuntimeError("sem áudio")), \
             patch.object(voice, "TTS_ONLINE_DISPONIVEL", True), \
             patch.object(voice, "_falar_online_pt_br", side_effect=OSError("offline")), \
             patch.object(voice, "_aviso_falha_audio_mostrado", False):
            voice.falar("teste")  # não deve levantar exceção


class TestMotorNovoPorFala(unittest.TestCase):
    """Regressão do bug em que só a primeira resposta era falada: o motor
    pyttsx3 era reaproveitado e, depois do primeiro runAndWait(), as
    chamadas seguintes retornavam sem produzir som."""

    def test_cada_fala_inicializa_um_motor_novo(self):
        motores = []

        def init_falso(*_a, **_k):
            motor = MagicMock()
            motor.getProperty.return_value = []  # nenhuma voz instalada
            motores.append(motor)
            return motor

        with patch.object(voice, "pyttsx3", MagicMock(init=init_falso)):
            voice._falar_local("primeira", exigir_portugues=False)
            voice._falar_local("segunda", exigir_portugues=False)
            voice._falar_local("terceira", exigir_portugues=False)

        self.assertEqual(len(motores), 3, "cada fala deve criar seu próprio motor")
        for motor in motores:
            motor.say.assert_called_once()
            motor.runAndWait.assert_called_once()

    def test_nao_fala_em_outro_idioma_quando_exige_portugues(self):
        motor = MagicMock()
        motor.getProperty.return_value = []  # nenhuma voz pt disponível

        with patch.object(voice, "pyttsx3", MagicMock(init=lambda *a, **k: motor)):
            falou = voice._falar_local("teste", exigir_portugues=True)

        self.assertFalse(falou)
        motor.say.assert_not_called()


if __name__ == "__main__":
    unittest.main()
