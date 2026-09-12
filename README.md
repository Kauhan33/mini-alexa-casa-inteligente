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
python main.py --texto    # somente teclado, sem usar o microfone
python main.py --demo     # roda comandos de exemplo, incluindo erros propositais
```

Não é preciso ativar nada: ao iniciar, o programa já está ouvindo **e** aceitando texto
digitado. A única diferença entre os dois:

| Entrada | Palavra-chave | Exemplo |
|---|---|---|
| **Falando** | obrigatória | `Alexa, ligar a luz da sala` |
| **Digitando** | não precisa | `ligar a luz da sala` |

Exemplo de sessão (voz e teclado misturados):

```
Você (voz): Alexa ligar a luz da sala
Alexa: Ok, ligando a luz na sala.
Você (voz): agora tá funcionando      (ignorado: sem a palavra-chave 'Alexa')
abrir a luz da sala                   <- digitado, sem palavra-chave
Alexa: Desculpe, não é possível 'abrir' a luz.
Você (voz): Alexa sair
Alexa: Até logo!
```

## Voz (palavra-chave + resposta em áudio)

- **Reconhecimento:** requer microfone e internet (transcrição via Google Web Speech
  API, pt-BR, sem chave necessária para uso limitado). A escuta contínua calibra o
  ruído ambiente **uma única vez**, ao entrar no modo de voz — não a cada comando —
  para não cortar o começo da fala (e da palavra-chave) a cada novo turno.
- **Resposta em áudio, sempre em pt-BR:** tenta primeiro uma voz local do sistema
  operacional (pyttsx3/SAPI5 no Windows — offline, mais rápido), mas só usa essa via se
  encontrar uma voz **pt-BR/português** instalada. Se não encontrar nenhuma (caso comum
  em Windows sem pacote de idioma), cai automaticamente para o **Google Text-to-Speech**
  (gTTS, requer internet) — assim a resposta sai em português mesmo sem nada configurado
  no sistema. Para instalar uma voz pt-BR local no Windows (deixa mais rápido, sem
  depender de internet para falar): Configurações → Hora e Idioma → Voz → Adicionar
  vozes.

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

Se a biblioteca de reconhecimento não estiver instalada, ou não houver microfone
disponível, o programa avisa e continua funcionando normalmente só com o teclado — a voz
é opcional em todos os sentidos: sem ela, o resto do programa funciona igual.

## Testes

```bash
python -m unittest discover -p "test_*.py" -v
```
