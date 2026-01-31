# alerts.py
import requests
import smtplib
from email.message import EmailMessage
from pathlib import Path


def send_webhook_alert(webhook_url: str, payload: dict):
    if not webhook_url:
        return
    try:
        resp = requests.post(webhook_url, json=payload, timeout=3)
        print("Alerta (webhook) enviado. Status:", resp.status_code)
    except Exception as e:
        print("Falha ao enviar alerta via webhook:", e)


def send_email_alert(email_cfg: dict, payload: dict, enabled: bool = True):
    if not enabled:
        return

    smtp_server = email_cfg.get("smtp_server")
    smtp_port = email_cfg.get("smtp_port", 587)
    username = email_cfg.get("username")
    password = email_cfg.get("password")
    from_addr = email_cfg.get("from_addr")
    to_addrs = email_cfg.get("to_addrs", [])
    use_tls = email_cfg.get("use_tls", True)

    if not (smtp_server and username and password and from_addr and to_addrs):
        print("Configuração de e-mail incompleta (variáveis de ambiente). Não enviando e-mail.")
        return

    severity = payload.get("severity", "medium")
    camera_id = payload.get("camera_id", "desconhecida")

    subject = f"[VisionSecure] Alerta {severity.upper()} - {camera_id}"
    body_lines = [
        f"Timestamp: {payload.get('timestamp')}",
        f"Câmera: {camera_id}",
        f"Severidade: {severity}",
        "",
        "Objetos detectados:",
    ]
    for obj in payload.get("objects_detected", []):
        body_lines.append(
            f"- Classe: {obj['class']}, Confiança: {obj['confidence']:.2f}, BBox: {obj['bbox']}"
        )

    frame_path = payload.get("frame_path")
    if frame_path:
        body_lines.append("")
        body_lines.append(f"Frame salvo em: {frame_path}")

    body = "\n".join(body_lines)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg.set_content(body)

    if frame_path:
        try:
            with open(frame_path, "rb") as f:
                img_data = f.read()
            msg.add_attachment(
                img_data,
                maintype="image",
                subtype="jpeg",
                filename=Path(frame_path).name,
            )
        except Exception as e:
            print("Não foi possível anexar o frame ao e-mail:", e)

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            if use_tls:
                server.starttls()
            server.login(username, password)
            server.send_message(msg)
        print("Alerta (e-mail) enviado para:", to_addrs)
    except Exception as e:
        print("Falha ao enviar e-mail de alerta:", e)
