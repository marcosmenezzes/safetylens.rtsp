# Safety Lens - Sistema de Monitoramento de EPIs com IA

## Descrição do Projeto

O **Safety Lens** é um sistema avançado de monitoramento de Equipamentos de Proteção Individual (EPIs) que utiliza inteligência artificial para identificação em tempo real. O sistema é composto por dois módulos principais que trabalham em conjunto:

1. **App Principal** (#app-principal.py): Responsável pela detecção em tempo real
2. **Servidor Web** (#servidor-web-site.py): Interface web para visualização e análise dos dados

## Estrutura do Projeto

```
SafetyLens-main/
├── #app-principal.py         # Aplicação principal de detecção
├── #servidor-web-site.py     # Servidor web Flask
├── #start-app-principal.bat  # Script para iniciar app principal
├── #start-servidor-web-site.bat # Script para iniciar servidor web
├── config.yaml              # Arquivo de configuração do sistema
├── requirements.txt         # Dependências do projeto
├── database/
│   └── epi_detections.db    # Banco de dados SQLite
├── model/
│   └── best.pt             # Modelo YOLO treinado
├── static/
│   └── style.css           # Estilos da interface web
└── templates/
    └── index.html          # Template da página web
```

## Funcionalidades

### 1. Detecção de EPIs (App Principal)
- Detecção em tempo real usando modelo YOLO v8
- Identificação de múltiplos EPIs:
  - Óculos de proteção
  - Capacete
  - Luvas
  - Abafador
- Interface gráfica com Tkinter para configurações
- Sistema de alertas visuais e sonoros configuráveis

### 2. Interface Web (Servidor Web)
- Visualização de detecções em tempo real
- Filtragem por data/hora
- Gráficos estatísticos:
  - Distribuição por tipo de EPI
  - Evolução temporal das detecções
- Visualização de imagens capturadas
- Atualização em tempo real via WebSocket

## Banco de Dados

O sistema utiliza SQLite com a seguinte estrutura:

### Tabelas

1. **epis**
   - id (INTEGER PRIMARY KEY)
   - nome (TEXT NOT NULL UNIQUE)

2. **detections**
   - id (INTEGER PRIMARY KEY)
   - timestamp (TEXT NOT NULL)
   - frame_data (BLOB)
   - epi_id (INTEGER, FOREIGN KEY)

3. **settings**
   - id (INTEGER PRIMARY KEY)
   - camera_resolution_w (INTEGER)
   - camera_resolution_h (INTEGER)
   - brightness_value (INTEGER)
   - contrast_value (INTEGER)
   - sharpness_value (INTEGER)
   - grayscale_value (INTEGER)
   - min_confidence_value (REAL)
   - alert_frequency_value (INTEGER)
   - alert_duration_value (INTEGER)
   - delay_time_value (INTEGER)
   - selected_epi_classes (TEXT)

## Configuração (config.yaml)

```yaml
alerts:
  delay_time: 10
  duration: 500
  frequency: 1000
camera:
  default_settings:
    brightness: 87
    contrast: 136
    grayscale: false
    sharpness: 1
  id: 0
  resolution:
    height: 720
    width: 1280
detection:
  classes:
    epi_ausentes:
    - 4  # Sem óculos
    - 5  # Sem capacete
    - 6  # Sem luva
    - 7  # Sem abafador
    epi_presentes:
    - 1  # Com óculos
    - 2  # Com capacete
    - 3  # Com luva
  min_confidence: 0.8
paths:
  database: database/epi_detections.db
  model: model/best.pt
```

## Instalação

1. Clone o repositório
2. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Como Executar

1. Inicie o App Principal:
```bash
#start-app-principal.bat
```
ou
```bash
python #app-principal.py
```

2. Inicie o Servidor Web:
```bash
#start-servidor-web-site.bat
```
ou
```bash
python #servidor-web-site.py
```

3. Acesse a interface web em: http://localhost:5000

## Dependências Principais

- opencv-python
- ultralytics (YOLO)
- numpy
- Pillow
- flask
- pyyaml
- tkinter

## Requisitos de Sistema

- Python 3.8+
- Webcam ou câmera USB
- Windows (para alertas sonoros via winsound)
- 4GB+ RAM recomendado

## Licença

Este projeto está sob a licença MIT.
