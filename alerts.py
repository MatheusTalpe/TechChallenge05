# alerts.py
import requests
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
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
    
    Para Mailtrap sandbox, recomenda-se usar porta 587 com STARTTLS.
    """
    import socket
    
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

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg.attach(MIMEText(body, "plain"))

    if frame_path:
        frame_file = Path(frame_path)
        if frame_file.exists():
            try:
                with open(frame_path, "rb") as f:
                    img_data = f.read()
                img_attachment = MIMEImage(img_data, _subtype="jpeg")
                img_attachment.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=frame_file.name
                )
                msg.attach(img_attachment)
                print(f"Imagem anexada ao e-mail: {frame_file.name}")
            except Exception as e:
                print(f"Nao foi possivel anexar o frame ao e-mail: {e}")
        else:
            print(f"Arquivo de frame nao encontrado: {frame_path}")

    try:
        local_hostname = socket.gethostname()
        
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, local_hostname=local_hostname, timeout=30)
            try:
                server.login(username, password)
                server.sendmail(from_addr, to_addrs, msg.as_string())
                print("Alerta (e-mail) enviado para:", to_addrs)
            finally:
                server.quit()
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, local_hostname=local_hostname, timeout=30)
            try:
                if use_tls:
                    server.starttls()
                server.login(username, password)
                server.sendmail(from_addr, to_addrs, msg.as_string())
                print("Alerta (e-mail) enviado para:", to_addrs)
            finally:
                server.quit()
                
    except smtplib.SMTPAuthenticationError as e:
        print(f"Falha na autenticacao SMTP: {e}")
        print("Verifique EMAIL_USERNAME e EMAIL_PASSWORD no arquivo .env")
    except smtplib.SMTPConnectError as e:
        print(f"Falha ao conectar ao servidor SMTP: {e}")
        print(f"Servidor: {smtp_server}:{smtp_port}")
    except smtplib.SMTPException as e:
        print(f"Erro SMTP: {e}")
        print("Tente usar porta 587 com EMAIL_USE_TLS=true para Mailtrap")
    except socket.timeout:
        print("Timeout ao conectar ao servidor SMTP")
        print(f"Servidor: {smtp_server}:{smtp_port}")
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
