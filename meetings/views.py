from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from .models import Organization, Meeting
from .serializers import MeetingCreateSerializer
from accounts.authenticate import SafeJWTAuthentication

class MeetingCreateView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [SafeJWTAuthentication]

    def post(self, request, organization_id):
        authentication = SafeJWTAuthentication()
        user, auth_error = authentication.authenticate(request)

        if not user:
            return Response({'error': 'Authentication failed.'}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            organization = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            return Response({"error": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        data['organization'] = organization.id
        serializer = MeetingCreateSerializer(data=data)
        
        if serializer.is_valid():
            meeting = serializer.save()
            return Response({"message": "Meeting created successfully", "meeting": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
