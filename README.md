# Jawalinggo Backend

Backend Flask untuk data user profile dengan MongoDB Atlas memakai format URI `mongodb+srv://`.
Backend juga menyediakan auth email/password, Google Sign-In, dan reset password via Brevo HTTP API.

## Setup

1. Buat virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependency:

```powershell
pip install -r requirements.txt
```

3. Salin konfigurasi environment:

```powershell
Copy-Item .env.example .env
```

4. Isi `MONGO_URI` di file `.env` dengan connection string MongoDB Atlas SRV:

```env
MONGO_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGO_DB_NAME=jawalinggo
```

Tambahkan juga konfigurasi Google Sign-In dan Brevo HTTP API:

```env
GOOGLE_CLIENT_ID=your-google-oauth-client-id.apps.googleusercontent.com
BREVO_API_KEY=your-brevo-api-key
BREVO_FROM_EMAIL=verified-sender@example.com
BREVO_FROM_NAME=Jawalinggo
BREVO_API_URL=https://api.brevo.com/v3/smtp/email
BREVO_TIMEOUT_SECONDS=15
```

Ambil `BREVO_API_KEY` dari halaman **SMTP & API > API Keys** di Brevo. `BREVO_FROM_EMAIL` harus menggunakan sender atau domain yang sudah diverifikasi di Brevo. API key hanya boleh disimpan di backend dan file `.env` tidak boleh di-commit.

5. Jalankan server:

```powershell
python run.py
```

Server default berjalan di `http://127.0.0.1:5000`.

## Deploy ke Render dengan Gunicorn

Repository ini menyediakan `render.yaml` di root project. Di Render, pilih **New > Blueprint**, hubungkan repository, lalu gunakan Blueprint tersebut untuk membuat web service `jawalinggo-backend`.

Render akan menjalankan perintah berikut dari direktori `backend`:

```bash
pip install -r requirements.txt
gunicorn --config gunicorn.conf.py run:app
```

Saat membuat Blueprint, isi environment variable rahasia yang bertanda `sync: false`:

- `MONGO_URI`
- `GOOGLE_AI_API_KEY`
- `GOOGLE_CLIENT_ID`
- `BREVO_API_KEY`
- `BREVO_FROM_EMAIL`

`SECRET_KEY` dibuat otomatis oleh Render. Jangan mengunggah file `.env`. Setelah deploy selesai, health check tersedia di `/api/health`.

## Endpoint

- `GET /api/health` cek status API dan database
- `POST /api/auth/register` registrasi email/password
- `POST /api/auth/login` login email/password
- `POST /api/auth/google` login Google dengan `id_token` dari aplikasi Flutter
- `POST /api/auth/forgot-password` kirim kode reset password ke email
- `POST /api/auth/reset-password` reset password memakai kode dari email
- `POST /api/profiles` buat profil user
- `GET /api/profiles` ambil semua profil
- `GET /api/profiles/<profile_id>` ambil profil berdasarkan id MongoDB
- `GET /api/profiles/by-user/<user_id>` ambil profil berdasarkan user id aplikasi
- `PATCH /api/profiles/<profile_id>` update profil
- `DELETE /api/profiles/<profile_id>` hapus profil

## Contoh Body Create Profile

```json
{
  "user_id": "user-001",
  "name": "Bima",
  "email": "bima@example.com",
  "avatar_url": "",
  "bio": "Sinau basa Jawa",
  "level": 1,
  "xp": 0,
  "preferred_language": "jv"
}
```

## Contoh Auth

Register:

```json
{
  "name": "Bima",
  "email": "bima@example.com",
  "password": "rahasia123"
}
```

Google login:

```json
{
  "id_token": "GOOGLE_ID_TOKEN_DARI_FLUTTER"
}
```

Forgot password:

```json
{
  "email": "bima@example.com"
}
```

Reset password:

```json
{
  "email": "bima@example.com",
  "code": "123456",
  "new_password": "passwordbaru123"
}
```
