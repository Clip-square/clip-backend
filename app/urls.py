from django.contrib import admin
from django.urls import path, include, re_path
from drf_yasg.views import get_schema_view
from rest_framework.permissions import AllowAny
from drf_yasg import openapi
from accounts.authenticate import SafeJWTAuthentication
from django.http import HttpResponse

def health_checker(request):
    return HttpResponse("OK")


schema_view_v1 = get_schema_view(
    openapi.Info(
        title = "Clip API Docs",
        default_version = 'v1',
        description = "AI 회의 도우미 서비스 Clip의 API Docs 입니다.",
        contact = openapi.Contact(email = "moonwlsdnl@gmail.com"),
    ),
    validators = ['flex'],
    public = True,
    permission_classes = [AllowAny],
    authentication_classes=[SafeJWTAuthentication],
    patterns=[
        path('accounts/', include('accounts.urls')),
        path('organizations/', include('organizations.urls')),
        path('meetings/', include('meetings.urls')),
    ]
)

urlpatterns = [
    path('', health_checker,),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('organizations/', include('organizations.urls')),
    path('meetings/', include('meetings.urls')),
    re_path(r'^v1/swagger/$', schema_view_v1.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^v1/redoc/$', schema_view_v1.with_ui('redoc', cache_timeout=0), name='schema-redoc-v1'),
]
