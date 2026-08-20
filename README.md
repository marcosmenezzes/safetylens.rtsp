# SafetyLens

O SafetyLens transforma câmeras comuns em uma ferramenta local de apoio à segurança do trabalho. O sistema analisa vídeo em tempo real com visão computacional, identifica a presença ou ausência de Equipamentos de Proteção Individual (EPIs), registra evidências e apresenta os resultados em um painel web.

> O SafetyLens é uma ferramenta de apoio. Ele não substitui inspeções, procedimentos de segurança, profissionais habilitados ou as obrigações legais da empresa.

## A história do projeto

O SafetyLens nasceu no SENAI com a proposta de tornar o monitoramento de EPIs mais acessível: usar uma câmera já disponível, processamento local e inteligência artificial para ajudar equipes a perceber situações de risco mais rapidamente.

O projeto conquistou o **segundo lugar em uma competição estadual do SENAI**. A experiência mostrou que a ideia poderia ir além da competição e evoluir como uma base aberta para estudo, pesquisa e criação de soluções reais de segurança industrial.

Hoje o SafetyLens é um projeto **open source**. O código pode ser estudado, modificado e reutilizado nos termos da [licença MIT](LICENSE). Modelos, bibliotecas e datasets de terceiros continuam sujeitos às licenças de seus respectivos autores.

## O que ele faz

- usa a câmera nativa do computador ou uma câmera IP da rede local;
- processa o vídeo localmente com OpenCV e YOLO;
- monitora oito classes: `Com_Oculos`, `Com_Capacete`, `Com_Luva`, `Com_Abafador`, `Sem_Oculos`, `Sem_Capacete`, `Sem_Luva` e `Sem_Abafador`;
- mostra o vídeo analisado em tempo real no navegador;
- permite ajustar brilho, contraste, nitidez e confiança mínima;
- salva ocorrências e capturas em SQLite;
- oferece histórico com filtros, paginação e visualização da evidência em modal;
- apresenta dashboard e estatísticas por período;
- mantém tema escuro e claro e funciona em desktop ou celular.

## Antes de começar

Você precisa de:

- macOS ou Linux;
- Python 3.11 ou mais recente;
- Node.js 20 ou mais recente;
- uma webcam ou câmera IP na mesma rede;
- o arquivo do modelo em `SafetyLens.IPCAMERA-main/model/best.pt`.

No macOS, permita que o Terminal/Python use a câmera em **Ajustes do Sistema → Privacidade e Segurança → Câmera**.

## Instalação passo a passo

Abra o Terminal, entre na pasta que contém o projeto e execute os comandos abaixo, um de cada vez.

### 1. Entre na pasta do projeto

```bash
cd /caminho/onde/voce/baixou/safetylens.rtsp
```

No computador original deste projeto, o caminho é:

```bash
cd /Users/marcosmenezes/Documents/GitHub/safetylens.rtsp
```

### 2. Crie o ambiente Python

```bash
python3 -m venv .venv
```

Não é necessário ativar o ambiente virtual para usar os comandos `make` deste projeto.

### 3. Instale as dependências Python

```bash
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r SafetyLens.IPCAMERA-main/requirements.txt
```

### 4. Instale o painel React

```bash
npm --prefix SafetyLens.IPCAMERA-main/frontend install
```

### 5. Crie a configuração local

Em uma instalação nova:

```bash
cp SafetyLens.IPCAMERA-main/config.example.yaml SafetyLens.IPCAMERA-main/config.yaml
```

O arquivo `config.yaml` guarda suas câmeras e ajustes locais. Ele não deve ser enviado ao Git porque uma URL RTSP pode conter usuário e senha.

### 6. Confira o modelo

O arquivo abaixo precisa existir:

```text
SafetyLens.IPCAMERA-main/model/best.pt
```

Sem esse arquivo a interface abre, mas a análise da câmera não consegue carregar o detector.

## Como iniciar

Na raiz do repositório, execute:

```bash
make start
```

Quando aparecer a mensagem do Flask, abra no navegador:

```text
http://127.0.0.1:5050
```

O primeiro acesso ao Monitoramento carrega o modelo e abre a câmera. Isso pode levar alguns segundos.

## Como parar e reiniciar

Se o programa estiver aberto no Terminal, pressione `Control + C`.

Para encerrar processos que ficaram em segundo plano:

```bash
make stop
```

Para reiniciar completamente:

```bash
make stop
make start
```

## Como usar a câmera nativa

1. Abra `http://127.0.0.1:5050/monitoring`.
2. Entre na aba **Câmeras**.
3. Clique em **Usar nativa**.
4. Autorize a câmera no sistema operacional se for solicitado.
5. Aguarde o status mudar para **Sistema online**.

Se a imagem estiver cortada, confira `camera.resolution` no `config.yaml`. Para webcam horizontal, use normalmente `width: 1920` e `height: 1080`.

## Como cadastrar uma câmera IP ou DroidCam

O computador e a câmera precisam estar na mesma rede.

1. Abra a aba **Câmeras** dentro do Monitoramento.
2. Informe um nome, por exemplo `Entrada principal`.
3. Informe o IPv4 mostrado pelo aplicativo ou pela câmera, por exemplo `192.168.1.20`.
4. Informe a porta. Câmeras RTSP costumam usar `554`; DroidCam costuma usar `4747`.
5. Clique em **Cadastrar e conectar**.
6. Se falhar, use **Tentar novamente** na câmera salva.

O SafetyLens testa caminhos RTSP e HTTP comuns. Alguns fabricantes exigem um caminho, usuário ou senha específico; nesse caso a integração precisa ser configurada conforme o manual da câmera.

## Páginas do painel

| Página | Endereço | Função |
| --- | --- | --- |
| Visão geral | `/` | Resume alertas, tendências e últimos eventos. |
| Monitoramento | `/monitoring` | Exibe o stream, ajustes e cadastro de câmeras. |
| Histórico | `/detections` | Filtra ocorrências e abre as capturas. |
| Estatísticas | `/analytics` | Compara volume, distribuição e tendências. |
| Sobre | `/about` | Explica missão, tecnologia e equipe. |

## Comandos principais

Execute sempre na raiz do repositório.

| Comando | O que faz |
| --- | --- |
| `make start` | Compila o React e inicia o sistema em `127.0.0.1:5050`. |
| `make stop` | Encerra Flask e Vite iniciados pelo projeto. |
| `make web` | Mesmo fluxo do `make start`; útil como nome explícito. |
| `make dev` | Inicia Flask e Vite juntos para desenvolvimento. |
| `make frontend` | Inicia somente o Vite em `127.0.0.1:5173`. |
| `make api` | Inicia somente Flask/API em `127.0.0.1:5050`. |
| `make test` | Executa testes Python, build React e Playwright. |
| `make train-status` | Mostra a última época e métricas do treinamento configurado. |
| `make train-live` | Atualiza as métricas continuamente até o treino terminar. |

## Desenvolvimento

Para alterar o frontend com atualização automática:

```bash
make dev
```

Use `http://127.0.0.1:5173`. O Vite encaminha `/api`, `/image` e o stream para o Flask em `5050`.

Para instalar o Chromium usado nos testes visuais:

```bash
npx --prefix SafetyLens.IPCAMERA-main/frontend playwright install chromium
```

Depois execute `make test`.

## Treinamento do modelo

O modelo ativo fica em `model/best.pt`. Datasets, vídeos, pesos intermediários e resultados de treino são dados locais grandes e por isso não entram no Git.

O treinamento atual é reproduzido por:

```bash
make train
```

Esse comando espera `datasets/safetylens-precision-v10/data.yaml`, usa Apple Metal (`device="mps"`), salva resultados em `model/runs/` e, ao concluir, faz backup do modelo anterior antes de instalar o novo.

As oito classes devem manter exatamente esta ordem em qualquer exportação YOLO:

```text
0 Com_Oculos
1 Com_Capacete
2 Com_Luva
3 Com_Abafador
4 Sem_Oculos
5 Sem_Capacete
6 Sem_Luva
7 Sem_Abafador
```

Os scripts em `SafetyLens.IPCAMERA-main/scripts/` documentam e reproduzem a preparação dos datasets usados durante a evolução do modelo. Pré-anotações automáticas devem sempre ser revisadas por uma pessoa antes do treino.

## Estrutura do projeto

```text
safetylens.rtsp/
├── Makefile                         # atalhos de operação
├── README.md                        # guia principal
├── LICENSE                          # licença do código
├── docs/ARCHITECTURE.md             # mapa técnico detalhado
└── SafetyLens.IPCAMERA-main/
    ├── config.example.yaml          # configuração segura de exemplo
    ├── config.yaml                  # configuração local ignorada pelo Git
    ├── frontend/                    # aplicação React e testes Playwright
    ├── model/best.pt                # peso YOLO usado em produção
    ├── scripts/                     # preparação de dados e treinamento
    ├── src/core/                    # configuração, detecção e SQLite
    ├── src/web/                     # Flask, API e runtime da câmera
    ├── static/img/                  # fotos usadas na página Sobre
    └── tests/                       # testes unitários e de contrato da API
```

O fluxo completo e a responsabilidade de cada função estão em [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Dados, privacidade e segurança

- O servidor escuta somente em `127.0.0.1` por padrão.
- O frontend e a API usam a mesma origem; CORS amplo não é habilitado.
- Apenas IPv4 privados são aceitos no cadastro para reduzir risco de SSRF.
- A API nunca devolve a URL interna da câmera.
- Capturas ficam em `detections.db` e podem conter pessoas ou ambientes privados.
- Banco, configurações, datasets e runs estão no `.gitignore`.
- Não exponha a aplicação em `0.0.0.0` sem autenticação, autorização e HTTPS.

Antes de publicar um fork, confirme que não há credenciais, bancos, imagens, vídeos ou pesos sem permissão no histórico Git.

## Problemas comuns

### `No module named src`

O comando foi executado na pasta errada. Volte para a raiz e use `make start`.

### `command not found: -m`

`-m` é uma opção do Python, não um comando sozinho. Use `make start` ou o comando `python -m ...` completo.

### Porta 5050 já está em uso

Execute `make stop` e depois `make start`.

### Câmera nativa não abre

- confirme a permissão de câmera do Terminal/Python;
- feche Photo Booth, Meet, Zoom ou outro programa que esteja usando a webcam;
- reinicie com `make stop` e `make start`.

### Câmera IP fica conectando

- confirme IP e porta no aplicativo da câmera;
- deixe celular e computador na mesma rede;
- teste novamente pelo botão da câmera salva;
- verifique se o fabricante exige credenciais ou caminho RTSP próprio.

## Equipe

- Ana Luisa — desenvolvimento;
- Davi Souza — inteligência artificial;
- Marcos Menezes — desenvolvimento full-stack;
- Rafael Marinato — experiência e interface.

## Licença

O código-fonte do SafetyLens é distribuído sob a [licença MIT](LICENSE). Dependências, modelos e conjuntos de dados mantêm suas próprias licenças e condições de uso.
