from django.urls import path
from . import views

app_name = 'farm'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # Bibit
    path('bibit/', views.BibitListView.as_view(), name='bibit_list'),
    path('bibit/tambah/', views.BibitCreateView.as_view(), name='bibit_create'),
    path('bibit/<int:pk>/edit/', views.BibitUpdateView.as_view(), name='bibit_update'),
    path('bibit/<int:pk>/hapus/', views.BibitDeleteView.as_view(), name='bibit_delete'),

    # Penanaman
    path('penanaman/', views.PenanamanListView.as_view(), name='penanaman_list'),
    path('penanaman/tambah/', views.PenanamanCreateView.as_view(), name='penanaman_create'),
    path('penanaman/<int:pk>/edit/', views.PenanamanUpdateView.as_view(), name='penanaman_update'),
    path('penanaman/<int:pk>/hapus/', views.PenanamanDeleteView.as_view(), name='penanaman_delete'),

    # Perawatan
    path('perawatan/', views.PerawatanListView.as_view(), name='perawatan_list'),
    path('perawatan/tambah/', views.PerawatanCreateView.as_view(), name='perawatan_create'),
    path('perawatan/<int:pk>/edit/', views.PerawatanUpdateView.as_view(), name='perawatan_update'),
    path('perawatan/<int:pk>/hapus/', views.PerawatanDeleteView.as_view(), name='perawatan_delete'),

    # Pemanenan
    path('pemanenan/', views.PemanenanListView.as_view(), name='pemanenan_list'),
    path('pemanenan/tambah/', views.PemanenanCreateView.as_view(), name='pemanenan_create'),
    path('pemanenan/<int:pk>/edit/', views.PemanenanUpdateView.as_view(), name='pemanenan_update'),
    path('pemanenan/<int:pk>/hapus/', views.PemanenanDeleteView.as_view(), name='pemanenan_delete'),

    # Penjualan
    path('penjualan/', views.PenjualanListView.as_view(), name='penjualan_list'),
    path('penjualan/tambah/', views.PenjualanCreateView.as_view(), name='penjualan_create'),
    path('penjualan/<int:pk>/edit/', views.PenjualanUpdateView.as_view(), name='penjualan_update'),
    path('penjualan/<int:pk>/hapus/', views.PenjualanDeleteView.as_view(), name='penjualan_delete'),

    # Biaya Operasional
    path('biaya/', views.BiayaOperasionalListView.as_view(), name='biaya_list'),
    path('biaya/tambah/', views.BiayaOperasionalCreateView.as_view(), name='biaya_create'),
    path('biaya/<int:pk>/edit/', views.BiayaOperasionalUpdateView.as_view(), name='biaya_update'),
    path('biaya/<int:pk>/hapus/', views.BiayaOperasionalDeleteView.as_view(), name='biaya_delete'),
]