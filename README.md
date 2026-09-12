# Mini-Alexa de Casa Inteligente

Projeto da disciplina de **Compiladores** (8º período — UNA). Simula uma assistente de
casa inteligente que interpreta comandos em linguagem natural, unindo análise léxica e
análise semântica — ver [enunciado.md](enunciado.md).

**Repositório:** https://github.com/Kauhan33/projeto-python-compiladores

## Como funciona

1. **Análise léxica** ([lexer.py](lexer.py)): quebra a frase digitada em `Token`s
   classificados em `ACAO`, `DISPOSITIVO`, `LOCAL`, `VALOR`, `CONECTIVO` (artigos,
   preposições) ou `DESCONHECIDO` (palavra fora do vocabulário).
2. **Análise semântica** ([semantic.py](semantic.py)): valida se a combinação de tokens
   faz sentido (ex.: não é possível `ABRIR` uma `luz`), aplica o comando ao estado
   simulado da casa (`CasaInteligente`) e gera a resposta em texto, como a Alexa faria.
3. **Execução** ([main.py](main.py)): laço interativo que aceita comandos **falados ou
   digitados** ao mesmo tempo e mostra a resposta; também tem um modo `--demo` com
   comandos de exemplo.
4. **Voz** ([voice.py](voice.py)): transcreve um comando falado pelo microfone em texto
   (entra no mesmo pipeline léxico/semântico — a voz não tem um caminho de
   interpretação separado) e lê a resposta da Alexa em voz alta, em pt-BR.
5. **Palavra-chave** ([wakeword.py](wakeword.py)): filtra, *antes* da análise léxica, o
   que foi realmente dirigido à assistente — só falas que começam com "Alexa" contam.
   Tolera os erros de transcrição comuns do nome ("Alexia", "Alex", "Alex eu") por
   similaridade aproximada, sem confundir com fala comum.

## Vocabulário reconhecido

- **Ações:** ligar/acender/ativar, desligar/apagar/desativar, abrir, fechar,
  aumentar/subir, diminuir/baixar
- **Dispositivos:** luz, ventilador, ar condicionado, tv, porta, portão, cortina,
  tomada, alarme
- **Locais (opcional):** sala, quarto, cozinha, banheiro, quintal, garagem,
  escritório, varanda
- **Valores:** números, usados para definir o nível de ventilador/ar-condicionado/tv

## Como executar

Instale as dependências (necessárias para a voz) e rode:

```bash
pip install -r requirements.txt
python main.py            # microfone JÁ ATIVO + teclado, ao mesmo tempo (padrão)
```

```bash
python main.py --texto       # somente teclado, sem usar o microfone
python main.py --demo        # roda comandos de exemplo, incluindo erros propositais
python main.py --diagnostico # mostra o que esta máquina tem disponível para voz
```

Não é preciso ativar nada: ao iniciar, o programa já está ouvindo **e** aceitando texto
digitado. A diferença entre os dois:

| Entrada | Palavra-chave | Resposta em áudio | Exemplo |
|---|---|---|---|
| **Falando** | obrigatória | sim | `Alexa, ligar a luz da sala` |
| **Digitando** | não precisa | não (só na tela) | `ligar a luz da sala` |

Exemplo de sessão (voz e teclado misturados):

```
Você (voz): Alexa ligar a luz da sala
Alexa: Ok, ligando a luz da sala.          (falado em áudio)
Você (voz): agora tá funcionando      (ignorado: sem a palavra-chave 'Alexa')
abrir a luz da sala                   <- digitado, sem palavra-chave
Alexa: Desculpe, não é possível 'abrir' a luz.   (só na tela, sem áudio)
Você (voz): Alexa sair
Alexa: Até logo!
```

## Estado da casa: ações redundantes

A assistente guarda o estado de cada dispositivo **por local**, e mandar fazer algo que
já está feito não é tratado como execução — ela informa o estado atual. É a parte da
análise semântica que depende de contexto, não só das palavras da frase:

```
Você: ligar a luz do quarto
Alexa: Ok, ligando a luz do quarto.
Você: ligar a luz do quarto
Alexa: A luz do quarto já está acesa.      <- não "executa" de novo
Você: desligar a luz do quarto
Alexa: Ok, desligando a luz do quarto.
Você: desligar a luz do quarto
Alexa: A luz do quarto já está apagada.
```

Os particípios acompanham o dispositivo e o gênero: a luz fica *acesa/apagada*, a porta
*aberta/fechada*, o ventilador *ligado/desligado*, o alarme *ativado/desativado*. O mesmo
vale para os níveis — "já está no máximo", "já está no mínimo", "já está em 80".

**Todo dispositivo começa desligado** (e portas/cortinas fechadas), em cada local. Isso
explica uma resposta que parece estranha na primeira vez: mandar desligar uma luz que
nunca foi ligada responde "já está apagada", porque ela realmente está — não há
influência de outros locais. Cada par *(dispositivo, local)* tem estado próprio:

```
Você: ligar a luz do quarto
Alexa: Ok, ligando a luz do quarto.
Você: ligar a luz da cozinha
Alexa: Ok, ligando a luz da cozinha.       <- a cozinha é independente do quarto
Você: desligar a luz do banheiro
Alexa: A luz do banheiro já está apagada.  <- nunca foi ligada, logo já estava apagada
```

O programa informa esse estado inicial ao iniciar, e `test_mini_alexa.py` guarda uma
sessão real inteira como teste, justamente para garantir que os locais não se misturam.

## Funciona em qualquer computador?

Sim. O núcleo do exercício (análise léxica + análise semântica) usa **apenas a biblioteca
padrão do Python** — um teste automatizado verifica que `lexer.py` e `semantic.py` não
importam nenhuma biblioteca de voz. Tudo relacionado a áudio é opcional e degrada sozinho:

| Ambiente | O que acontece |
|---|---|
| Tudo instalado, com microfone e internet | voz + teclado, respostas faladas em pt-BR |
| Sem voz pt-BR instalada no sistema | usa o Google TTS (online) para falar em pt-BR |
| Sem internet | usa a voz do sistema; se não houver em português, fala na voz padrão |
| Sem microfone | avisa e continua só pelo teclado |
| Sem as bibliotecas de voz (`pip install` não rodado) | avisa e continua só pelo teclado |
| Sem placa de som / áudio falha | mostra o motivo uma vez e segue respondendo por escrito |

Em nenhum desses casos o programa quebra ou encerra. Para conferir o ambiente antes de
testar, rode `python main.py --diagnostico`, que lista o que está disponível; e
`python main.py --texto` roda sem tocar no microfone.

## Voz (palavra-chave + resposta em áudio)

- **Reconhecimento:** requer microfone e internet (transcrição via Google Web Speech
  API, pt-BR, sem chave necessária para uso limitado). A escuta contínua calibra o
  ruído ambiente **uma única vez**, ao entrar no modo de voz — não a cada comando —
  para não cortar o começo da fala (e da palavra-chave) a cada novo turno.
- **Aviso de "ouvindo":** enquanto a assistente fala a resposta, o microfone não capta
  nada — falar nesse intervalo perde justamente o começo da frase (o "Alexa"). Por isso
  a linha `>> ouvindo... (pode falar ou digitar)` reaparece a cada vez que o microfone
  volta a escutar. Silêncio não repete o aviso (o anterior continua valendo), mas som
  captado e não transcrito avisa `(não entendi o que foi falado — pode repetir)`, para
  não deixar ninguém esperando uma resposta que não vem.
- **Resposta em áudio, sempre em pt-BR:** tenta primeiro uma voz local do sistema
  operacional (pyttsx3/SAPI5 no Windows — offline, mais rápido), mas só usa essa via se
  encontrar uma voz **pt-BR/português** instalada. Se não encontrar nenhuma (caso comum
  em Windows sem pacote de idioma), cai automaticamente para o **Google Text-to-Speech**
  (gTTS, requer internet) — assim a resposta sai em português mesmo sem nada configurado
  no sistema. Para instalar uma voz pt-BR local no Windows (deixa mais rápido, sem
  depender de internet para falar): Configurações → Hora e Idioma → Voz → Adicionar
  vozes.
- **Um motor de voz novo por fala:** reaproveitar a instância do pyttsx3 parece natural,
  mas depois do primeiro `runAndWait()` o loop interno do motor é encerrado e as falas
  seguintes retornam sem produzir som — só a primeira resposta era falada. `voice.py`
  cria um motor por fala justamente para evitar isso (ver o teste de regressão em
  `test_voice.py`).

### Palavra-chave tolerante a erros de transcrição

O reconhecimento de fala erra bastante no nome da assistente. Em uso real apareceram
"Alexia", "Alexis" e até "Alex eu" (nome quebrado em duas palavras) — todas essas são
aceitas, por similaridade aproximada calibrada com transcrições reais:

| Frase ouvida | Comando extraído |
|---|---|
| `Alexa ligar a luz da sala` | `ligar a luz da sala` |
| `Alexia sair` | `sair` |
| `Alex eu sair` | `sair` |
| `agora tá funcionando` | *(ignorado — não é a palavra-chave)* |
| `Alexa tv` | `tv` *(não engole "tv": é um dispositivo)* |

Fala sem a palavra-chave **não gera nenhuma resposta** em texto ou áudio (a transcrição
aparece marcada como "ignorado" só para facilitar depurar o reconhecimento).

Digitar, por outro lado, **nunca** precisa da palavra-chave, e funciona em paralelo à
escuta (thread separada) — então não é preciso esperar o ciclo de escuta atual terminar
para digitar um comando ou "sair".

## Testes

```bash
python -m unittest discover -p "test_*.py" -v
```

São 65 testes, cobrindo a análise léxica, a análise semântica (incluindo as ações
redundantes e a independência entre locais), a detecção da palavra-chave com transcrições
reais, o aviso de "ouvindo", a portabilidade sem nenhuma biblioteca de voz instalada e
dois testes de regressão de bugs encontrados em uso real: o motor de voz que falava só na
primeira resposta e o `EOFError` de stdin não interativo que encerrava o modo de voz na
largada.

| Arquivo | Cobre |
|---|---|
| `test_mini_alexa.py` | lexer, semântica e estado (ações redundantes) |
| `test_wakeword.py` | palavra-chave e suas variações mal transcritas |
| `test_voice.py` | ordem dos motores de síntese e regressão do motor reutilizado |
| `test_main.py` | fluxo de interação, áudio só na voz, teclado em paralelo |
| `test_sem_dependencias.py` | portabilidade: rodar sem microfone/bibliotecas/internet |
