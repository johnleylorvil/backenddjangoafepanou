FROM python:3.11-slim

# Définir des variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=afepanou.settings

# Créer et définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système essentielles
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Dépendances PostgreSQL
    libpq-dev \
    postgresql-client \
    # Dépendances de compilation
    gcc \
    python3-dev \
    # Dépendances Pillow
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    # Outils réseau et utilitaires
    netcat-traditional \
    gettext \
    curl \
    # Autres dépendances
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    # S'assurer que psycopg2 est correctement installé
    && pip install psycopg2-binary --no-binary psycopg2-binary

# Copier le projet
COPY . .

# Créer un utilisateur non-root pour exécuter l'application
RUN adduser --disabled-password --gecos "" django
RUN chown -R django:django /app
USER django

# Collecte des fichiers statiques
RUN mkdir -p /app/staticfiles /app/media
RUN python manage.py collectstatic --noinput

# Script d'entrée
COPY --chown=django:django entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]

# Port à exposer
EXPOSE 8000

# Commande pour démarrer l'application
CMD ["gunicorn", "afepanou.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]