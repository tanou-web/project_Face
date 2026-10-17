from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rend 'username' optionnel si 'email' est fourni
        if 'username' in self.fields:
            self.fields['username'].required = False
        self.fields['email'] = serializers.EmailField(required=False)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        username = attrs.get('username')

        if email and not username:
            user = User.objects.filter(email__iexact=email).first()
            if user:
                attrs['username'] = user.username

        return super().validate(attrs)
