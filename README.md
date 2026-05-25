# SafeBite AI

## Aplikasi Deteksi Risiko Komposisi Makanan dan Alergen Berbasis OCR + NLP

SafeBite AI adalah aplikasi web berbasis Artificial Intelligence yang membantu pengguna memahami label komposisi makanan/minuman kemasan. Aplikasi ini membaca teks dari foto label makanan menggunakan OCR, kemudian menganalisis komposisi untuk mendeteksi alergen, zat aditif/sintesis, serta bahan yang berisiko jika dikonsumsi berlebihan.

Project ini dikembangkan sebagai tugas besar Rekayasa Perangkat Lunak dengan pendekatan Agile-Scrum, sesuai kebutuhan pengembangan aplikasi AI yang memiliki novelty, implementasi AI, evaluasi model, dokumentasi proyek, dan produk perangkat lunak yang dapat didemokan.

---

## Latar Belakang

Banyak pengguna mengalami kesulitan memahami label komposisi makanan karena istilah bahan sering ditulis dalam bentuk teknis, bahasa campuran Indonesia-Inggris, atau menggunakan nama turunan bahan tertentu.

Contoh:

- `whey powder`, `casein`, dan `lactose` merupakan turunan dari susu.
- `soy lecithin` berkaitan dengan kedelai.
- `wheat flour` atau `tepung terigu` mengandung gluten.
- `tartrazine` merupakan pewarna sintetis.
- `sodium benzoate` merupakan bahan pengawet.

SafeBite AI hadir untuk membantu pengguna membaca dan memahami label makanan secara lebih mudah melalui analisis otomatis.

---

## Tujuan Project

1. Membuat aplikasi web yang dapat membaca label komposisi makanan dari gambar.
2. Mengimplementasikan OCR untuk mengekstrak teks dari foto label makanan.
3. Mendeteksi alergen seperti susu, telur, gluten, kedelai, kacang, seafood, dan wijen.
4. Mendeteksi zat aditif/sintesis seperti pewarna, pengawet, pemanis buatan, MSG, dan pengemulsi.
5. Mendeteksi bahan yang berisiko jika dikonsumsi berlebihan seperti gula, natrium, lemak trans, lemak jenuh, dan kafein.
6. Memberikan rekomendasi risiko berdasarkan profil alergi pengguna.
7. Mengembangkan aplikasi menggunakan metode Agile-Scrum.

---

## Novelty / Kebaharuan

SafeBite AI berbeda dari aplikasi OCR biasa karena tidak hanya membaca teks pada label makanan, tetapi juga menganalisis komposisi menggunakan NLP sederhana untuk mendeteksi:

- Alergen makanan
- Zat aditif/sintesis
- Risiko konsumsi berlebihan
- Risiko personal berdasarkan profil alergi pengguna

Aplikasi ini menggabungkan OCR, text processing, rule-based NLP, dan sistem rekomendasi risiko dalam satu aplikasi web.

---

## Fitur Utama

### MVP

- Upload foto label makanan
- OCR untuk membaca teks dari gambar
- Menampilkan teks hasil OCR
- Deteksi alergen dasar
- Deteksi zat aditif/sintesis
- Deteksi risiko konsumsi berlebihan
- Menampilkan status risiko

### Fitur Lanjutan

- Profil alergi pengguna
- Highlight bahan berisiko
- Riwayat hasil scan
- Dashboard statistik
- Export hasil analisis
- Evaluasi akurasi OCR dan deteksi bahan

---

## Kategori Deteksi

### 1. Alergen

SafeBite AI dapat mendeteksi beberapa alergen umum, seperti:

- Susu
- Telur
- Gluten / gandum
- Kedelai
- Kacang tanah
- Tree nuts
- Seafood
- Wijen
- Sulfit

Contoh kata kunci:

| Alergen | Contoh Keyword |
|---|---|
| Susu | susu, milk, whey, casein, lactose, skim milk |
| Telur | telur, egg, albumin, ovalbumin |
| Gluten | gandum, wheat, tepung terigu, gluten, barley |
| Kedelai | kedelai, soy, soybean, soy lecithin |
| Kacang | peanut, kacang tanah, almond, cashew |
| Seafood | fish, ikan, shrimp, udang, crab, kepiting |
| Wijen | sesame, wijen, sesame oil |
| Sulfit | sulfite, sulphite, sulfur dioxide |

---

### 2. Zat Aditif / Sintesis

Aplikasi juga dapat mendeteksi zat aditif atau bahan sintesis, seperti:

| Kategori | Contoh Keyword |
|---|---|
| Pewarna sintetis | tartrazine, sunset yellow, allura red, brilliant blue |
| Pengawet | sodium benzoate, natrium benzoat, potassium sorbate |
| Pemanis buatan | aspartame, sucralose, sukralosa, sakarin |
| Penguat rasa | MSG, monosodium glutamate, vetsin |
| Pengemulsi | lecithin, lesitin, soy lecithin |
| Antioksidan sintetis | BHA, BHT, TBHQ |
| Pengental | carrageenan, xanthan gum, guar gum, CMC |

---

### 3. Risiko Konsumsi Berlebihan

| Kategori Risiko | Contoh Keyword |
|---|---|
| Gula tinggi | gula, sugar, sukrosa, glukosa, fruktosa |
| Natrium tinggi | garam, sodium, natrium, MSG |
| Lemak jenuh | saturated fat, palm oil, minyak sawit, butter |
| Lemak trans | partially hydrogenated oil, shortening |
| Kafein | caffeine, kafein, coffee extract, guarana |

---

## Tech Stack

| Komponen | Teknologi |
|---|---|
| Bahasa Pemrograman | Python |
| Web Framework | Streamlit |
| OCR | EasyOCR |
| Image Processing | OpenCV |
| Text Processing / NLP | Regex, Keyword Matching, Scikit-learn |
| Database | SQLite / CSV |
| Visualisasi | Streamlit Chart / Matplotlib |
| Version Control | GitHub |
| Project Management | Trello / GitHub Projects |

---

## Arsitektur Sistem

```text
User
 │
 │ Upload foto label makanan
 ▼
Streamlit Web App
 │
 │ Preprocessing gambar
 ▼
OpenCV
 │
 │ Gambar diperjelas
 ▼
EasyOCR
 │
 │ Teks komposisi hasil OCR
 ▼
Text Analyzer / NLP
 │
 ├── Deteksi alergen
 ├── Deteksi zat aditif/sintesis
 ├── Deteksi risiko konsumsi berlebihan
 │
 ▼
Risk Recommendation Engine
 │
 │ Cocokkan dengan profil alergi pengguna
 ▼
SQLite / CSV Database
 │
 ▼
Hasil Analisis + Riwayat Scan
