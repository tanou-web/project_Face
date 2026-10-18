from rest_framework import serializers
from apps.participants.models import Participant
from apps.participants.utils import normalize_phone, validate_phone


class ParticipantSerializer(serializers.ModelSerializer):
    firstName = serializers.CharField(source="first_name")
    lastName = serializers.CharField(source="last_name")
    matchStatus = serializers.CharField(source="match_status", read_only=True)

    class Meta:
        model = Participant
        fields = ["id", "firstName", "lastName", "phone", "matchStatus"]

    def validate_phone(self, value):
        """Normalise et valide le numéro de téléphone au format E.164."""
        result = validate_phone(value)
        if not result["valid"]:
            raise serializers.ValidationError(result["error"])
        return result["phone"]

