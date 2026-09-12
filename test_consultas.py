"""Testes dos comandos de consulta: "estado da casa" e "comandos".

São ações que respondem sobre a casa (ou sobre o próprio programa) e, ao
contrário das demais, não exigem um dispositivo na frase.

Rodar com:  python -m unittest test_consultas.py -v
"""

import unittest

from lexer import TipoToken, analisar_lexico
from semantic import (
    AJUDA_FALADA,
    CasaInteligente,
    interpretar,
    montar_ajuda,
    texto_para_audio,
)


class TestLexicoDasConsultas(unittest.TestCase):
    def test_estado_e_reconhecido_como_acao(self):
        tokens = analisar_lexico("estado da casa")
        acoes = [t.valor for t in tokens if t.tipo == TipoToken.ACAO]
        self.assertEqual(acoes, ["ESTADO"])

    def test_comandos_e_reconhecido_como_acao(self):
        for frase in ("comandos", "ajuda", "help", "lista de comandos"):
            with self.subTest(frase=frase):
                tokens = analisar_lexico(frase)
                acoes = [t.valor for t in tokens if t.tipo == TipoToken.ACAO]
                self.assertEqual(acoes, ["AJUDA"])

    def test_palavras_de_apoio_nao_viram_desconhecidas(self):
        """"casa", "lista", "qual"... acompanham as consultas sem significado
        próprio — não devem gerar o aviso de palavra não reconhecida."""
        for frase in ("estado da casa", "qual o estado da casa", "me diga o estado"):
            with self.subTest(frase=frase):
                tokens = analisar_lexico(frase)
                desconhecidos = [t.lexema for t in tokens if t.tipo == TipoToken.DESCONHECIDO]
                self.assertEqual(desconhecidos, [])


class TestEstadoDaCasa(unittest.TestCase):
    def setUp(self) -> None:
        self.casa = CasaInteligente()

    def _dizer(self, frase: str) -> str:
        return interpretar(analisar_lexico(frase), self.casa)

    def test_casa_sem_nada_ligado(self):
        self.assertEqual(
            self._dizer("estado da casa"),
            "Nenhum dispositivo está ligado ou aberto no momento.",
        )

    def test_lista_apenas_o_que_esta_ativo(self):
        self._dizer("ligar a luz do quarto")
        self._dizer("ligar a luz da cozinha")
        self._dizer("desligar a luz da cozinha")

        resposta = self._dizer("estado da casa")
        self.assertIn("a luz do quarto está acesa", resposta)
        self.assertNotIn("cozinha", resposta)

    def test_inclui_nivel_quando_houver(self):
        self._dizer("aumentar o ventilador da sala para 60")
        self.assertIn("o ventilador da sala está ligado, em 60", self._dizer("estado da casa"))

    def test_usa_o_participio_certo_de_cada_dispositivo(self):
        self._dizer("abrir a porta da garagem")
        self._dizer("ligar o alarme")

        resposta = self._dizer("estado da casa")
        self.assertIn("a porta da garagem está aberta", resposta)
        self.assertIn("o alarme está ativado", resposta)

    def test_consulta_nao_altera_o_estado(self):
        self._dizer("ligar a luz da sala")
        self._dizer("estado da casa")
        # continuar acesa: a consulta não deve mexer em nada
        self.assertEqual(self._dizer("ligar a luz da sala"), "A luz da sala já está acesa.")

    def test_variacoes_da_frase(self):
        self._dizer("ligar a luz da sala")
        for frase in ("estado da casa", "status da casa", "qual o estado", "situacao da casa"):
            with self.subTest(frase=frase):
                self.assertIn("No momento", self._dizer(frase))


class TestListaDeComandos(unittest.TestCase):
    def setUp(self) -> None:
        self.casa = CasaInteligente()
        self.ajuda = interpretar(analisar_lexico("comandos"), self.casa)

    def test_responde_com_a_lista(self):
        self.assertEqual(self.ajuda, montar_ajuda())
        self.assertTrue(self.ajuda.startswith("Comandos disponíveis:"))

    def test_lista_todas_as_acoes_do_vocabulario(self):
        for verbo in ("ligar", "desligar", "abrir", "fechar", "aumentar", "diminuir"):
            with self.subTest(verbo=verbo):
                self.assertIn(verbo, self.ajuda)

    def test_lista_todos_os_dispositivos(self):
        for dispositivo in ("luz", "ventilador", "ar-condicionado", "tv", "porta", "cortina"):
            with self.subTest(dispositivo=dispositivo):
                self.assertIn(dispositivo, self.ajuda)

    def test_lista_locais_acentuados(self):
        self.assertIn("escritório", self.ajuda)
        self.assertNotIn("escritorio", self.ajuda)

    def test_menciona_as_consultas_e_a_saida(self):
        self.assertIn("estado", self.ajuda)
        self.assertIn("sair", self.ajuda)

    def test_acao_principal_vem_antes_dos_sinonimos(self):
        self.assertIn("ligar/acender", self.ajuda)
        self.assertIn("desligar/apagar", self.ajuda)

    def test_audio_da_ajuda_e_resumido(self):
        """Ler a lista inteira em voz alta seria interminável: o áudio recebe
        um resumo, e a tela fica com a lista completa."""
        self.assertEqual(texto_para_audio(self.ajuda), AJUDA_FALADA)
        self.assertLess(len(AJUDA_FALADA), len(self.ajuda))

    def test_outras_respostas_sao_faladas_na_integra(self):
        resposta = interpretar(analisar_lexico("ligar a luz da sala"), self.casa)
        self.assertEqual(texto_para_audio(resposta), resposta)


if __name__ == "__main__":
    unittest.main()
