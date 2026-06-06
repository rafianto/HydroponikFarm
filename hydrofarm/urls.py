from django.contrib import admin
from django.urls import path, include
from farm import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # --- PENTING: URL UNTUK LOGIN, LOGOUT, DAN REGISTER ---
    path('accounts/', include('django.contrib.auth.urls')), 
    path('accounts/register/', views.register_view, name='register'),
    
    # --- URL APLIKASI FARM ---
    path('', include('farm.urls')),
]