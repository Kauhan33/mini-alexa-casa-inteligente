"""
Interface gráfica do Mini-Alexa de Casa Inteligente.

    python gui.py          (ou: python main.py --gui)

Usa apenas tkinter, da biblioteca padrão — nada a instalar além do que a
voz já pede.

A tela tem três partes:

- um círculo no centro, que gira continuamente e funciona como botão:
  clicar liga a escuta, clicar de novo desliga (só isso interrompe);
- barras de som ao redor do círculo, que crescem com o volume real captado
  pelo microfone (ver visual.MedidorDeNivel) e ficam paradas quando não há
  captura;
- uma caixa de texto embaixo, com o histórico da conversa, onde também se
  pode digitar comandos.

A análise dos comandos é exatamente a mesma do modo terminal: esta janela
só troca a forma de entrar com a frase e de mostrar a resposta.

Regras de interação (iguais às do terminal):
- falando, o comando precisa começar com a palavra-chave "Alexa", e a
  resposta sai em áudio;
- digitando, não precisa de palavra-chave e a resposta sai só na tela;
- "sair" encerra o programa, falado ou digitado.
"""

from __future__ import annotations

import math
import queue
import threading
import tkinter as tk
from tkinter import font as tkfont

from lexer import analisar_lexico
from semantic import CasaInteligente, interpretar, texto_para_audio
from visual import AnimacaoCircular, MedidorDeNivel, gerar_disco_ppm, misturar_cores
from voice import STT_DISPONIVEL, ErroReconhecimento, OuvidorContinuo, falar
from wakeword import extrair_comando

COMANDOS_SAIR = ("sair", "exit", "quit")

# ~30 quadros por segundo: suave o suficiente e leve para o tkinter
INTERVALO_QUADRO_MS = 33

COR_FUNDO = "#0f1220"
COR_PAINEL = "#171a2b"
COR_ENTRADA = "#1e2236"
COR_BORDA = "#343b5c"
COR_TEXTO = "#e8eaf6"
COR_TEXTO_FRACO = "#8a90b5"
COR_CIRCULO_PARADO = "#252b48"
COR_CIRCULO_PARADO_CLARO = "#39416b"   # centro do gradiente, parado
COR_CIRCULO_OUVINDO = "#17697a"
COR_CIRCULO_OUVINDO_CLARO = "#2a9fb5"  # centro do gradiente, ouvindo
COR_ARCO = "#4dd0e1"
COR_BARRA_BAIXA = "#2a3050"
COR_BARRA_ALTA = "#4dd0e1"

# o arco que gira dentro do círculo: quanto ele cobre e em quantos
# segmentos é desenhado (mais segmentos = curva mais lisa)
ARCO_GRAUS = 110
ARCO_SEGMENTOS = 40

TEXTO_AJUDA_ENTRADA = "digite um comando (ex.: ligar a luz da sala)"


class JanelaMiniAlexa:
    """Janela principal. Toda manipulação de widget acontece na thread do
    tkinter; a escuta do microfone roda em uma thread separada e conversa
    com a interface por uma fila (queue), que é o jeito seguro de fazer
    isso em tkinter."""

    def __init__(self, casa: CasaInteligente | None = None) -> None:
        self.casa = casa or CasaInteligente()
        self.medidor = MedidorDeNivel()
        self.animacao = AnimacaoCircular(quantidade_barras=self.medidor.niveis().__len__())
        self.eventos: queue.Queue[tuple[str, str]] = queue.Queue()

        self.escutando = threading.Event()
        self._thread_audio: threading.Thread | None = None
        self._ouvidor: OuvidorContinuo | None = None
        self._trava_casa = threading.Lock()

        self.raiz = tk.Tk()
        self.raiz.title("Mini-Alexa de Casa Inteligente")
        self.raiz.configure(bg=COR_FUNDO)
        self.raiz.minsize(560, 640)

        self._montar_interface()
        self._desenhar_barras_iniciais()

        self.raiz.protocol("WM_DELETE_WINDOW", self.encerrar)
        self.raiz.after(INTERVALO_QUADRO_MS, self._quadro)
        self.raiz.after(80, self._processar_eventos)

    # ------------------------------------------------------------------
    # Construção da tela
    # ------------------------------------------------------------------

    def _montar_interface(self) -> None:
        fonte_titulo = tkfont.Font(family="Segoe UI", size=15, weight="bold")
        fonte_normal = tkfont.Font(family="Segoe UI", size=10)
        fonte_conversa = tkfont.Font(family="Consolas", size=10)

        tk.Label(
            self.raiz,
            text="Mini-Alexa de Casa Inteligente",
            bg=COR_FUNDO,
            fg=COR_TEXTO,
            font=fonte_titulo,
        ).pack(pady=(16, 2))

        self.rotulo_status = tk.Label(
            self.raiz,
            text="",
            bg=COR_FUNDO,
            fg=COR_TEXTO_FRACO,
            font=fonte_normal,
        )
        self.rotulo_status.pack()

        self.canvas = tk.Canvas(
            self.raiz, width=360, height=300, bg=COR_FUNDO, highlightthickness=0
        )
        self.canvas.pack(pady=4)
        self.canvas.bind("<Button-1>", self._clique_no_canvas)

        self.centro = (180, 150)
        raio = self.animacao.raio_circulo
        cx, cy = self.centro

        # A ordem de criação é a ordem de empilhamento no Canvas, e importa:
        # a imagem do círculo é um QUADRADO (preenchido com a cor do fundo),
        # cujos cantos alcançam mais longe que a própria borda circular. Se
        # ela fosse criada depois, esses cantos cobririam o começo das barras
        # nas diagonais. Por isso: imagem primeiro, barras por cima.
        lado = int(raio * 2) + 8
        self.imagens_circulo = {
            "parado": tk.PhotoImage(
                data=gerar_disco_ppm(lado, raio, COR_CIRCULO_PARADO_CLARO, COR_CIRCULO_PARADO, COR_FUNDO)
            ),
            "ouvindo": tk.PhotoImage(
                data=gerar_disco_ppm(lado, raio, COR_CIRCULO_OUVINDO_CLARO, COR_CIRCULO_OUVINDO, COR_FUNDO)
            ),
        }
        self.item_circulo = self.canvas.create_image(
            cx, cy, image=self.imagens_circulo["parado"]
        )

        # as barras são criadas uma vez e depois só têm coordenadas e cor
        # atualizadas — recriar itens a cada quadro deixaria a animação lenta
        self.itens_barras = [
            self.canvas.create_line(cx, cy, cx, cy, width=4, fill=COR_BARRA_BAIXA, capstyle=tk.ROUND)
            for _ in range(self.animacao.quantidade_barras)
        ]

        # o arco que gira é uma polilinha suavizada, em vez de create_arc:
        # linhas aceitam pontas arredondadas e ficam bem menos serrilhadas
        self.item_arco = self.canvas.create_line(
            cx, cy, cx, cy,
            fill=COR_ARCO, width=5, capstyle=tk.ROUND, joinstyle=tk.ROUND, smooth=True,
        )
        self.item_texto_circulo = self.canvas.create_text(
            cx, cy, text="", fill=COR_TEXTO, font=tkfont.Font(family="Segoe UI", size=11, weight="bold")
        )

        painel = tk.Frame(self.raiz, bg=COR_FUNDO)
        painel.pack(fill=tk.BOTH, expand=True, padx=16, pady=(4, 10))

        self.conversa = tk.Text(
            painel,
            height=10,
            bg=COR_PAINEL,
            fg=COR_TEXTO,
            insertbackground=COR_TEXTO,
            font=fonte_conversa,
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=10,
            pady=8,
        )
        self.conversa.pack(fill=tk.BOTH, expand=True)
        self.conversa.tag_configure("voce", foreground="#9fe6f5")
        self.conversa.tag_configure("alexa", foreground="#c5e1a5")
        self.conversa.tag_configure("sistema", foreground=COR_TEXTO_FRACO)
        self.conversa.configure(state=tk.DISABLED)

        linha_entrada = tk.Frame(painel, bg=COR_FUNDO)
        linha_entrada.pack(fill=tk.X, pady=(8, 0))

        self.entrada = tk.Entry(
            linha_entrada,
            bg=COR_ENTRADA,
            fg=COR_TEXTO,
            insertbackground=COR_TEXTO,
            font=fonte_normal,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=COR_BORDA,
            highlightcolor=COR_ARCO,
        )
        self.entrada.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=7, padx=(0, 8))
        self.entrada.bind("<Return>", lambda _evento: self._enviar_texto())
        self.entrada.focus_set()
        self._preparar_texto_de_ajuda_da_entrada()

        tk.Button(
            linha_entrada,
            text="Enviar",
            command=self._enviar_texto,
            bg=COR_CIRCULO_OUVINDO,
            fg=COR_TEXTO,
            activebackground=COR_ARCO,
            relief=tk.FLAT,
            font=fonte_normal,
            padx=16,
        ).pack(side=tk.LEFT)

        self._mostrar_boas_vindas()
        self._atualizar_visual_do_circulo()

    def _preparar_texto_de_ajuda_da_entrada(self) -> None:
        """Texto-fantasma na caixa de digitação, que sai ao clicar nela."""
        self._entrada_com_ajuda = True
        self.entrada.insert(0, TEXTO_AJUDA_ENTRADA)
        self.entrada.configure(fg=COR_TEXTO_FRACO)

        def ao_focar(_evento=None):
            if self._entrada_com_ajuda:
                self.entrada.delete(0, tk.END)
                self.entrada.configure(fg=COR_TEXTO)
                self._entrada_com_ajuda = False

        def ao_desfocar(_evento=None):
            if not self.entrada.get().strip():
                self._entrada_com_ajuda = True
                self.entrada.delete(0, tk.END)
                self.entrada.insert(0, TEXTO_AJUDA_ENTRADA)
                self.entrada.configure(fg=COR_TEXTO_FRACO)

        self.entrada.bind("<FocusIn>", ao_focar)
        self.entrada.bind("<FocusOut>", ao_desfocar)
        self.entrada.bind("<Button-1>", ao_focar, add="+")

    def _mostrar_boas_vindas(self) -> None:
        self._escrever(
            "Clique no círculo para ligar o microfone. Falando, comece com "
            '"Alexa" (ex.: "Alexa, ligar a luz da sala"). Digitando, não precisa.',
            "sistema",
        )
        self._escrever(
            'Digite "comandos" para ver tudo que é aceito, ou "estado da casa" para '
            "saber o que está ligado. Todos os dispositivos começam desligados.",
            "sistema",
        )
        if not STT_DISPONIVEL:
            self._escrever(
                "Reconhecimento de voz não instalado (pip install -r requirements.txt): "
                "a janela funciona normalmente digitando.",
                "sistema",
            )

    def _desenhar_barras_iniciais(self) -> None:
        self._atualizar_barras(self.medidor.niveis())

    # ------------------------------------------------------------------
    # Animação
    # ------------------------------------------------------------------

    def _quadro(self) -> None:
        """Um quadro da animação: o círculo gira sempre; as barras seguem o
        volume captado (e ficam no repouso quando não há captura)."""
        self.animacao.avancar()

        if not self.escutando.is_set():
            self.medidor.registrar_silencio()

        self._atualizar_barras(self.medidor.niveis())
        self._atualizar_arco()
        self.raiz.after(INTERVALO_QUADRO_MS, self._quadro)

    def _atualizar_arco(self) -> None:
        """Reposiciona o arco que gira dentro do círculo, ponto a ponto."""
        centro_x, centro_y = self.centro
        raio = self.animacao.raio_circulo - 10
        pontos = []
        for passo in range(ARCO_SEGMENTOS + 1):
            graus = self.animacao.angulo + ARCO_GRAUS * (passo / ARCO_SEGMENTOS)
            radianos = math.radians(graus)
            pontos.extend(
                (centro_x + math.cos(radianos) * raio, centro_y + math.sin(radianos) * raio)
            )
        self.canvas.coords(self.item_arco, *pontos)

    def _atualizar_barras(self, niveis: list[float]) -> None:
        centro_x, centro_y = self.centro
        posicoes = self.animacao.posicoes_das_barras(centro_x, centro_y, niveis)
        ativo = self.escutando.is_set()

        for item, (x1, y1, x2, y2), nivel in zip(self.itens_barras, posicoes, niveis):
            self.canvas.coords(item, x1, y1, x2, y2)
            cor = misturar_cores(COR_BARRA_BAIXA, COR_BARRA_ALTA, nivel) if ativo else COR_BARRA_BAIXA
            self.canvas.itemconfig(item, fill=cor)

    def _atualizar_visual_do_circulo(self) -> None:
        ouvindo = self.escutando.is_set()
        self.canvas.itemconfig(
            self.item_circulo,
            image=self.imagens_circulo["ouvindo" if ouvindo else "parado"],
        )
        self.canvas.itemconfig(
            self.item_texto_circulo, text="ouvindo" if ouvindo else "clique\npara falar"
        )
        if ouvindo:
            self.rotulo_status.config(text="Microfone ligado — clique no círculo para parar")
        elif STT_DISPONIVEL:
            self.rotulo_status.config(text="Microfone desligado — clique no círculo para começar")
        else:
            self.rotulo_status.config(text="Sem reconhecimento de voz: use a caixa de texto")

    # ------------------------------------------------------------------
    # Entrada por texto
    # ------------------------------------------------------------------

    def _enviar_texto(self) -> None:
        frase = self.entrada.get()
        # enquanto o texto-fantasma estiver ativo, ele não faz parte do
        # comando (pode ter sobrado se o texto foi inserido sem passar pelo
        # clique que o apaga)
        if getattr(self, "_entrada_com_ajuda", False):
            frase = frase.replace(TEXTO_AJUDA_ENTRADA, "")
        frase = frase.strip()
        if not frase:
            return
        self.entrada.delete(0, tk.END)
        self._escrever(f"Você: {frase}", "voce")

        if frase.lower() in COMANDOS_SAIR:
            self.encerrar()
            return

        resposta = self._processar(frase)
        self._escrever(f"Alexa: {resposta}", "alexa")  # digitado: sem áudio

    # ------------------------------------------------------------------
    # Entrada por voz
    # ------------------------------------------------------------------

    def _clique_no_canvas(self, evento) -> None:
        """Só o clique dentro do círculo central alterna a escuta."""
        centro_x, centro_y = self.centro
        distancia = ((evento.x - centro_x) ** 2 + (evento.y - centro_y) ** 2) ** 0.5
        if distancia <= self.animacao.raio_circulo:
            self.alternar_escuta()

    def alternar_escuta(self) -> None:
        if self.escutando.is_set():
            self._parar_escuta()
        else:
            self._iniciar_escuta()

    def _iniciar_escuta(self) -> None:
        if not STT_DISPONIVEL:
            self._escrever(
                "Reconhecimento de voz não está instalado. Rode: pip install -r requirements.txt",
                "sistema",
            )
            return

        self.escutando.set()
        self._atualizar_visual_do_circulo()
        self._escrever("(microfone ligado)", "sistema")

        self._thread_audio = threading.Thread(target=self._laco_de_escuta, daemon=True)
        self._thread_audio.start()

    def _parar_escuta(self) -> None:
        self.escutando.clear()
        self._atualizar_visual_do_circulo()
        self._escrever("(microfone desligado)", "sistema")

    def _laco_de_escuta(self) -> None:
        """Roda fora da thread da interface: abre o microfone e fica ouvindo
        até o círculo ser clicado de novo. Nada aqui toca em widget — tudo
        vai para a fila de eventos."""
        try:
            if self._ouvidor is None:
                self._ouvidor = OuvidorContinuo(ao_medir_nivel=self.medidor.registrar)
        except ErroReconhecimento as erro:
            self.eventos.put(("erro_fatal", str(erro)))
            return

        while self.escutando.is_set():
            try:
                frase = self._ouvidor.ouvir(timeout=3.0)
            except ErroReconhecimento as erro:
                mensagem = str(erro)
                if "Ninguém falou" in mensagem:
                    continue  # silêncio é normal com o microfone sempre aberto
                if "não consegui entender" in mensagem.lower():
                    self.eventos.put(("sistema", "(não entendi o que foi falado — pode repetir)"))
                    continue
                self.eventos.put(("sistema", mensagem))
                continue

            if not self.escutando.is_set():
                break

            comando = extrair_comando(frase)
            if comando is None:
                self.eventos.put(("ignorado", frase))
                continue

            self.eventos.put(("voz", frase))

            if not comando:
                self.eventos.put(("resposta_falada", "Diga um comando depois de 'Alexa'."))
                continue

            if comando.lower() in COMANDOS_SAIR:
                self.eventos.put(("sair", ""))
                return

            with self._trava_casa:
                resposta = self._processar(comando)
            self.eventos.put(("resposta_falada", resposta))

    def _processar(self, frase: str) -> str:
        return interpretar(analisar_lexico(frase), self.casa)

    # ------------------------------------------------------------------
    # Ponte entre a thread de áudio e a interface
    # ------------------------------------------------------------------

    def _processar_eventos(self) -> None:
        """Consome a fila preenchida pela thread de áudio. Só aqui os
        widgets são alterados, sempre na thread do tkinter."""
        try:
            while True:
                tipo, conteudo = self.eventos.get_nowait()

                if tipo == "voz":
                    self._escrever(f"Você (voz): {conteudo}", "voce")
                elif tipo == "ignorado":
                    self._escrever(
                        f"Você (voz): {conteudo}  (ignorado: sem a palavra-chave 'Alexa')",
                        "sistema",
                    )
                elif tipo == "sistema":
                    self._escrever(conteudo, "sistema")
                elif tipo == "resposta_falada":
                    self._escrever(f"Alexa: {conteudo}", "alexa")
                    # falar bloqueia alguns segundos: em outra thread, para
                    # não congelar a animação nem a digitação
                    threading.Thread(
                        target=falar, args=(texto_para_audio(conteudo),), daemon=True
                    ).start()
                elif tipo == "erro_fatal":
                    self.escutando.clear()
                    self._atualizar_visual_do_circulo()
                    self._escrever(conteudo, "sistema")
                elif tipo == "sair":
                    self.encerrar()
                    return
        except queue.Empty:
            pass

        self.raiz.after(80, self._processar_eventos)

    def _escrever(self, texto: str, estilo: str) -> None:
        self.conversa.configure(state=tk.NORMAL)
        self.conversa.insert(tk.END, texto + "\n", estilo)
        self.conversa.see(tk.END)
        self.conversa.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Encerramento
    # ------------------------------------------------------------------

    def encerrar(self) -> None:
        self.escutando.clear()
        try:
            self.raiz.destroy()
        except tk.TclError:
            pass

    def executar(self) -> None:
        self.raiz.mainloop()


def main() -> None:
    JanelaMiniAlexa().executar()


if __name__ == "__main__":
    main()
