# train_yolo.py
# =============================================================================
# Script de Treinamento para o modelo YOLO (YOLOv8)
# =============================================================================
# Este script treina o modelo YOLOv8 (arquitetura baseada em CNN - Convolutional
# Neural Network) para deteccao de objetos perigosos.
#
# Arquitetura: YOLO (You Only Look Once)
# - Tipo: Rede Neural Convolucional (CNN)
# - Caracteristicas: Single-stage detector, rapido, ideal para tempo real
# - Modelo base: YOLOv8n (nano) - versao leve para prototipagem
#
# Uso: python train_yolo.py
#
# Configuracao: Edite a secao 'train.yolo' em config.yaml
#
# Saida: Os pesos treinados sao salvos em ./runs/yolo/detectX/weights/best.pt
# =============================================================================

from ultralytics import YOLO
from config import load_yaml_config
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import yaml
import tempfile
import os


def create_dataset_yaml_with_absolute_path(original_yaml_path: Path) -> str:
    """
    Cria um dataset.yaml temporario com caminhos absolutos para compatibilidade Windows.
    YOLO as vezes ignora caminhos relativos, entao convertemos para absolutos.
    """
    with open(original_yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    data_dir = original_yaml_path.parent.resolve()
    data["path"] = str(data_dir)
    
    temp_fd, temp_path = tempfile.mkstemp(suffix=".yaml", prefix="dataset_")
    with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    
    return temp_path


def plot_training_metrics(results_dir: Path):
    """
    Lê o results.csv gerado pelo YOLO e plota:
      - perdas de treino/validação
      - mAP50, mAP50-95
      - precisão e recall

    Salva as figuras em PNG dentro da pasta de treino.
    """
    csv_path = results_dir / "results.csv"
    if not csv_path.exists():
        print("results.csv não encontrado, não será possível gerar gráficos.")
        return

    df = pd.read_csv(csv_path)
    epochs = df.index  # cada linha = 1 época

    # 1) Perdas
    plt.figure(figsize=(8, 5))
    if "train/box_loss" in df.columns:
        plt.plot(epochs, df["train/box_loss"], label="Box loss (train)")
    if "train/cls_loss" in df.columns:
        plt.plot(epochs, df["train/cls_loss"], label="Cls loss (train)")
    if "val/box_loss" in df.columns:
        plt.plot(epochs, df["val/box_loss"], label="Box loss (val)")
    if "val/cls_loss" in df.columns:
        plt.plot(epochs, df["val/cls_loss"], label="Cls loss (val)")
    plt.xlabel("Época")
    plt.ylabel("Loss")
    plt.title("Perdas de treino e validação")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(results_dir / "losses.png")
    plt.close()

    # 2) mAP
    plt.figure(figsize=(8, 5))
    if "metrics/mAP50" in df.columns:
        plt.plot(epochs, df["metrics/mAP50"], label="mAP@0.50")
    if "metrics/mAP50-95" in df.columns:
        plt.plot(epochs, df["metrics/mAP50-95"], label="mAP@0.50:0.95")
    plt.xlabel("Época")
    plt.ylabel("mAP")
    plt.title("Evolução do mAP")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(results_dir / "map.png")
    plt.close()

    # 3) Precisão e Recall
    plt.figure(figsize=(8, 5))
    if "metrics/precision" in df.columns:
        plt.plot(epochs, df["metrics/precision"], label="Precisão")
    if "metrics/recall" in df.columns:
        plt.plot(epochs, df["metrics/recall"], label="Recall")
    plt.xlabel("Época")
    plt.ylabel("Valor")
    plt.title("Precisão e Recall por época")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(results_dir / "precision_recall.png")
    plt.close()

    print(f"Gráficos salvos em: {results_dir}")


def main():
    """
    Funcao principal de treinamento do modelo YOLO.
    
    Configuracoes sao lidas de config.yaml:
    - train.yolo.* : parametros especificos do YOLO
    - train.* : parametros gerais de treinamento (fallback)
    """
    print("=" * 60)
    print("TREINAMENTO DO MODELO YOLO (YOLOv8)")
    print("Arquitetura: CNN (Convolutional Neural Network)")
    print("=" * 60)
    
    cfg = load_yaml_config()

    # Criar dataset.yaml temporario com caminhos absolutos para compatibilidade Windows
    script_dir = Path(__file__).parent.resolve()
    original_data_yaml = script_dir / cfg["data_yaml"]
    data_yaml = create_dataset_yaml_with_absolute_path(original_data_yaml)
    
    # Configuracoes especificas do YOLO (com fallback para config geral)
    train_cfg = cfg.get("train", {})
    yolo_cfg = train_cfg.get("yolo", {})
    
    # Modelo base YOLO
    model_name = yolo_cfg.get("model", cfg.get("model_name", "yolov8n.pt"))
    
    # Diretorio de saida para YOLO (separado do RT-DETR)
    runs_dir = cfg.get("runs_dir", "./runs")
    yolo_runs_dir = f"{runs_dir}/yolo"

    # Verifica se existem labels na pasta de treino
    labels_train_dir = Path("data/labels/train")
    if not labels_train_dir.exists() or not any(labels_train_dir.glob("*.txt")):
        print("Nenhum arquivo de anotacao encontrado em data/labels/train/")
        print("Crie o dataset antes de treinar.")
        return

    # Parametros de treinamento (YOLO especifico com fallback para geral)
    imgsz = yolo_cfg.get("imgsz", train_cfg.get("imgsz", 640))
    epochs = yolo_cfg.get("epochs", train_cfg.get("epochs", 40))
    batch = yolo_cfg.get("batch", train_cfg.get("batch", 8))
    device = yolo_cfg.get("device", train_cfg.get("device", 0))
    patience = yolo_cfg.get("patience", train_cfg.get("patience", 10))

    print(f"\nParametros de treinamento YOLO:")
    print(f"  - Modelo: {model_name}")
    print(f"  - Tamanho da imagem: {imgsz}")
    print(f"  - Epocas: {epochs}")
    print(f"  - Batch size: {batch}")
    print(f"  - Device: {device}")
    print(f"  - Patience: {patience}")
    print(f"  - Saida: {yolo_runs_dir}/detect/")

    # Carrega modelo base YOLO
    print(f"\nCarregando modelo base: {model_name}")
    model = YOLO(model_name)

    # Treinamento
    print("\nIniciando treinamento YOLO...")
    results = model.train(
        data=data_yaml,
        imgsz=imgsz,
        epochs=epochs,
        batch=batch,
        device=device,
        project=yolo_runs_dir,
        name="detect",
        patience=patience,
        workers=0,  # Desabilita multiprocessing para evitar erros de memoria no Windows
        amp=False,  # Desabilita AMP para evitar NaN em GPUs como GTX 1660 Ti
    )

    best_weights_path = results.save_dir / "weights" / "best.pt"
    print("\n" + "=" * 60)
    print("TREINAMENTO YOLO FINALIZADO!")
    print("=" * 60)
    print(f"Melhor modelo salvo em: {best_weights_path}")

    # Gera graficos com base no results.csv
    print("\nGerando graficos de metricas (loss, mAP, precisao, recall)...")
    plot_training_metrics(results.save_dir)

    # Avaliacao final usando o melhor modelo
    print("\nCarregando melhor modelo para avaliacao final...")
    best_model = YOLO(str(best_weights_path))

    print("Iniciando avaliacao (val)...")
    val_results = best_model.val(
        data=data_yaml,
        imgsz=imgsz,
        batch=batch,
        device=device,
        verbose=False,
    )

    metrics = val_results.results_dict

    mAP50 = metrics.get("metrics/mAP50", None)
    mAP5095 = metrics.get("metrics/mAP50-95", None)
    precision = metrics.get("metrics/precision", None)
    recall = metrics.get("metrics/recall", None)

    print("\n" + "=" * 60)
    print("RESULTADOS DE AVALIACAO - MODELO YOLO")
    print("=" * 60)
    if mAP50 is not None:
        print(f"mAP@0.50 (mAP50):        {mAP50:.4f}")
    if mAP5095 is not None:
        print(f"mAP@0.50:0.95:           {mAP5095:.4f}")
    if precision is not None:
        print(f"Precisao media:          {precision:.4f}")
    if recall is not None:
        print(f"Revocacao (Recall) med.: {recall:.4f}")

    if mAP50 is not None:
        if mAP50 >= 0.8:
            nivel = "ALTA"
        elif mAP50 >= 0.6:
            nivel = "MEDIA"
        else:
            nivel = "BAIXA"
        print(f"\nNivel de assertividade (mAP@0.50): {nivel}")

    print(f"\nResultados completos em: {results.save_dir}")
    print("\nPara usar este modelo na deteccao, configure em config.yaml:")
    print(f'  inference.yolo.weights: "{best_weights_path}"')


if __name__ == "__main__":
    main()
