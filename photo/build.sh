#!/usr/bin/env bash
# ==============================================================================
# Script d'automatisation de build et de déploiement pour Render (et conteneurs CI/CD)
# ==============================================================================
# Interrompt immédiatement le script si une commande échoue (code de retour != 0)
set -o errexit

# 1. Mise à jour du gestionnaire de paquets et installation des dépendances Python
echo "==> Installation des dépendances Python..."
pip install --upgrade pip
pip install -r requirements.txt

# 2. Détection dynamique de l'arborescence (selon que le build s'exécute à la racine ou dans photo/)
if [ -f "manage.py" ]; then
    echo "==> Collecte des fichiers statiques pour WhiteNoise..."
    python manage.py collectstatic --noinput

    echo "==> Application des migrations de base de données..."
    python manage.py migrate

    echo "==> Injection des données de démonstration initiales (seed_data)..."
    python manage.py seed_data
elif [ -f "photo/manage.py" ]; then
    echo "==> Collecte des fichiers statiques pour WhiteNoise..."
    python photo/manage.py collectstatic --noinput

    echo "==> Application des migrations de base de données..."
    python photo/manage.py migrate

    echo "==> Injection des données de démonstration initiales (seed_data)..."
    python photo/manage.py seed_data
fi
echo "==> Build terminé avec succès !"
