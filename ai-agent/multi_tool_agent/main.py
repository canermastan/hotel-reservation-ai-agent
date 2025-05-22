from functions import (sehir_sec, otelleri_listele, fiyat_filtrele, 
                      oda_sec, tarih_sec, rezervasyon_olustur, rezervasyon_kaldir)

@tool
def iptal_et(rezervasyon_id: str) -> str:
    """Belirtilen rezervasyon ID'si ile rezervasyonu iptal et.
    
    Args:
        rezervasyon_id: İptal edilecek rezervasyonun ID numarası.
    
    Returns:
        Rezervasyon iptal işlemi sonucunu içeren mesaj.
    """
    result = rezervasyon_kaldir(rezervasyon_id)
    if result["status"] == "success":
        return result["report"]
    else:
        return result["error_message"] 