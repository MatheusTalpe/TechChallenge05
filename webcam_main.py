# webcam_main.py
import time
import cv2

from config import load_yaml_config, load_email_env
from detection import (
    load_model,
    run_inference,
    save_frame,
    build_alert_payload,
)
from alerts import send_webhook_alert, send_email_alert


def main():
    cfg = load_yaml_config()
    inf_cfg = cfg["inference"]
    stream_cfg = cfg["stream"]
    alerts_cfg = cfg["alerts"]

    # Email (variáveis de ambiente)
    email_env_cfg = load_email_env()
    email_enabled = alerts_cfg.get("email", {}).get("enabled", True)

    # Modelo
    model = load_model(inf_cfg["weights"])
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
