# config.py
import yaml
from pathlib import Path
import os
from dotenv import load_dotenv


def load_yaml_config(path: str = "config.yaml") -> dict:
    print("Lendo config de:", path)  # DEBUG
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
        print("Conteúdo bruto do config.yaml:\n", text[:500])  # mostra início
        f.seek(0)
        return yaml.safe_load(f)


def load_email_env() -> dict:
    """
    Carrega configuracoes de email das variaveis de ambiente.
    
    Variaveis suportadas:
    - EMAIL_SMTP_SERVER: Servidor SMTP (ex: smtp.gmail.com, sandbox.smtp.mailtrap.io)
    - EMAIL_SMTP_PORT: Porta SMTP (padrao: 587)
    - EMAIL_USE_TLS: Usar STARTTLS (padrao: true) - para portas 587, 25, 2525
    - EMAIL_USE_SSL: Usar SSL implicito (padrao: false) - para porta 465
    - EMAIL_USERNAME: Usuario para autenticacao
    - EMAIL_PASSWORD: Senha para autenticacao
    - EMAIL_FROM: Endereco de origem
    - EMAIL_TO: Enderecos de destino (separados por virgula)
    
    Nota para Mailtrap sandbox (porta 2525):
    - Use EMAIL_USE_TLS=false para evitar erro "Connection unexpectedly closed"
    """
    load_dotenv()

    return {
        "smtp_server": os.getenv("EMAIL_SMTP_SERVER"),
        "smtp_port": int(os.getenv("EMAIL_SMTP_PORT", "587")),
        "use_tls": os.getenv("EMAIL_USE_TLS", "true").lower() == "true",
        "use_ssl": os.getenv("EMAIL_USE_SSL", "false").lower() == "true",
        "username": os.getenv("EMAIL_USERNAME"),
        "password": os.getenv("EMAIL_PASSWORD"),
        "from_addr": os.getenv("EMAIL_FROM"),
        "to_addrs": [
            addr.strip()
            for addr in os.getenv("EMAIL_TO", "").split(",")
            if addr.strip()
        ],
    }
