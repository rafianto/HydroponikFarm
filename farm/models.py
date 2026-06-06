from django.db import models
from django.urls import reverse
from django.utils import timezone


class Bibit(models.Model):
    JENIS_CHOICES = [
        ('sayuran_daun', 'Sayuran Daun'),
        ('sayuran_buah', 'Sayuran Buah'),
        ('herbal', 'Herbal'),
        ('buah', 'Buah'),
        ('bunga', 'Bunga'),
    ]

    nama = models.CharField('Nama Bibit', max_length=100)
    jenis = models.CharField('Jenis Tanaman', max_length=20, choices=JENIS_CHOICES)
    varietas = models.CharField('Varietas', max_length=100, blank=True)
    supplier = models.CharField('Supplier', max_length=150, blank=True)
    harga_beli = models.DecimalField('Harga Beli (Rp)', max_digits=12, decimal_places=2, default=0)
    stok = models.PositiveIntegerField('Stok (unit)', default=0)
    tanggal_masuk = models.DateField('Tanggal Masuk', default=timezone.now)
    keterangan = models.TextField('Keterangan', blank=True)

    class Meta:
        verbose_name = 'Bibit'
        verbose_name_plural = 'Data Bibit'
        ordering = ['-tanggal_masuk', 'nama']

    def __str__(self):
        return f"{self.nama} ({self.get_jenis_display()})"

    def get_absolute_url(self):
        return reverse('farm:bibit_list')


class Penanaman(models.Model):
    SISTEM_CHOICES = [
        ('nft', 'NFT (Nutrient Film Technique)'),
        ('dft', 'DFT (Deep Flow Technique)'),
        ('wick', 'Wick System'),
        ('drip', 'Drip System'),
        ('ebb_flow', 'Ebb & Flow'),
        ('aeroponik', 'Aeroponik'),
    ]

    STATUS_CHOICES = [
        ('aktif', 'Aktif'),
        ('masa_tumbuh', 'Masa Tumbuh'),
        ('siap_panen', 'Siap Panen'),
        ('selesai', 'Selesai'),
        ('gagal', 'Gagal'),
    ]

    bibit = models.ForeignKey(Bibit, on_delete=models.CASCADE, related_name='penanaman', verbose_name='Bibit')
    tanggal_tanam = models.DateField('Tanggal Tanam', default=timezone.now)
    jumlah = models.PositiveIntegerField('Jumlah Tanam', default=1)
    lokasi = models.CharField('Lokasi / Rak', max_length=100)
    sistem_hidroponik = models.CharField('Sistem Hidroponik', max_length=20, choices=SISTEM_CHOICES)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='aktif')
    estimasi_panen = models.DateField('Estimasi Panen', null=True, blank=True)
    catatan = models.TextField('Catatan', blank=True)

    class Meta:
        verbose_name = 'Penanaman'
        verbose_name_plural = 'Data Penanaman'
        ordering = ['-tanggal_tanam']

    def __str__(self):
        return f"{self.bibit.nama} - {self.lokasi} ({self.tanggal_tanam.strftime('%d/%m/%Y')})"

    @property
    def hari_sejak_tanam(self):
        return (timezone.now().date() - self.tanggal_tanam).days

    @property
    def estimasi_hari_panen(self):
        if self.estimasi_panen:
            delta = (self.estimasi_panen - timezone.now().date()).days
            return delta
        return None

    def get_absolute_url(self):
        return reverse('farm:penanaman_list')


class Perawatan(models.Model):
    JENIS_CHOICES = [
        ('pemupukan', 'Pemupukan'),
        ('pengaturan_ph', 'Pengaturan pH'),
        ('penggantian_air', 'Penggantian Air'),
        ('pengendalian_hama', 'Pengendalian Hama'),
        ('pemangkasan', 'Pemangkasan'),
        ('pembersihan', 'Pembersihan Sistem'),
        ('lainnya', 'Lainnya'),
    ]

    penanaman = models.ForeignKey(Penanaman, on_delete=models.CASCADE, related_name='perawatan', verbose_name='Penanaman')
    tanggal = models.DateField('Tanggal Perawatan', default=timezone.now)
    jenis_perawatan = models.CharField('Jenis Perawatan', max_length=20, choices=JENIS_CHOICES)
    nutrisi_digunakan = models.CharField('Nutrisi Digunakan', max_length=200, blank=True)
    ph_air = models.FloatField('pH Air', null=True, blank=True)
    ec = models.FloatField('EC (mS/cm)', null=True, blank=True)
    volume_nutrisi_ml = models.FloatField('Volume Nutrisi (ml)', null=True, blank=True)
    biaya = models.DecimalField('Biaya (Rp)', max_digits=12, decimal_places=2, default=0)
    catatan = models.TextField('Catatan', blank=True)

    class Meta:
        verbose_name = 'Perawatan'
        verbose_name_plural = 'Data Perawatan'
        ordering = ['-tanggal']

    def __str__(self):
        return f"{self.penanaman.bibit.nama} - {self.get_jenis_perawatan_display()} ({self.tanggal.strftime('%d/%m/%Y')})"

    def get_absolute_url(self):
        return reverse('farm:perawatan_list')


class Pemanenan(models.Model):
    KUALITAS_CHOICES = [
        ('premium', 'Premium'),
        ('baik', 'Baik'),
        ('cukup', 'Cukup'),
    ]

    SATUAN_CHOICES = [
        ('kg', 'Kilogram'),
        ('gram', 'Gram'),
        ('ikat', 'Ikat'),
        ('buah', 'Buah'),
        ('liter', 'Liter'),
        ('lusin', 'Lusin'),
    ]

    penanaman = models.ForeignKey(Penanaman, on_delete=models.CASCADE, related_name='pemanenan', verbose_name='Penanaman')
    tanggal_panen = models.DateField('Tanggal Panen', default=timezone.now)
    jumlah_panen = models.DecimalField('Jumlah Panen', max_digits=12, decimal_places=2)
    satuan = models.CharField('Satuan', max_length=10, choices=SATUAN_CHOICES, default='kg')
    kualitas = models.CharField('Kualitas', max_length=10, choices=KUALITAS_CHOICES, default='baik')
    catatan = models.TextField('Catatan', blank=True)

    class Meta:
        verbose_name = 'Pemanenan'
        verbose_name_plural = 'Data Pemanenan'
        ordering = ['-tanggal_panen']

    def __str__(self):
        return f"{self.penanaman.bibit.nama} - {self.jumlah_panen} {self.get_satuan_display()} ({self.tanggal_panen.strftime('%d/%m/%Y')})"

    def get_absolute_url(self):
        return reverse('farm:pemanenan_list')


class Penjualan(models.Model):
    STATUS_CHOICES = [
        ('lunas', 'Lunas'),
        ('belum_bayar', 'Belum Bayar'),
        ('cicilan', 'Cicilan'),
    ]

    pemanenan = models.ForeignKey(Pemanenan, on_delete=models.CASCADE, related_name='penjualan', verbose_name='Pemanenan')
    tanggal_jual = models.DateField('Tanggal Jual', default=timezone.now)
    pembeli = models.CharField('Nama Pembeli', max_length=200)
    jumlah_jual = models.DecimalField('Jumlah Jual', max_digits=12, decimal_places=2)
    harga_satuan = models.DecimalField('Harga Satuan (Rp)', max_digits=12, decimal_places=2)
    status_pembayaran = models.CharField('Status Pembayaran', max_length=15, choices=STATUS_CHOICES, default='lunas')
    catatan = models.TextField('Catatan', blank=True)

    class Meta:
        verbose_name = 'Penjualan'
        verbose_name_plural = 'Data Penjualan'
        ordering = ['-tanggal_jual']

    @property
    def total(self):
        return self.jumlah_jual * self.harga_satuan

    def __str__(self):
        return f"{self.pembeli} - {self.pemanenan.penanaman.bibit.nama} ({self.tanggal_jual.strftime('%d/%m/%Y')})"

    def get_absolute_url(self):
        return reverse('farm:penjualan_list')


class BiayaOperasional(models.Model):
    KATEGORI_CHOICES = [
        ('listrik', 'Listrik'),
        ('air', 'Air'),
        ('nutrisi', 'Nutrisi'),
        ('media_tanam', 'Media Tanam'),
        ('peralatan', 'Peralatan'),
        ('tenaga_kerja', 'Tenaga Kerja'),
        ('transportasi', 'Transportasi'),
        ('pemeliharaan', 'Pemeliharaan'),
        ('lainnya', 'Lainnya'),
    ]

    tanggal = models.DateField('Tanggal', default=timezone.now)
    kategori = models.CharField('Kategori', max_length=20, choices=KATEGORI_CHOICES)
    deskripsi = models.CharField('Deskripsi', max_length=200)
    jumlah = models.DecimalField('Jumlah (Rp)', max_digits=12, decimal_places=2)
    catatan = models.TextField('Catatan', blank=True)

    class Meta:
        verbose_name = 'Biaya Operasional'
        verbose_name_plural = 'Data Biaya Operasional'
        ordering = ['-tanggal']

    def __str__(self):
        return f"{self.get_kategori_display()} - {self.deskripsi} ({self.tanggal.strftime('%d/%m/%Y')})"

    def get_absolute_url(self):
        return reverse('farm:biaya_list')