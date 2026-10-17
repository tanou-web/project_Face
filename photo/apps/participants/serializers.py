from rest_framework import serializers
from apps.participants.models import Participant

class ParticipantSerializer(serializers.ModelSerializer):
    firstName = serializers.CharField(source="first_name")
    lastName = serializers.CharField(source="last_name")
    matchStatus = serializers.CharField(source="match_status", read_only=True)

    class Meta:
        model = Participant
        fields = ["id", "firstName", "lastName", "phone", "matchStatus"]
