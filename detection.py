# detection.py
import cv2
from pathlib import Path
from datetime import datetime
from ultralytics import YOLO


def load_model(weights_path: str) -> YOLO:
    """
    Carrega o modelo YOLO a partir do arquivo de pesos.
    
    Args:
        weights_path: Caminho para o arquivo de pesos (.pt)
        
    Returns:
        Modelo YOLO carregado
        
    Raises:
        FileNotFoundError: Se o arquivo de pesos nao existir
        Exception: Se houver erro ao carregar o modelo
    """
    weights_file = Path(weights_path)
    if not weights_file.exists():
        raise FileNotFoundError(f"Arquivo de pesos nao encontrado: {weights_path}")
    
    try:
        model = YOLO(weights_path)
        return model
    except Exception as e:
        raise Exception(f"Erro ao carregar modelo YOLO: {e}")


def run_inference(model, frame, conf_thres: float, iou_thres: float, classes_of_interest: set):
    results = model.predict(
        source=frame,
        conf=conf_thres,
        iou=iou_thres,
        verbose=False
    )

    detections_of_interest = []
    for r in results:
        boxes = r.boxes
        names = r.names
        for box in boxes:
            cls_id = int(box.cls[0])
            cls_name = names[cls_id]
            if cls_name not in classes_of_interest:
                continue

            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detections_of_interest.append(
                {
                    "class": cls_name,
                    "confidence": conf,
                    "bbox": [x1, y1, x2, y2],
                }
            )

            # Desenha BB no frame
            cv2.rectangle(
                frame,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                (0, 0, 255),
                2,
            )
            cv2.putText(
                frame,
                f"{cls_name} {conf:.2f}",
                (int(x1), int(y1) - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                1,
                cv2.LINE_AA,
            )

    return frame, detections_of_interest


def save_frame(frame, output_dir="frames"):
    """
    Salva um frame em disco com timestamp unico.
    
    Args:
        frame: Frame OpenCV a ser salvo
        output_dir: Diretorio onde salvar o frame
        
    Returns:
        Caminho absoluto do arquivo salvo
    """
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    filename = output_path / f"frame_{ts}.jpg"
    cv2.imwrite(str(filename), frame)
    return str(filename)


def build_alert_payload(camera_id, detections, frame_path=None):
    """
    Constroi o payload de alerta com informacoes das deteccoes.
    
    Args:
        camera_id: Identificador da camera
        detections: Lista de deteccoes com classe, confianca e bbox
        frame_path: Caminho opcional do frame salvo
        
    Returns:
        Dicionario com payload do alerta
    """
    payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "camera_id": camera_id,
        "objects_detected": [],
        "severity": "medium",
    }

    severity_map = {
        "knife": "high",
        "scissor": "medium",
        "scissors": "medium",
        "hammer": "medium",
        "screwdriver": "medium",
        "wrench": "medium",
    }

    max_severity = "low"
    severity_order = {"low": 0, "medium": 1, "high": 2}

    for det in detections:
        cls_name = det["class"]
        conf = det["confidence"]
        bbox = det["bbox"]

        payload["objects_detected"].append(
            {"class": cls_name, "confidence": conf, "bbox": bbox}
        )

        det_severity = severity_map.get(cls_name, "medium")
        if severity_order.get(det_severity, 0) > severity_order.get(max_severity, 0):
            max_severity = det_severity

    payload["severity"] = max_severity if max_severity != "low" else "medium"
    if frame_path:
        payload["frame_path"] = frame_path

    return payload
