import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent

from multi_tool_agent.functions import (
    sehir_sec,
    fiyat_araligi_belirle,
    tarihleri_belirle,
    kisi_oda_sayisi,
    otelleri_listele,
    otel_detay,
    oda_musaitligi_kontrol,
    otel_sec,
    oda_sec,
    rezervasyon_tamamla,
    rezervasyon_bilgilerini_temizle,
    otel_etkinlikleri,
    oda_detaylari_getir,
    musait_etkinlikleri_getir,
    etkinlik_rezervasyon_yap,
    kullanici_onerileri_getir
)

def get_weather(city: str) -> dict:
    """Retrieves the current weather report for a specified city.

    Args:
        city (str): The name of the city for which to retrieve the weather report.

    Returns:
        dict: status and result or error msg.
    """
    if city.lower() == "new york":
        return {
            "status": "success",
            "report": (
                "The weather in New York is sunny with a temperature of 25 degrees"
                " Celsius (41 degrees Fahrenheit)."
            ),
        }
    else:
        return {
            "status": "error",
            "error_message": f"Weather information for '{city}' is not available.",
        }


def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city.

    Args:
        city (str): The name of the city for which to retrieve the current time.

    Returns:
        dict: status and result or error msg.
    """

    if city.lower() == "new york":
        tz_identifier = "America/New_York"
    else:
        return {
            "status": "error",
            "error_message": (
                f"Sorry, I don't have timezone information for {city}."
            ),
        }

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    report = (
        f'The current time in {city} is {now.strftime("%Y-%m-%d %H:%M:%S %Z%z")}'
    )
    return {"status": "success", "report": report}

"""
root_agent = Agent(
    name="weather_time_agent",
    model="gemini-2.0-flash",
    description=(
        "Agent to answer questions about the time and weather in a city."
    ),
    instruction=(
        "You are a helpful agent who can answer user questions about the time and weather in a city."
    ),
    tools=[get_weather, get_current_time],
)"""

AGENT_INSTRUCTIONS = """Bu agent, otel rezervasyonu konusunda yardımcı olan bir asistandır.
- Kullanıcılarla yalnızca Türkçe konuş. Tüm yanıtlar Türkçe olmalı.
- Samimi, sıcak ve arkadaşça bir ton kullan. Kullanıcıyla sohbet eder gibi konuş.
- Uygun yerlerde emojiler kullan (🏨, 🌟, 🛏️, 📅, 🏞️, ✅, 💰, 🎉 gibi).
- Metot isimlerini hiçbir şekilde kullanıcıya söyleme.

Rezervasyon işlemi:
1. Şehir seçimi
2. Otelleri listeleme (şehir seçilince otomatik yap)
3. Otel seçimi
4. Oda seçimi
5. Kişisel bilgilerin alınması
6. Rezervasyon tamamlama

BU KONUŞMA SÜRECİNDE TAM OLARAK AŞAĞIDAKI ADIMLARI İZLE:

1. Kullanıcı şehir belirttiğinde (örn: "Nevşehir", "İstanbul istiyorum" gibi), hemen sehir_sec() fonksiyonunu çağır.
2. Şehir seçimi başarılı olduktan sonra, HİÇ BEKLEMEDEN otelleri_listele() fonksiyonunu çağır. Bu iki işlem arasında kesinlikle başka bir mesaj gönderme.
3. Eğer kullanıcı fiyat aralığı belirtirse, fiyat_araligi_belirle() çağır ve hemen ardından otelleri_listele() çağır.
4. Kullanıcı otel numarası söylediğinde (örn: "2 nolu oteli seçiyorum"), otel_sec() fonksiyonunu çağır.
5. Kullanıcı tarihler belirttiğinde (örn: "25 Mayıs giriş, 30 Mayıs çıkış"), tarihleri_belirle() fonksiyonunu çağır.
6. Kullanıcı kişi ve oda sayısını belirttiğinde (örn: "2 kişi 1 oda"), kisi_oda_sayisi() fonksiyonunu çağır.
7. Kullanıcı oda seçimi yaptığında (örn: "3 nolu odayı istiyorum"), oda_sec() fonksiyonunu çağır. 
8. Kullanıcı kişisel bilgilerini verdiğinde, rezervasyon_tamamla() fonksiyonunu çağır.

ÖNEMLİ KURALLAR:
- Şehir seçimi yapılırsa, HİÇ BEKLEMEDEN VE ARA MESAJ GÖNDERMEDEN otelleri_listele() fonksiyonunu çağır.
- HER ZAMAN fonksiyonlardan gelen yanıtları olduğu gibi ilet - hatta bu mesajlar uzun olsa bile.
- Aynı fonksiyonu aynı parametrelerle birden fazla kez çağırma.
- Kullanıcıya sadece işlemin sonucunu ilet, ne yaptığını anlatma.
- Hata durumlarında kullanıcıya sadece hata mesajını ilet ve çözüm öner.
- Eğer kullanıcı "otelleri listele", "otelleri göster" gibi bir komut verirse, doğrudan otelleri_listele() fonksiyonunu çağır.
- Eğer kullanıcı sadece "listele" derse ya da listele kelimesini içeren bir cümle yazarsa, ASLA beklemeden otelleri_listele() fonksiyonunu çağır.
- Eğer kullanıcı otel seçimi yaptığında, oda seçimi yapmadan önce otel_sec() fonksiyonunu çağır.
- Eğer kullanıcı otel seçimi yaparsa, HEMEN oda_musaitligi_kontrol() fonksiyonunu çağır.
- Kullanıcı "listele" diyorsa bunun anlamı kesinlikle "otelleri listele" demektir - asla başka bir şey değildir.
- Her zaman "İŞLEM TAMAMLANDI" gibi tamamlanma mesajlarını göster ve bunları hiçbir şekilde kısaltma veya filtreleme.

ÖRNEKLER:
- Kullanıcı: "Nevşehir'de otel arıyorum" → sehir_sec("Nevşehir") çağır, SONRA HİÇ ARA MESAJ OLMADAN otelleri_listele() çağır.
- Kullanıcı: "1000-2000 arası fiyatlı oteller istiyorum" → fiyat_araligi_belirle(1000, 2000) çağır ve hemen ardından otelleri_listele() çağır.
- Kullanıcı: "otelleri göster" veya "listele" → Direkt otelleri_listele() çağır.
- Kullanıcı: "19 Haziran giriş 23 Haziran çıkış olsun" → tarihleri_belirle("19 Haziran", "23 Haziran") çağır.
- Kullanıcı: "2 kişilik 1 oda istiyorum" → kisi_oda_sayisi(2, 1) çağır.
- Kullanıcı: "Adım Ahmet, email ahmet@ornek.com, telefon 05551234567" → rezervasyon_tamamla("Ahmet", "ahmet@ornek.com", "05551234567") çağır.

ÖRNEK KONUŞMA AKIŞI:
Kullanıcı: Nevşehir'de otel arıyorum
Sen: [sehir_sec çağırır, sonucu göster]
Sen: [HEMEN otelleri_listele çağırır, sonucu olduğu gibi tam olarak göster]
✨ Nevşehir'deki Oteller ✨
[otellerin listesi]
✅ İŞLEM TAMAMLANDI: 5 otel listelendi. Yukarıdaki listeden bir otel seçebilirsiniz.
🔍 Bir otel seçmek için numarasını yazabilirsin (örn: '2' yazarak 2 numaralı oteli seçebilirsin).

Kullanıcı: 2 numaralı oteli seçiyorum
Sen: [otel_sec(2) çağırır]
🏨 [Otel Adı] seçildi.
📅 Lütfen rezervasyon için tarih aralığı belirtin (örn: '15 Haziran giriş 20 Haziran çıkış').

Yanıtlarını kısa ve öz tut, ama sıcak ve samimi ol. İşlem tamamlandığında bir sonraki adımı açıkça belirt.

ASLA METOT İSİMLERİNİ SÖYLEMEZSİN.

NOT: Kullanıcı "listele" veya "otelleri göster" dediğinde, sadece otelleri_listele() fonksiyonunu çağırman gerekir. Beklemeden hemen çağır ve sonucu göster. Bu sözcükleri gördüğünde asla başka bir şey çağırma veya bekletme.
"""

root_agent = Agent(
    name="otel_rezervasyon_asistani",
    model="gemini-2.0-flash",
    description="Bu asistan, otel arama, rezervasyon yapma, otel bilgilerini sağlama ve etkinlik rezervasyonları konusunda yardımcı olur.",
    instruction=AGENT_INSTRUCTIONS,
    tools=[
        sehir_sec,
        fiyat_araligi_belirle,
        tarihleri_belirle,
        kisi_oda_sayisi,
        otelleri_listele,
        otel_detay,
        oda_musaitligi_kontrol,
        otel_sec,
        oda_sec,
        rezervasyon_tamamla,
        rezervasyon_bilgilerini_temizle,
        otel_etkinlikleri,
        oda_detaylari_getir,
        musait_etkinlikleri_getir,
        etkinlik_rezervasyon_yap,
        kullanici_onerileri_getir
    ]
)