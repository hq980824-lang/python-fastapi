from email.mime.text import MIMEText
import random
import smtplib

from src.config.settings import settings


class EmailUtil:
    @staticmethod
    def generate_code() -> str:
        return ''.join(random.choices('0123456789', k=6))

    @staticmethod
    def send_verify_code(to_email: str, code: str):
        mail_content = f"""
        <h3>邮箱登录验证码</h3>
        <p>你的登录验证码为：<strong style="color:red;font-size:20px">{code}</strong></p>
        <p>验证码5分钟内有效，请勿泄露给他人</p>
        """
        msg = MIMEText(mail_content, 'html', 'utf-8')
        msg['Subject'] = '系统登录安全验证码'
        msg['From'] = settings.SMTP_USER
        msg['To'] = to_email

        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)