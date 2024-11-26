from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from .models import Meeting
from .serializers import MeetingCreateSerializer
from accounts.authenticate import SafeJWTAuthentication
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from organizations.models import Organization


class MeetingView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [SafeJWTAuthentication]

    @swagger_auto_schema(
        operation_summary="회의 생성",
        operation_description="새로운 회의를 생성합니다.",
        request_body=MeetingCreateSerializer,
        responses={
            201: openapi.Response(
                description='Meeting created successfully',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='성공 메시지'),
                        'meeting': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='회의 ID'),
                                'title': openapi.Schema(type=openapi.TYPE_STRING, description='회의 제목'),
                                'total_duration': openapi.Schema(type=openapi.TYPE_INTEGER, description='총 시간 (분 단위)'),
                                'organization': openapi.Schema(type=openapi.TYPE_STRING, description='조직 이름'),
                                'sections': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'name': openapi.Schema(type=openapi.TYPE_STRING, description='섹션 이름'),
                                        }
                                    ),
                                    description='회의의 섹션 리스트'
                                ),
                                'participants': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'user': openapi.Schema(
                                                type=openapi.TYPE_OBJECT,
                                                properties={
                                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='사용자 ID'),
                                                    'username': openapi.Schema(type=openapi.TYPE_STRING, description='사용자 이름'),
                                                    'email': openapi.Schema(type=openapi.TYPE_STRING, description='사용자 이메일'),
                                                },
                                                description='참여자 정보'
                                            )
                                        }
                                    ),
                                    description='참여자 리스트'
                                ),
                                'save_minutes': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='회의록 저장 여부'),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='생성일'),
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(description='Bad Request'),
            401: openapi.Response(description='Authentication failed')
        }
    )
    def post(self, request):
        authentication = SafeJWTAuthentication()
        user, auth_error = authentication.authenticate(request)

        if not user:
            return Response({'error': 'Authentication failed.'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = MeetingCreateSerializer(data=request.data)
        if serializer.is_valid():
            meeting = serializer.save(creator=user)
            return Response({"message": "Meeting created successfully", "meeting": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="회의 전체 조회",
        operation_description="사용자가 참가 중인 조직 내의 모든 회의 정보를 조회합니다.",
        responses={
            200: openapi.Response(
                description='Meetings retrieved successfully',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'meetings': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='회의 ID'),
                                    'title': openapi.Schema(type=openapi.TYPE_STRING, description='회의 제목'),
                                    'total_duration': openapi.Schema(type=openapi.TYPE_INTEGER, description='총 시간 (분 단위)'),
                                    'organization': openapi.Schema(type=openapi.TYPE_STRING, description='조직 이름'),
                                    'save_minutes': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='회의록 저장 여부'),
                                    'sections': openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                'name': openapi.Schema(type=openapi.TYPE_STRING, description='섹션 이름'),
                                            }
                                        )
                                    ),
                                    'participants': openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                'user': openapi.Schema(
                                                    type=openapi.TYPE_OBJECT,
                                                    properties={
                                                        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='사용자 ID'),
                                                        'username': openapi.Schema(type=openapi.TYPE_STRING, description='사용자 이름'),
                                                        'email': openapi.Schema(type=openapi.TYPE_STRING, description='사용자 이메일'),
                                                    }
                                                )
                                            }
                                        )
                                    ),
                                    'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='생성일'),
                                }
                            )
                        )
                    }
                )
            ),
            401: openapi.Response(description='Authentication failed'),
        }
    )
    def get(self, request):
        authentication = SafeJWTAuthentication()
        user, auth_error = authentication.authenticate(request)

        if not user:
            return Response({'error': 'Authentication failed.'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user_organizations = Organization.objects.filter(members__user=user)
    
        if not user_organizations.exists():
            return Response({'meetings': []}, status=status.HTTP_200_OK)

        meetings = Meeting.objects.filter(organization__in=user_organizations)
        serializer = MeetingCreateSerializer(meetings, many=True)
        return Response({"meetings": serializer.data}, status=status.HTTP_200_OK)


class MeetingDetailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [SafeJWTAuthentication]

    @swagger_auto_schema(
        operation_summary="단일 회의 조회",
        operation_description="특정 ID를 가진 단일 회의 정보를 조회합니다.",
        responses={
            200: openapi.Response(
                description='Meeting retrieved successfully',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='회의 ID'),
                        'title': openapi.Schema(type=openapi.TYPE_STRING, description='회의 제목'),
                        'total_duration': openapi.Schema(type=openapi.TYPE_INTEGER, description='총 시간 (분 단위)'),
                        'organization': openapi.Schema(type=openapi.TYPE_STRING, description='조직 이름'),
                        'save_minutes': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='회의록 저장 여부'),
                        'sections': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'name': openapi.Schema(type=openapi.TYPE_STRING, description='섹션 이름'),
                                }
                            )
                        ),
                        'participants': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'user': openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='사용자 ID'),
                                            'username': openapi.Schema(type=openapi.TYPE_STRING, description='사용자 이름'),
                                            'email': openapi.Schema(type=openapi.TYPE_STRING, description='사용자 이메일'),
                                        }
                                    )
                                }
                            )
                        ),
                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='생성일'),
                    }
                )
            ),
            401: openapi.Response(description='Authentication failed'),
            404: openapi.Response(description='Meeting not found')
        }
    )
    def get(self, request, meeting_id):
        authentication = SafeJWTAuthentication()
        user, auth_error = authentication.authenticate(request)

        if not user:
            return Response({'error': 'Authentication failed.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            meeting = Meeting.objects.get(id=meeting_id)
        except Meeting.DoesNotExist:
            return Response({"error": "Meeting not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = MeetingCreateSerializer(meeting)
        return Response(serializer.data, status=status.HTTP_200_OK)
