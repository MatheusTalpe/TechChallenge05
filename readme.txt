VisionSecure AI – MVP de Detecção de Objetos Cortantes
MVP para detecção de objetos perigosos (facas, bastões e ferramentas de impacto) em imagens e vídeo (webcam), com geração de alertas via webhook e e‑mail, usando YOLO.

1. Justificativa das Escolhas de Dataset e Treinamento
A definição do volume de dados e dos hiperparâmetros de treinamento foi guiada por um compromisso entre qualidade do modelo e tempo de processamento, considerando a infraestrutura utilizada (CPU Ryzen 7 5700X3D, 32 GB de RAM e GPU RTX 5070 Ti).

Optou-se por um conjunto de aproximadamente 4.000 imagens, distribuídas entre amostras positivas (contendo facas, bastões e ferramentas de impacto) e negativas (sem objetos cortantes), pois essa ordem de grandeza é geralmente suficiente para treinar modelos de detecção de poucos objetos com capacidade de generalização adequada, sem tornar o tempo de treino proibitivo. A inclusão de um número significativo de imagens negativas é essencial para reduzir falsos positivos e ensinar ao modelo que a ausência de objetos perigosos é um estado frequente e esperado no contexto de monitoramento.

Como arquitetura, foi escolhido inicialmente o modelo YOLOv8n, por ser uma variante leve, adequada para protótipos em tempo quase real, permitindo testar rapidamente diferentes combinações de dados e ajustes. Para esse modelo, adotaram-se imagens redimensionadas para 640×640 pixels, 75 épocas de treinamento e batch size 32 (ajustável para 16 em caso de limitação de memória), valores que exploram razoavelmente o espaço de hipóteses sem causar sobrecarga excessiva na GPU. Essa configuração proporciona um bom equilíbrio entre tempo de execução (na ordem de dezenas de minutos) e desempenho esperado (mAP, precisão e recall consistentes), sendo adequada para um MVP acadêmico com foco em viabilidade e demonstração prática do sistema de detecção de objetos cortantes.

2. Estrutura do Projeto
text

Collapse


 Copy

visionsecure-mvp/
├─ alerts.py               # envio de alertas (webhook + e-mail)
├─ auto_label.py           # auto-rotulagem (pseudo-labeling) usando YOLO pré-treinado
├─ config.py               # leitura de config.yaml e .env
├─ config.yaml             # arquivo de configuração principal (já pronto no projeto)
├─ detection.py            # funções de detecção e construção de payload
├─ train_model.py          # treinamento do modelo + gráficos + avaliação
├─ webcam_main.py          # loop principal da webcam (inferência + alertas)
├─ webhook_server.py       # servidor FastAPI para receber alertas (webhook)
├─ annotation_tool.py      # anotação manual (opcional, para refinar rótulos)
├─ requirements.txt
├─ README.md
├─ .env                    # credenciais de e-mail (NÃO versionar)
└─ data/
   ├─ raw/                 # imagens sem rótulo (entrada da auto-rotulagem)
   ├─ auto_labeled/
   │   ├─ images/          # imagens após auto-rotulagem
   │   └─ labels/          # labels YOLO gerados automaticamente
   ├─ images/
   │   ├─ train/           # imagens de treino
   │   └─ val/             # imagens de validação
   ├─ labels/
   │   ├─ train/           # labels YOLO de treino
   │   └─ val/             # labels YOLO de validação
   └─ dataset.yaml         # definição do dataset no formato YOLO
3. Configuração do Ambiente (Windows 11)
3.1. Pré‑requisitos
Windows 11
Python 3.10+
(Opcional) Git
(Opcional) GPU NVIDIA com drivers atualizados (para usar a RTX 5070 Ti)
3.2. Instalar Python
Baixe em: https://www.python.org/downloads/windows/
Instale marcando “Add Python to PATH”.
Verifique:
bash

Collapse


 Copy

python --version
3.3. Obter o projeto
bash

Collapse


 Copy

git clone <URL-do-repositório> visionsecure-mvp
cd visionsecure-mvp
Ou copie a pasta do projeto para algo como C:\visionsecure-mvp.

3.4. Criar ambiente virtual e instalar dependências
No Prompt/PowerShell na pasta do projeto:

bash

Collapse


 Copy

python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
3.5. Verificar config.yaml e criar .env
O projeto já possui um config.yaml pronto. Abra-o apenas para confirmar/ajustar, se necessário, os seguintes pontos:

yaml

Collapse


 Copy

project_name: "visionsecure_mvp"

data_yaml: "./data/dataset.yaml"

model_name: "yolov8n.pt"

runs_dir: "./runs"

train:
  imgsz: 640
  epochs: 75
  batch: 32        # reduza para 16 se faltar memória na GPU
  device: 0        # 0 = primeira GPU; -1 = CPU
  patience: 15

inference:
  weights: "./runs/detect/train/weights/best.pt"   # será atualizado depois do treino
  conf_thres: 0.5
  iou_thres: 0.45
  classes_of_interest: ["knife", "bat", "impact_tool"]

stream:
  source: 0
  fps_process: 5

alerts:
  min_persistent_frames: 3
  webhook_url: "http://localhost:8000/alert"
  send_frame: true
  email:
    enabled: true

auto_label:
  weights: "runs/pretrained/weapons.pt"  # modelo YOLO pré-treinado p/ armas/objetos
  conf_thres: 0.5
  iou_thres: 0.45
  classes_of_interest: ["knife", "bat", "impact_tool"]
Crie o arquivo .env (não faça commit) com as credenciais de e‑mail:

env

Collapse


 Copy

EMAIL_SMTP_SERVER=smtp.seuprovedor.com
EMAIL_SMTP_PORT=587
EMAIL_USE_TLS=true
EMAIL_USERNAME=usuario@dominio.com
EMAIL_PASSWORD=SENHA
EMAIL_FROM=alertas@visionsecure.ai
EMAIL_TO=central@visionsecure.ai,outro@dominio.com
4. Passo 1 – Treinamento do Modelo (inclui anotação)
4.1. Preparar imagens brutas
Coloque imagens SEM rótulo em:

text

Collapse


 Copy

data/raw/
Idealmente:

Imagens com facas, bastões e ferramentas de impacto em diversos contextos.
Imagens SEM qualquer objeto cortante (negativas).
4.2. Auto‑rotulagem (pseudo‑labels)
Com o ambiente virtual ativo:

bash

Collapse


 Copy

python auto_label.py
O script:

Lê data/raw/.
Aplica o modelo pré‑treinado definido em auto_label.weights (no config.yaml).
Gera:
Imagens em data/auto_labeled/images/.
Labels YOLO em data/auto_labeled/labels/.
4.3. (Opcional) Anotação manual / correções
Para refinar rótulos em casos específicos:

bash

Collapse


 Copy

python annotation_tool.py
Você poderá desenhar bounding boxes manualmente e salvar no formato YOLO.

4.4. Organizar dataset (train/val)
A partir de data/auto_labeled/ (e eventuais anotações manuais), distribua:
text

Collapse


 Copy

data/images/train/   # subset para treino
data/images/val/     # subset para validação

data/labels/train/   # rótulos correspondentes
data/labels/val/
Verifique/ajuste data/dataset.yaml (já existe no projeto) para este formato:
yaml

Collapse


 Copy

path: ../data

train: images/train
val: images/val

names:
  0: knife
  1: bat
  2: impact_tool
O config.yaml já aponta para esse arquivo via data_yaml: "./data/dataset.yaml".

4.5. Executar o treinamento
bash

Collapse


 Copy

python train_model.py
O script:

Verifica se existem labels em data/labels/train.
Treina o modelo YOLO (model_name do config.yaml).
Salva pesos e logs em runs/detect/train/.
Gera gráficos:
losses.png
map.png
precision_recall.png
Executa avaliação final (validação) e imprime mAP, precisão, recall.
O melhor modelo é salvo em:

text

Collapse


 Copy

runs/detect/train/weights/best.pt
Atualize apenas se necessário o campo inference.weights no config.yaml (por padrão ele já aponta para esse caminho):

yaml

Collapse


 Copy

inference:
  weights: "runs/detect/train/weights/best.pt"
5. Passo 2 – Validação da Precisão do Modelo
A validação é executada automaticamente ao final do train_model.py.

Métricas no console:

mAP@0.50
mAP@0.50:0.95
Precisão média
Recall médio
Nível de assertividade (ALTA/MÉDIA/BAIXA) baseado em mAP@0.50.
Gráficos na pasta do experimento (por exemplo runs/detect/train/):

losses.png: evolução das perdas de treino/validação.
map.png: evolução do mAP.
precision_recall.png: evolução de precisão e recall.
6. Passo 3 – Execução em um Dataset de Imagens
Para testar o modelo em um conjunto de imagens estáticas:

Crie uma pasta de teste (se ainda não existir):
text

Collapse


 Copy

data/test_images/
Coloque as imagens a serem avaliadas nessa pasta.

A partir da lógica de detection.py e webcam_main.py, você pode (opcionalmente) criar um script detect_images.py que:

Carrega o modelo definido em inference.weights.
Percorre data/test_images/.
Roda inferência e salva as imagens anotadas em data/test_results/.
7. Passo 4 – Execução via Webcam (Detecção em Tempo Real)
7.1. (Opcional) Iniciar servidor de webhook
Em um terminal:

bash

Collapse


 Copy

.venv\Scripts\activate
python webhook_server.py
Sobe um servidor FastAPI em http://localhost:8000/alert.
Salva cada alerta recebido em alert_logs/ como JSON.
7.2. Rodar a detecção pela webcam
Em outro terminal:

bash

Collapse


 Copy

cd visionsecure-mvp
.venv\Scripts\activate
python webcam_main.py
O script:

Lê config.yaml e .env.
Carrega o modelo em inference.weights.
Abre a webcam (source: 0).
Processa frames a ~`fps_process` FPS.
Detecta knife, bat, impact_tool.
Desenha bounding boxes na janela.
Quando a detecção é persistente por min_persistent_frames:
Salva o frame (se send_frame = true).
Monta payload de alerta (timestamp, câmera, objetos, severidade, frame).
Envia webhook e e‑mail (se configurados).
Pressione q para encerrar a exibição da webcam.

8. Resumo dos Comandos Principais
bash

Collapse


 Copy

# Ativar ambiente
.venv\Scripts\activate

# Auto-rotulagem
python auto_label.py

# (Opcional) Refinar rótulos manualmente
python annotation_tool.py

# Treinar o modelo
python train_model.py

# (Opcional) Servidor de alertas (webhook)
python webhook_server.py

# Detecção em tempo real via webcam
python webcam_main.py