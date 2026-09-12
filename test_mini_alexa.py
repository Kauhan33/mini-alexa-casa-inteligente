"""Testes automatizados do Mini-Alexa de Casa Inteligente.

Rodar com:  python -m unittest test_mini_alexa.py -v
"""

import unittest

from lexer import TipoToken, analisar_lexico
from semantic import CasaInteligente, interpretar


class TestLexer(unittest.TestCase):
    def test_reconhece_acao_dispositivo_local(self):
        tokens = analisar_lexico("Ligar a luz da sala")
        tipos = [t.tipo for t in tokens]
        self.assertIn(TipoToken.ACAO, tipos)
        self.assertIn(TipoToken.DISPOSITIVO, tipos)
        self.assertIn(TipoToken.LOCAL, tipos)

    def test_reconhece_dispositivo_composto(self):
        tokens = analisar_lexico("Ligar o ar condicionado do quarto")
        dispositivos = [t.valor for t in tokens if t.tipo == TipoToken.DISPOSITIVO]
        self.assertEqual(dispositivos, ["ar_condicionado"])

    def test_reconhece_valor_numerico(self):
        tokens = analisar_lexico("Aumentar o ventilador da sala para 60")
        valores = [t.valor for t in tokens if t.tipo == TipoToken.VALOR]
        self.assertEqual(valores, ["60"])

    def test_palavra_desconhecida(self):
        tokens = analisar_lexico("Ligar o forno")
        desconhecidos = [t.lexema for t in tokens if t.tipo == TipoToken.DESCONHECIDO]
        self.assertIn("forno", desconhecidos)


class TestSemantic(unittest.TestCase):
    def setUp(self) -> None:
        self.casa = CasaInteligente()

    def test_comando_valido_liga_dispositivo(self):
        resposta = interpretar(analisar_lexico("Ligar a luz da sala"), self.casa)
        self.assertIn("ligando", resposta.lower())
        self.assertTrue(self.casa.obter("luz", "sala").ligado)

    def test_acao_incompativel_com_dispositivo(self):
        resposta = interpretar(analisar_lexico("Abrir a luz da sala"), self.casa)
        self.assertIn("não é possível", resposta.lower())

    def test_falta_dispositivo(self):
        resposta = interpretar(analisar_lexico("Ligar"), self.casa)
        self.assertIn("dispositivo", resposta.lower())

    def test_falta_acao(self):
        resposta = interpretar(analisar_lexico("a luz da sala"), self.casa)
        self.assertIn("ação", resposta.lower())

    def test_aumentar_altera_nivel(self):
        interpretar(analisar_lexico("Aumentar o ventilador da sala para 60"), self.casa)
        self.assertEqual(self.casa.obter("ventilador", "sala").nivel, 60)


if __name__ == "__main__":
    unittest.main()
