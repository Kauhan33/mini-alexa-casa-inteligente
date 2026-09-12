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


class TestEstadoJaAplicado(unittest.TestCase):
    """Ações redundantes devem informar o estado atual, não fingir que
    executaram — é análise semântica dependente de contexto."""

    def setUp(self) -> None:
        self.casa = CasaInteligente()

    def _dizer(self, frase: str) -> str:
        return interpretar(analisar_lexico(frase), self.casa)

    def test_ligar_luz_ja_acesa(self):
        primeira = self._dizer("ligar a luz do quarto")
        self.assertIn("ligando", primeira.lower())

        segunda = self._dizer("ligar a luz do quarto")
        self.assertEqual(segunda, "A luz do quarto já está acesa.")

    def test_desligar_luz_ja_apagada(self):
        resposta = self._dizer("desligar a luz do quarto")
        self.assertEqual(resposta, "A luz do quarto já está apagada.")

    def test_ciclo_completo_liga_desliga(self):
        self.assertIn("ligando", self._dizer("ligar a luz da sala").lower())
        self.assertEqual(self._dizer("ligar a luz da sala"), "A luz da sala já está acesa.")
        self.assertIn("desligando", self._dizer("desligar a luz da sala").lower())
        self.assertEqual(self._dizer("desligar a luz da sala"), "A luz da sala já está apagada.")

    def test_concordancia_de_genero_e_participio_por_dispositivo(self):
        self._dizer("abrir a porta da garagem")
        self.assertEqual(
            self._dizer("abrir a porta da garagem"), "A porta da garagem já está aberta."
        )

        self._dizer("ligar o ventilador da sala")
        self.assertEqual(
            self._dizer("ligar o ventilador da sala"), "O ventilador da sala já está ligado."
        )

        self.assertEqual(self._dizer("fechar o portao"), "O portão já está fechado.")

    def test_locais_diferentes_tem_estados_independentes(self):
        self._dizer("ligar a luz da sala")
        # a luz do quarto continua apagada, então ligar deve executar
        self.assertIn("ligando", self._dizer("ligar a luz do quarto").lower())

    def test_ligar_um_local_nao_afeta_outro(self):
        """Ligar a luz do quarto não pode fazer a cozinha se considerar
        acesa — cada (dispositivo, local) tem seu próprio estado."""
        self._dizer("ligar a luz do quarto")

        resposta = self._dizer("ligar a luz da cozinha")
        self.assertIn("ligando", resposta.lower())
        self.assertNotIn("já está", resposta)

    def test_desligar_um_local_nao_afeta_outro(self):
        self._dizer("ligar a luz do quarto")
        self._dizer("ligar a luz da cozinha")
        self._dizer("desligar a luz do quarto")

        # a cozinha segue acesa, então desligar deve executar de verdade
        resposta = self._dizer("desligar a luz da cozinha")
        self.assertIn("desligando", resposta.lower())

    def test_sequencia_completa_de_uso_real(self):
        """Reproduz uma sessão real que levantou a suspeita de conflito
        entre locais. Todas as respostas abaixo são as corretas: um
        dispositivo nunca acionado começa desligado, então mandar desligá-lo
        informa que já está apagado — sem relação com os outros locais."""
        esperado = [
            ("ligar a luz do quarto", "Ok, ligando a luz do quarto."),
            ("ligar a luz do quarto", "A luz do quarto já está acesa."),
            ("desligar a luz do quarto", "Ok, desligando a luz do quarto."),
            ("desligar a luz do quarto", "A luz do quarto já está apagada."),
            # banheiro e cozinha nunca foram ligados: começam apagados
            ("desligar a luz do banheiro", "A luz do banheiro já está apagada."),
            ("desligar a luz da cozinha", "A luz da cozinha já está apagada."),
            ("ligar a luz da cozinha", "Ok, ligando a luz da cozinha."),
            ("desligar a luz da cozinha", "Ok, desligando a luz da cozinha."),
            ("ligar a luz do quarto", "Ok, ligando a luz do quarto."),
        ]
        for frase, resposta_esperada in esperado:
            with self.subTest(frase=frase):
                self.assertEqual(self._dizer(frase), resposta_esperada)

    def test_nivel_no_maximo_e_no_minimo(self):
        self._dizer("aumentar o ventilador da sala para 100")
        self.assertEqual(
            self._dizer("aumentar o ventilador da sala"), "O ventilador da sala já está no máximo."
        )

        self._dizer("diminuir o ventilador do quarto")
        self.assertEqual(
            self._dizer("diminuir o ventilador do quarto"),
            "O ventilador do quarto já está no mínimo.",
        )

    def test_aumentar_para_nivel_menor_que_o_atual(self):
        self._dizer("aumentar a tv para 80")
        self.assertEqual(self._dizer("aumentar a tv para 50"), "A tv já está em 80.")


if __name__ == "__main__":
    unittest.main()
