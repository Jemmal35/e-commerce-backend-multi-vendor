from rest_framework.response import Response
from rest_framework import status, permissions, parsers
from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404
from django.contrib.auth import get_user_model

from .serializers import UserSerializer, UserProfileSerializer, LogoutSerializer, UserPasswordChangeSerializer
from .models import User, UserProfile

User = get_user_model()

class UserRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        user_data = request.data
        serializer = UserSerializer(data = user_data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status= status.HTTP_201_CREATED)
        return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)
    
       
class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    # parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    
    def get(self, request):
        user = request.user
        profile, _ = UserProfile.objects.get_or_create(user = user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data, status= status.HTTP_200_OK)
    
    def put(self, request):
        profile, _ = UserProfile.objects.get_or_create(user = request.user)
        user_data = request.data
        serializer = UserProfileSerializer(profile, data = user_data, partial =False)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status= status.HTTP_200_OK)
        return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request):
        user_data = request.data
        profile, _= UserProfile.objects.get_or_create(user = request.user)
        
        serializer = UserProfileSerializer(profile, data = user_data, partial = True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status= status.HTTP_200_OK)
        return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        profile = get_object_or_404(UserProfile, user = request.user)
        user = request.user
        user.delete()
        profile.delete()
        return Response({"detail": "Your account has been deleted successfully."}, status= status.HTTP_204_NO_CONTENT)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        context = {
            'request': request
        }
        serializer = UserPasswordChangeSerializer(data = request.data, context = context)
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)
    
    
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        data = request.data
        serializer = LogoutSerializer(data = data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Successfully logged out."}, status= status.HTTP_200_OK)
        return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)   