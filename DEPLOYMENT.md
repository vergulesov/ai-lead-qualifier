# VPS

Ubuntu 24.04.

## 1. System packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

## 2. Project

```bash
mkdir -p ~/ai-lead-qualifier
cd ~/ai-lead-qualifier
```

Скопируй проект сюда.

## 3. Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
```

## 4. Test

```bash
pytest -q
```

## 5. Start

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Для первого запуска оставляем процесс в foreground и проверяем его. После успешной проверки добавим systemd.
