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
3. **Execução** ([main.py](main.py)): laço interativo que lê frases do usuário e mostra
   a resposta; também tem um modo `--demo` com comandos de exemplo.
4. **Voz** ([voice.py](voice.py)) *(opcional)*: transcreve um comando falado pelo
   microfone em texto (entra no mesmo pipeline léxico/semântico — a voz não tem um
   caminho de interpretação separado) e lê a resposta da Alexa em voz alta.

## Vocabulário reconhecido

- **Ações:** ligar/acender/ativar, desligar/apagar/desativar, abrir, fechar,
  aumentar/subir, diminuir/baixar
- **Dispositivos:** luz, ventilador, ar condicionado, tv, porta, portão, cortina,
  tomada, alarme
- **Locais (opcional):** sala, quarto, cozinha, banheiro, quintal, garagem,
  escritório, varanda
- **Valores:** números, usados para definir o nível de ventilador/ar-condicionado/tv

## Como executar

```bash
python main.py            # modo interativo (digitado)
python main.py --demo     # roda comandos de exemplo, incluindo erros propositais
```

Exemplo de sessão:

```
Você: Ligar a luz da sala
Alexa: Ok, ligando a luz na sala.

Você: Abrir a luz da sala
Alexa: Desculpe, não é possível 'abrir' a luz.
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

Instale as dependências extras primeiro:

```bash
pip install -r requirements.txt
```

Depois, use de um dos dois jeitos:

```bash
python main.py --voz      # já entra direto no modo de voz contínuo
```

```bash
python main.py            # modo texto normal...
Você: voz                 # ...mas digite "voz" (ou "ouvir"/"falar") para ativar o modo de voz
```

No **modo de voz contínuo**, a Alexa fica ouvindo o microfone o tempo todo, mas só
**responde** a frases que começam com a palavra-chave **"Alexa"** — qualquer outra fala
captada (conversa de fundo, TV, etc.) não gera nenhuma resposta em texto ou áudio (a
transcrição aparece marcada como "ignorado", só para facilitar depurar o reconhecimento):

```
Você (voz): isso é só uma conversa qualquer no fundo  (ignorado: sem a palavra-chave 'Alexa')
Você (voz): Alexa, ligar a luz da sala
Alexa: Ok, ligando a luz na sala.                          (falado em áudio também)
```

Toda resposta dada nesse modo — tanto por comando falado quanto digitado — é falada em
áudio além de impressa na tela. Para encerrar: diga **"Alexa, sair"** ou apenas
**digite** "sair" (digitar não precisa da palavra-chave, já que digitar já é um ato
deliberado; e roda em paralelo numa thread separada, então não é preciso esperar a
escuta atual terminar para conseguir sair).

Se a biblioteca de reconhecimento não estiver instalada ou não houver microfone, o
programa avisa e continua funcionando normalmente em modo texto — a voz é opcional em
todos os sentidos: sem ela, o resto do programa funciona igual.

## Testes

```bash
python -m unittest discover -p "test_*.py" -v
```
