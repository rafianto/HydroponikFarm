from django import template

register = template.Library()


@register.filter(name='rupiah')
def rupiah(value):
    """Format angka menjadi format Rupiah: Rp 1.500.000"""
    try:
        value = float(value)
        formatted = f"{value:,.0f}"
        # Ganti koma pemisah ribuan dengan titik (format Indonesia)
        formatted = formatted.replace(",", ".")
        return f"Rp {formatted}"
    except (ValueError, TypeError):
        return value


@register.filter(name='status_badge')
def status_badge(value):
    """Mengembalikan kelas CSS badge berdasarkan status."""
    badges = {
        'aktif': 'bg-emerald-100 text-emerald-800',
        'masa_tumbuh': 'bg-blue-100 text-blue-800',
        'siap_panen': 'bg-amber-100 text-amber-800',
        'selesai': 'bg-gray-100 text-gray-800',
        'gagal': 'bg-red-100 text-red-800',
        'lunas': 'bg-emerald-100 text-emerald-800',
        'belum_bayar': 'bg-red-100 text-red-800',
        'cicilan': 'bg-amber-100 text-amber-800',
        'premium': 'bg-emerald-100 text-emerald-800',
        'baik': 'bg-blue-100 text-blue-800',
        'cukup': 'bg-amber-100 text-amber-800',
    }
    return badges.get(value, 'bg-gray-100 text-gray-800')