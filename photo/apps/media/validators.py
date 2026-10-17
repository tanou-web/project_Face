import os
from PIL import Image
from rest_framework.exceptions import ValidationError

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp'}

def validate_uploaded_image(file_obj, max_mb: int = 20):
    """
    Validation de sécurité pour les fichiers images :
    1. Taille maximale en Mo.
    2. Extension de fichier autorisée.
    3. Type MIME déclaré.
    4. Validation de la structure interne avec Pillow pour éviter les fichiers malveillants/corrompus.
    """
    # 1. Vérification de la taille
    file_size = file_obj.size
    if file_size > max_mb * 1024 * 1024:
        raise ValidationError(f"La taille du fichier dépasse la limite maximale autorisée de {max_mb} Mo.")

    # 2. Vérification de l'extension
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Format de fichier non supporté '{ext}'. Formats acceptés : JPEG, PNG, WEBP."
        )

    # 3. Vérification du type MIME si disponible
    content_type = getattr(file_obj, 'content_type', None)
    if content_type and content_type.lower() not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            f"Type MIME non autorisé '{content_type}'. Formats acceptés : image/jpeg, image/png, image/webp."
        )

    # 4. Vérification d'intégrité de l'image avec Pillow
    try:
        file_obj.seek(0)
        img = Image.open(file_obj)
        img.verify()  # Valide les en-têtes et la cohérence de l'image
        file_obj.seek(0)
    except Exception as e:
        raise ValidationError(f"Le fichier image est invalide ou corrompu : {str(e)}")
