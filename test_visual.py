"""Testes da parte visual.

Divididos em dois grupos:

- `visual.py` não importa tkinter, então seus cálculos (nível do áudio,
  geometria das barras, rotação, geração do círculo suavizado) são testados
  sempre, sem precisar de tela;
- os testes da janela em si são pulados automaticamente onde não há
  tkinter ou display disponível (a janela é opcional; o resto do programa
  não depende dela).

Rodar com:  python -m unittest test_visual.py -v
"""

import unittest
from unittest.mock import patch

from visual import (
    REFERENCIA_MINIMA,
    AnimacaoCircular,
    MedidorDeNivel,
    gerar_disco_ppm,
    misturar_cores,
)

try:
    import tkinter as tk

    _raiz_teste = tk.Tk()
    _raiz_teste.destroy()
    TEM_JANELA = True
except Exception:  # sem tkinter ou sem display
    TEM_JANELA = False


class TestMedidorDeNivel(unittest.TestCase):
    def test_comeca_em_silencio(self):
        medidor = MedidorDeNivel()
        self.assertEqual(medidor.nivel_atual(), 0.0)
        self.assertTrue(medidor.em_silencio())

    def test_volume_alto_gera_nivel_alto(self):
        medidor = MedidorDeNivel()
        medidor.registrar(REFERENCIA_MINIMA * 4)
        self.assertGreater(medidor.nivel_atual(), 0.9)
        self.assertFalse(medidor.em_silencio())

    def test_nivel_fica_entre_zero_e_um(self):
        medidor = MedidorDeNivel()
        for volume in (0, 10, 500, 5_000, 100_000):
            medidor.registrar(volume)
            self.assertGreaterEqual(medidor.nivel_atual(), 0.0)
            self.assertLessEqual(medidor.nivel_atual(), 1.0)

    def test_ruido_de_fundo_nao_enche_as_barras(self):
        """Sem um piso de referência, o silêncio (ruído baixíssimo) seria
        normalizado para o máximo e as barras viveriam agitadas."""
        medidor = MedidorDeNivel()
        for _ in range(20):
            medidor.registrar(5.0)
        self.assertTrue(medidor.em_silencio())

    def test_silencio_devolve_o_anel_ao_repouso(self):
        medidor = MedidorDeNivel(quantidade_barras=8)
        medidor.registrar(REFERENCIA_MINIMA * 5)
        for _ in range(8):
            medidor.registrar_silencio()
        self.assertTrue(medidor.em_silencio())

    def test_historico_tem_um_valor_por_barra(self):
        medidor = MedidorDeNivel(quantidade_barras=12)
        self.assertEqual(len(medidor.niveis()), 12)
        medidor.registrar(1000)
        self.assertEqual(len(medidor.niveis()), 12)


class TestAnimacaoCircular(unittest.TestCase):
    def test_gira_e_volta_ao_inicio(self):
        animacao = AnimacaoCircular(graus_por_quadro=90)
        self.assertEqual(animacao.avancar(), 90)
        animacao.avancar()
        animacao.avancar()
        self.assertEqual(animacao.avancar(), 0.0)  # 360 -> volta a zero

    def test_gira_mesmo_sem_audio(self):
        """O círculo gira sempre: sem captura, é a única coisa em movimento."""
        animacao = AnimacaoCircular()
        antes = animacao.angulo
        animacao.avancar()
        self.assertNotEqual(animacao.angulo, antes)

    def test_barra_cresce_com_o_nivel(self):
        animacao = AnimacaoCircular()
        curta = animacao.comprimento_da_barra(0.0)
        longa = animacao.comprimento_da_barra(1.0)
        self.assertEqual(curta, animacao.comprimento_minimo)
        self.assertEqual(longa, animacao.comprimento_maximo)
        self.assertLess(curta, animacao.comprimento_da_barra(0.5))

    def test_barras_ficam_fora_do_circulo(self):
        """Nenhuma barra pode invadir o círculo central."""
        animacao = AnimacaoCircular()
        posicoes = animacao.posicoes_das_barras(0, 0, [1.0] * animacao.quantidade_barras)
        for x1, y1, _x2, _y2 in posicoes:
            distancia = (x1**2 + y1**2) ** 0.5
            self.assertGreaterEqual(round(distancia, 6), animacao.raio_circulo)

    def test_uma_posicao_por_nivel(self):
        animacao = AnimacaoCircular()
        self.assertEqual(len(animacao.posicoes_das_barras(0, 0, [0.5] * 10)), 10)

    def test_barras_distribuidas_em_volta(self):
        """As barras cobrem os quatro lados do círculo, não só um pedaço."""
        animacao = AnimacaoCircular(quantidade_barras=4)
        animacao.angulo = 0
        posicoes = animacao.posicoes_das_barras(100, 100, [0.5] * 4)
        xs = [p[2] for p in posicoes]
        ys = [p[3] for p in posicoes]
        self.assertGreater(max(xs), 100)
        self.assertLess(min(xs), 100)
        self.assertGreater(max(ys), 100)
        self.assertLess(min(ys), 100)


class TestMisturarCores(unittest.TestCase):
    def test_extremos(self):
        self.assertEqual(misturar_cores("#000000", "#ffffff", 0.0), "#000000")
        self.assertEqual(misturar_cores("#000000", "#ffffff", 1.0), "#ffffff")

    def test_meio(self):
        self.assertEqual(misturar_cores("#000000", "#ffffff", 0.5), "#808080")

    def test_proporcao_fora_da_faixa_e_limitada(self):
        self.assertEqual(misturar_cores("#000000", "#ffffff", 5.0), "#ffffff")
        self.assertEqual(misturar_cores("#000000", "#ffffff", -2.0), "#000000")


class TestDiscoSuavizado(unittest.TestCase):
    """O Canvas do tkinter não tem antialiasing, então o círculo é gerado
    como imagem PPM com a borda calculada por amostragem."""

    def setUp(self) -> None:
        self.lado = 40
        self.raio = 15.0
        self.dados = gerar_disco_ppm(
            self.lado, self.raio, "#ffffff", "#ffffff", "#000000", amostras=4
        )

    def _pixel(self, x: int, y: int) -> tuple[int, int, int]:
        cabecalho = b"P6\n%d %d\n255\n" % (self.lado, self.lado)
        corpo = self.dados[len(cabecalho) :]
        inicio = (y * self.lado + x) * 3
        return tuple(corpo[inicio : inicio + 3])

    def test_formato_ppm_valido(self):
        self.assertTrue(self.dados.startswith(b"P6\n40 40\n255\n"))

    def test_tamanho_corresponde_as_dimensoes(self):
        cabecalho = b"P6\n40 40\n255\n"
        self.assertEqual(len(self.dados) - len(cabecalho), self.lado * self.lado * 3)

    def test_centro_preenchido_e_canto_no_fundo(self):
        self.assertEqual(self._pixel(20, 20), (255, 255, 255))
        self.assertEqual(self._pixel(0, 0), (0, 0, 0))

    def test_borda_tem_tons_intermediarios(self):
        """É isso que diferencia de um create_oval: na borda existem pixels
        parcialmente preenchidos, e não só preto ou branco."""
        intermediarios = 0
        for x in range(self.lado):
            for y in range(self.lado):
                valor = self._pixel(x, y)[0]
                if 20 < valor < 235:
                    intermediarios += 1
        self.assertGreater(intermediarios, 10)

    def test_gradiente_radial_escurece_para_a_borda(self):
        dados_gradiente = gerar_disco_ppm(40, 15.0, "#ffffff", "#404040", "#000000")
        cabecalho = b"P6\n40 40\n255\n"
        corpo = dados_gradiente[len(cabecalho) :]

        def canal_vermelho(x, y):
            return corpo[(y * 40 + x) * 3]

        self.assertGreater(canal_vermelho(20, 20), canal_vermelho(20, 27))


@unittest.skipUnless(TEM_JANELA, "tkinter/display não disponível")
class TestJanela(unittest.TestCase):
    """Testes da janela: criam a interface de verdade, mas nunca abrem o
    microfone (o reconhecimento é sempre substituído por dublê)."""

    def setUp(self) -> None:
        from gui import JanelaMiniAlexa

        self.janela = JanelaMiniAlexa()

    def tearDown(self) -> None:
        self.janela.encerrar()

    def _digitar(self, frase: str) -> None:
        self.janela.entrada.delete(0, tk.END)
        self.janela._entrada_com_ajuda = False
        self.janela.entrada.insert(0, frase)
        self.janela._enviar_texto()

    def _conversa(self) -> str:
        return self.janela.conversa.get("1.0", tk.END)

    def test_comando_digitado_e_processado(self):
        self._digitar("ligar a luz do quarto")
        self.assertIn("Ok, ligando a luz do quarto.", self._conversa())
        self.assertTrue(self.janela.casa.obter("luz", "quarto").ligado)

    def test_comando_digitado_nao_fala(self):
        with patch("gui.falar") as falar_mock:
            self._digitar("ligar a luz da sala")
        falar_mock.assert_not_called()

    def test_texto_fantasma_nao_entra_no_comando(self):
        """Regressão: o texto de ajuda da caixa não pode virar parte do
        comando se sobrar junto com o que foi digitado."""
        from gui import TEXTO_AJUDA_ENTRADA

        self.janela.entrada.delete(0, tk.END)
        self.janela._entrada_com_ajuda = True
        self.janela.entrada.insert(0, "ligar a luz da sala" + TEXTO_AJUDA_ENTRADA)
        self.janela._enviar_texto()
        self.assertIn("Ok, ligando a luz da sala.", self._conversa())

    def test_clique_no_circulo_alterna_a_escuta(self):
        # a thread de áudio é substituída: aqui só interessa a mudança de
        # estado, e deixá-la rodar abriria o microfone de verdade
        with patch("gui.STT_DISPONIVEL", True), patch("gui.threading.Thread"):
            self.janela.alternar_escuta()
            self.assertTrue(self.janela.escutando.is_set())
            self.janela.alternar_escuta()
            self.assertFalse(self.janela.escutando.is_set())

    def test_clique_fora_do_circulo_nao_liga_o_microfone(self):
        class EventoFalso:
            x, y = 5, 5  # canto do canvas, longe do círculo

        with patch("gui.STT_DISPONIVEL", True), patch("gui.threading.Thread"):
            self.janela._clique_no_canvas(EventoFalso())
        self.assertFalse(self.janela.escutando.is_set())

    def test_clique_no_centro_liga_o_microfone(self):
        class EventoFalso:
            x, y = 180, 150  # centro do círculo

        with patch("gui.STT_DISPONIVEL", True), patch("gui.threading.Thread"):
            self.janela._clique_no_canvas(EventoFalso())
        self.assertTrue(self.janela.escutando.is_set())
        self.janela.escutando.clear()

    def test_sem_reconhecimento_o_clique_avisa_e_nao_escuta(self):
        with patch("gui.STT_DISPONIVEL", False):
            self.janela.alternar_escuta()
        self.assertFalse(self.janela.escutando.is_set())
        self.assertIn("não está instalado", self._conversa())

    def test_barras_paradas_quando_nao_ha_captura(self):
        self.janela.medidor.registrar(5000)
        for _ in range(len(self.janela.medidor.niveis()) + 1):
            self.janela._quadro()
        self.assertTrue(self.janela.medidor.em_silencio())

    def test_circulo_gira_a_cada_quadro(self):
        antes = self.janela.animacao.angulo
        self.janela._quadro()
        self.assertNotEqual(self.janela.animacao.angulo, antes)

    def test_sair_digitado_encerra(self):
        with patch.object(self.janela, "encerrar") as encerrar_mock:
            self._digitar("sair")
        encerrar_mock.assert_called_once()

    def test_evento_de_voz_responde_com_audio(self):
        self.janela.eventos.put(("resposta_falada", "Ok, ligando a luz da sala."))
        with patch("gui.falar") as falar_mock, patch("gui.threading.Thread") as thread_mock:
            self.janela._processar_eventos()
        self.assertIn("Ok, ligando a luz da sala.", self._conversa())
        thread_mock.assert_called_once()  # a fala roda fora da thread da interface
        falar_mock.assert_not_called()    # ...então não é chamada aqui direto

    def test_fala_sem_palavra_chave_aparece_como_ignorada(self):
        self.janela.eventos.put(("ignorado", "conversa qualquer"))
        self.janela._processar_eventos()
        self.assertIn("ignorado: sem a palavra-chave", self._conversa())


if __name__ == "__main__":
    unittest.main()
