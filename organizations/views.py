from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Organization, OrganizationMember
from .serializers import OrganizationSerializer, OrganizationMemberSerializer
from accounts.authenticate import SafeJWTAuthentication
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import IntegrityError


class OrganizationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [SafeJWTAuthentication]

    @swagger_auto_schema(
        operation_description="현재 사용자가 참가중인 모든 조직의 정보를 조회합니다.",
        responses={
            200: OrganizationSerializer,
            401: openapi.Response(description="인증 실패")
        }
    )
    def get(self, request):
        authentication = SafeJWTAuthentication()
        user, auth_error = authentication.authenticate(request)

        if not user:
            return Response({'error': '인증에 실패했습니다.'}, status=status.HTTP_401_UNAUTHORIZED)

        organizations = Organization.objects.filter(members__user=user)
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

        if Organization.objects.filter(name=name).exists():
            return Response({"error": "이미 존재하는 조직 이름입니다."}, status=status.HTTP_409_CONFLICT)

        try:
            organization = Organization.objects.create(name=name, owner=user)
            OrganizationMember.objects.create(organization=organization, user=user)
        except IntegrityError:
            return Response({"error": "조직 이름이 중복되었습니다."}, status=status.HTTP_409_CONFLICT)

        return Response(OrganizationSerializer(organization).data, status=status.HTTP_201_CREATED)

class OrganizationDetailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [SafeJWTAuthentication]

    
    @swagger_auto_schema(
        operation_description="특정 조직의 정보를 조회합니다. 조직의 정보와 함께 조직원들도 반환합니다.",
        responses={
            200: openapi.Response(
                description="조직 정보와 조직원 목록",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description="조직 ID"),
                        'name': openapi.Schema(type=openapi.TYPE_STRING, description="조직 이름"),
                        'owner': openapi.Schema(type=openapi.TYPE_STRING, description="조직 주인의 이메일"),
                        'invite_code': openapi.Schema(type=openapi.TYPE_STRING, description="조직 초대 코드"),
                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, description="조직 생성 시간"),
                        'members': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER, description="조직원 ID"),
                                    'organization': openapi.Schema(type=openapi.TYPE_INTEGER, description="조직 ID"),
                                    'user': openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER, description="사용자 ID"),
                                            'username': openapi.Schema(type=openapi.TYPE_STRING, description="사용자 이름"),
                                            'email': openapi.Schema(type=openapi.TYPE_STRING, description="사용자 이메일")
                                        }
                                    ),
                                    'joined_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, description="조직 가입 시간")
                                }
                            )
                        )
                    }
                )
            ),
            404: openapi.Response(description="조직을 찾을 수 없습니다."),
            401: openapi.Response(description="인증 실패")
        }
    )
    def get(self, request, organization_id):
        authentication = SafeJWTAuthentication()
        user, auth_error = authentication.authenticate(request)

        if not user:
            return Response({'error': '인증에 실패했습니다.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            organization = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            return Response({"error": "조직을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        members = OrganizationMember.objects.filter(organization=organization)
        members_data = OrganizationMemberSerializer(members, many=True).data
        
        organization_data = OrganizationSerializer(organization).data
        organization_data['members'] = members_data
        
        return Response(organization_data, status=status.HTTP_200_OK)
    
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
