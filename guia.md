VisionSecure AI – Guia Completo de Execução do MVP
MVP para detecção de objetos perigosos (facas, bastões, ferramentas de impacto) em vídeo de webcam, com alertas via webhook e e‑mail, usando YOLO.

1. Pré‑requisitos e Configuração no Windows 11
1.1. Instalar Python
Acesse: https://www.python.org/downloads/windows/
Baixe a versão Python 3.10+.
Durante a instalação:
Marque a opção “Add Python to PATH”.
Complete a instalação.
Para verificar:

bash

Collapse


 Copy

python --version
1.2. (Opcional) Instalar Git
Se for clonar o repositório:

Baixe em: https://git-scm.com/downloads
Instale com opções padrão.
1.3. Obter o projeto
Opção 1 – Clonar com Git:

bash

Collapse


 Copy

git clone https://seu-repositorio/visionsecure-mvp.git
cd visionsecure-mvp
Opção 2 – Baixar ZIP:

Baixe o ZIP do projeto.
Extraia em uma pasta, por exemplo: C:\visionsecure-mvp.
Abra o Prompt de Comando ou PowerShell nessa pasta.
1.4. Criar ambiente virtual e instalar dependências
No Prompt/PowerShell dentro da pasta do projeto:

bash

Collapse


 Copy

python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
1.5. Configurar config.yaml
Copie o arquivo de exemplo:
bash

Collapse


 Copy

copy config_example.yaml config.yaml
Abra config.yaml em um editor de texto e verifique:
data_yaml: por padrão ./data/dataset.yaml (criaremos depois).
Em auto_label.weights: informe o caminho de um modelo YOLO pré‑treinado de armas/objetos perigosos. Exemplo:
yaml

Collapse


 Copy

auto_label:
  weights: "runs/pretrained/weapons.pt"
(Você deve baixar esse .pt de alguma fonte pública, como Roboflow ou GitHub.)
1.6. Configurar .env para envio de e‑mail
Na pasta raiz do projeto, crie um arquivo chamado .env com o conteúdo:

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
Ajuste todos os campos para o seu provedor de e‑mail real.
Não envie o .env para o repositório (credenciais sensíveis).
2. Execução da Auto‑Rotulação (Pseudo‑Labeling)
Objetivo: gerar automaticamente rótulos (bounding boxes) para imagens sem anotação, usando um modelo YOLO pré‑treinado.

2.1. Preparar imagens brutas
Coloque as imagens sem rótulo na pasta:

text

Collapse


 Copy

data/raw/
Aceitos: .jpg, .jpeg, .png, .bmp.
Exemplo de caminho: C:\visionsecure-mvp\data\raw\img001.jpg.
2.2. Ajustar seção auto_label no config.yaml
Exemplo mínimo:

yaml

Collapse


 Copy

auto_label:
  weights: "runs/pretrained/weapons.pt"
  conf_thres: 0.5
  iou_thres: 0.45
  classes_of_interest: ["knife", "bat", "impact_tool"]
weights: caminho do modelo YOLO pré‑treinado de armas/objetos (deve existir).
classes_of_interest: nomes de classes que o modelo pré‑treinado detecta e que você quer manter.
2.3. Rodar a auto‑rotulação
No terminal (com o ambiente .venv ativado):

bash

Collapse


 Copy

python auto_label.py
O que acontece:

Lê todas as imagens de data/raw/.
Aplica o modelo pré‑treinado.
Para cada imagem:
Copia a imagem para data/auto_labeled/images/.
Cria um arquivo .txt YOLO correspondente em data/auto_labeled/labels/.
Formato dos rótulos gerados:

0 → knife
1 → bat (ou bastão similar)
2 → impact_tool (martelo, chave inglesa, etc.)
3. Treinamento do Modelo com Arquivos Auto‑Rotulados
3.1. Organizar o dataset (train/val)
Decida um split, por exemplo:

80% das imagens para treino (train)
20% para validação (val)
A partir de data/auto_labeled/:

Copie imagens para:

text

Collapse


 Copy

data/images/train/
data/images/val/
Copie os rótulos correspondentes para:

text

Collapse


 Copy

data/labels/train/
data/labels/val/
Regras importantes:

Para cada imagem.jpg em data/images/train/, deve existir imagem.txt em data/labels/train/.
O mesmo para val.
3.2. Criar data/dataset.yaml (formato YOLO)
Na pasta data/, crie o arquivo dataset.yaml com algo como:

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
No config.yaml, confirme que:

yaml

Collapse


 Copy

data_yaml: "./data/dataset.yaml"
3.3. Treinar o modelo
No terminal, ainda com o ambiente virtual ativo:

bash

Collapse


 Copy

python train_model.py
O script:

Lê config.yaml.
Verifica se há labels em data/labels/train/.
Faz fine‑tuning do modelo base (por exemplo, yolov8n.pt).
Salva os resultados em runs/detect/train/.
O melhor modelo normalmente fica em:

text

Collapse


 Copy

runs/detect/train/weights/best.pt
3.4. Atualizar o modelo para inferência
No config.yaml, ajuste:

yaml

Collapse


 Copy

inference:
  weights: "runs/detect/train/weights/best.pt"
  conf_thres: 0.5
  iou_thres: 0.45
  classes_of_interest: ["knife", "bat", "impact_tool"]
4. Execução do Script de Detecção (Webcam + Alertas)
4.1. (Opcional) Iniciar o servidor de webhook
Se quiser receber e registrar os alertas via HTTP:

Em um terminal:
bash

Collapse


 Copy

cd C:\visionsecure-mvp
.venv\Scripts\activate
python webhook_server.py
Sobe um servidor FastAPI em http://localhost:8000/alert.
Cada alerta recebido é salvo em alert_logs/ como arquivo .json.
Garanta no config.yaml:

yaml

Collapse


 Copy

alerts:
  webhook_url: "http://localhost:8000/alert"
  send_frame: true
  min_persistent_frames: 3
  email:
    enabled: true
4.2. Rodar a detecção em tempo real pela webcam
Em outro terminal:
bash

Collapse


 Copy

cd C:\visionsecure-mvp
.venv\Scripts\activate
python webcam_main.py
O que o script faz:

Lê config.yaml e o .env.

Carrega o modelo treinado em inference.weights.

Abre a webcam padrão (stream.source: 0).

Processa frames em “quase tempo real”:

Roda YOLO para detectar knife, bat e impact_tool.
Desenha bounding boxes e rótulos na janela de vídeo.
Mantém um contador de frames consecutivos com detecção.
Quando a detecção é persistente por pelo menos min_persistent_frames:

Salva o frame em disco (se alerts.send_frame = true).
Monta um payload JSON com:
timestamp
camera_id (por padrão, webcam_0)
objects_detected (classe, confiança, bounding boxes)
severity (alta se for knife, média para outros)
frame_path (caminho do frame salvo)
Envia:
Webhook para alerts.webhook_url (se configurado).
E‑mail usando SMTP definido no .env.
Para encerrar, pressione q na janela da webcam.

5. Resumo do Fluxo Completo
Configurar ambiente no Windows 11

Instalar Python.
Criar .venv.
pip install -r requirements.txt.
Ajustar config.yaml e criar .env.
Auto‑rotulação

Colocar imagens sem rótulo em data/raw/.
Configurar auto_label.weights em config.yaml.
Executar:
bash

Collapse


 Copy

python auto_label.py
Treino com arquivos auto‑rotulados

Organizar:
data/images/train, data/images/val
data/labels/train, data/labels/val
Criar data/dataset.yaml.
Rodar:
bash

Collapse


 Copy

python train_model.py
Atualizar inference.weights com runs/detect/train/weights/best.pt.
Detecção em tempo real + alertas

(Opcional) Iniciar:
bash

Collapse


 Copy

python webhook_server.py
Iniciar detecção:
bash

Collapse


 Copy

python webcam_main.py
Ver detecções e alertas em tempo real (webcam, logs, e‑mail).
