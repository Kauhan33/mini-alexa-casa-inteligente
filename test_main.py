"""Testes do fluxo de interação em main.py: o modo de voz (microfone e
fala mockados, sem depender de hardware real) e o modo texto.

Rodar com:  python -m unittest test_main.py -v
"""

import io
import threading
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


class TestAudioSomenteParaVoz(unittest.TestCase):
    """Áudio é só para comandos falados: quem digitou está olhando a tela."""

    def test_comando_falado_responde_em_audio(self):
        casa = CasaInteligente()
        ouvidor = _ouvidor_falso(["Alexa ligar a luz da sala", "Alexa sair"])
        falas = []

        with patch("main.falar", falas.append):
            with self.assertRaises(SystemExit):
                main.rodar_modo_voz(casa, ouvidor)

        self.assertIn("Ok, ligando a luz da sala.", falas)

    def test_comando_digitado_nao_responde_em_audio(self):
        casa = CasaInteligente()
        entradas = iter(["ligar a luz da sala", "sair"])
        falas = []

        with patch("builtins.input", lambda *_: next(entradas)), \
             patch("main.falar", falas.append):
            main._thread_teclado(threading.Event(), casa, threading.Lock())

        self.assertEqual(falas, [])
        self.assertTrue(casa.obter("luz", "sala").ligado)

    def test_modo_texto_nunca_fala(self):
        casa = CasaInteligente()
        entradas = iter(["ligar a luz da sala", "sair"])
        falas = []

        with patch("builtins.input", lambda *_: next(entradas)), \
             patch("main.falar", falas.append):
            main.rodar_modo_texto(casa)

        self.assertEqual(falas, [])


class TestAvisoDeOuvindo(unittest.TestCase):
    """O aviso de "ouvindo" precisa reaparecer depois de cada resposta: é o
    sinal de que o microfone voltou a captar (durante a fala da resposta,
    nada é ouvido)."""

    def _capturar_saida(self, ouvidor):
        casa = CasaInteligente()
        with patch("main.falar", lambda *_: None), \
             patch("sys.stdout", new=io.StringIO()) as saida:
            with self.assertRaises(SystemExit):
                main.rodar_modo_voz(casa, ouvidor)
        return saida.getvalue()

    def test_avisa_ouvindo_apos_cada_resposta(self):
        ouvidor = _ouvidor_falso([
            "Alexa ligar a luz da sala",
            "Alexa ligar a luz do quarto",
            "Alexa sair",
        ])
        saida = self._capturar_saida(ouvidor)
        # uma vez na abertura + uma depois de cada um dos dois comandos
        self.assertEqual(saida.count(main.AVISO_OUVINDO), 3)

    def test_avisa_ouvindo_apos_fala_ignorada(self):
        ouvidor = _ouvidor_falso(["conversa qualquer no fundo", "Alexa sair"])
        saida = self._capturar_saida(ouvidor)
        self.assertEqual(saida.count(main.AVISO_OUVINDO), 2)

    def test_silencio_nao_repete_o_aviso(self):
        """Timeout sem ninguém falar não deve poluir a tela: o aviso
        anterior continua valendo."""
        erro = main.ErroReconhecimento("Ninguém falou a tempo.")
        respostas = [erro, erro, erro, "Alexa sair"]
        respostas_iter = iter(respostas)

        def ouvir(*_a, **_k):
            valor = next(respostas_iter)
            if isinstance(valor, Exception):
                raise valor
            return valor

        ouvidor = MagicMock()
        ouvidor.ouvir.side_effect = ouvir

        saida = self._capturar_saida(ouvidor)
        self.assertEqual(saida.count(main.AVISO_OUVINDO), 1)

    def test_avisa_quando_nao_conseguiu_transcrever(self):
        erro = main.ErroReconhecimento("Não consegui entender o que foi falado.")
        respostas_iter = iter([erro, "Alexa sair"])

        def ouvir(*_a, **_k):
            valor = next(respostas_iter)
            if isinstance(valor, Exception):
                raise valor
            return valor

        ouvidor = MagicMock()
        ouvidor.ouvir.side_effect = ouvir

        saida = self._capturar_saida(ouvidor)
        self.assertIn("não entendi o que foi falado", saida)
        self.assertEqual(saida.count(main.AVISO_OUVINDO), 2)

    def test_estado_inicial_e_informado_na_abertura(self):
        ouvidor = _ouvidor_falso(["Alexa sair"])
        saida = self._capturar_saida(ouvidor)
        self.assertIn(main.AVISO_ESTADO_INICIAL, saida)


class TestTecladoSemStdin(unittest.TestCase):
    """Regressão: stdin não interativo (entrada redirecionada) fazia o
    input() estourar EOFError na hora, e isso encerrava o modo de voz —
    deve apenas parar a leitura de teclado, mantendo a escuta ativa."""

    def test_eof_no_teclado_nao_encerra_o_modo_voz(self):
        parar = threading.Event()

        def input_com_eof(*_a):
            raise EOFError

        with patch("builtins.input", input_com_eof):
            main._thread_teclado(parar, CasaInteligente(), threading.Lock())

        self.assertFalse(parar.is_set(), "EOF no teclado não deve pedir para sair")

    def test_ctrl_c_no_teclado_encerra(self):
        parar = threading.Event()

        def input_com_interrupcao(*_a):
            raise KeyboardInterrupt

        with patch("builtins.input", input_com_interrupcao):
            main._thread_teclado(parar, CasaInteligente(), threading.Lock())

        self.assertTrue(parar.is_set())


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
