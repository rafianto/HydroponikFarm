from django.contrib import admin
from .models import Bibit, Penanaman, Perawatan, Pemanenan, Penjualan, BiayaOperasional


@admin.register(Bibit)
class BibitAdmin(admin.ModelAdmin):
    list_display = ['nama', 'jenis', 'varietas', 'supplier', 'harga_beli', 'stok', 'tanggal_masuk']
    list_filter = ['jenis', 'supplier']
    search_fields = ['nama', 'varietas', 'supplier']
    list_per_page = 20


@admin.register(Penanaman)
class PenanamanAdmin(admin.ModelAdmin):
    list_display = ['bibit', 'tanggal_tanam', 'jumlah', 'lokasi', 'sistem_hidroponik', 'status', 'estimasi_panen']
    list_filter = ['status', 'sistem_hidroponik']
    search_fields = ['bibit__nama', 'lokasi']
    list_per_page = 20


@admin.register(Perawatan)
class PerawatanAdmin(admin.ModelAdmin):
    list_display = ['penanaman', 'tanggal', 'jenis_perawatan', 'ph_air', 'ec', 'biaya']
    list_filter = ['jenis_perawatan']
    search_fields = ['penanaman__bibit__nama']
    list_per_page = 20


@admin.register(Pemanenan)
class PemanenanAdmin(admin.ModelAdmin):
    list_display = ['penanaman', 'tanggal_panen', 'jumlah_panen', 'satuan', 'kualitas']
    list_filter = ['kualitas', 'satuan']
    search_fields = ['penanaman__bibit__nama']
    list_per_page = 20


@admin.register(Penjualan)
class PenjualanAdmin(admin.ModelAdmin):
    list_display = ['pemanenan', 'tanggal_jual', 'pembeli', 'jumlah_jual', 'harga_satuan', 'status_pembayaran']
    list_filter = ['status_pembayaran']
    search_fields = ['pembeli', 'pemanenan__penanaman__bibit__nama']
    list_per_page = 20


@admin.register(BiayaOperasional)
class BiayaOperasionalAdmin(admin.ModelAdmin):
    list_display = ['tanggal', 'kategori', 'deskripsi', 'jumlah']
    list_filter = ['kategori']
    search_fields = ['deskripsi']
    list_per_page = 20