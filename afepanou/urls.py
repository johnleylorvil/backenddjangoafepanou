from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # Inclure les URLs des applications (à créer dans chaque app)
  # path('api/v1/core/', include('core.urls')),
   #path('api/v1/cms/', include('cms.urls')),
   #path('api/v1/erp/', include('erp.urls')),
   #path('api/v1/marketplace/', include('marketplace.urls')),
   #path('api/v1/payments/', include('payments.urls')),
]

# Servir les fichiers statiques et médias en développement uniquement
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)