# train_rtdetr.py
# =============================================================================
# Script de Treinamento para o modelo RT-DETR (Real-Time Detection Transformer)
# =============================================================================
# Este script treina o modelo RT-DETR (arquitetura baseada em Transformer)
# para deteccao de objetos perigosos.
#
# Arquitetura: RT-DETR (Real-Time DEtection TRansformer)
# - Tipo: Rede Neural baseada em Transformer (mecanismos de atencao)
# - Caracteristicas: Hibrido CNN+Transformer, nao requer NMS, alta precisao
# - Modelo base: rtdetr-l (large) - versao balanceada entre precisao e velocidade
#
# Vantagem: Utiliza o mesmo formato de dataset do YOLO, permitindo
# reaproveitar os dados de treinamento sem conversao.
#
# Saida: Os pesos treinados sao salvos em ./runs/rtdetr/detectX/weights/best.pt
# =============================================================================

from ultralytics import RTDETR
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
    RT-DETR usa o mesmo formato de dataset do YOLO.
    """
    with open(original_yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    data_dir = original_yaml_path.parent.resolve()
    data["path"] = str(data_dir)
    
    temp_fd, temp_path = tempfile.mkstemp(suffix=".yaml", prefix="dataset_rtdetr_")
    with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    
    return temp_path


def plot_training_metrics(results_dir: Path, model_name: str = "RT-DETR"):
    """
    Le o results.csv gerado pelo treinamento e plota graficos de metricas.
    
    Args:
        results_dir: Diretorio onde os resultados foram salvos
        model_name: Nome do modelo para os titulos dos graficos
    """
    csv_path = results_dir / "results.csv"
    if not csv_path.exists():
        print("results.csv nao encontrado, nao sera possivel gerar graficos.")
        return

    df = pd.read_csv(csv_path)
    epochs = df.index

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
    plt.xlabel("Epoca")
    plt.ylabel("Loss")
    plt.title(f"{model_name} - Perdas de treino e validacao")
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
    plt.xlabel("Epoca")
    plt.ylabel("mAP")
    plt.title(f"{model_name} - Evolucao do mAP")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(results_dir / "map.png")
    plt.close()

    # 3) Precisao e Recall
    plt.figure(figsize=(8, 5))
    if "metrics/precision" in df.columns:
        plt.plot(epochs, df["metrics/precision"], label="Precisao")
    if "metrics/recall" in df.columns:
        plt.plot(epochs, df["metrics/recall"], label="Recall")
    plt.xlabel("Epoca")
    plt.ylabel("Valor")
    plt.title(f"{model_name} - Precisao e Recall por epoca")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(results_dir / "precision_recall.png")
    plt.close()

    print(f"Graficos salvos em: {results_dir}")


def main():
    """
    Funcao principal de treinamento do modelo RT-DETR.
    
    Configuracoes sao lidas de config.yaml:
    - train.rtdetr.* : parametros especificos do RT-DETR
    - train.* : parametros gerais de treinamento
    """
    print("=" * 60)
    print("TREINAMENTO DO MODELO RT-DETR (Real-Time Detection Transformer)")
    print("Arquitetura: Transformer (mecanismos de atencao)")
    print("=" * 60)
    
    cfg = load_yaml_config()

    # Criar dataset.yaml temporario com caminhos absolutos
    script_dir = Path(__file__).parent.resolve()
    original_data_yaml = script_dir / cfg["data_yaml"]
    data_yaml = create_dataset_yaml_with_absolute_path(original_data_yaml)
    
    # Configuracoes especificas do RT-DETR
    rtdetr_cfg = cfg.get("train", {}).get("rtdetr", {})
    train_cfg = cfg.get("train", {})
    
    # Modelo base RT-DETR
    # Opcoes: rtdetr-l (large), rtdetr-x (extra-large)
    model_name = rtdetr_cfg.get("model", "rtdetr-l.pt")
    
    # Diretorio de saida para RT-DETR (separado do YOLO)
    runs_dir = cfg.get("runs_dir", "./runs")
    rtdetr_runs_dir = f"{runs_dir}/rtdetr"

    # Verifica se existem labels na pasta de treino
    labels_train_dir = Path("data/labels/train")
    if not labels_train_dir.exists() or not any(labels_train_dir.glob("*.txt")):
        print("Nenhum arquivo de anotacao encontrado em data/labels/train/")
        print("Crie o dataset antes de treinar.")
        print("NOTA: RT-DETR usa o mesmo formato de dataset do YOLO!")
        return

    # Carrega modelo base RT-DETR
    print(f"\nCarregando modelo base: {model_name}")
    model = RTDETR(model_name)

    # Parametros de treinamento
    imgsz = rtdetr_cfg.get("imgsz", train_cfg.get("imgsz", 640))
    epochs = rtdetr_cfg.get("epochs", train_cfg.get("epochs", 40))
    batch = rtdetr_cfg.get("batch", train_cfg.get("batch", 4))  # RT-DETR usa mais memoria
    device = rtdetr_cfg.get("device", train_cfg.get("device", 0))
    patience = rtdetr_cfg.get("patience", train_cfg.get("patience", 10))

    print(f"\nParametros de treinamento RT-DETR:")
    print(f"  - Modelo: {model_name}")
    print(f"  - Tamanho da imagem: {imgsz}")
    print(f"  - Epocas: {epochs}")
    print(f"  - Batch size: {batch}")
    print(f"  - Device: {device}")
    print(f"  - Patience: {patience}")
    print(f"  - Saida: {rtdetr_runs_dir}/detect/")
    print("\nNOTA: RT-DETR e mais lento que YOLO mas pode ter maior precisao.")

    # Treinamento
    print("\nIniciando treinamento RT-DETR...")
    results = model.train(
        data=data_yaml,
        imgsz=imgsz,
        epochs=epochs,
        batch=batch,
        device=device,
        project=rtdetr_runs_dir,
        name="detect",
        patience=patience,
        workers=0,  # Desabilita multiprocessing para evitar erros de memoria no Windows
        amp=False,  # Desabilita AMP para evitar NaN em GPUs como GTX 1660 Ti
        plots=False,  # Desabilita plots durante treinamento para evitar erro de memoria
    )

    best_weights_path = results.save_dir / "weights" / "best.pt"
    print("\n" + "=" * 60)
    print("TREINAMENTO RT-DETR FINALIZADO!")
    print("=" * 60)
    print(f"Melhor modelo salvo em: {best_weights_path}")

    # Gera graficos
    print("\nGerando graficos de metricas...")
    plot_training_metrics(results.save_dir, "RT-DETR")

    # Avaliacao final
    print("\nCarregando melhor modelo para avaliacao final...")
    best_model = RTDETR(str(best_weights_path))

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
    print("RESULTADOS DE AVALIACAO - MODELO RT-DETR")
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
    print(f'  inference.rtdetr.weights: "{best_weights_path}"')


if __name__ == "__main__":
    main()
