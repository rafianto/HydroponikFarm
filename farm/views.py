import json
from datetime import timedelta
from collections import defaultdict

from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Sum, Count, F, Q, Value, DecimalField, ExpressionWrapper, Avg, OuterRef, Subquery, CharField
from django.db.models.functions import TruncMonth, TruncYear
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm

from .models import Bibit, Penanaman, Perawatan, Pemanenan, Penjualan, BiayaOperasional
from .forms import (
    BibitForm, PenanamanForm, PerawatanForm,
    PemanenanForm, PenjualanForm, BiayaOperasionalForm
)


# ==================== AUTHENTICATION ====================

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


# ==================== DASHBOARD ====================

@login_required(login_url='/accounts/login/')
def dashboard(request):
    today = timezone.now().date()
    bulan_ini = today.month
    tahun_ini = today.year
    period = request.GET.get('period', 'daily')

    # --- Statistik Utama ---
    total_bibit = Bibit.objects.aggregate(total=Sum('stok'))['total'] or 0
    penanaman_aktif = Penanaman.objects.filter(
        status__in=['aktif', 'masa_tumbuh', 'siap_panen']
    ).count()
    panen_bulan_ini = Pemanenan.objects.filter(
        tanggal_panen__month=bulan_ini,
        tanggal_panen__year=tahun_ini
    ).count()

    pendapatan_bulan_ini = Penjualan.objects.filter(
        tanggal_jual__month=bulan_ini,
        tanggal_jual__year=tahun_ini
    ).annotate(total_harga=F('jumlah_jual') * F('harga_satuan')).aggregate(
        total=Sum('total_harga')
    )['total'] or 0

    pengeluaran_ops_bulan = BiayaOperasional.objects.filter(
        tanggal__month=bulan_ini,
        tanggal__year=tahun_ini
    ).aggregate(total=Sum('jumlah'))['total'] or 0

    pengeluaran_rawat_bulan = Perawatan.objects.filter(
        tanggal__month=bulan_ini,
        tanggal__year=tahun_ini
    ).aggregate(total=Sum('biaya'))['total'] or 0

    total_pengeluaran = pengeluaran_ops_bulan + pengeluaran_rawat_bulan
    profit = pendapatan_bulan_ini - total_pengeluaran

    # ==========================================
    # --- LOGIKA CASHFLOW & MUTASI ---
    # ==========================================
    if period == 'monthly':
        inflow_qs = Penjualan.objects.annotate(period=TruncMonth('tanggal_jual')).values('period').annotate(total=Sum(F('jumlah_jual') * F('harga_satuan')))
        outflow_ops = BiayaOperasional.objects.annotate(period=TruncMonth('tanggal')).values('period').annotate(total=Sum('jumlah'))
        outflow_rawat = Perawatan.objects.annotate(period=TruncMonth('tanggal')).values('period').annotate(total=Sum('biaya'))
    elif period == 'yearly':
        inflow_qs = Penjualan.objects.annotate(period=TruncYear('tanggal_jual')).values('period').annotate(total=Sum(F('jumlah_jual') * F('harga_satuan')))
        outflow_ops = BiayaOperasional.objects.annotate(period=TruncYear('tanggal')).values('period').annotate(total=Sum('jumlah'))
        outflow_rawat = Perawatan.objects.annotate(period=TruncYear('tanggal')).values('period').annotate(total=Sum('biaya'))
    else: # daily
        inflow_qs = Penjualan.objects.annotate(period=F('tanggal_jual')).values('period').annotate(total=Sum(F('jumlah_jual') * F('harga_satuan')))
        outflow_ops = BiayaOperasional.objects.annotate(period=F('tanggal')).values('period').annotate(total=Sum('jumlah'))
        outflow_rawat = Perawatan.objects.annotate(period=F('tanggal')).values('period').annotate(total=Sum('biaya'))
    
    inflow_dict = {item['period']: float(item['total'] or 0) for item in inflow_qs}
    outflow_dict = defaultdict(float)
    for item in outflow_ops:
        outflow_dict[item['period']] += float(item['total'] or 0)
    for item in outflow_rawat:
        outflow_dict[item['period']] += float(item['total'] or 0)

    all_periods = set(inflow_dict.keys()).union(set(outflow_dict.keys()))
    sorted_periods = sorted(list(all_periods))

    cashflow_report = []
    accumulated_balance = 0.0
    grand_total_inflow = 0.0
    grand_total_outflow = 0.0

    for p in sorted_periods:
        inflow = inflow_dict.get(p, 0.0)
        outflow = outflow_dict.get(p, 0.0)
        net_flow = inflow - outflow
        accumulated_balance += net_flow
        grand_total_inflow += inflow
        grand_total_outflow += outflow

        if period == 'monthly':
            label = p.strftime('%B %Y') if hasattr(p, 'strftime') else str(p)
        elif period == 'yearly':
            label = str(p.year) if hasattr(p, 'year') else str(p)
        else:
            label = p.strftime('%d %b %Y') if hasattr(p, 'strftime') else str(p)

        cashflow_report.append({
            'period': p, 'label': label, 'inflow': inflow,
            'outflow': outflow, 'net_flow': net_flow,
            'accumulated_balance': accumulated_balance
        })
    cashflow_report.reverse()

    # --- Charts ---
    chart_labels = []
    chart_pendapatan = []
    chart_pengeluaran = []
    for i in range(5, -1, -1):
        m = bulan_ini - i
        y = tahun_ini
        while m <= 0: m += 12; y -= 1
        chart_labels.append(f"{m}/{y}")
        pend = Penjualan.objects.filter(tanggal_jual__month=m, tanggal_jual__year=y).annotate(total_harga=F('jumlah_jual') * F('harga_satuan')).aggregate(total=Sum('total_harga'))['total'] or 0
        ops = BiayaOperasional.objects.filter(tanggal__month=m, tanggal__year=y).aggregate(total=Sum('jumlah'))['total'] or 0
        rawat = Perawatan.objects.filter(tanggal__month=m, tanggal__year=y).aggregate(total=Sum('biaya'))['total'] or 0
        chart_pendapatan.append(float(pend))
        chart_pengeluaran.append(float(ops + rawat))

    status_data_raw = Penanaman.objects.values('status').annotate(count=Count('id'))
    status_map = dict(Penanaman.STATUS_CHOICES)
    status_labels = [status_map.get(s['status'], s['status']) for s in status_data_raw]
    status_data = [s['count'] for s in status_data_raw]

    biaya_kategori_raw = BiayaOperasional.objects.filter(tanggal__month=bulan_ini, tanggal__year=tahun_ini).values('kategori').annotate(total=Sum('jumlah'))
    kategori_map = dict(BiayaOperasional.KATEGORI_CHOICES)
    kategori_labels = [kategori_map.get(b['kategori'], b['kategori']) for b in biaya_kategori_raw]
    kategori_data = [float(b['total']) for b in biaya_kategori_raw]

    top_bibit = Penanaman.objects.values('bibit__nama').annotate(total_tanam=Sum('jumlah')).order_by('-total_tanam')[:5]
    penjualan_terbaru = Penjualan.objects.select_related('pemanenan__penanaman__bibit')[:5]
    pemanenan_terbaru = Pemanenan.objects.select_related('penanaman__bibit')[:5]
    perawatan_terbaru = Perawatan.objects.select_related('penanaman__bibit')[:5]

    context = {
        'total_bibit': total_bibit, 'penanaman_aktif': penanaman_aktif,
        'panen_bulan_ini': panen_bulan_ini, 'pendapatan_bulan_ini': pendapatan_bulan_ini,
        'total_pengeluaran': total_pengeluaran, 'profit': profit,
        'chart_labels': json.dumps(chart_labels), 'chart_pendapatan': json.dumps(chart_pendapatan),
        'chart_pengeluaran': json.dumps(chart_pengeluaran), 'status_labels': json.dumps(status_labels),
        'status_data': json.dumps(status_data), 'kategori_labels': json.dumps(kategori_labels),
        'kategori_data': json.dumps(kategori_data), 'top_bibit': top_bibit,
        'penjualan_terbaru': penjualan_terbaru, 'pemanenan_terbaru': pemanenan_terbaru,
        'perawatan_terbaru': perawatan_terbaru,
        'period': period, 'cashflow_report': cashflow_report,
        'grand_total_inflow': grand_total_inflow, 'grand_total_outflow': grand_total_outflow,
        'accumulated_balance': accumulated_balance,
    }
    return render(request, 'farm/dashboard.html', context)


# ==================== BIBIT ====================

class BibitListView(LoginRequiredMixin, ListView):
    model = Bibit
    template_name = 'farm/bibit_list.html'
    context_object_name = 'object_list'
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(Q(nama__icontains=search) | Q(varietas__icontains=search) | Q(supplier__icontains=search))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search'] = self.request.GET.get('search', '')
        ctx['page_title'] = 'Data Bibit'
        ctx['create_url'] = 'farm:bibit_create'
        return ctx


class BibitCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Bibit
    form_class = BibitForm
    template_name = 'farm/bibit_form.html'
    success_url = reverse_lazy('farm:bibit_list')
    success_message = 'Bibit "%(nama)s" berhasil ditambahkan!'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Tambah Bibit Baru'
        ctx['cancel_url'] = reverse_lazy('farm:bibit_list')
        return ctx


class BibitUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Bibit
    form_class = BibitForm
    template_name = 'farm/bibit_form.html'
    success_url = reverse_lazy('farm:bibit_list')
    success_message = 'Bibit "%(nama)s" berhasil diperbarui!'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Edit Bibit'
        ctx['cancel_url'] = reverse_lazy('farm:bibit_list')
        return ctx


class BibitDeleteView(LoginRequiredMixin, DeleteView):
    model = Bibit
    template_name = 'farm/confirm_delete.html'
    success_url = reverse_lazy('farm:bibit_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Hapus Bibit'
        ctx['cancel_url'] = reverse_lazy('farm:bibit_list')
        return ctx


# ==================== PENANAMAN ====================
class PenanamanListView(LoginRequiredMixin, ListView):
    model = Penanaman
    template_name = 'farm/penanaman_list.html'
    context_object_name = 'object_list'
    paginate_by = 15

    def get_queryset(self):
        # 1. Subquery harga jual rata-rata
        avg_price_qs = Penjualan.objects.filter(
            pemanenan__penanaman__bibit_id=OuterRef('bibit_id')
        ).order_by().values('pemanenan__penanaman__bibit_id').annotate(
            avg_price=Avg('harga_satuan')
        ).values('avg_price')[:1]

        # 2. Subquery satuan panen terakhir
        satuan_qs = Pemanenan.objects.filter(
            penanaman_id=OuterRef('pk')
        ).order_by('-tanggal_panen').values('satuan')[:1]

        # 3. Queryset utama
        qs = super().get_queryset().select_related('bibit').annotate(
            total_panen=Sum('pemanenan__jumlah_panen', default=Value(0)),
            total_terjual=Sum('pemanenan__penjualan__jumlah_jual', default=Value(0)),
            harga_rata_rata=Subquery(avg_price_qs, output_field=DecimalField()),
            satuan_panen=Subquery(satuan_qs, output_field=CharField())
        ).annotate(
            sisa_stok=ExpressionWrapper(F('total_panen') - F('total_terjual'), output_field=DecimalField()),
            estimasi_nilai_jual=ExpressionWrapper((F('total_panen') - F('total_terjual')) * F('harga_rata_rata'), output_field=DecimalField())
        )

        # ==========================================
        # --- LOGIKA PENCARIAN & FILTER (BARU) ---
        # ==========================================
        komoditi = self.request.GET.get('komoditi', '').strip()
        lokasi = self.request.GET.get('lokasi', '').strip()
        tgl_mulai = self.request.GET.get('tgl_mulai', '')
        tgl_selesai = self.request.GET.get('tgl_selesai', '')
        status = self.request.GET.get('status', '')

        if komoditi:
            qs = qs.filter(Q(bibit__nama__icontains=komoditi) | Q(bibit__varietas__icontains=komoditi))
        if lokasi:
            qs = qs.filter(lokasi__icontains=lokasi)
        if tgl_mulai:
            qs = qs.filter(tanggal_tanam__gte=tgl_mulai)
        if tgl_selesai:
            qs = qs.filter(tanggal_tanam__lte=tgl_selesai)
        if status:
            qs = qs.filter(status=status)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Simpan parameter pencarian ke context agar form tetap terisi setelah submit
        ctx['status_filter'] = self.request.GET.get('status', '')
        ctx['komoditi_filter'] = self.request.GET.get('komoditi', '')
        ctx['lokasi_filter'] = self.request.GET.get('lokasi', '')
        ctx['tgl_mulai_filter'] = self.request.GET.get('tgl_mulai', '')
        ctx['tgl_selesai_filter'] = self.request.GET.get('tgl_selesai', '')
        
        ctx['status_choices'] = Penanaman.STATUS_CHOICES
        ctx['page_title'] = 'Data Penanaman'
        ctx['create_url'] = 'farm:penanaman_create'
        return ctx    

class PenanamanCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Penanaman
    form_class = PenanamanForm
    template_name = 'farm/penanaman_form.html'
    success_url = reverse_lazy('farm:penanaman_list')
    success_message = 'Data penanaman berhasil ditambahkan!'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Tambah Penanaman Baru'
        ctx['cancel_url'] = reverse_lazy('farm:penanaman_list')
        return ctx


class PenanamanUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Penanaman
    form_class = PenanamanForm
    template_name = 'farm/penanaman_form.html'
    success_url = reverse_lazy('farm:penanaman_list')
    success_message = 'Data penanaman berhasil diperbarui!'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Edit Penanaman'
        ctx['cancel_url'] = reverse_lazy('farm:penanaman_list')
        return ctx


class PenanamanDeleteView(LoginRequiredMixin, DeleteView):
    model = Penanaman
    template_name = 'farm/confirm_delete.html'
    success_url = reverse_lazy('farm:penanaman_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Hapus Penanaman'
        ctx['cancel_url'] = reverse_lazy('farm:penanaman_list')
        return ctx


# ==================== PERAWATAN ====================
class PerawatanListView(LoginRequiredMixin, ListView):
    model = Perawatan
    template_name = 'farm/perawatan_list.html'
    context_object_name = 'object_list'
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset().select_related('penanaman__bibit')
        
        # Ambil parameter pencarian
        q_bibit = self.request.GET.get('q_bibit', '').strip()
        q_lokasi = self.request.GET.get('q_lokasi', '').strip()
        q_mulai = self.request.GET.get('q_mulai', '')
        q_selesai = self.request.GET.get('q_selesai', '')
        jenis_perawatan = self.request.GET.get('jenis_perawatan', '')

        # Terapkan filter
        if q_bibit:
            qs = qs.filter(Q(penanaman__bibit__nama__icontains=q_bibit) | Q(penanaman__bibit__varietas__icontains=q_bibit))
        if q_lokasi:
            qs = qs.filter(penanaman__lokasi__icontains=q_lokasi)
        if q_mulai:
            qs = qs.filter(tanggal__gte=q_mulai)
        if q_selesai:
            qs = qs.filter(tanggal__lte=q_selesai)
        if jenis_perawatan:
            qs = qs.filter(jenis_perawatan=jenis_perawatan)
            
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Data Perawatan'
        ctx['create_url'] = 'farm:perawatan_create'
        # Simpan parameter ke context agar form tetap terisi
        ctx['q_bibit'] = self.request.GET.get('q_bibit', '')
        ctx['q_lokasi'] = self.request.GET.get('q_lokasi', '')
        ctx['q_mulai'] = self.request.GET.get('q_mulai', '')
        ctx['q_selesai'] = self.request.GET.get('q_selesai', '')
        ctx['jenis_perawatan_filter'] = self.request.GET.get('jenis_perawatan', '')
        ctx['jenis_perawatan_choices'] = Perawatan.JENIS_CHOICES
        return ctx


class PerawatanCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Perawatan
    form_class = PerawatanForm
    template_name = 'farm/perawatan_form.html'
    success_url = reverse_lazy('farm:perawatan_list')
    success_message = 'Data perawatan berhasil ditambahkan!'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Tambah Perawatan Baru'
        ctx['cancel_url'] = reverse_lazy('farm:perawatan_list')
        return ctx

    def get_initial(self):
        initial = super().get_initial()
        penanaman_id = self.request.GET.get('penanaman')
        if penanaman_id:
            initial['penanaman'] = penanaman_id
        return initial


class PerawatanUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Perawatan
    form_class = PerawatanForm
    template_name = 'farm/perawatan_form.html'
    success_url = reverse_lazy('farm:perawatan_list')
    success_message = 'Data perawatan berhasil diperbarui!'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Edit Perawatan'
        ctx['cancel_url'] = reverse_lazy('farm:perawatan_list')
        return ctx


class PerawatanDeleteView(LoginRequiredMixin, DeleteView):
    model = Perawatan
    template_name = 'farm/confirm_delete.html'
    success_url = reverse_lazy('farm:perawatan_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Hapus Perawatan'
        ctx['cancel_url'] = reverse_lazy('farm:perawatan_list')
        return ctx


# ==================== PEMANENAN ====================
class PemanenanListView(LoginRequiredMixin, ListView):
    model = Pemanenan
    template_name = 'farm/pemanenan_list.html'
    context_object_name = 'object_list'
    paginate_by = 15

    def get_queryset(self):
        # Base queryset dengan annotation
        qs = super().get_queryset().select_related('penanaman__bibit').annotate(
            total_terjual=Sum('penjualan__jumlah_jual', default=Value(0))
        ).annotate(
            sisa_stok=ExpressionWrapper(F('jumlah_panen') - F('total_terjual'), output_field=DecimalField())
        )

        # Ambil parameter pencarian
        q_bibit = self.request.GET.get('q_bibit', '').strip()
        q_lokasi = self.request.GET.get('q_lokasi', '').strip()
        q_mulai = self.request.GET.get('q_mulai', '')
        q_selesai = self.request.GET.get('q_selesai', '')
        q_kualitas = self.request.GET.get('q_kualitas', '')
        q_status_jual = self.request.GET.get('q_status_jual', '')

        # Terapkan filter
        if q_bibit:
            qs = qs.filter(Q(penanaman__bibit__nama__icontains=q_bibit) | Q(penanaman__bibit__varietas__icontains=q_bibit))
        if q_lokasi:
            qs = qs.filter(penanaman__lokasi__icontains=q_lokasi)
        if q_mulai:
            qs = qs.filter(tanggal_panen__gte=q_mulai)
        if q_selesai:
            qs = qs.filter(tanggal_panen__lte=q_selesai)
        if q_kualitas:
            qs = qs.filter(kualitas=q_kualitas)
        
        # Filter Status Penjualan berdasarkan sisa stok (Annotation)
        if q_status_jual == 'belum':
            qs = qs.filter(total_terjual=0)
        elif q_status_jual == 'sebagian':
            qs = qs.filter(total_terjual__gt=0, sisa_stok__gt=0)
        elif q_status_jual == 'habis':
            qs = qs.filter(sisa_stok__lte=0)
            
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Data Pemanenan'
        ctx['create_url'] = 'farm:pemanenan_create'
        # Simpan parameter ke context agar form tetap terisi
        ctx['q_bibit'] = self.request.GET.get('q_bibit', '')
        ctx['q_lokasi'] = self.request.GET.get('q_lokasi', '')
        ctx['q_mulai'] = self.request.GET.get('q_mulai', '')
        ctx['q_selesai'] = self.request.GET.get('q_selesai', '')
        ctx['q_kualitas'] = self.request.GET.get('q_kualitas', '')
        ctx['q_status_jual'] = self.request.GET.get('q_status_jual', '')
        ctx['kualitas_choices'] = Pemanenan.KUALITAS_CHOICES
        return ctx
        
class PemanenanCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Pemanenan
    form_class = PemanenanForm
    template_name = 'farm/pemanenan_form.html'
    success_url = reverse_lazy('farm:pemanenan_list')
    success_message = 'Data pemanenan berhasil ditambahkan!'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Tambah Pemanenan Baru'
        ctx['cancel_url'] = reverse_lazy('farm:pemanenan_list')
        return ctx

    def get_initial(self):
        initial = super().get_initial()
        penanaman_id = self.request.GET.get('penanaman')
        if penanaman_id:
            initial['penanaman'] = penanaman_id
        return initial


class PemanenanUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Pemanenan
    form_class = PemanenanForm
    template_name = 'farm/pemanenan_form.html'
    success_url = reverse_lazy('farm:pemanenan_list')
    success_message = 'Data pemanenan berhasil diperbarui!'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Edit Pemanenan'
        ctx['cancel_url'] = reverse_lazy('farm:pemanenan_list')
        return ctx


class PemanenanDeleteView(LoginRequiredMixin, DeleteView):
    model = Pemanenan
    template_name = 'farm/confirm_delete.html'
    success_url = reverse_lazy('farm:pemanenan_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Hapus Pemanenan'
        ctx['cancel_url'] = reverse_lazy('farm:pemanenan_list')
        return ctx


# ==================== PENJUALAN ====================
class PenjualanListView(LoginRequiredMixin, ListView):
    model = Penjualan
    template_name = 'farm/penjualan_list.html'
    context_object_name = 'object_list'
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset().select_related('pemanenan__penanaman__bibit')
        
        # Ambil parameter pencarian
        q_bibit = self.request.GET.get('q_bibit', '').strip()
        q_pembeli = self.request.GET.get('q_pembeli', '').strip()
        q_mulai = self.request.GET.get('q_mulai', '')
        q_selesai = self.request.GET.get('q_selesai', '')
        status = self.request.GET.get('status', '')

        # Terapkan filter
        if q_bibit:
            qs = qs.filter(Q(pemanenan__penanaman__bibit__nama__icontains=q_bibit) | Q(pemanenan__penanaman__bibit__varietas__icontains=q_bibit))
        if q_pembeli:
            qs = qs.filter(pembeli__icontains=q_pembeli)
        if q_mulai:
            qs = qs.filter(tanggal_jual__gte=q_mulai)
        if q_selesai:
            qs = qs.filter(tanggal_jual__lte=q_selesai)
        if status:
            qs = qs.filter(status_pembayaran=status)
            
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Data Penjualan'
        ctx['create_url'] = 'farm:penjualan_create'
        # Simpan parameter ke context agar form tetap terisi
        ctx['q_bibit'] = self.request.GET.get('q_bibit', '')
        ctx['q_pembeli'] = self.request.GET.get('q_pembeli', '')
        ctx['q_mulai'] = self.request.GET.get('q_mulai', '')
        ctx['q_selesai'] = self.request.GET.get('q_selesai', '')
        ctx['status_pembayaran_filter'] = self.request.GET.get('status', '')
        ctx['status_pembayaran_choices'] = Penjualan.STATUS_CHOICES
        return ctx

class PenjualanCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Penjualan
    form_class = PenjualanForm
    template_name = 'farm/penjualan_form.html'
    success_url = reverse_lazy('farm:penjualan_list')
    success_message = 'Data penjualan berhasil ditambahkan!'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Tambah Penjualan Baru'
        ctx['cancel_url'] = reverse_lazy('farm:penjualan_list')
        return ctx

    def get_initial(self):
        initial = super().get_initial()
        pemanenan_id = self.request.GET.get('pemanenan')
        if pemanenan_id:
            initial['pemanenan'] = pemanenan_id
        return initial


class PenjualanUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Penjualan
    form_class = PenjualanForm
    template_name = 'farm/penjualan_form.html'
    success_url = reverse_lazy('farm:penjualan_list')
    success_message = 'Data penjualan berhasil diperbarui!'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Edit Penjualan'
        ctx['cancel_url'] = reverse_lazy('farm:penjualan_list')
        return ctx


class PenjualanDeleteView(LoginRequiredMixin, DeleteView):
    model = Penjualan
    template_name = 'farm/confirm_delete.html'
    success_url = reverse_lazy('farm:penjualan_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Hapus Penjualan'
        ctx['cancel_url'] = reverse_lazy('farm:penjualan_list')
        return ctx


# ==================== BIAYA OPERASIONAL ====================

class BiayaOperasionalListView(LoginRequiredMixin, ListView):
    model = BiayaOperasional
    template_name = 'farm/biaya_list.html'
    context_object_name = 'object_list'
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset()
        kategori = self.request.GET.get('kategori', '')
        if kategori:
            qs = qs.filter(kategori=kategori)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['kategori_filter'] = self.request.GET.get('kategori', '')
        ctx['kategori_choices'] = BiayaOperasional.KATEGORI_CHOICES
        ctx['page_title'] = 'Data Biaya Operasional'
        ctx['create_url'] = 'farm:biaya_create'
        return ctx


class BiayaOperasionalCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = BiayaOperasional
    form_class = BiayaOperasionalForm
    template_name = 'farm/biaya_form.html'
    success_url = reverse_lazy('farm:biaya_list')
    success_message = 'Biaya operasional berhasil ditambahkan!'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Tambah Biaya Operasional'
        ctx['cancel_url'] = reverse_lazy('farm:biaya_list')
        return ctx


class BiayaOperasionalUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = BiayaOperasional
    form_class = BiayaOperasionalForm
    template_name = 'farm/biaya_form.html'
    success_url = reverse_lazy('farm:biaya_list')
    success_message = 'Biaya operasional berhasil diperbarui!'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Edit Biaya Operasional'
        ctx['cancel_url'] = reverse_lazy('farm:biaya_list')
        return ctx


class BiayaOperasionalDeleteView(LoginRequiredMixin, DeleteView):
    model = BiayaOperasional
    template_name = 'farm/confirm_delete.html'
    success_url = reverse_lazy('farm:biaya_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Hapus Biaya Operasional'
        ctx['cancel_url'] = reverse_lazy('farm:biaya_list')
        return ctx