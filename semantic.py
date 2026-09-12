"""
Analisador semântico + executor de comandos do Mini-Alexa de Casa Inteligente.

Recebe a lista de tokens produzida pela fase léxica (lexer.py) e faz três
verificações de significado antes de agir:

1. a frase tem os elementos necessários (uma ação e um dispositivo)?
2. a ação faz sentido para aquele dispositivo (não se "abre" uma luz)?
3. a ação muda algo, dado o **estado atual** da casa? Mandar ligar uma luz
   que já está acesa é uma frase perfeitamente válida, mas redundante — e a
   assistente responde informando o estado ("A luz do quarto já está
   acesa.") em vez de fingir que executou.

A verificação 3 é o que diferencia análise semântica de simples validação
de sintaxe: o significado do comando depende do contexto, não só das palavras.
"""

from __future__ import annotations

from dataclasses import dataclass

from lexer import ACOES as ACOES_LEXICAS
from lexer import LOCAIS, Token, TipoToken

# quais ações são compatíveis com quais dispositivos
COMPATIBILIDADE: dict[str, set[str]] = {
    "LIGAR": {"luz", "ventilador", "ar_condicionado", "tv", "tomada", "alarme"},
    "DESLIGAR": {"luz", "ventilador", "ar_condicionado", "tv", "tomada", "alarme"},
    "ABRIR": {"porta", "portao", "cortina"},
    "FECHAR": {"porta", "portao", "cortina"},
    "AUMENTAR": {"ventilador", "ar_condicionado", "tv"},
    "DIMINUIR": {"ventilador", "ar_condicionado", "tv"},
}

# Cada dispositivo tem artigo (para concordância de gênero) e os particípios
# que descrevem seus dois estados — uma luz fica "acesa/apagada", uma porta
# "aberta/fechada", um alarme "ativado/desativado".
DISPOSITIVOS: dict[str, dict[str, str]] = {
    "luz":             {"artigo": "a", "nome": "luz",             "ativo": "acesa",   "inativo": "apagada"},
    "ventilador":      {"artigo": "o", "nome": "ventilador",      "ativo": "ligado",  "inativo": "desligado"},
    "ar_condicionado": {"artigo": "o", "nome": "ar-condicionado", "ativo": "ligado",  "inativo": "desligado"},
    "tv":              {"artigo": "a", "nome": "tv",              "ativo": "ligada",  "inativo": "desligada"},
    "porta":           {"artigo": "a", "nome": "porta",           "ativo": "aberta",  "inativo": "fechada"},
    "portao":          {"artigo": "o", "nome": "portão",          "ativo": "aberto",  "inativo": "fechado"},
    "cortina":         {"artigo": "a", "nome": "cortina",         "ativo": "aberta",  "inativo": "fechada"},
    "tomada":          {"artigo": "a", "nome": "tomada",          "ativo": "ligada",  "inativo": "desligada"},
    "alarme":          {"artigo": "o", "nome": "alarme",          "ativo": "ativado", "inativo": "desativado"},
}

LOCAL_GENITIVO = {
    "sala": "da sala", "quarto": "do quarto", "cozinha": "da cozinha",
    "banheiro": "do banheiro", "quintal": "do quintal", "garagem": "da garagem",
    "escritorio": "do escritório", "varanda": "da varanda",
}

GERUNDIO = {
    "LIGAR": "ligando", "DESLIGAR": "desligando",
    "ABRIR": "abrindo", "FECHAR": "fechando",
    "AUMENTAR": "aumentando", "DIMINUIR": "diminuindo",
}

ACOES_QUE_ATIVAM = ("LIGAR", "ABRIR")
ACOES_QUE_DESATIVAM = ("DESLIGAR", "FECHAR")
ACOES_DE_NIVEL = ("AUMENTAR", "DIMINUIR")

# consultas: ações que respondem sobre a casa ou sobre o próprio programa,
# e por isso não exigem um dispositivo na frase
ACOES_DE_CONSULTA = ("ESTADO", "AJUDA")

NIVEL_MINIMO = 0
NIVEL_MAXIMO = 100
PASSO_PADRAO = 10


@dataclass
class Dispositivo:
    ligado: bool = False
    nivel: int = 0  # velocidade / temperatura / volume, quando aplicável


def descrever(dispositivo: str, local: str | None = None) -> str:
    """Ex.: ("luz", "quarto") -> "a luz do quarto"."""
    info = DISPOSITIVOS.get(dispositivo)
    if info is None:
        return dispositivo
    texto = f"{info['artigo']} {info['nome']}"
    if local in LOCAL_GENITIVO:
        texto += f" {LOCAL_GENITIVO[local]}"
    return texto


def _maiuscula(texto: str) -> str:
    """Primeira letra maiúscula, sem mexer no resto (str.capitalize()
    rebaixaria o resto da frase)."""
    return texto[:1].upper() + texto[1:]


class CasaInteligente:
    """Guarda o estado atual de cada dispositivo (por local, quando informado)."""

    def __init__(self) -> None:
        self._estado: dict[tuple[str, str], Dispositivo] = {}

    def _chave(self, dispositivo: str, local: str | None) -> tuple[str, str]:
        return (dispositivo, local or "geral")

    def obter(self, dispositivo: str, local: str | None) -> Dispositivo:
        chave = self._chave(dispositivo, local)
        if chave not in self._estado:
            self._estado[chave] = Dispositivo()
        return self._estado[chave]

    def resumir_estado(self) -> str:
        """Responde ao comando "estado da casa": lista o que está ligado ou
        aberto agora. Só aparecem dispositivos já acionados — os demais
        continuam no estado inicial (desligados), o que a própria frase
        final deixa claro."""
        ativos = []
        for (dispositivo, local), estado in sorted(self._estado.items()):
            if not estado.ligado:
                continue
            info = DISPOSITIVOS[dispositivo]
            alvo = descrever(dispositivo, None if local == "geral" else local)
            texto = f"{alvo} está {info['ativo']}"
            if estado.nivel > NIVEL_MINIMO:
                texto += f", em {estado.nivel}"
            ativos.append(texto)

        if not ativos:
            return "Nenhum dispositivo está ligado ou aberto no momento."
        return "No momento, " + "; ".join(ativos) + ". O restante está desligado."

    def executar(self, acao: str, dispositivo: str, local: str | None, valor: int | None) -> str:
        """Aplica a ação ao estado da casa e devolve a resposta da assistente.
        Quando a ação não mudaria nada, informa o estado atual em vez de
        executar."""
        estado = self.obter(dispositivo, local)
        info = DISPOSITIVOS[dispositivo]
        alvo = descrever(dispositivo, local)

        if acao in ACOES_QUE_ATIVAM:
            if estado.ligado:
                return f"{_maiuscula(alvo)} já está {info['ativo']}."
            estado.ligado = True
            return f"Ok, {GERUNDIO[acao]} {alvo}."

        if acao in ACOES_QUE_DESATIVAM:
            if not estado.ligado:
                return f"{_maiuscula(alvo)} já está {info['inativo']}."
            estado.ligado = False
            return f"Ok, {GERUNDIO[acao]} {alvo}."

        if acao in ACOES_DE_NIVEL:
            return self._ajustar_nivel(acao, estado, alvo, valor)

        return f"Não sei como executar '{acao}' em {alvo}."

    def _ajustar_nivel(self, acao: str, estado: Dispositivo, alvo: str, valor: int | None) -> str:
        if acao == "AUMENTAR" and estado.nivel >= NIVEL_MAXIMO:
            return f"{_maiuscula(alvo)} já está no máximo."
        if acao == "DIMINUIR" and estado.nivel <= NIVEL_MINIMO:
            return f"{_maiuscula(alvo)} já está no mínimo."

        if valor is not None:
            # com valor explícito ("para 60"), o número é o nível desejado —
            # mas pedir para *aumentar* até um nível igual ou menor que o
            # atual é contraditório, então a assistente só informa o estado
            desejado = max(NIVEL_MINIMO, min(NIVEL_MAXIMO, valor))
            if acao == "AUMENTAR" and desejado <= estado.nivel:
                return f"{_maiuscula(alvo)} já está em {estado.nivel}."
            if acao == "DIMINUIR" and desejado >= estado.nivel:
                return f"{_maiuscula(alvo)} já está em {estado.nivel}."
            estado.nivel = desejado
        else:
            delta = PASSO_PADRAO if acao == "AUMENTAR" else -PASSO_PADRAO
            estado.nivel = max(NIVEL_MINIMO, min(NIVEL_MAXIMO, estado.nivel + delta))

        estado.ligado = estado.nivel > NIVEL_MINIMO
        return f"Ok, {GERUNDIO[acao]} {alvo} para {estado.nivel}."


def _sinonimos_de(acao_canonica: str) -> list[str]:
    """Todas as palavras que o lexer aceita para uma mesma ação, com a
    palavra principal (a que dá nome à ação) na frente."""
    palavras = [p for p, canonica in ACOES_LEXICAS.items() if canonica == acao_canonica]
    return sorted(palavras, key=lambda p: (p != acao_canonica.lower(), p))


def _locais_para_exibir() -> list[str]:
    """Nomes dos locais acentuados para leitura. O lexer guarda as palavras
    sem acento (para facilitar o casamento), então a grafia bonita vem do
    LOCAL_GENITIVO, que já traz "do escritório", "da sala"..."""
    nomes = []
    for local in sorted(LOCAIS):
        genitivo = LOCAL_GENITIVO.get(local)
        nomes.append(genitivo.split(" ", 1)[1] if genitivo else local)
    return nomes


def _dispositivos_de(acao_canonica: str) -> list[str]:
    return sorted(DISPOSITIVOS[d]["nome"] for d in COMPATIBILIDADE.get(acao_canonica, set()))


def montar_ajuda() -> str:
    """Responde ao comando "comandos"/"ajuda", montando a lista a partir do
    vocabulário real do lexer e da tabela de compatibilidade — assim ela
    nunca fica desatualizada em relação ao que o programa aceita."""
    linhas = ["Comandos disponíveis:", ""]

    pares = [("LIGAR", "DESLIGAR"), ("ABRIR", "FECHAR"), ("AUMENTAR", "DIMINUIR")]
    for acao, oposta in pares:
        verbos = "/".join(_sinonimos_de(acao))
        verbos_opostos = "/".join(_sinonimos_de(oposta))
        linhas.append(f"  {verbos}  ou  {verbos_opostos}")
        linhas.append(f"    dispositivos: {', '.join(_dispositivos_de(acao))}")
        if acao == "AUMENTAR":
            linhas.append(f"    aceita um nível de {NIVEL_MINIMO} a {NIVEL_MAXIMO} (ex.: 'para 60')")
        linhas.append("")

    linhas.append(f"  locais (opcionais): {', '.join(_locais_para_exibir())}")
    linhas.append("")
    linhas.append("  consultas:")
    linhas.append(f"    {'/'.join(_sinonimos_de('ESTADO'))} da casa  -> o que está ligado agora")
    linhas.append(f"    {'/'.join(_sinonimos_de('AJUDA'))}  -> esta lista")
    linhas.append("    sair  -> encerra o programa")
    linhas.append("")
    linhas.append("Exemplos:")
    linhas.append("  ligar a luz da sala")
    linhas.append("  aumentar o ventilador do quarto para 60")
    linhas.append("  abrir a cortina da sala")
    linhas.append("  estado da casa")
    linhas.append("")
    linhas.append('Por voz, comece com a palavra-chave: "Alexa, ligar a luz da sala".')

    return "\n".join(linhas)


AJUDA_FALADA = (
    "A lista completa apareceu na tela. Resumindo: eu posso ligar, desligar, abrir, "
    "fechar, aumentar e diminuir dispositivos como luz, ventilador, ar-condicionado, "
    "televisão, porta, cortina, tomada e alarme, em locais como sala, quarto e cozinha. "
    "Você também pode pedir o estado da casa."
)


def texto_para_audio(resposta: str) -> str:
    """Versão da resposta adequada para ser falada.

    A lista de comandos é útil na tela, mas ouvi-la inteira em voz alta seria
    interminável — nesse caso a assistente fala um resumo e deixa a lista
    completa por escrito.
    """
    if resposta.startswith("Comandos disponíveis:"):
        return AJUDA_FALADA
    return resposta


def interpretar(tokens: list[Token], casa: CasaInteligente) -> str:
    """Fase de análise semântica: valida o significado da frase e, se for
    válida, pede para a CasaInteligente executar a ação."""

    acoes = [t for t in tokens if t.tipo == TipoToken.ACAO]
    dispositivos = [t for t in tokens if t.tipo == TipoToken.DISPOSITIVO]
    locais = [t for t in tokens if t.tipo == TipoToken.LOCAL]
    valores = [t for t in tokens if t.tipo == TipoToken.VALOR]
    desconhecidos = [t for t in tokens if t.tipo == TipoToken.DESCONHECIDO]

    if not acoes:
        return "Desculpe, não entendi qual ação você quer executar."
    if len(acoes) > 1:
        return "Desculpe, entendi mais de um comando na mesma frase. Fale um de cada vez."

    acao = acoes[0].valor

    # consultas respondem sozinhas: não controlam nenhum dispositivo, então
    # são resolvidas antes de exigir um na frase
    if acao == "ESTADO":
        return casa.resumir_estado()
    if acao == "AJUDA":
        return montar_ajuda()

    if not dispositivos:
        return "Desculpe, não entendi qual dispositivo você quer controlar."
    if len(dispositivos) > 1:
        return "Desculpe, entendi mais de um dispositivo na mesma frase. Fale um de cada vez."

    dispositivo = dispositivos[0].valor
    local = locais[0].valor if locais else None
    valor = int(valores[0].valor) if valores else None

    if dispositivo not in COMPATIBILIDADE.get(acao, set()):
        return f"Desculpe, não é possível '{acao.lower()}' {descrever(dispositivo)}."

    resposta = casa.executar(acao, dispositivo, local, valor)

    if desconhecidos:
        palavras = ", ".join(f"'{t.lexema}'" for t in desconhecidos)
        resposta += f" (não reconheci: {palavras})"

    return resposta
