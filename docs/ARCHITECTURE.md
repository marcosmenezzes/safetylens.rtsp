# Arquitetura do SafetyLens

Este documento explica o papel de cada pasta, módulo e função mantidos no projeto. Ele complementa o guia de uso do README e ajuda uma pessoa nova a descobrir onde alterar algo e por que aquela parte existe.

## Fluxo principal

```text
Câmera nativa/IP
       ↓
CameraRuntime (thread de captura)
       ↓
ImageProcessor → EPIDetector/YOLO
       ↓                  ↓
stream MJPEG         DatabaseManager
       ↓                  ↓
React ← API Flask ← SQLite
```

1. O navegador solicita `/api/camera/stream`.
2. `CameraRuntime` abre a fonte configurada e mantém uma thread de captura.
3. `ImageProcessor` aplica os ajustes definidos no painel.
4. `EPIDetector` executa o modelo, remove caixas concorrentes e desenha resultados.
5. O frame vira MJPEG para o navegador.
6. Quando há EPI ausente e o intervalo permite, `DatabaseManager` salva a captura.
7. A API consulta o SQLite para dashboard, histórico e estatísticas.

## Arquivos da raiz

- `Makefile`: atalhos para iniciar, parar, desenvolver, testar e acompanhar treinamento. Existe para esconder caminhos e comandos longos.
- `.gitignore`: mantém fora do Git configurações, bancos, datasets, runs, dependências, builds e caches.
- `config.example.yaml`: configuração pública sem câmera ou segredo pessoal. Deve ser copiada para `config.yaml`.
- `requirements.txt`: somente dependências Python importadas diretamente pelo sistema; dependências transitivas são resolvidas pelo `pip`.

## Backend: `src/core`

### `epis.py`

- `EPI_NAMES`: fonte única da ordem e do nome das oito classes; impede divergência entre banco e detector.
- `MISSING_EPI_IDS`: conjunto imutável das quatro classes que geram ocorrência.

### `config.py`

- `Config`: representa a configuração local em memória.
- `__init__`: escolhe o YAML padrão ou o caminho isolado fornecido pelos testes.
- `load_config`: carrega o YAML antes de qualquer leitura.
- `save_config`: grava em arquivo temporário e troca ao final para evitar arquivo parcial.
- `model_path`: resolve o peso YOLO sem depender da pasta atual do Terminal.
- `database_path`: resolve o SQLite pelo mesmo motivo.
- `camera_id`: informa o índice OpenCV da webcam.
- `camera_url`: lê a URL salva ou a substituição temporária `SAFETYLENS_CAMERA_URL`.
- `camera_source`: escolhe URL de rede ou índice nativo.
- `registered_cameras`: entrega uma cópia da lista salva.
- `camera_candidates`: valida nome/IP/porta e gera caminhos RTSP/HTTP conhecidos. Aceitar apenas IPv4 privado reduz risco de SSRF.
- `register_camera`: salva uma fonte validada e a torna ativa.
- `activate_camera`: seleciona uma fonte existente pelo IP.
- `remove_camera`: apaga uma fonte e retorna à webcam quando necessário.
- `activate_native_camera`: volta à webcam sem apagar cadastros.
- `camera_resolution`: normaliza a orientação da webcam para evitar corte/zoom.
- `min_confidence`: entrega o limite usado pelo YOLO.
- `delay_time`: entrega o intervalo mínimo entre evidências.
- `update_camera_settings`: aplica ajustes nas seções corretas e salva uma vez.

### `detection.py`

- `_overlap_over_smaller`: mede sobreposição relativa ao menor objeto.
- `_deduplicate`: elimina previsões duplicadas ou conflitantes e mantém a mais confiante.
- `EPIDetector`: mantém o modelo carregado durante a transmissão.
- `EPIDetector.__init__`: carrega peso, confiança e taxonomia.
- `EPIDetector.detect`: executa inferência, desenha caixas e retorna classes/ausências.
- `EPIDetector.update_min_confidence`: muda o filtro sem recarregar o modelo.
- `ImageProcessor`: agrupa ajustes aplicados antes da inferência.
- `ImageProcessor.adjust_image`: aplica brilho, contraste, nitidez e escala de cinza.

### `database.py`

- `initialize_database`: cria schema, classes e índices sem alterar registros existentes.
- `DatabaseManager`: coordena gravações assíncronas.
- `__init__`: prepara banco e um worker único para o SQLite.
- `get_connection`: abre conexão curta com chaves estrangeiras e espera por bloqueios breves.
- `execute_with_retry`: repete operações afetadas por contenção temporária.
- `log_detection`: agenda a gravação sem parar a câmera.
- `_log_detection_task`: deduplica classes e grava uma linha por EPI ausente.
- `close`: espera gravações pendentes antes de encerrar.
- `__del__`: proteção final se o encerramento explícito não ocorrer.

O banco usa `epis(id, nome)` como catálogo e `detections(id, timestamp, frame_data, epi_id)` como histórico. Bancos antigos podem conter `settings`; ela não é apagada automaticamente para preservar dados, mas não é usada pelo código atual.

## Backend web: `src/web`

### `__init__.py`

- `create_app`: mantém a fábrica como API pública para testes, mas faz o import sob demanda para que `python -m src.web.app` não carregue o módulo duas vezes.

### `app.py`

- `create_app`: fábrica Flask usada na execução e em testes isolados.
- `secure_headers`: aplica cabeçalhos de segurança a toda resposta.
- `frontend_assets`: entrega bundles do Vite.
- `images`: entrega as fotos da página Sobre.
- `frontend_app`: entrega a SPA para todas as rotas navegáveis.
- `main`: inicia somente em `127.0.0.1:5050` por padrão.

### `camera_runtime.py`

- `CameraRuntime`: estado compartilhado entre captura e requisições.
- `__init__`: cria locks, evento de parada, frame e telemetria sem abrir a câmera.
- `status`: devolve uma cópia do estado para evitar corrida com a thread.
- `ensure_started`: inicia no máximo uma thread quando o stream é solicitado.
- `restart`: reabre a fonte somente se ela já estava em uso.
- `stop`: sinaliza parada e libera o dispositivo.
- `update_confidence`: atualiza o detector ativo.
- `frames`: publica frames como partes MJPEG consumidas por `<img>`.
- `_run`: testa fontes, processa vídeo, salva alertas e atualiza telemetria.

### `api.py`

`create_api` concentra as rotas porque todas compartilham banco, validação de período e serialização. Os helpers continuam internos porque só têm um consumidor.

- `query`: usa uma conexão SQLite curta por thread.
- `parse_date`: aceita ISO 8601 e normaliza timezone.
- `period`: resolve filtros ou usa os últimos 30 dias.
- `sql_period`: cria condição SQL parametrizada.
- `serialize_detection`: produz JSON sem o BLOB da imagem.
- `require_camera`: separa testes de dados de uma aplicação completa.
- `json_body`: limita 4 KB e rejeita campos inesperados.
- `camera_payload`: monta o estado público sem URL/credenciais.
- `detections`, `total`, `by_epi`, `daily`: consultas reutilizadas pelas páginas.
- `invalid_request`: converte validação em HTTP 400 consistente.
- `health`: verifica servidor e banco.
- `camera`: retorna fonte, ajustes e telemetria.
- `camera_settings`: valida faixas e persiste ajustes.
- `cameras`: lista nome, IP, porta e seleção.
- `register_camera`: cadastra uma fonte local.
- `native_camera`: seleciona a webcam.
- `connect_camera`: repete conexão de uma fonte cadastrada.
- `delete_camera`: remove a fonte solicitada.
- `restart_camera`: repete a conexão atual.
- `camera_stream`: entrega MJPEG sem cache.
- `dashboard`: agrega resumo e eventos recentes.
- `detection_list`: pagina o histórico no mesmo universo da contagem.
- `analytics`: calcula participação, tendências e séries.
- `detection_image`: entrega JPEG por ID sem cache público.

## Frontend: `frontend/src`

### Entrada e dados

- `main.jsx`: monta o React e importa tokens, base, componentes e páginas.
- `App.jsx` / `App`: associa URL à página. Links nativos cobrem navegação sem dependência de roteador.
- `api.js` / `useApi`: busca JSON, cancela requisições antigas, repete falhas e oferece polling.
- `formatDate`: centraliza datas em português do Brasil.
- `buildQuery`: monta filtros com escape correto.
- `sendJson`: centraliza mutações e mensagens de erro.

### Componentes

- `AppShell`: sidebar, topbar, tema, responsividade e preferências locais.
- `Charts.smoothPath`: cria a curva cúbica dos gráficos SVG.
- `BarChart`: compara categorias.
- `LineChart`: mostra evolução temporal sem biblioteca externa.
- `DateRangeFilter`: valida início/fim antes da API.
- `DetectionTable`: lista eventos e abre evidência em `<dialog>` nativo.
- `Icon`: mantém SVGs locais e consistentes.
- `StatCard`: padroniza métricas e tons semânticos.
- `LoadingState`, `ErrorState`, `EmptyState`: distinguem espera, falha e ausência real de dados.

### Páginas e suas funções

- `Dashboard`: visão resumida e atalhos operacionais.
- `Monitoring`: stream, ajustes, seleção e cadastro de câmeras.
- `RangeField`: renderiza sliders a partir da definição de campo.
- `saveSettings`: persiste o conjunto de ajustes.
- `registerCamera`: cadastra uma fonte validada pelo backend.
- `useNativeCamera`: volta à webcam e renova o stream.
- `reconnectCamera`: tenta novamente uma câmera salva.
- `deleteCamera`: confirma e remove uma câmera.
- `Detections`: histórico paginado.
- `Detections.apply`: aplica filtros e volta à primeira página.
- `Analytics`: gráficos e comparações do período.
- `About`: missão, fluxo e equipe.

### Estilos

- `tokens.css`: cores, fontes, raios M3, medidas e temas.
- `global.css`: reset, tipografia, fundo e movimento reduzido.
- `components.css`: shell, botões, tabelas, modal, gráficos e estados.
- `pages.css`: composições exclusivas das páginas.

## Scripts de dados e treino

- `prepare_absent_ppe_video.py`: extrai vídeo e pré-anota regiões ausentes usando pose.
- `prepare_glove_pair_video.py`: cria pares controlados de mão com/sem luva.
- `prepare_headset_video.py`: cria exemplos de capacete ausente com abafador presente/ausente.
- `prepare_personal_dataset.py`: combina anotações MakeSense e frames próprios.
- `prepare_ppe_dataset.py`: converte ZIPs para oito classes e bloqueia ZIP Slip.
- `select_curated_positive_ppe.py`: seleciona 400 exemplos positivos e normaliza caixas.
- `train_personal.py`: reproduz o fine-tuning v10, instala o melhor peso e preserva backup.
- `watch_training.py`: lê `results.csv` e mostra métricas atuais.

Cada função desses scripts tem uma docstring junto ao código. Eles permanecem porque registram como os datasets e o peso ativo foram produzidos; os dados grandes ficam fora do Git.

## Testes

- `tests/test_camera_config.py`: IPv4/porta, DroidCam, persistência e remoção.
- `tests/test_epi_mapping.py`: ordem de classes e deduplicação.
- `tests/test_image_processor.py`: neutralidade dos ajustes padrão.
- `tests/test_web_api.py`: paginação, períodos, imagens, SSRF e configurações.
- `frontend/tests/app.spec.js`: páginas, responsividade, tema, câmera, gráficos, filtros e modal.

## Decisões intencionais

- **Sem React Router:** há poucas rotas e links nativos resolvem o fluxo atual.
- **Gráficos SVG próprios:** as visualizações são simples e não justificam outra dependência.
- **MJPEG:** funciona diretamente em `<img>`; WebRTC só vale quando latência/escala exigirem.
- **SQLite:** é local e portátil; um servidor de banco só será necessário com múltiplas instâncias concorrentes.
- **YAML:** é legível para uma instalação. Segredos futuros devem usar Keychain/secret manager.
- **Inferência em thread separada:** mantém Flask responsivo e carrega o modelo apenas uma vez.
