# VisionSecure AI - MVP de Detecao de Objetos Perigosos

MVP para deteccao de objetos perigosos (facas, bastoes e ferramentas de impacto) em imagens e video (webcam), com geracao de alertas via webhook e e-mail, usando YOLO.

## Sobre o Projeto

A VisionSecure AI e uma empresa especializada em monitoramento inteligente que busca aprimorar seus sistemas de seguranca utilizando inteligencia artificial. O objetivo e identificar em tempo real objetos potencialmente perigosos capturados por cameras de seguranca, alertando a central de monitoramento sobre situacoes de risco.

Este MVP (Minimum Viable Product) e capaz de identificar objetos perigosos em diferentes cenarios e gerar alertas automaticos.

### Funcionalidades

O sistema oferece deteccao automatizada de tres classes de objetos perigosos: facas (knife), bastoes (bat) e ferramentas de impacto (impact_tool). Alem disso, possui um sistema de alertas automaticos via webhook e e-mail quando objetos perigosos sao detectados, suporte a deteccao em tempo real via webcam, auto-rotulagem de imagens usando modelo YOLO pre-treinado, e treinamento de modelo customizado com dataset proprio.

### Arquitetura

O projeto utiliza YOLOv8n como arquitetura de rede neural, escolhida por ser uma variante leve e adequada para prototipos em tempo quase real. O dataset contem aproximadamente 4.000 imagens distribuidas entre amostras positivas (contendo objetos perigosos) e negativas (sem objetos perigosos), garantindo robustez e reducao de falsos positivos.

## Estrutura do Projeto

```
visionsecure-mvp/
├── alerts.py               # envio de alertas (webhook + e-mail)
├── auto_label.py           # auto-rotulagem usando YOLO pre-treinado
├── config.py               # leitura de config.yaml e .env
├── config.yaml             # arquivo de configuracao principal
├── config_example.yaml     # exemplo de configuracao
├── detection.py            # funcoes de deteccao e construcao de payload
├── train_model.py          # treinamento do modelo + graficos + avaliacao
├── webcam_main.py          # loop principal da webcam (inferencia + alertas)
├── webhook_server.py       # servidor FastAPI para receber alertas
├── requirements.txt        # dependencias Python
├── .env.example            # exemplo de variaveis de ambiente
├── .gitignore              # arquivos ignorados pelo git
└── data/
    ├── raw/                # imagens sem rotulo (entrada da auto-rotulagem)
    ├── auto_labeled/
    │   ├── images/         # imagens apos auto-rotulagem
    │   └── labels/         # labels YOLO gerados automaticamente
    ├── images/
    │   ├── train/          # imagens de treino
    │   └── val/            # imagens de validacao
    ├── labels/
    │   ├── train/          # labels YOLO de treino
    │   └── val/            # labels YOLO de validacao
    └── dataset.yaml        # definicao do dataset no formato YOLO
```

## Configuracao do Ambiente (Windows 11)

### Pre-requisitos

Para executar este projeto voce precisara de Windows 11, Python 3.10 ou superior, Git (opcional, para clonar o repositorio), e opcionalmente uma GPU NVIDIA com drivers atualizados para acelerar o treinamento e inferencia.

### Passo 1: Instalar Python

Baixe o Python em https://www.python.org/downloads/windows/ e durante a instalacao marque a opcao "Add Python to PATH". Apos a instalacao, verifique se foi instalado corretamente abrindo o Prompt de Comando ou PowerShell e executando:

```bash
python --version
```

### Passo 2: Obter o Projeto

Voce pode clonar o repositorio usando Git:

```bash
git clone https://github.com/MatheusTalpe/TechChallenge05.git
cd TechChallenge05
```

Ou baixe o ZIP do projeto, extraia em uma pasta (por exemplo, `C:\TechChallenge05`) e abra o Prompt de Comando ou PowerShell nessa pasta.

### Passo 3: Criar Ambiente Virtual e Instalar Dependencias

No Prompt de Comando ou PowerShell, dentro da pasta do projeto, execute os seguintes comandos:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Passo 4: Configurar Variaveis de Ambiente

Copie o arquivo de exemplo e edite com suas credenciais:

```bash
copy .env.example .env
```

Abra o arquivo `.env` em um editor de texto e configure as credenciais de e-mail:

```
EMAIL_SMTP_SERVER=smtp.seuprovedor.com
EMAIL_SMTP_PORT=587
EMAIL_USE_TLS=true
EMAIL_USERNAME=seu_email@dominio.com
EMAIL_PASSWORD=sua_senha
EMAIL_FROM=alertas@visionsecure.ai
EMAIL_TO=destinatario@dominio.com
```

### Passo 5: Verificar config.yaml

O arquivo `config.yaml` ja vem configurado com valores padrao. Verifique se os caminhos e parametros estao corretos para seu ambiente. Se necessario, use `config_example.yaml` como referencia.

## Execucao Passo a Passo

### 1. Auto-Rotulagem (Opcional)

Se voce tiver imagens sem rotulo que deseja processar, coloque-as na pasta `data/raw/` e execute:

```bash
python auto_label.py
```

Este script aplica um modelo YOLO pre-treinado para gerar automaticamente os rotulos das imagens, salvando os resultados em `data/auto_labeled/`.

### 2. Treinamento do Modelo

Antes de treinar, certifique-se de que existem imagens e labels nas pastas `data/images/train/`, `data/images/val/`, `data/labels/train/` e `data/labels/val/`.

Execute o treinamento:

```bash
python train_model.py
```

O script ira treinar o modelo YOLOv8n com os parametros definidos em `config.yaml`, gerar graficos de metricas (perdas, mAP, precisao, recall), executar avaliacao final e exibir metricas de assertividade, e salvar o melhor modelo em `runs/detect/train/weights/best.pt`.

### 3. Iniciar Servidor de Webhook (Opcional)

Em um terminal separado, inicie o servidor que recebera os alertas:

```bash
.venv\Scripts\activate
python webhook_server.py
```

O servidor FastAPI sera iniciado em `http://localhost:8000/alert` e salvara cada alerta recebido na pasta `alert_logs/`.

### 4. Deteccao em Tempo Real via Webcam

Em outro terminal, execute a deteccao:

```bash
.venv\Scripts\activate
python webcam_main.py
```

O script ira carregar o modelo treinado, abrir a webcam padrao, processar frames em tempo real detectando objetos perigosos, desenhar bounding boxes na janela de video, e enviar alertas via webhook e e-mail quando deteccoes persistentes forem identificadas.

Pressione `q` para encerrar a deteccao.

## Resumo dos Comandos

```bash
# Ativar ambiente virtual
.venv\Scripts\activate

# Auto-rotulagem (opcional)
python auto_label.py

# Treinar o modelo
python train_model.py

# Servidor de alertas (em terminal separado)
python webhook_server.py

# Deteccao em tempo real via webcam
python webcam_main.py
```

## Metricas e Avaliacao

Apos o treinamento, o sistema exibe as seguintes metricas: mAP@0.50 (mean Average Precision), mAP@0.50:0.95, Precisao media, e Recall medio. O nivel de assertividade e classificado como ALTA (mAP >= 0.8), MEDIA (mAP >= 0.6) ou BAIXA (mAP < 0.6).

Os graficos gerados incluem `losses.png` (evolucao das perdas de treino/validacao), `map.png` (evolucao do mAP), e `precision_recall.png` (evolucao de precisao e recall).

## Sistema de Alertas

O sistema de alertas e acionado quando uma deteccao persiste por um numero minimo de frames consecutivos (configuravel em `alerts.min_persistent_frames`). Cada alerta contem timestamp, identificador da camera, lista de objetos detectados com classe, confianca e bounding box, nivel de severidade (alta para facas, media para outros), e caminho do frame salvo.

Os alertas sao enviados via webhook HTTP POST para a URL configurada e via e-mail SMTP para os destinatarios configurados.

## Classes Detectadas

O modelo detecta tres classes de objetos perigosos: knife (faca) com severidade alta, bat (bastao) com severidade media, e impact_tool (ferramenta de impacto como martelo, chave inglesa) com severidade media.

## Requisitos de Hardware

Para treinamento recomenda-se GPU NVIDIA com pelo menos 4GB de VRAM, 16GB de RAM, e processador moderno (Intel i5/AMD Ryzen 5 ou superior). Para inferencia em tempo real, uma GPU e recomendada para melhor performance, mas o sistema tambem funciona em CPU.

## Solucao de Problemas

Se a webcam nao abrir, verifique se outra aplicacao esta usando a camera e se os drivers estao atualizados. Se ocorrer erro de memoria durante o treinamento, reduza o `batch` em `config.yaml` de 32 para 16 ou 8. Se os e-mails nao forem enviados, verifique as credenciais no arquivo `.env` e se o provedor permite acesso SMTP.

## Licenca

Este projeto foi desenvolvido como parte do Tech Challenge - Fase 5.
