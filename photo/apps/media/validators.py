"""
Validateurs de sécurité pour les fichiers médias uploadés.

Ce module met en œuvre une politique stricte de validation défensive afin de protéger
le serveur et les workers d'intelligence artificielle contre :
- L'injection de scripts exécutables déguisés en images (attaques polyglottes / webshells)
- Les bombes de décompression (zip/image bombs) et le déni de service mémoire
- Les fichiers binaires corrompus qui feraient crasher les algorithmes de détection faciale.
"""

import os
from PIL import Image
from rest_framework.exceptions import ValidationError

# Whitelist stricte des extensions et types MIME autorisés
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp'}


def validate_uploaded_image(file_obj, max_mb: int = 20):
    """
    Validation multicouche de sécurité pour tout fichier image entrant :

    1. Contrôle du volume : Plafonne la taille en Mo pour préserver la RAM du serveur.
    2. Filtrage de l'extension : N'autorise que les formats web et photo standards.
    3. En-tête HTTP Content-Type : Valide le type MIME déclaré par le client.
    4. Analyse binaire profonde (Pillow img.verify) : Ouvre le fichier en mémoire
       pour vérifier la structure réelle des blocs d'en-tête (magic bytes).
       Réinitialise le curseur de lecture (`file_obj.seek(0)`) pour les lectures ultérieures.
    """
    # 1. Vérification de la taille maximale
    file_size = file_obj.size
    if file_size > max_mb * 1024 * 1024:
        raise ValidationError(f"La taille du fichier dépasse la limite maximale autorisée de {max_mb} Mo.")

    # 2. Vérification de l'extension de fichier
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Format de fichier non supporté '{ext}'. Formats acceptés : JPEG, PNG, WEBP."
        )

    # 3. Vérification du type MIME déclaré par le navigateur/client HTTP
    content_type = getattr(file_obj, 'content_type', None)
    if content_type and content_type.lower() not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            f"Type MIME non autorisé '{content_type}'. Formats acceptés : image/jpeg, image/png, image/webp."
        )

    # 4. Vérification d'intégrité binaire avec la bibliothèque Pillow
    try:
        file_obj.seek(0)
        img = Image.open(file_obj)
        # verify() analyse les marqueurs de début/fin de fichier sans décoder toute l'image
        img.verify()
        # Repositionnement indispensable au début du flux binaire pour que Django puisse l'enregistrer sur disque
        file_obj.seek(0)
    except Exception as e:
        raise ValidationError(f"Le fichier image est invalide, non reconnu ou corrompu : {str(e)}")
