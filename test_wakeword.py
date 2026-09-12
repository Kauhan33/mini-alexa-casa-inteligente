"""Testes da detecção da palavra-chave.

Os casos marcados como "(log real)" vieram de uma sessão real de uso, em
que o reconhecimento de fala transcreveu o nome da assistente errado.

Rodar com:  python -m unittest test_wakeword.py -v
"""

import unittest

from wakeword import extrair_comando, parece_palavra_chave


class TestVariacoesDaPalavraChave(unittest.TestCase):
    def test_nome_correto(self):
        self.assertEqual(
            extrair_comando("Alexa ligar a luz da sala"), "ligar a luz da sala"
        )

    def test_com_virgula(self):
        self.assertEqual(
            extrair_comando("Alexa, ligar a luz da sala"), "ligar a luz da sala"
        )

    def test_alexia_log_real(self):
        self.assertEqual(
            extrair_comando("Alexia Desligar a luz do quarto"), "Desligar a luz do quarto"
        )

    def test_alexia_sair_log_real(self):
        self.assertEqual(extrair_comando("Alexia sair"), "sair")

    def test_nome_quebrado_em_duas_palavras_log_real(self):
        """"Alex eu sair" deve virar "sair": o "eu" é resto do nome mal
        transcrito, não parte do comando."""
        self.assertEqual(extrair_comando("Alex eu sair"), "sair")

    def test_outras_variacoes(self):
        for frase in ("Alex ligar a luz", "Alexis ligar a luz", "Lexa ligar a luz"):
            with self.subTest(frase=frase):
                self.assertEqual(extrair_comando(frase), "ligar a luz")

    def test_maiusculas_e_acentos_nao_importam(self):
        self.assertEqual(extrair_comando("ALEXA ligar a luz"), "ligar a luz")


class TestFalasIgnoradas(unittest.TestCase):
    def test_fala_comum_sem_palavra_chave(self):
        for frase in ("ligar a luz da sala", "legal", "agora tá funcionando", "isso aí"):
            with self.subTest(frase=frase):
                self.assertIsNone(extrair_comando(frase))

    def test_frase_vazia(self):
        self.assertIsNone(extrair_comando(""))
        self.assertIsNone(extrair_comando("   "))

    def test_palavras_comuns_nao_sao_confundidas_com_o_nome(self):
        for palavra in ("legal", "agora", "ligar", "desligar", "abrir", "sair"):
            with self.subTest(palavra=palavra):
                self.assertFalse(parece_palavra_chave(palavra))


class TestCasosDeBorda(unittest.TestCase):
    def test_apenas_o_nome_devolve_comando_vazio(self):
        self.assertEqual(extrair_comando("Alexa"), "")

    def test_nao_engole_dispositivo_curto_apos_o_nome(self):
        """"tv" é curto, mas significa algo no vocabulário — não pode ser
        confundido com resto de uma transcrição errada do nome."""
        self.assertEqual(extrair_comando("Alexa tv"), "tv")
        self.assertEqual(extrair_comando("Alexa ligar a tv"), "ligar a tv")

    def test_nao_engole_o_comando_sair(self):
        self.assertEqual(extrair_comando("Alexa sair"), "sair")


if __name__ == "__main__":
    unittest.main()
