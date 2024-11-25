from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Organization, OrganizationMember
from .serializers import OrganizationSerializer
from accounts.authenticate import SafeJWTAuthentication
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class OrganizationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [SafeJWTAuthentication]

    @swagger_auto_schema(
        operation_description="조직의 정보를 조회합니다. `organization_id`가 제공되면 해당 조직만, 제공되지 않으면 모든 조직 정보를 반환합니다.",
        responses={
            200: OrganizationSerializer,
            404: openapi.Response(description="조직을 찾을 수 없습니다."),
            401: openapi.Response(description="인증 실패")
        }
    )
    def get(self, request, organization_id=None):
        authentication = SafeJWTAuthentication()
        user, auth_error = authentication.authenticate(request)

        if not user:
            return Response({'error': '인증에 실패했습니다.'}, status=status.HTTP_401_UNAUTHORIZED)

        if organization_id:
            try:
                organization = Organization.objects.get(id=organization_id)
            except Organization.DoesNotExist:
                return Response({"error": "조직을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

            return Response(OrganizationSerializer(organization).data, status=status.HTTP_200_OK)

        else:
            organizations = Organization.objects.all()
            return Response(OrganizationSerializer(organizations, many=True).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="새로운 조직을 생성합니다. 조직의 이름을 요청 본문에 포함시켜야 합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, description="조직의 이름")
            },
            required=['name']
        ),
        responses={
            201: OrganizationSerializer,
            400: openapi.Response(description="조직 이름이 필요합니다."),
            401: openapi.Response(description="인증 실패")
        }
    )
    def post(self, request):
        authentication = SafeJWTAuthentication()
        user, auth_error = authentication.authenticate(request)

        if not user:
            return Response({'error': '인증에 실패했습니다.'}, status=status.HTTP_401_UNAUTHORIZED)

        name = request.data.get("name")
        if not name:
            return Response({"error": "조직 이름은 필수입니다."}, status=status.HTTP_400_BAD_REQUEST)

        organization = Organization.objects.create(name=name, owner=user)
        OrganizationMember.objects.create(organization=organization, user=user)

        return Response(OrganizationSerializer(organization).data, status=status.HTTP_201_CREATED)


class OrganizationInviteView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [SafeJWTAuthentication]

    @swagger_auto_schema(
        operation_description="초대 코드로 조직에 가입합니다. 초대 코드를 요청 본문에 포함시켜야 합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'invite_code': openapi.Schema(type=openapi.TYPE_STRING, description="조직 초대 코드")
            },
            required=['invite_code']
        ),
        responses={
            200: openapi.Response(description="조직에 성공적으로 가입했습니다."),
            400: openapi.Response(description="사용자가 이미 조직에 가입되어 있습니다."),
            404: openapi.Response(description="잘못된 초대 코드입니다."),
            401: openapi.Response(description="인증 실패")
        }
    )
    def post(self, request):
        authentication = SafeJWTAuthentication()
        user, auth_error = authentication.authenticate(request)

        if not user:
            return Response({'error': '인증에 실패했습니다.'}, status=status.HTTP_401_UNAUTHORIZED)

        invite_code = request.data.get("invite_code")
        if not invite_code:
            return Response({"error": "초대 코드가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            organization = Organization.objects.get(invite_code=invite_code)
        except Organization.DoesNotExist:
            return Response({"error": "잘못된 초대 코드입니다."}, status=status.HTTP_404_NOT_FOUND)

        if OrganizationMember.objects.filter(organization=organization, user=user).exists():
            return Response({"error": "사용자가 이미 조직에 가입되어 있습니다."}, status=status.HTTP_400_BAD_REQUEST)

        OrganizationMember.objects.create(organization=organization, user=user)
        return Response({"message": "조직에 성공적으로 가입했습니다."}, status=status.HTTP_200_OK)
