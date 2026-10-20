"""
Sérialiseur d'authentification JWT personnalisé.

Ce module étend le comportement standard de SimpleJWT :
- Permet aux utilisateurs et administrateurs de se connecter soit avec leur adresse email,
  soit avec leur nom d'utilisateur (username).
- Résout automatiquement le username correspondant à l'email pour le module d'authentification Django.
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Sérialiseur de jeton JWT acceptant l'email comme identifiant de connexion.

    Pourquoi cette surcharge :
    Par défaut, SimpleJWT n'accepte que le champ 'username'. En rendant 'username'
    facultatif et en autorisant 'email', nous offrons une expérience de connexion moderne
    sans modifier le modèle utilisateur natif de Django.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rend 'username' optionnel si 'email' est fourni dans le formulaire de login
        if 'username' in self.fields:
            self.fields['username'].required = False
        self.fields['email'] = serializers.EmailField(required=False)

    def validate(self, attrs):
        email = attrs.get('email')
        username = attrs.get('username')

        # Si l'utilisateur saisit son email au lieu de son nom d'utilisateur,
        # nous recherchons le compte de manière insensible à la casse (iexact)
        # et injectons son véritable username avant la validation par Django.
        if email and not username:
            user = User.objects.filter(email__iexact=email).first()
            if user:
                attrs['username'] = user.username

        return super().validate(attrs)
