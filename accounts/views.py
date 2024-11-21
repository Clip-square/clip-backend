from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.views import APIView
from .serializers import *
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework import status
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from app.settings import SECRET_KEY
from rest_framework.permissions import AllowAny
import jwt


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="회원가입",
        operation_description="사용자 회원가입을 수행합니다.",
        request_body=UserSerializer,
        responses={
            200: openapi.Response("회원가입 성공", UserSerializer),
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

    @swagger_auto_schema(
        operation_summary="사용자 인증 확인",
        operation_description="쿠키에 저장된 액세스 토큰을 기반으로 사용자 정보를 반환합니다.",
        responses={
            200: openapi.Response("인증 성공", UserSerializer),
            400: "쿠키에 유효한 토큰이 없습니다.",
        },
    )
    def get(self, request):
        try:
            access = request.COOKIES.get("access", None)

            if access:
                payload = jwt.decode(access, SECRET_KEY, algorithms=["HS256"])
                pk = payload.get("user_id")
                user = get_object_or_404(CustomUser, pk=pk)
                serializer = UserSerializer(instance=user)

                return Response(serializer.data, status=status.HTTP_200_OK)

            return Response({"detail": "Access token not found in cookies."}, status=status.HTTP_400_BAD_REQUEST)

        except jwt.exceptions.ExpiredSignatureError:
            data = {"refresh": request.COOKIES.get("refresh", None)}
            serializer = TokenRefreshSerializer(data=data)

            if serializer.is_valid(raise_exception=True):
                access = serializer.data.get("access", None)
                refresh = serializer.data.get("refresh", None)
                payload = jwt.decode(access, SECRET_KEY, algorithms=["HS256"])
                pk = payload.get("user_id")

                user = get_object_or_404(CustomUser, pk=pk)
                serializer = UserSerializer(instance=user)

                res = Response(serializer.data, status=status.HTTP_200_OK)
                res.set_cookie("access", access)
                res.set_cookie("refresh", refresh)

                return res

            raise jwt.exceptions.InvalidTokenError

        except jwt.exceptions.InvalidTokenError:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="로그인",
        operation_description="이메일과 비밀번호로 사용자 로그인을 수행합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 이메일"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 비밀번호"),
            },
            required=["email", "password"],
        ),
        responses={
            200: "로그인 성공",
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
        response = Response({"message": "Logout success"}, status=status.HTTP_202_ACCEPTED)

        response.delete_cookie("access")
        response.delete_cookie("refresh")

        return response
