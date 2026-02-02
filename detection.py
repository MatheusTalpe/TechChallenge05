# detection.py
import cv2
from pathlib import Path
from datetime import datetime
from ultralytics import YOLO


def load_model(weights_path: str):
    return YOLO(weights_path)


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
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    filename = Path(output_dir) / f"frame_{ts}.jpg"
    import cv2 as _cv2
    _cv2.imwrite(str(filename), frame)
    return str(filename)


def build_alert_payload(camera_id, detections, frame_path=None):
    from datetime import datetime as _dt

    payload = {
        "timestamp": _dt.utcnow().isoformat() + "Z",
        "camera_id": camera_id,
        "objects_detected": [],
        "severity": "medium",
    }

    max_severity = "medium"
    for det in detections:
        cls_name = det["class"]
        conf = det["confidence"]
        bbox = det["bbox"]

        payload["objects_detected"].append(
            {"class": cls_name, "confidence": conf, "bbox": bbox}
        )

        if cls_name == "knife" or cls_name == "scissor" or cls_name == "scissors" :
            max_severity = "high"
        elif cls_name in ["bat", "impact_tool"] and max_severity != "high":
            max_severity = "medium"

    payload["severity"] = max_severity
    if frame_path:
        payload["frame_path"] = frame_path

    return payload
