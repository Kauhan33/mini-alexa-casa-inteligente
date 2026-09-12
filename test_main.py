"""Testes do fluxo de interação em main.py: o modo de voz (microfone e
fala mockados, sem depender de hardware real) e o modo texto.

Rodar com:  python -m unittest test_main.py -v
"""

import unittest
from unittest.mock import MagicMock, patch

import main
from semantic import CasaInteligente


def _ouvidor_falso(falas):
    """Cria um OuvidorContinuo falso cujo .ouvir() devolve, em sequência,
    cada item de `falas` (sem precisar de microfone real)."""
    falas_iter = iter(falas)
    ouvidor = MagicMock()
    ouvidor.ouvir.side_effect = lambda *a, **k: next(falas_iter)
    return ouvidor


class TestModoVoz(unittest.TestCase):
    def test_ignora_falas_sem_palavra_chave_e_processa_as_que_tem(self):
        casa = CasaInteligente()
        ouvidor = _ouvidor_falso([
            "agora tá funcionando",        # sem palavra-chave: deve ser ignorada
            "Alexa ligar a luz da sala",   # sem vírgula: deve funcionar
            "Alexa sair",
        ])

        with patch("main.falar", lambda *_: None):
            with self.assertRaises(SystemExit):
                main.rodar_modo_voz(casa, ouvidor)

        # só o comando com a palavra-chave deve ter sido executado
        self.assertTrue(casa.obter("luz", "sala").ligado)

    def test_aceita_variacoes_do_nome_mal_transcrito(self):
        casa = CasaInteligente()
        ouvidor = _ouvidor_falso([
            "Alexia ligar a luz do quarto",  # variação vista em uso real
            "Alex eu sair",                  # nome quebrado em duas palavras
        ])

        with patch("main.falar", lambda *_: None):
            with self.assertRaises(SystemExit):
                main.rodar_modo_voz(casa, ouvidor)

        self.assertTrue(casa.obter("luz", "quarto").ligado)

    def test_alexa_sozinha_nao_encerra_o_programa(self):
        casa = CasaInteligente()
        ouvidor = _ouvidor_falso(["Alexa", "Alexa sair"])

        with patch("main.falar", lambda *_: None):
            with self.assertRaises(SystemExit):
                main.rodar_modo_voz(casa, ouvidor)


class TestModoTexto(unittest.TestCase):
    def test_comando_digitado_nao_precisa_de_palavra_chave(self):
        casa = CasaInteligente()
        entradas = iter(["ligar a luz da sala", "sair"])

        with patch("builtins.input", lambda *_: next(entradas)), \
             patch("main.falar", lambda *_: None):
            main.rodar_modo_texto(casa)

        self.assertTrue(casa.obter("luz", "sala").ligado)


class TestFallbackSemMicrofone(unittest.TestCase):
    def test_cai_para_modo_texto_se_microfone_falhar(self):
        """Se o microfone não inicializar, o programa não deve quebrar:
        segue funcionando só com o teclado."""
        erro = main.ErroReconhecimento("Não encontrei um microfone disponível.")

        with patch("main.STT_DISPONIVEL", True), \
             patch("main.OuvidorContinuo", side_effect=erro), \
             patch("main.rodar_modo_texto") as modo_texto_mock:
            main.rodar_interativo(usar_voz=True)

        modo_texto_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
