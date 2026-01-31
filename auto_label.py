# auto_label.py
from pathlib import Path
import cv2
from ultralytics import YOLO
from config import load_yaml_config  # já existe no seu projeto


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def auto_label_image(
    model,
    img_path: Path,
    out_img_dir: Path,
    out_lbl_dir: Path,
    conf_thres: float,
    iou_thres: float,
):
    img = cv2.imread(str(img_path))
    if img is None:
        print(f"Falha ao ler imagem: {img_path}")
        return

    h, w = img.shape[:2]

    results = model.predict(
        source=img,
        conf=conf_thres,
        iou=iou_thres,
        verbose=False,
    )

    ensure_dir(out_img_dir)
    ensure_dir(out_lbl_dir)

    out_img_path = out_img_dir / img_path.name
    cv2.imwrite(str(out_img_path), img)

    label_path = out_lbl_dir / f"{img_path.stem}.txt"

    lines = []
    for r in results:
        boxes = r.boxes
        names = r.names  # devem ser: Axe, Chainsaw, ..., Stapler
        for box in boxes:
            cls_id = int(box.cls[0])
            cls_name = names[cls_id]

            # Se quiser, pode limitar a algumas classes:
            # if cls_name not in {"Axe", "Chainsaw", "Knife", "Scissors"}:
            #     continue

            x1, y1, x2, y2 = box.xyxy[0].tolist()

            x_center = (x1 + x2) / 2.0 / w
            y_center = (y1 + y2) / 2.0 / h
            bw = (x2 - x1) / w
            bh = (y2 - y1) / h

            # Índice do modelo = índice do dataset (mesmo names / mesma ordem)
            dataset_cls_id = cls_id

            lines.append(f"{dataset_cls_id} {x_center} {y_center} {bw} {bh}\n")

    if not lines:
        # Sem detecções: imagem negativa -> txt vazio
        open(label_path, "w", encoding="utf-8").close()
        print(f"Auto-rotulada (sem detecções): {img_path} -> {label_path}")
        return

    with open(label_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"Auto-rotulada: {img_path} -> {label_path}")


def main():
    # Carrega config
    cfg = load_yaml_config()
    model_weights = cfg.get("model_name", "yolov8n.pt")

    print(f"Carregando modelo pré-existente para auto-rotulagem: {model_weights}")
    model = YOLO(model_weights)

    conf_thres = 0.5
    iou_thres = 0.45

    raw_dir = Path("data/raw")
    out_img_dir = Path("data/auto_labeled/images")
    out_lbl_dir = Path("data/auto_labeled/labels")

    raw_dir.mkdir(parents=True, exist_ok=True)

    image_paths = sorted(
        [
            p
            for p in raw_dir.iterdir()
            if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp"]
        ]
    )

    if not image_paths:
        print(f"Nenhuma imagem encontrada em {raw_dir}.")
        print("Coloque imagens brutas lá antes de rodar auto-rotulagem.")
        return

    print(f"Encontradas {len(image_paths)} imagens em {raw_dir} para auto-rotulagem.")

    for img_path in image_paths:
        auto_label_image(
            model=model,
            img_path=img_path,
            out_img_dir=out_img_dir,
            out_lbl_dir=out_lbl_dir,
            conf_thres=conf_thres,
            iou_thres=iou_thres,
        )

    print("Auto-rotulagem concluída.")
    print("Imagens e labels em: data/auto_labeled/images e data/auto_labeled/labels")


if __name__ == "__main__":
    main()
