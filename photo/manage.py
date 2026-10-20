#!/usr/bin/env python
"""
Utilitaire en ligne de commande de Django pour les tâches administratives.

Permet d'exécuter les opérations de gestion du projet :
- Lancement du serveur de développement local (`runserver`)
- Création et application des migrations de base de données (`makemigrations`, `migrate`)
- Peuplement initial de la base de données (`seed_data`)
- Collecte des ressources statiques (`collectstatic`)
"""
import os
import sys


def main():
    """
    Point d'entrée principal de l'utilitaire d'administration.
    Configure le module de paramètres 'photo.settings' et délègue
    l'exécution des arguments CLI à Django.
    """
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'photo.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Impossible d'importer Django. Vérifiez qu'il est correctement installé et "
            "accessible dans votre variable d'environnement PYTHONPATH. Avez-vous "
            "oublié d'activer votre environnement virtuel ?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
