"""Testes do fluxo de interação em main.py: extração da palavra-chave
("Alexa, ...") e o modo de voz contínuo (com microfone e fala mockados,
sem depender de hardware real).

Rodar com:  python -m unittest test_main.py -v
"""

import unittest
from unittest.mock import patch

import main
from semantic import CasaInteligente


class TestPalavraChave(unittest.TestCase):
    def test_frase_com_palavra_chave_extrai_o_comando(self):
        self.assertEqual(
            main._extrair_comando_apos_palavra_chave("Alexa, ligar a luz da sala"),
            "ligar a luz da sala",
        )

    def test_e_insensivel_a_maiusculas_e_acentos(self):
        self.assertEqual(
            main._extrair_comando_apos_palavra_chave("ALEXA ligar a luz"),
            "ligar a luz",
        )

    def test_frase_sem_palavra_chave_retorna_none(self):
        self.assertIsNone(main._extrair_comando_apos_palavra_chave("ligar a luz da sala"))

    def test_apenas_a_palavra_chave_retorna_string_vazia(self):
        self.assertEqual(main._extrair_comando_apos_palavra_chave("Alexa"), "")

    def test_frase_vazia_retorna_none(self):
        self.assertIsNone(main._extrair_comando_apos_palavra_chave(""))


class TestModoVozContinuo(unittest.TestCase):
    def test_ignora_falas_sem_palavra_chave_e_processa_as_que_tem(self):
        casa = CasaInteligente()
        falas = iter([
            "isso e so uma conversa qualquer no fundo",  # sem "alexa": deve ser ignorada
            "Alexa, ligar a luz da sala",
            "Alexa, sair",
        ])

        with patch("main.ouvir_comando", side_effect=lambda *a, **k: next(falas)), \
             patch("main.falar", lambda *_: None):
            with self.assertRaises(SystemExit):
                main.rodar_modo_voz_continuo(casa)

        # só o comando com a palavra-chave deve ter sido executado
        self.assertTrue(casa.obter("luz", "sala").ligado)

    def test_alexa_sozinha_nao_encerra_o_programa(self):
        casa = CasaInteligente()
        falas = iter(["Alexa", "Alexa, sair"])

        with patch("main.ouvir_comando", side_effect=lambda *a, **k: next(falas)), \
             patch("main.falar", lambda *_: None):
            with self.assertRaises(SystemExit):
                main.rodar_modo_voz_continuo(casa)


if __name__ == "__main__":
    unittest.main()
