from django import forms
from django.db.models import Sum, F, Q, DecimalField
from .models import Bibit, Penanaman, Perawatan, Pemanenan, Penjualan, BiayaOperasional

# Kelas CSS dasar untuk styling form input
INPUT_CSS = 'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all duration-200 bg-white'
SELECT_CSS = INPUT_CSS
TEXTAREA_CSS = 'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all duration-200 bg-white resize-none'
DATE_FORMAT = '%Y-%m-%d'


# ==========================================
# CUSTOM FIELD UNTUK DROPDOWN PEMANENAN
# ==========================================
class PemanenanChoiceField(forms.ModelChoiceField):
    """Custom field agar dropdown hanya menampilkan stok yang tersisa dan labelnya jelas"""
    
    def label_from_instance(self, obj):
        # Ambil total terjual dari annotation, default 0 jika tidak ada
        terjual = getattr(obj, 'total_terjual', 0) or 0
        sisa = obj.jumlah_panen - terjual
        # Format label: "Nama Bibit - Sisa: 5 Kilogram (12/06)"
        return f"{obj.penanaman.bibit.nama} - Sisa: {float(sisa):g} {obj.get_satuan_display()} ({obj.tanggal_panen.strftime('%d/%m')})"


# ==========================================
# FORM FORMS
# ==========================================

class BibitForm(forms.ModelForm):
    class Meta:
        model = Bibit
        fields = '__all__'
        widgets = {
            'nama': forms.TextInput(attrs={'class': INPUT_CSS, 'placeholder': 'Masukkan nama bibit'}),
            'jenis': forms.Select(attrs={'class': SELECT_CSS}),
            'varietas': forms.TextInput(attrs={'class': INPUT_CSS, 'placeholder': 'Opsional'}),
            'supplier': forms.TextInput(attrs={'class': INPUT_CSS, 'placeholder': 'Nama supplier'}),
            'harga_beli': forms.NumberInput(attrs={'class': INPUT_CSS, 'step': '0.01', 'min': '0'}),
            'stok': forms.NumberInput(attrs={'class': INPUT_CSS, 'min': '0'}),
            'tanggal_masuk': forms.DateInput(attrs={'class': INPUT_CSS, 'type': 'date'}, format=DATE_FORMAT),
            'keterangan': forms.Textarea(attrs={'class': TEXTAREA_CSS, 'rows': 3, 'placeholder': 'Catatan tambahan...'}),
        }


class PenanamanForm(forms.ModelForm):
    class Meta:
        model = Penanaman
        fields = '__all__'
        widgets = {
            'bibit': forms.Select(attrs={'class': SELECT_CSS}),
            'tanggal_tanam': forms.DateInput(attrs={'class': INPUT_CSS, 'type': 'date'}, format=DATE_FORMAT),
            'jumlah': forms.NumberInput(attrs={'class': INPUT_CSS, 'min': '1'}),
            'lokasi': forms.TextInput(attrs={'class': INPUT_CSS, 'placeholder': 'Contoh: Rak A1, Greenhouse 2'}),
            'sistem_hidroponik': forms.Select(attrs={'class': SELECT_CSS}),
            'status': forms.Select(attrs={'class': SELECT_CSS}),
            'estimasi_panen': forms.DateInput(attrs={'class': INPUT_CSS, 'type': 'date'}, format=DATE_FORMAT),
            'catatan': forms.Textarea(attrs={'class': TEXTAREA_CSS, 'rows': 3}),
        }


class PerawatanForm(forms.ModelForm):
    class Meta:
        model = Perawatan
        fields = '__all__'
        widgets = {
            'penanaman': forms.Select(attrs={'class': SELECT_CSS}),
            'tanggal': forms.DateInput(attrs={'class': INPUT_CSS, 'type': 'date'}, format=DATE_FORMAT),
            'jenis_perawatan': forms.Select(attrs={'class': SELECT_CSS}),
            'nutrisi_digunakan': forms.TextInput(attrs={'class': INPUT_CSS, 'placeholder': 'Contoh: AB Mix, Nutrisi Hidroponik'}),
            'ph_air': forms.NumberInput(attrs={'class': INPUT_CSS, 'step': '0.1', 'min': '0', 'max': '14'}),
            'ec': forms.NumberInput(attrs={'class': INPUT_CSS, 'step': '0.01', 'min': '0'}),
            'volume_nutrisi_ml': forms.NumberInput(attrs={'class': INPUT_CSS, 'step': '0.1', 'min': '0'}),
            'biaya': forms.NumberInput(attrs={'class': INPUT_CSS, 'step': '0.01', 'min': '0'}),
            'catatan': forms.Textarea(attrs={'class': TEXTAREA_CSS, 'rows': 3}),
        }


class PemanenanForm(forms.ModelForm):
    class Meta:
        model = Pemanenan
        fields = '__all__'
        widgets = {
            'penanaman': forms.Select(attrs={'class': SELECT_CSS}),
            'tanggal_panen': forms.DateInput(attrs={'class': INPUT_CSS, 'type': 'date'}, format=DATE_FORMAT),
            'jumlah_panen': forms.NumberInput(attrs={'class': INPUT_CSS, 'step': '0.01', 'min': '0'}),
            'satuan': forms.Select(attrs={'class': SELECT_CSS}),
            'kualitas': forms.Select(attrs={'class': SELECT_CSS}),
            'catatan': forms.Textarea(attrs={'class': TEXTAREA_CSS, 'rows': 3}),
        }


class PenjualanForm(forms.ModelForm):
    # Gunakan custom field di atas, jangan pakai forms.Select lagi di sini
    pemanenan = PemanenanChoiceField(
        queryset=Pemanenan.objects.none(), # Akan di-override di __init__
        widget=forms.Select(attrs={'class': SELECT_CSS}),
        label='Sumber Pemanenan'
    )

    class Meta:
        model = Penjualan
        fields = '__all__'
        # Pemanenan tidak perlu dimasukkan ke widgets karena sudah di-handle di atas
        widgets = {
            'tanggal_jual': forms.DateInput(attrs={'class': INPUT_CSS, 'type': 'date'}, format=DATE_FORMAT),
            'pembeli': forms.TextInput(attrs={'class': INPUT_CSS, 'placeholder': 'Nama pembeli'}),
            'jumlah_jual': forms.NumberInput(attrs={'class': INPUT_CSS, 'step': '0.01', 'min': '0'}),
            'harga_satuan': forms.NumberInput(attrs={'class': INPUT_CSS, 'step': '0.01', 'min': '0'}),
            'status_pembayaran': forms.Select(attrs={'class': SELECT_CSS}),
            'catatan': forms.Textarea(attrs={'class': TEXTAREA_CSS, 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Hitung total terjual untuk setiap pemanenan menggunakan Annotation
        base_qs = Pemanenan.objects.select_related('penanaman__bibit').annotate(
            total_terjual=Sum('penjualan__jumlah_jual', output_field=DecimalField())
        )
        
        # 2. Filter: Hanya tampilkan yang BELUM HABIS TERJUAL
        q_filter = Q(total_terjual__isnull=True) | Q(total_terjual__lt=F('jumlah_panen'))
        
        # 3. Jika sedang MENGEDIT data penjualan, pastikan pemanenan yang saat ini terpilih 
        # tetap muncul di dropdown agar form tidak error.
        if self.instance.pk and self.instance.pemanenan_id:
            q_filter |= Q(pk=self.instance.pemanenan_id)
            
        # 4. Terapkan filter ke custom field queryset
        self.fields['pemanenan'].queryset = base_qs.filter(q_filter).distinct()

        # Tambahkan class styling khusus untuk input Harga agar prefix Rp tidak tertimpa
        if 'harga_satuan' in self.fields:
            self.fields['harga_satuan'].widget.attrs.update({'class': 'pl-10 ' + INPUT_CSS})


class BiayaOperasionalForm(forms.ModelForm):
    class Meta:
        model = BiayaOperasional
        fields = '__all__'
        widgets = {
            'tanggal': forms.DateInput(attrs={'class': INPUT_CSS, 'type': 'date'}, format=DATE_FORMAT),
            'kategori': forms.Select(attrs={'class': SELECT_CSS}),
            'deskripsi': forms.TextInput(attrs={'class': INPUT_CSS, 'placeholder': 'Deskripsi pengeluaran'}),
            'jumlah': forms.NumberInput(attrs={'class': INPUT_CSS, 'step': '0.01', 'min': '0'}),
            'catatan': forms.Textarea(attrs={'class': TEXTAREA_CSS, 'rows': 3}),
        }