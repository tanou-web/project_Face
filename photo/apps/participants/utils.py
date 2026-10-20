"""
Utilitaires de normalisation et validation téléphonique (Format international E.164).

Pourquoi ce module est crucial :
Le numéro de téléphone (WhatsApp) constitue l'identifiant pivot des usagers sur la plateforme.
Les utilisateurs saisissent fréquemment leur numéro avec des syntaxes hétérogènes :
- Espaces ou séparateurs : "70 12 34 56" ou "70-12-34-56"
- Préfixe local sans indicatif : "70123456" (8 chiffres au Burkina Faso)
- Préfixe international avec double zéro : "0022670123456"
- Indicatif sans symbole plus : "22670123456"

La normalisation au standard E.164 (`+226...`) garantit l'unicité stricte en base de données
et la compatibilité directe avec les API WhatsApp Business et SMS (Aqilas).
"""

import re

# Indicatif pays par défaut : Burkina Faso (+226)
DEFAULT_COUNTRY_CODE = "226"


def normalize_phone(raw_phone: str) -> str:
    """
    Transforme toute chaîne téléphonique brute en numéro normalisé standard E.164.

    Algorithme de nettoyage :
    1. Nettoie les caractères d'espacement et la ponctuation parasite (tirets, points, parenthèses).
    2. Convertit le préfixe international '00' en signe '+'.
    3. Si l'indicatif est omis (format local 8 chiffres), ajoute automatiquement le préfixe '+226'.
    4. Garantit la présence du '+' initial pour former un numéro mondialement exploitable.
    """
    cleaned = raw_phone.strip()
    if not cleaned:
        return ""

    # Détecte la présence d'un préfixe '+' originel
    has_plus = cleaned.startswith("+")
    # Ne conserve strictement que les chiffres
    digits = re.sub(r"[^\d]", "", cleaned)

    if not digits:
        return ""

    # Cas 1 : Préfixe de numérotation internationale '00' (ex: 0022670123456 -> +22670123456)
    if digits.startswith("00"):
        digits = digits[2:]
        return f"+{digits}"

    # Cas 2 : Numéro explicitement préfixé d'un '+' (ex: +22670123456 ou +33612345678)
    if has_plus:
        return f"+{digits}"

    # Cas 3 : Commence par '226' sans le '+' et dispose d'assez de chiffres (au moins 11)
    if digits.startswith(DEFAULT_COUNTRY_CODE) and len(digits) >= 11:
        return f"+{digits}"

    # Cas 4 : Numéro local Burkinabè (8 chiffres) -> attribution automatique de l'indicatif '+226'
    return f"+{DEFAULT_COUNTRY_CODE}{digits}"


def validate_phone(phone: str) -> dict:
    """
    Valide la conformité structurelle d'un numéro de téléphone après normalisation.

    Critères vérifiés selon la recommandation UIT-T E.164 :
    - Non vide
    - Longueur minimale : Indicatif (ex: 3 chiffres pour 226) + au moins 8 chiffres nationaux = 11 chiffres
    - Longueur maximale : 15 chiffres au maximum au niveau international.
    
    Retourne un dictionnaire explicite : `{"valid": True, "phone": "+226..."}`
    ou `{"valid": False, "error": "Description du motif de rejet"}`.
    """
    normalized = normalize_phone(phone)

    if not normalized:
        return {"valid": False, "error": "Le numéro de téléphone est vide."}

    # Extraction des seuls chiffres pour calculer la longueur nette
    digits_only = re.sub(r"[^\d]", "", normalized)

    # Vérification de la longueur minimale requise
    if len(digits_only) < 11:
        return {
            "valid": False,
            "error": f"Numéro trop court ({len(digits_only)} chiffres). Minimum 8 chiffres après l'indicatif.",
        }

    # Vérification du plafond imposé par le standard E.164
    if len(digits_only) > 15:
        return {
            "valid": False,
            "error": f"Numéro trop long ({len(digits_only)} chiffres). Maximum 15 chiffres.",
        }

    return {"valid": True, "phone": normalized}
