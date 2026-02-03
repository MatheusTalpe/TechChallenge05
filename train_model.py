# train_model.py
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
    Creates a temporary dataset.yaml with absolute paths for Windows compatibility.
    YOLO sometimes ignores relative paths, so we convert them to absolute paths.
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
    cfg = load_yaml_config()

    # Create temporary dataset.yaml with absolute paths for Windows compatibility
    script_dir = Path(__file__).parent.resolve()
    original_data_yaml = script_dir / cfg["data_yaml"]
    data_yaml = create_dataset_yaml_with_absolute_path(original_data_yaml)
    model_name = cfg.get("model_name", "yolov8n.pt")
    runs_dir = cfg.get("runs_dir", "./runs")
    train_cfg = cfg.get("train", {})

    # Verifica se existem labels na pasta de treino
    labels_train_dir = Path("data/labels/train")
    if not labels_train_dir.exists() or not any(labels_train_dir.glob("*.txt")):
        print("Nenhum arquivo de anotação encontrado em data/labels/train/")
        print("Crie o dataset (auto-rotulagem + organização) antes de treinar.")
        return

    # Carrega modelo base
    model = YOLO(model_name)

    # Treinamento
    print("Iniciando treinamento...")
    results = model.train(
        data=data_yaml,
        imgsz=train_cfg.get("imgsz", 640),
        epochs=train_cfg.get("epochs", 50),
        batch=train_cfg.get("batch", 8),
        device=train_cfg.get("device", 0),
        project=runs_dir,
        name="detect",
        patience=train_cfg.get("patience", 10),
        workers=0,  # Disable multiprocessing to avoid memory errors on Windows
    )

    best_weights_path = results.save_dir / "weights" / "best.pt"
    print("\nTreinamento finalizado!")
    print("Melhor modelo salvo em:", best_weights_path)

    # Gera gráficos com base no results.csv
    print("\nGerando gráficos de métricas (loss, mAP, precisão, recall)...")
    plot_training_metrics(results.save_dir)

    # Avaliação final usando o melhor modelo
    print("\nCarregando melhor modelo para avaliação final...")
    best_model = YOLO(str(best_weights_path))

    print("Iniciando avaliação (val)...")
    val_results = best_model.val(
        data=data_yaml,
        imgsz=train_cfg.get("imgsz", 640),
        batch=train_cfg.get("batch", 8),
        device=train_cfg.get("device", 0),
        verbose=False,
    )

    metrics = val_results.results_dict

    mAP50 = metrics.get("metrics/mAP50", None)
    mAP5095 = metrics.get("metrics/mAP50-95", None)
    precision = metrics.get("metrics/precision", None)
    recall = metrics.get("metrics/recall", None)

    print("\n=== RESULTADOS DE AVALIAÇÃO (ASSERTIVIDADE DO MODELO) ===")
    if mAP50 is not None:
        print(f"mAP@0.50 (mAP50):        {mAP50:.4f}")
    if mAP5095 is not None:
        print(f"mAP@0.50:0.95:           {mAP5095:.4f}")
    if precision is not None:
        print(f"Precisão média:          {precision:.4f}")
    if recall is not None:
        print(f"Revocação (Recall) méd.: {recall:.4f}")

    if mAP50 is not None:
        if mAP50 >= 0.8:
            nivel = "ALTA"
        elif mAP50 >= 0.6:
            nivel = "MÉDIA"
        else:
            nivel = "BAIXA"
        print(f"\nNível de assertividade (mAP@0.50): {nivel}")

    print("\nAvaliação concluída. Consulte também os gráficos gerados em:")
    print(results.save_dir)


if __name__ == "__main__":
    main()
