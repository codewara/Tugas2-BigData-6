from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pymongo
from transformers import pipeline

# Summarizer dari Transformers
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# Fungsi ringkas berita
def ringkas_berita(teks):
    try:
        word_count = len(teks.split())
        max_len = min(150, word_count // 2 + 20)
        min_len = min(80, word_count // 4)
        summary = summarizer(teks, max_length=max_len, min_length=min_len, do_sample=False)
        return summary[0]['summary_text']
    except Exception as e:
        print(f"ERROR saat meringkas berita: {e}")
        return teks


# Fungsi lainnya (click_button_when_ready, go_to_next_page, load_more_articles, get_all_articles) tetap sama...
def click_button_when_ready(xpath):
    try:
        # Tunggu hingga tombol tersedia (meningkatkan waktu tunggu jika perlu)
        button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, xpath)))
        driver.execute_script("arguments[0].scrollIntoView();", button)  # Pastikan tombol terlihat
        button.click()  # Klik tombol
        time.sleep(5)
        return True
    except Exception as e:
        print(f"ERROR: Tidak dapat mengklik tombol dengan XPath '{xpath}': {e}")
        return False

# Fungsi untuk berpindah ke halaman berikutnya
def go_to_next_page():
    try:
        next_button = driver.find_element(By.XPATH, "//a[@class='navred']")
        if next_button.is_enabled():
            next_button.click()
            time.sleep(5)
            return True
        else:
            print("Tidak ada halaman berikutnya.")
            return False
    except Exception as e:
        print(f"ERROR berpindah halaman: {e}")
        return False

# Fungsi untuk mengklik "More" dan memuat lebih banyak artikel
def load_more_articles():
    try:
        more_button = driver.find_element(By.XPATH, "//a[class='navred']//b[contains(text(), 'more')]")
        if more_button.is_enabled():
            more_button.click()
            time.sleep(5)  # Tunggu sampai artikel lebih banyak dimuat
            return True
        else:
            print("Tidak ada tombol 'More' lagi.")
            return False
    except Exception as e:
        print(f"ERROR mengklik 'More': {e}")
        return False

# Fungsi untuk mengambil daftar berita dari halaman
def get_all_articles():
    berita_elements = driver.find_elements(By.XPATH, "//div[@class='box']//ul[@class='news']/li/a")  # Ambil semua berita
    tanggal_elements = driver.find_elements(By.XPATH, "//div[@class='box']//ul[@class='news']/li/b")  # Ambil semua tanggal

    berita_links = []
    for i in range(len(berita_elements)):
        try:
            berita_url = berita_elements[i].get_attribute("href")
            judul = berita_elements[i].text.strip()
            tanggal = tanggal_elements[i].text.strip() if i < len(tanggal_elements) else "Tidak Diketahui"

            # Tunggu sebentar agar tidak terdeteksi sebagai bot
            time.sleep(2)

            berita_links.append({
                "judul": judul,
                "url": berita_url,
                "tanggal": tanggal
            })
        except Exception as e:
            print(f"ERROR mengambil berita ke-{i}: {e}")

    return berita_links

# Koneksi MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["local"]
berita_collection = db["BERITA"]

# Konfigurasi WebDriver
options = webdriver.EdgeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Edge(options=options)
page = 1

start_time = time.time()
MAX_DURATION = 3600

for page in range(1, 51):
    if time.time() - start_time > MAX_DURATION:
        print("⏰ Waktu maksimum 1 jam telah tercapai. Menghentikan program.")
        break
    url = f"http://www.iqplus.info/news/stock_news/go-to-page,{page}.html"
    driver.get(url)
    time.sleep(3)

    links = get_all_articles()
    print(f"Ditemukan {len(links)} berita di halaman {page} Stock News.")

    for berita in links:
        if time.time() - start_time > MAX_DURATION:
            print("⏰ Waktu maksimum 1 jam telah tercapai. Menghentikan program.")
            break

        driver.get(berita['url'])
        time.sleep(2)

        try:
            isi_berita = driver.find_element(By.XPATH, "//div[@id='zoomthis']").text.strip()

            # RINGKAS ISI BERITA DI SINI 🔥
            # ringkasan = ringkas_berita(isi_berita)

            # Simpan ke MongoDB
            berita["isi"] = isi_berita  # full content
            berita["ringkasan"] = ringkas_berita(isi_berita)  # summary
            berita_collection.insert_one(berita)

            print(f"✅ Berita '{berita['judul']}' berhasil disimpan & diringkas!")

        except Exception as e:
            print(f"❌ ERROR mengambil isi berita dari {berita['url']}: {e}")

        time.sleep(2)

driver.quit()
print("✅ Semua berita selesai diproses!")
