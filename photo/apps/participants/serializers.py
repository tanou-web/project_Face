"""
Sérialiseur pour la gestion et l'enregistrement des Participants.

Ce module valide les données d'identité des usagers :
- Conversion des champs Python snake_case vers camelCase pour le frontend
- Normalisation et validation automatique du numéro de téléphone au format E.164.
"""

from rest_framework import serializers
from apps.participants.models import Participant
from apps.participants.utils import normalize_phone, validate_phone


class ParticipantSerializer(serializers.ModelSerializer):
    """
    Sérialiseur d'inscription et de consultation du profil d'un participant.
    """
    firstName = serializers.CharField(source="first_name", help_text="Prénom de l'usager")
    lastName = serializers.CharField(source="last_name", help_text="Nom de famille de l'usager")
    matchStatus = serializers.CharField(source="match_status", read_only=True, help_text="Statut d'avancement du matching")

    class Meta:
        model = Participant
        fields = ["id", "firstName", "lastName", "phone", "matchStatus"]

    def validate_phone(self, value):
        """
        Intercepte la saisie du numéro de téléphone pour la valider et la normaliser (+226...).
        Rejette immédiatement les numéros trop courts ou syntaxiquement invalides.
        """
        result = validate_phone(value)
        if not result["valid"]:
            raise serializers.ValidationError(result["error"])
        return result["phone"]

