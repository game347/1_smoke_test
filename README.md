# Soccer EKG — Smoke Test Edition

This repo contains the full soccer commentary pipeline + a smoke test to verify 
it runs end-to-end on ONE match (Burnley). ~30-45 minutes on H100 or A100 80GB GPU.

## Repository structure
This repo includes the COMPLETE pipeline code:
- `src/` — pipeline modules (video processor, KG builder, commentator, etc.)
- `experiments/` — experiment scaffold (level1_baseline.py, level2, level3)
- `main.py` — pipeline orchestrator
- `ekg_tbox.ttl` — RDF/OWL ontology
- `run_smoke.py` — smoke test runner (Python)

You ONLY need to fetch:
- `data/` — match videos + ground truth (from DGX, ~2.5 GB)
- `models/` — Qwen3-VL-30B + Qwen2.5-7B-AWQ (from DGX, ~65 GB)

## Prerequisites
- Linux server with conda installed
- 1x GPU with **>=80 GB memory** (H100 80GB or A100 80GB required)
  - Qwen3-VL-30B is ~60 GB in bf16, needs 80 GB to fit alongside vLLM
- ~80 GB free disk space
- SSH access to `admin@spark-296d` (DGX)
- ffmpeg installed (apt or conda)

## Setup (one-time, ~30 min)

### 1. Clone this repo
```bash
cd ~
git clone https://github.com/game347/1_smoke_test
cd 1_smoke_test
```

### 2. Get data from DGX (~2.5 GB)
```bash
mkdir -p data/sn_long
rsync -avhP \
    "admin@spark-296d:~/work/s2616011/real-time_KG-with-vlm/data/sn_long/2015-04-11 - Burnley - Arsenal/" \
    "data/sn_long/2015-04-11 - Burnley - Arsenal/"
```

### 3. Get models from DGX (~65 GB)
```bash
mkdir -p ~/models
rsync -avhP admin@spark-296d:~/work/s2616011/models/Qwen2.5-7B-Instruct-AWQ/ ~/models/Qwen2.5-7B-Instruct-AWQ/
rsync -avhP admin@spark-296d:~/work/s2616011/models/Qwen3-VL-30B-A3B-Instruct/ ~/models/Qwen3-VL-30B-A3B-Instruct/
```

### 4. System dependencies (if ffmpeg not already installed)
```bash
sudo apt update && sudo apt install -y ffmpeg
# OR without sudo, via conda (after step 5):
# conda install -c conda-forge ffmpeg
```

### 5. Set up conda env
```bash
conda create -n rag python=3.11 -y
conda activate rag
pip install vllm transformers torch rdflib requests opencv-python-headless \
    nltk rouge-score pycocoevalcap bert-score thefuzz Pillow \
    numpy pandas beautifulsoup4 lxml accelerate
```

## Run the smoke test
```bash
python run_smoke.py
```

Takes ~45 min. Watch progress in another terminal:

```bash
tail -f smoke_test.log
```

## When done — send back
- `experiments/results.json` (the metrics)
- `smoke_test.log` (full pipeline output)
- `vllm.log` (vLLM startup log)

## If something breaks
Send me the log files. Don't try to fix.

## What this test does
1. Starts vLLM serving Qwen2.5-7B-AWQ on port 8001 (background subprocess)
2. Runs main.py on the Burnley match — VLM detects events from frames, builds RDF/OWL KG, commentator generates commentary
3. Extracts AI commentary into JSON
4. Evaluates against SN-Short ground truth (BLEU, METEOR, ROUGE, CIDEr, BERTScore, CRR)
5. Saves results to `experiments/results.json`

## Expected runtime
| Stage | Time |
|-------|------|
| vLLM startup | ~2 min |
| Pipeline on Burnley | ~30-40 min |
| Evaluation | ~1 min |
| **Total** | **~35-45 min** |
