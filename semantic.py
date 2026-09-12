"""
Analisador semântico + executor de comandos do Mini-Alexa de Casa Inteligente.

Recebe a lista de tokens produzida pela fase léxica (lexer.py), valida se o
comando faz sentido (ex.: não dá para "abrir" uma "luz") e, se for válido,
atualiza o estado simulado da casa e devolve a resposta que a "Alexa" daria.
"""

from __future__ import annotations

from dataclasses import dataclass

from lexer import Token, TipoToken

# quais ações são compatíveis com quais dispositivos
COMPATIBILIDADE: dict[str, set[str]] = {
    "LIGAR": {"luz", "ventilador", "ar_condicionado", "tv", "tomada", "alarme"},
    "DESLIGAR": {"luz", "ventilador", "ar_condicionado", "tv", "tomada", "alarme"},
    "ABRIR": {"porta", "portao", "cortina"},
    "FECHAR": {"porta", "portao", "cortina"},
    "AUMENTAR": {"ventilador", "ar_condicionado", "tv"},
    "DIMINUIR": {"ventilador", "ar_condicionado", "tv"},
}

NOME_LEGIVEL = {
    "luz": "a luz", "ventilador": "o ventilador", "ar_condicionado": "o ar-condicionado",
    "tv": "a tv", "porta": "a porta", "portao": "o portão", "cortina": "a cortina",
    "tomada": "a tomada", "alarme": "o alarme",
}

LOCAL_PREPOSICAO = {
    "sala": "na sala", "quarto": "no quarto", "cozinha": "na cozinha",
    "banheiro": "no banheiro", "quintal": "no quintal", "garagem": "na garagem",
    "escritorio": "no escritório", "varanda": "na varanda",
}


@dataclass
class Dispositivo:
    ligado: bool = False
    nivel: int = 0  # velocidade / temperatura / volume, quando aplicável


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

    def executar(self, acao: str, dispositivo: str, local: str | None, valor: int | None) -> str:
        estado = self.obter(dispositivo, local)
        nome = NOME_LEGIVEL.get(dispositivo, dispositivo)
        onde = f" {LOCAL_PREPOSICAO[local]}" if local in LOCAL_PREPOSICAO else ""

        if acao == "LIGAR":
            estado.ligado = True
            return f"Ok, ligando {nome}{onde}."
        if acao == "DESLIGAR":
            estado.ligado = False
            return f"Ok, desligando {nome}{onde}."
        if acao == "ABRIR":
            estado.ligado = True
            return f"Ok, abrindo {nome}{onde}."
        if acao == "FECHAR":
            estado.ligado = False
            return f"Ok, fechando {nome}{onde}."
        if acao in ("AUMENTAR", "DIMINUIR"):
            passo = valor if valor is not None else 10
            delta = passo if acao == "AUMENTAR" else -passo
            estado.nivel = max(0, min(100, estado.nivel + delta))
            estado.ligado = estado.nivel > 0 or estado.ligado
            verbo = "aumentando" if acao == "AUMENTAR" else "diminuindo"
            return f"Ok, {verbo} {nome}{onde} para {estado.nivel}."
        return f"Não sei como executar '{acao}' em {nome}."


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
    if not dispositivos:
        return "Desculpe, não entendi qual dispositivo você quer controlar."
    if len(dispositivos) > 1:
        return "Desculpe, entendi mais de um dispositivo na mesma frase. Fale um de cada vez."

    acao = acoes[0].valor
    dispositivo = dispositivos[0].valor
    local = locais[0].valor if locais else None
    valor = int(valores[0].valor) if valores else None

    if dispositivo not in COMPATIBILIDADE.get(acao, set()):
        nome = NOME_LEGIVEL.get(dispositivo, dispositivo)
        return f"Desculpe, não é possível '{acao.lower()}' {nome}."

    resposta = casa.executar(acao, dispositivo, local, valor)

    if desconhecidos:
        palavras = ", ".join(f"'{t.lexema}'" for t in desconhecidos)
        resposta += f" (não reconheci: {palavras})"

    return resposta
