# alerts.py
import requests
import smtplib
import threading
from email.message import EmailMessage
from pathlib import Path


def send_webhook_alert(webhook_url: str, payload: dict):
    """
    Envia alerta via webhook HTTP POST.
    
    Args:
        webhook_url: URL do endpoint de webhook
        payload: Dados do alerta em formato dict
    """
    if not webhook_url:
        return
    try:
        resp = requests.post(webhook_url, json=payload, timeout=3)
        print("Alerta (webhook) enviado. Status:", resp.status_code)
    except Exception as e:
        print("Falha ao enviar alerta via webhook:", e)


def _send_email_sync(email_cfg: dict, payload: dict):
    """
    Funcao interna que envia o email de forma sincrona.
    Chamada em uma thread separada para nao bloquear o loop principal.
    
    Suporta diferentes configuracoes de SMTP:
    - Porta 465: SSL implicito (use_ssl=True)
    - Porta 587: STARTTLS (use_tls=True)
    - Porta 25/2525: Sem criptografia ou STARTTLS opcional
    """
    smtp_server = email_cfg.get("smtp_server")
    smtp_port = email_cfg.get("smtp_port", 587)
    username = email_cfg.get("username")
    password = email_cfg.get("password")
    from_addr = email_cfg.get("from_addr")
    to_addrs = email_cfg.get("to_addrs", [])
    use_tls = email_cfg.get("use_tls", True)
    use_ssl = email_cfg.get("use_ssl", False)

    severity = payload.get("severity", "medium")
    camera_id = payload.get("camera_id", "desconhecida")

    subject = f"[VisionSecure] Alerta {severity.upper()} - {camera_id}"
    body_lines = [
        f"Timestamp: {payload.get('timestamp')}",
        f"Camera: {camera_id}",
        f"Severidade: {severity}",
        "",
        "Objetos detectados:",
    ]
    for obj in payload.get("objects_detected", []):
        body_lines.append(
            f"- Classe: {obj['class']}, Confianca: {obj['confidence']:.2f}, BBox: {obj['bbox']}"
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
            print("Nao foi possivel anexar o frame ao e-mail:", e)

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=15) as server:
                server.login(username, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
                server.ehlo()
                if use_tls:
                    server.starttls()
                    server.ehlo()
                server.login(username, password)
                server.send_message(msg)
        print("Alerta (e-mail) enviado para:", to_addrs)
    except smtplib.SMTPAuthenticationError as e:
        print(f"Falha na autenticacao SMTP: {e}")
    except smtplib.SMTPConnectError as e:
        print(f"Falha ao conectar ao servidor SMTP: {e}")
    except smtplib.SMTPException as e:
        print(f"Erro SMTP: {e}")
    except Exception as e:
        print(f"Falha ao enviar e-mail de alerta: {e}")


def send_email_alert(email_cfg: dict, payload: dict, enabled: bool = True):
    """
    Envia alerta via e-mail de forma assincrona (nao bloqueia o loop principal).
    O envio e feito em uma thread separada para evitar congelamento da camera.
    
    Args:
        email_cfg: Configuracoes do servidor SMTP
        payload: Dados do alerta
        enabled: Se True, envia o email; se False, ignora
    """
    if not enabled:
        return

    smtp_server = email_cfg.get("smtp_server")
    username = email_cfg.get("username")
    password = email_cfg.get("password")
    from_addr = email_cfg.get("from_addr")
    to_addrs = email_cfg.get("to_addrs", [])

    if not (smtp_server and username and password and from_addr and to_addrs):
        print("Configuracao de e-mail incompleta (variaveis de ambiente). Nao enviando e-mail.")
        return

    email_thread = threading.Thread(
        target=_send_email_sync,
        args=(email_cfg, payload),
        daemon=True
    )
    email_thread.start()
    print("Enviando e-mail em background...")
