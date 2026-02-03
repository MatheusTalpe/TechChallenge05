# webcam_main.py
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


def find_best_weights(runs_dir: str = "./runs") -> str:
    """
    Encontra o melhor arquivo de pesos (best.pt) dentre todos os runs de treinamento.
    Prioriza o run mais recente que contenha um arquivo best.pt valido.
    
    Args:
        runs_dir: Diretorio base onde os runs sao salvos
        
    Returns:
        Caminho para o melhor arquivo de pesos encontrado, ou None se nao encontrar
    """
    runs_path = Path(runs_dir)
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


def get_model_weights(cfg: dict) -> str:
    """
    Determina o caminho dos pesos do modelo a ser usado.
    Primeiro tenta usar o caminho configurado, se nao existir,
    busca automaticamente o melhor modelo disponivel.
    
    Args:
        cfg: Configuracao carregada do config.yaml
        
    Returns:
        Caminho para os pesos do modelo
        
    Raises:
        FileNotFoundError: Se nenhum modelo for encontrado
    """
    inf_cfg = cfg["inference"]
    configured_weights = inf_cfg.get("weights", "")
    runs_dir = cfg.get("runs_dir", "./runs")
    
    if configured_weights and os.path.exists(configured_weights):
        print(f"Usando modelo configurado: {configured_weights}")
        return configured_weights
    
    print(f"Modelo configurado nao encontrado: {configured_weights}")
    print("Buscando melhor modelo disponivel...")
    
    best_weights = find_best_weights(runs_dir)
    
    if best_weights:
        print(f"Modelo encontrado automaticamente: {best_weights}")
        return best_weights
    
    raise FileNotFoundError(
        f"Nenhum modelo encontrado. Execute train_model.py primeiro para treinar um modelo, "
        f"ou configure o caminho correto em config.yaml (inference.weights)"
    )


def main():
    cfg = load_yaml_config()
    inf_cfg = cfg["inference"]
    stream_cfg = cfg["stream"]
    alerts_cfg = cfg["alerts"]

    # Email (variáveis de ambiente)
    email_env_cfg = load_email_env()
    email_enabled = alerts_cfg.get("email", {}).get("enabled", True)

    # Modelo - busca automaticamente o melhor disponivel
    try:
        weights_path = get_model_weights(cfg)
        model = load_model(weights_path)
    except FileNotFoundError as e:
        print(f"Erro: {e}")
        return
    except Exception as e:
        print(f"Erro ao carregar modelo: {e}")
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
        print("Não foi possível abrir a webcam (source=0).")
        return

    last_frame_time = 0.0
    consecutive_detection_frames = 0
    min_persistent_frames = alerts_cfg.get("min_persistent_frames", 3)
    webhook_url = alerts_cfg.get("webhook_url", None)
    camera_id = "webcam_0"

    print("Usando WEBCAM. Pressione 'q' para sair.")

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
