#!/bin/bash
set -e

# Attendre que PostgreSQL soit prêt
if [ "$DATABASE_URL" ]; then
  echo "Waiting for PostgreSQL..."
  
  # Extraire les informations de connexion depuis DATABASE_URL
  if [[ $DATABASE_URL == postgres* ]]; then
    DB_HOST=$(echo $DATABASE_URL | sed -e 's/^.*@\(.*\):.*/\1/')
    DB_PORT=$(echo $DATABASE_URL | sed -e 's/^.*:\([0-9]*\)\/.*/\1/')
    
    until nc -z $DB_HOST $DB_PORT; do
      echo "PostgreSQL n'est pas disponible - attente..."
      sleep 1
    done
    
    echo "PostgreSQL est disponible !"
  fi
fi

# Vérifier l'accès aux ressources externes
echo "Vérification de l'accès à Redis..."
if [ "$REDIS_URL" ]; then
  REDIS_HOST=$(echo $REDIS_URL | sed -e 's/^.*@\(.*\):.*/\1/')
  REDIS_PORT=$(echo $REDIS_URL | sed -e 's/^.*:\([0-9]*\).*/\1/')
  
  if nc -z $REDIS_HOST $REDIS_PORT; then
    echo "Redis est accessible!"
  else
    echo "Avertissement: Redis n'est pas accessible!"
  fi
fi

# Créer les répertoires nécessaires s'ils n'existent pas
mkdir -p /app/staticfiles
mkdir -p /app/media

# Appliquer les migrations Django
echo "Applying database migrations..."
python manage.py migrate --noinput

# Exécuter la commande spécifiée
exec "$@"