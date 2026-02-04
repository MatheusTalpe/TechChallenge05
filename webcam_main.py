# webcam_main.py
# =============================================================================
# Script de Deteccao em Tempo Real via Webcam
# =============================================================================
# Este script realiza deteccao de objetos perigosos em tempo real usando a
# webcam. Suporta dois modelos de deteccao:
#
# - YOLO (YOLOv8): Arquitetura CNN, rapido (~30+ FPS)
# - RT-DETR: Arquitetura Transformer, maior precisao, mais lento (~5-10 FPS)
#
# Para alternar entre os modelos, edite 'inference.model_type' em config.yaml:
#   model_type: "yolo"   # Para usar YOLO
#   model_type: "rtdetr" # Para usar RT-DETR
#
# Uso: python webcam_main.py
# =============================================================================

import time
import cv2
import os
from pathlib import Path

from config import load_yaml_config, load_email_env
from detection import (
    load_model,
    run_inference,
    save_frame,
    build_alert_payload,
)
from alerts import send_webhook_alert, send_email_alert


def find_best_weights(model_runs_dir: str) -> str:
    """
    Encontra o melhor arquivo de pesos (best.pt) dentre todos os runs de treinamento
    de um modelo especifico.
    
    Args:
        model_runs_dir: Diretorio de runs do modelo (ex: ./runs/yolo ou ./runs/rtdetr)
        
    Returns:
        Caminho para o melhor arquivo de pesos encontrado, ou None se nao encontrar
    """
    runs_path = Path(model_runs_dir)
    if not runs_path.exists():
        return None
    
    best_weights = None
    latest_mtime = 0
    
    for run_dir in runs_path.iterdir():
        if not run_dir.is_dir():
            continue
        
        weights_path = run_dir / "weights" / "best.pt"
        if weights_path.exists():
            mtime = weights_path.stat().st_mtime
            if mtime > latest_mtime:
                latest_mtime = mtime
                best_weights = str(weights_path)
    
    return best_weights


def get_model_weights(cfg: dict, model_type: str) -> str:
    """
    Determina o caminho dos pesos do modelo a ser usado.
    Primeiro tenta usar o caminho configurado, se nao existir,
    busca automaticamente o melhor modelo disponivel.
    
    Args:
        cfg: Configuracao carregada do config.yaml
        model_type: Tipo do modelo ("yolo" ou "rtdetr")
        
    Returns:
        Caminho para os pesos do modelo
        
    Raises:
        FileNotFoundError: Se nenhum modelo for encontrado
    """
    inf_cfg = cfg["inference"]
    runs_dir = cfg.get("runs_dir", "./runs")
    
    # Busca configuracao especifica do modelo
    model_cfg = inf_cfg.get(model_type, {})
    configured_weights = model_cfg.get("weights", "")
    
    # Diretorio de runs especifico do modelo
    model_runs_dir = f"{runs_dir}/{model_type}"
    
    if configured_weights and os.path.exists(configured_weights):
        print(f"[{model_type.upper()}] Usando modelo configurado: {configured_weights}")
        return configured_weights
    
    print(f"[{model_type.upper()}] Modelo configurado nao encontrado: {configured_weights}")
    print(f"[{model_type.upper()}] Buscando melhor modelo disponivel em {model_runs_dir}...")
    
    best_weights = find_best_weights(model_runs_dir)
    
    if best_weights:
        print(f"[{model_type.upper()}] Modelo encontrado automaticamente: {best_weights}")
        return best_weights
    
    # Fallback: buscar em runs antigos (compatibilidade com estrutura anterior)
    old_runs_dir = runs_dir
    best_weights = find_best_weights(old_runs_dir)
    if best_weights:
        print(f"[{model_type.upper()}] Modelo encontrado em estrutura antiga: {best_weights}")
        return best_weights
    
    raise FileNotFoundError(
        f"Nenhum modelo {model_type.upper()} encontrado. "
        f"Execute train_{model_type}.py primeiro para treinar um modelo, "
        f"ou configure o caminho correto em config.yaml (inference.{model_type}.weights)"
    )


def main():
    """
    Funcao principal de deteccao em tempo real via webcam.
    
    O tipo de modelo (YOLO ou RT-DETR) e definido em config.yaml:
    - inference.model_type: "yolo" ou "rtdetr"
    """
    print("=" * 60)
    print("VisionSecure AI - Deteccao em Tempo Real")
    print("=" * 60)
    
    cfg = load_yaml_config()
    inf_cfg = cfg["inference"]
    stream_cfg = cfg["stream"]
    alerts_cfg = cfg["alerts"]

    # Determina qual modelo usar (YOLO ou RT-DETR)
    model_type = inf_cfg.get("model_type", "yolo").lower()
    
    if model_type not in ["yolo", "rtdetr"]:
        print(f"Tipo de modelo invalido: {model_type}")
        print("Use 'yolo' ou 'rtdetr' em config.yaml (inference.model_type)")
        return
    
    print(f"\nModelo selecionado: {model_type.upper()}")
    if model_type == "yolo":
        print("  Arquitetura: CNN (Convolutional Neural Network)")
        print("  Caracteristicas: Rapido, ideal para tempo real (~30+ FPS)")
    else:
        print("  Arquitetura: Transformer (mecanismos de atencao)")
        print("  Caracteristicas: Alta precisao, mais lento (~5-10 FPS)")

    # Email (variaveis de ambiente)
    email_env_cfg = load_email_env()
    email_enabled = alerts_cfg.get("email", {}).get("enabled", True)

    # Carrega o modelo selecionado
    try:
        weights_path = get_model_weights(cfg, model_type)
        model = load_model(weights_path)
    except FileNotFoundError as e:
        print(f"\nErro: {e}")
        return
    except Exception as e:
        print(f"\nErro ao carregar modelo: {e}")
        return
    
    class_names_of_interest = set(inf_cfg["classes_of_interest"])
    conf_thres = inf_cfg.get("conf_thres", 0.5)
    iou_thres = inf_cfg.get("iou_thres", 0.45)

    # Webcam
    source = stream_cfg.get("source", 0)
    if not isinstance(source, int):
        source = 0

    fps_process = stream_cfg.get("fps_process", 5)
    frame_interval = 1.0 / fps_process

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print("Nao foi possivel abrir a webcam (source=0).")
        return

    last_frame_time = 0.0
    consecutive_detection_frames = 0
    min_persistent_frames = alerts_cfg.get("min_persistent_frames", 3)
    webhook_url = alerts_cfg.get("webhook_url", None)
    camera_id = "webcam_0"

    print(f"\nUsando WEBCAM com modelo {model_type.upper()}. Pressione 'q' para sair.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Erro na captura da webcam.")
            break

        now = time.time()
        if now - last_frame_time < frame_interval:
            cv2.imshow("VisionSecure MVP - Webcam", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            continue

        last_frame_time = now

        # Detecção
        frame, detections_of_interest = run_inference(
            model=model,
            frame=frame,
            conf_thres=conf_thres,
            iou_thres=iou_thres,
            classes_of_interest=class_names_of_interest,
        )

        if detections_of_interest:
            consecutive_detection_frames += 1
        else:
            consecutive_detection_frames = 0

        # Gatilho de alerta
        if consecutive_detection_frames >= min_persistent_frames:
            frame_path = None
            if alerts_cfg.get("send_frame", True):
                frame_path = save_frame(frame)

            payload = build_alert_payload(
                camera_id=camera_id,
                detections=detections_of_interest,
                frame_path=frame_path,
            )

            # Notificações
            send_webhook_alert(webhook_url, payload)
            send_email_alert(email_env_cfg, payload, enabled=email_enabled)

            consecutive_detection_frames = 0

        cv2.imshow("VisionSecure MVP - Webcam", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
