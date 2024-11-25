from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.views import APIView
from .serializers import *
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import status
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny
from .authenticate import SafeJWTAuthentication


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="회원가입",
        operation_description="사용자 회원가입을 수행합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 이메일"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 비밀번호"),
                "name": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 이름"),
            },
            required=["email", "password", "name"],
        ),
        responses={
            200: openapi.Response(
                "회원가입 성공",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "user": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "id": openapi.Schema(type=openapi.TYPE_INTEGER, description="사용자 ID"),
                                "email": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 이메일"),
                                "name": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 이름"),
                                "created_at": openapi.Schema(type=openapi.FORMAT_DATETIME, description="생성 시간"),
                                "updated_at": openapi.Schema(type=openapi.FORMAT_DATETIME, description="수정 시간"),
                            },
                        ),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, description="결과 메시지"),
                        "token": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "access": openapi.Schema(type=openapi.TYPE_STRING, description="액세스 토큰"),
                                "refresh": openapi.Schema(type=openapi.TYPE_STRING, description="리프레시 토큰"),
                            },
                        ),
                    },
                ),
            ),
            400: "유효성 검사 오류",
        },
    )
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token = TokenObtainPairSerializer.get_token(user)
            refresh_token = str(token)
            access_token = str(token.access_token)

            response = Response(
                {
                    "user": serializer.data,
                    "message": "Register successs",
                    "token": {
                        "access": access_token,
                        "refresh": refresh_token,
                    },
                },
                status=status.HTTP_200_OK,
            )

            response.set_cookie("access", access_token, httponly=True)
            response.set_cookie("refresh", refresh_token, httponly=True)

            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AuthAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [SafeJWTAuthentication]


    @swagger_auto_schema(
        operation_summary="사용자 인증 확인",
        operation_description="쿠키에 저장된 액세스 토큰을 기반으로 사용자 정보를 반환합니다.",
        responses={
            200: openapi.Response(
                "인증 성공",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER, description="사용자 ID"),
                        "email": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 이메일"),
                        "name": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 이름"),
                        "created_at": openapi.Schema(type=openapi.FORMAT_DATETIME, description="생성 시간"),
                        "updated_at": openapi.Schema(type=openapi.FORMAT_DATETIME, description="수정 시간"),
                    },
                ),
            ),
            400: "쿠키에 유효한 토큰이 없습니다.",
        },
    )
    def get(self, request):
        authentication = SafeJWTAuthentication()
        user, auth_error = authentication.authenticate(request)

        if user:
            serializer = UserSerializer(instance=user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Authentication failed.'}, status=status.HTTP_401_UNAUTHORIZED)


    @swagger_auto_schema(
        operation_summary="로그인",
        operation_description="이메일, 비밀번호로 사용자 로그인을 수행합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 이메일"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 비밀번호"),
            },
            required=["email", "password"],
        ),
        responses={
            200: openapi.Response(
                "로그인 성공",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "user": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "id": openapi.Schema(type=openapi.TYPE_INTEGER, description="사용자 ID"),
                                "email": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 이메일"),
                                "name": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 이름"),
                                "created_at": openapi.Schema(type=openapi.FORMAT_DATETIME, description="생성 시간"),
                                "updated_at": openapi.Schema(type=openapi.FORMAT_DATETIME, description="수정 시간"),
                            },
                        ),
                        "token": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "access": openapi.Schema(type=openapi.TYPE_STRING, description="액세스 토큰"),
                                "refresh": openapi.Schema(type=openapi.TYPE_STRING, description="리프레시 토큰"),
                            },
                        ),
                    },
                ),
            ),
            400: "로그인 실패 또는 잘못된 입력",
        },
    )
    def post(self, request):
        user = authenticate(email=request.data.get("email"), password=request.data.get("password"))

        if user is not None:
            serializer = UserSerializer(user)

            token = TokenObtainPairSerializer.get_token(user)
            refresh_token = str(token)
            access_token = str(token.access_token)

            response = Response(
                {
                    "user": serializer.data,
                    "message": "login success",
                    "token": {
                        "access": access_token,
                        "refresh": refresh_token,
                    },
                },
                status=status.HTTP_200_OK,
            )

            response.set_cookie("access", access_token, httponly=True)
            response.set_cookie("refresh", refresh_token, httponly=True)

            return response
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="로그아웃",
        operation_description="로그아웃을 수행하고 쿠키에 저장된 토큰을 제거합니다.",
        responses={202: "로그아웃 성공"},
    )
    def delete(self, request):
        authentication = SafeJWTAuthentication()
        user, auth_error = authentication.authenticate(request)

        
        if not user:
            return Response({'error': 'Authentication failed.'}, status=status.HTTP_401_UNAUTHORIZED)
        
        response = Response({"message": "Logout success"}, status=status.HTTP_202_ACCEPTED)
        response.delete_cookie("access")
        response.delete_cookie("refresh")

        return response