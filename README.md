# latsol-py

Generator soal UTBK-SNBT **Pengetahuan Kuantitatif** berbasis LLM (Ollama),
tersedia sebagai layanan **FastAPI** dan **CLI**. Setiap request menghasilkan
**tepat 5 soal pilihan ganda** (4 opsi, 1 jawaban benar) beserta pembahasan.

Topik yang tersedia:

- `aljabar`
- `himpunan`
- `persamaan garis (fungsi linear dan kuadrat)`
- `trigonometri`
- `fungsi invers`
- `statistika data tunggal`
- `barisan dan deret`
- `peluang`

## Struktur proyek

```
.
├── pyproject.toml
├── uv.lock
├── README.md
├── LICENSE
├── .env.example
├── src/
│   └── latsol_py/
│       ├── __init__.py     # docstring paket
│       ├── __main__.py     # python -m latsol_py
│       ├── app.py          # aplikasi FastAPI
│       ├── cli.py          # antarmuka command line
│       ├── config.py       # konfigurasi via environment variable
│       ├── quiz.py         # logika generasi & validasi
│       ├── py.typed
│       └── data/
│           └── system_prompt.txt
└── tests/
    ├── conftest.py
    ├── test_api.py
    ├── test_config.py
    └── test_quiz.py
```

## Persyaratan

- [uv](https://docs.astral.sh/uv/) — mengelola Python 3.14 dan dependency.
- [Ollama](https://ollama.com/) berjalan di `http://localhost:11434`.

## Setup

1. **Instal uv** (lewati jika sudah ada):

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Instal & jalankan Ollama**, lalu tarik modelnya:

   ```bash
   ollama serve
   ollama pull llama3.1:8b
   ```

3. **Clone repo dan pasang dependency** (uv juga memasang Python 3.14 otomatis):

   ```bash
   git clone git@github.com:daffarahman/latsol-py.git
   cd latsol-py
   uv sync
   ```

4. **Konfigurasi** (opsional — semua punya default untuk Ollama lokal):

   ```bash
   cp .env.example .env
   ```

5. **Jalankan server**:

   ```bash
   uv run uvicorn latsol_py.app:app --reload
   # atau: uv run latsol-api
   ```

6. **Verifikasi**:

   ```bash
   curl http://127.0.0.1:8000/health
   curl "http://127.0.0.1:8000/quiz?topic=aljabar"
   ```

Dokumentasi interaktif: <http://127.0.0.1:8000/docs>.

## Menjalankan API

### Endpoint

| Method | Path | Deskripsi |
| ------ | ---- | --------- |
| `GET`  | `/` | Info service |
| `GET`  | `/health` | Health check (liveness) |
| `GET`  | `/ready` | Readiness — ping model, `503` bila model mati |
| `GET`  | `/topics` | Daftar topik yang didukung |
| `GET`  | `/quiz?topic=...` | Generate 5 soal via query string |
| `POST` | `/quiz` | Generate 5 soal via JSON body |

```bash
# GET
curl "http://127.0.0.1:8000/quiz?topic=peluang"

# POST
curl -X POST http://127.0.0.1:8000/quiz \
  -H "Content-Type: application/json" \
  -d '{"topic": "trigonometri"}'
```

Contoh respons (dipersingkat):

```json
{
  "topic": "aljabar",
  "questions": [
    {
      "content": "Sederhanakan \\(2x^2 + 5x - 3\\) ...",
      "options": [
        {"content": "\\((2x - 1)(x + 3)\\)", "correct": true},
        {"content": "\\((2x + 1)(x - 3)\\)", "correct": false},
        {"content": "\\((2x - 3)(x + 1)\\)", "correct": false},
        {"content": "\\((2x + 3)(x - 1)\\)", "correct": false}
      ],
      "answerExplanation": "Faktorkan ..."
    }
  ]
}
```

## CLI

```bash
uv run latsol "himpunan"
uv run latsol --help
uv run python -m latsol_py peluang --indent 0
```

## Konfigurasi

Semua lewat environment variable (opsional). Nilai `.env` di root proyek dimuat
secara otomatis saat aplikasi dijalankan; environment variable asli tetap
menang. Mulai dari contoh:

```bash
cp .env.example .env
```

Daftar variabel (lihat `src/latsol_py/config.py`):

| Variabel | Default | Keterangan |
| -------- | ------- | ---------- |
| `LATSOL_MODEL` | `llama3.1:8b` | Nama model |
| `LATSOL_BASE_URL` | `http://localhost:11434/v1` | Base URL OpenAI-compatible |
| `LATSOL_API_KEY` | `ollama` | API key upstream |
| `LATSOL_TEMPERATURE` | `0.4` | Temperatur sampling |
| `LATSOL_MAX_TOKENS` | `4096` | Batas token output |
| `LATSOL_REQUEST_TIMEOUT` | `30` | Timeout request ke model (detik) |
| `LATSOL_MAX_RETRIES` | `1` | Jumlah retry transport ke model |
| `LATSOL_MAX_ATTEMPTS` | `2` | Berapa kali model diminta ulang saat output gagal validasi |
| `LATSOL_MAX_CONCURRENCY` | `4` | Maksimal generasi bersamaan (lebih → HTTP 503) |
| `LATSOL_SERVICE_API_KEY` | _(kosong)_ | Jika diisi, `/quiz` wajib header `X-API-Key` |
| `LATSOL_DOCS_ENABLED` | `true` | Set `false` di produksi untuk menyembunyikan `/docs` |

## Keamanan

### Ringkasan model ancaman

| Vektor | Status |
| ------ | ------ |
| Prompt injection lewat `topic` | **Dicegah** — allowlist |
| Field liar di body request | **Diabaikan** — Pydantic `extra="ignore"` |
| Akses tanpa izin ke `/quiz` | **Dicegah** — jika `LATSOL_SERVICE_API_KEY` diisi |
| Ledakan konkurensi / biaya | **Dibatasi** — semaphore (per-proses) |
| Kebocoran detail internal via error | **Dicegah** — pesan generik |
| Output model salah / di luar topik | **Tidak divalidasi** — risiko kualitas |
| Rate limit per-IP | **Belum ada** — pasang di reverse proxy |

### Apa yang dilindungi

- **Topik adalah allowlist, bukan teks bebas.** `topic` divalidasi sebagai
  `Literal` berisi 8 topik tetap, dan `generate_quiz()` memeriksa ulang
  keanggotaannya. Satu-satunya teks pengguna yang masuk ke prompt adalah nama
  topik yang sudah pasti, sehingga **prompt injection lewat topik tidak mungkin**.
  Field ekstra pada body (mis. `system`, `messages`) diabaikan Pydantic.
- **Autentikasi opsional.** Setel `LATSOL_SERVICE_API_KEY` untuk mewajibkan header
  `X-API-Key` pada `/quiz`. Perbandingan memakai `secrets.compare_digest`
  (constant-time). `/health` dan `/topics` tetap publik.
- **Pembatas konkurensi.** `LATSOL_MAX_CONCURRENCY` membatasi jumlah generasi
  bersamaan; kelebihannya dibalas **HTTP 503** + `Retry-After: 5`.
- **Timeout & retry** ke model dibatasi (`LATSOL_REQUEST_TIMEOUT`,
  `LATSOL_MAX_RETRIES`) agar tidak memakai default library (600 detik, 2 retry).
- **Pesan error generik.** Kegagalan upstream/validasi hanya dicatat di log
  server; respons ke klien tidak memuat detail internal.
- **Dokumentasi** bisa dimatikan di produksi via `LATSOL_DOCS_ENABLED=false`
  (menonaktifkan `/docs`, `/redoc`, `/openapi.json`).

Contoh memanggil dengan API key:

```bash
curl "http://127.0.0.1:8000/quiz?topic=aljabar" -H "X-API-Key: $LATSOL_SERVICE_API_KEY"
```

### Batasan yang perlu diketahui

- **Model bisa melanggar skema.** JSON Schema memaksa opsi `correct` bertipe
  boolean, tetapi tidak bisa memastikan "tepat satu bernilai true". Bila model
  gagal, server mencoba ulang hingga `LATSOL_MAX_ATTEMPTS` kali dengan umpan
  balik perbaikan. Model kecil (mis. `llama3.1:8b`) lebih sering gagal; model
  yang lebih besar biasanya lebih patuh. Jika semua percobaan gagal, respons
  adalah **502** (bukan soal yang salah).
- **Retry menambah latensi.** Setiap percobaan adalah panggilan model penuh,
  jadi batas total waktu ≈ `LATSOL_MAX_ATTEMPTS` × durasi satu generasi.
- **Timeout bukan batas waktu total.** Ia hanya membatasi jeda antar-data
  (read timeout). Karena Ollama mengalirkan token perlahan, generasi bisa
  berjalan lebih lama dari `LATSOL_REQUEST_TIMEOUT` (terbukti ~57 detik dengan
  nilai 30). Batas keras perlu timeout di reverse proxy.
- **Semaphore bersifat per-proses.** Di balik beberapa worker `uvicorn` atau
  replika, tiap proses punya batasnya sendiri. Untuk batas global, gunakan
  reverse proxy / Redis.
- **Tidak ada rate limit per-IP.** Endpoint publik tanpa API key bisa disalahkan
  untuk menghabiskan sumber daya. Batasi di reverse proxy (nginx `limit_req`,
  Cloudflare, dsb.).
- **Output model tidak dimoderasi.** Sistem prompt meminta soal sesuai topik,
  tetapi tidak ada verifikasi otomatis bahwa jawaban benar atau relevan.
  Jangan pakai untuk penilaian tanpa verifikasi.
- **Keamanan sisi klien.** API mengembalikan JSON dengan benar, tetapi jika
  frontend merender `content`/`answerExplanation` sebagai HTML mentah, XSS
  mungkin terjadi. Render sebagai teks, dan bila memakai KaTeX gunakan
  `trust: false` (default).

### Daftar periksa produksi

- [ ] Setel `LATSOL_SERVICE_API_KEY` (jangan biarkan kosong).
- [ ] Setel `LATSOL_DOCS_ENABLED=false`.
- [ ] Jalankan di balik reverse proxy dengan TLS + rate limit per-IP.
- [ ] Gunakan `/ready` (bukan `/health`) sebagai readiness probe load balancer.
- [ ] Batasi `LATSOL_BASE_URL` ke endpoint yang tepercaya.
- [ ] Jangan commit `.env` (sudah di-`.gitignore`); simpan rahasia di secret store.
- [ ] Pantau log server (level WARNING/ERROR) untuk anomali.
- [ ] Sanitasi output di klien sebelum merender.

> Jika nanti menambahkan topik bebas (free text), prompt injection kembali
> terbuka: batasi panjangnya, buang karakter kontrol, dan jaga di dalam template
> ketat.

## Pengembangan

```bash
uv run pytest          # jalankan test
uv run ruff check .    # lint
uv run ruff format .   # format
uv build               # bangun sdist + wheel
```

## Lisensi

Dirilis di bawah [MIT License](LICENSE).
