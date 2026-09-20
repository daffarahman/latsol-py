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
├── src/
│   └── latsol_py/
│       ├── __init__.py     # API publik paket
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
    └── test_quiz.py
```

## Persiapan

Pastikan Ollama berjalan (default `http://localhost:11434`) dengan model
`llama3.1:8b`.

```bash
uv sync            # termasuk dependency dev
```

## Menjalankan API

```bash
uv run uvicorn latsol_py.app:app --reload
# atau melalui script:
uv run latsol-api
```

Dokumentasi interaktif: <http://127.0.0.1:8000/docs>.

### Endpoint

| Method | Path | Deskripsi |
| ------ | ---- | --------- |
| `GET`  | `/` | Info service |
| `GET`  | `/health` | Health check |
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
| `LATSOL_API_KEY` | `ollama` | API key |
| `LATSOL_TEMPERATURE` | `0.4` | Temperatur sampling |
| `LATSOL_MAX_TOKENS` | `4096` | Batas token output |

## Pengembangan

```bash
uv run pytest          # jalankan test
uv run ruff check .    # lint
uv run ruff format .   # format
uv build               # bangun sdist + wheel
```

## Lisensi

Dirilis di bawah [MIT License](LICENSE).
