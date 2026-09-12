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

## Voz (reconhecimento + resposta em áudio)

- **Reconhecimento:** requer microfone e internet (transcrição via Google Web Speech
  API, pt-BR, sem chave necessária para uso limitado).
- **Resposta em áudio:** usa a síntese de voz do próprio sistema operacional (SAPI5 no
  Windows), então funciona offline. Se o Windows não tiver um pacote de voz em
  português instalado, cai automaticamente para a voz padrão (geralmente em inglês) —
  para instalar uma voz pt-BR: Configurações → Hora e Idioma → Voz → Adicionar vozes.

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

No **modo de voz contínuo**, a Alexa fica ouvindo o microfone repetidamente — cada
comando reconhecido é processado e respondido em texto **e** em áudio — até você dizer
ou **digitar** "sair" (digitar continua funcionando nesse modo: roda em paralelo, numa
thread separada, então não é preciso esperar a escuta para conseguir sair).

Se a biblioteca de reconhecimento não estiver instalada ou não houver microfone, o
programa avisa e continua funcionando normalmente em modo texto — a voz é opcional em
todos os sentidos: sem ela, o resto do programa funciona igual.

## Testes

```bash
python -m unittest discover -p "test_*.py" -v
```
