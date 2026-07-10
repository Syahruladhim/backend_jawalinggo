import requests

from flask import current_app


class MailConfigurationError(RuntimeError):
    pass


class MailDeliveryError(RuntimeError):
    pass


def send_reset_code_email(to_email, code):
    subject = "Kode Reset Password Jawalinggo"
    body = (
        "Halo,\n\n"
        f"Kode reset password Jawalinggo kamu adalah: {code}\n\n"
        "Kode ini berlaku selama 10 menit. Abaikan email ini kalau kamu tidak meminta reset password.\n"
    )

    send_email(to_email, subject, body)


def send_register_otp_email(to_email, code):
    subject = "Kode OTP Pendaftaran Jawalinggo"
    body = (
        "Halo,\n\n"
        f"Kode OTP pendaftaran Jawalinggo kamu adalah: {code}\n\n"
        "Kode ini berlaku selama 10 menit. Abaikan email ini kalau kamu tidak mendaftar akun Jawalinggo.\n"
    )

    send_email(to_email, subject, body)


def send_email(to_email, subject, body):
    api_key = current_app.config["BREVO_API_KEY"]
    from_email = current_app.config["BREVO_FROM_EMAIL"]
    from_name = current_app.config["BREVO_FROM_NAME"]

    if not api_key or not from_email:
        raise MailConfigurationError(
            "Konfigurasi Brevo HTTP API belum lengkap di .env."
        )

    if api_key.startswith("xsmtpsib-"):
        raise MailConfigurationError(
            "BREVO_API_KEY harus berisi Brevo API key, bukan SMTP key."
        )

    payload = {
        "sender": {"name": from_name, "email": from_email},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body,
    }

    try:
        response = requests.post(
            current_app.config["BREVO_API_URL"],
            headers={
                "accept": "application/json",
                "api-key": api_key,
                "content-type": "application/json",
            },
            json=payload,
            timeout=current_app.config["BREVO_TIMEOUT_SECONDS"],
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise MailDeliveryError(
            "Gagal mengirim email melalui Brevo HTTP API."
        ) from exc
