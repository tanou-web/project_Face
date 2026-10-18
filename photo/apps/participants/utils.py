import re

# Indicatif par défaut : Burkina Faso
DEFAULT_COUNTRY_CODE = "226"


def normalize_phone(raw_phone: str) -> str:
    """
    Normalise un numéro de téléphone au format E.164 (+226XXXXXXXXX).

    Règles :
    - Supprime espaces, tirets, parenthèses, points
    - +226060328888  →  +226060328888   (déjà complet)
    - 060328888      →  +226060328888   (pas d'indicatif → +226 par défaut)
    - 00226 06032... →  +226060328888   (format international 00)
    - 226 06032...   →  +226060328888   (indicatif sans +)
    """
    cleaned = raw_phone.strip()
    if not cleaned:
        return ""

    # Conserver le + initial s'il existe, puis ne garder que les chiffres
    has_plus = cleaned.startswith("+")
    digits = re.sub(r"[^\d]", "", cleaned)

    if not digits:
        return ""

    # Format international avec 00 en tête (ex: 0022670123456)
    if digits.startswith("00"):
        digits = digits[2:]
        return f"+{digits}"

    # Déjà préfixé avec + (ex: +22670123456)
    if has_plus:
        return f"+{digits}"

    # Commence par 226 et a suffisamment de chiffres (226 + 8-9 chiffres locaux)
    if digits.startswith(DEFAULT_COUNTRY_CODE) and len(digits) >= 11:
        return f"+{digits}"

    # Numéro local sans indicatif → ajouter +226
    return f"+{DEFAULT_COUNTRY_CODE}{digits}"


def validate_phone(phone: str) -> dict:
    """
    Valide un numéro de téléphone après normalisation.
    Retourne {"valid": True, "phone": "+226..."} ou {"valid": False, "error": "..."}.
    """
    normalized = normalize_phone(phone)

    if not normalized:
        return {"valid": False, "error": "Le numéro de téléphone est vide."}

    # Extraire les chiffres après l'indicatif pour vérifier la longueur
    digits_only = re.sub(r"[^\d]", "", normalized)

    # Minimum : indicatif (3) + numéro local (8) = 11 chiffres
    if len(digits_only) < 11:
        return {
            "valid": False,
            "error": f"Numéro trop court ({len(digits_only)} chiffres). Minimum 8 chiffres après l'indicatif.",
        }

    # Maximum raisonnable : 15 chiffres (norme E.164)
    if len(digits_only) > 15:
        return {
            "valid": False,
            "error": f"Numéro trop long ({len(digits_only)} chiffres). Maximum 15 chiffres.",
        }

    return {"valid": True, "phone": normalized}
