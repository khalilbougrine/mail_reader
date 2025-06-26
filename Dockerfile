FROM python:3.10-slim

# Dépendances pour Tesseract + PDF
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    cron \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Dossier de travail
WORKDIR /app

# Copier fichiers
COPY email_watcher.py .
COPY requirements.txt .
COPY cronjob /etc/cron.d/cronjob

# Créer fichier de log vide pour éviter l'erreur
RUN touch /app/logs.txt

# Installer dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Donner les droits au cronjob + l'activer
RUN chmod 0644 /etc/cron.d/cronjob
RUN crontab /etc/cron.d/cronjob

# Démarrer cron + suivre les logs
CMD ["sh", "-c", "cron && tail -f /app/logs.txt"]
