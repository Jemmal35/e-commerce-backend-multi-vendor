from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.contrib.auth import get_user_model

from .models import User, UserProfile
import re
User = get_user_model()

class UserProfileDetailSerializer(serializers.ModelSerializer):
    class Meta:
            model = UserProfile
            fields = [
                'avatar', 'bio', 'phone_number', 'address', 'city', 'country']
            

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only = True, min_length = 8, required = False, style = {'input':'password'})
    profile = UserProfileDetailSerializer(required = False)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'password','profile']
        read_only_fields = ['id', 'role']
        
    def validate_password(self, value):
        """
        Enforces standard password rules:
        - Minimum 8 characters
        - At least 1 Uppercase letter (A-Z)
        - At least 1 Lowercase letter (a-z)
        - At least 1 Number (0-9)
        - At least 1 Special character
        """
        if not value:
            return value

        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter (A-Z).")
        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError("Password must contain at least one lowercase letter (a-z).")
        if not re.search(r'[0-9]', value):
            raise serializers.ValidationError("Password must contain at least one number (0-9).")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise serializers.ValidationError("Password must contain at least one special character.")

        return value
     
        
    def create(self, validated_data):
        profile_data = validated_data.pop('profile', None)
        password = validated_data.pop('password')
        
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        
        if profile_data:
            profile, _= UserProfile.objects.get_or_create(user = user)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
            
            user.profile = profile
            
        return user

class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role']
        read_only_fields = ['id', 'email', 'role']
        extra_kwargs = {
            'username': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }
            
        
class UserProfileSerializer(serializers.ModelSerializer):

    user = UserDetailSerializer()
        
    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'avatar', 'bio', 'phone_number', 'address', 'city', 'country', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')
    
        
    def update(self, instance, validated_data):
        
        user_data = validated_data.pop('user',None)

        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()
            
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        
        return instance
            
class UserPasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only = True, required =True, style = {'input':'password'})
    new_password = serializers.CharField(write_only = True, required =True, style = {'input':'password'})
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError({"error": "Current Password is incorrect."})
        return value
    
    def validate_new_password(self, value):
            """
            Enforces standard password rules:
            - Minimum 8 characters
            - At least 1 Uppercase letter (A-Z)
            - At least 1 Lowercase letter (a-z)
            - At least 1 Number (0-9)
            - At least 1 Special character
            """
            if not value:
                return value
    
            if len(value) < 8:
                raise serializers.ValidationError("Password must be at least 8 characters long.")
            if not re.search(r'[A-Z]', value):
                raise serializers.ValidationError("Password must contain at least one uppercase letter (A-Z).")
            if not re.search(r'[a-z]', value):
                raise serializers.ValidationError("Password must contain at least one lowercase letter (a-z).")
            if not re.search(r'[0-9]', value):
                raise serializers.ValidationError("Password must contain at least one number (0-9).")
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
                raise serializers.ValidationError("Password must contain at least one special character.")
    
            return value
    
    def validate(self, attrs):
        if attrs.get('old_password') == attrs.get('new_password'):
            raise serializers.ValidationError({'new_password': "New password can not be the same as the current password."})
        return attrs
    
    
class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text = "The refresh token to be blacklisted.")
    def save(self, **kwargs):
        
        try:
            token = RefreshToken(self.validated_data['refresh'])
            token.blacklist()
        except TokenError:
            raise serializers.ValidationError({'refresh':"Invalid or Expired refresh token."})