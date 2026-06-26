#!/usr/bin/env python3
"""
Soccer EKG Pipeline — Smoke Test Runner

Starts vLLM, waits for it to be ready, then runs the smoke test on Burnley.
Logs everything to smoke_test.log and vllm.log.

Usage:
    python run_smoke.py
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.error

HOME           = Path.home()
LOG_FILE       = Path("smoke_test.log")
VLLM_LOG       = Path("vllm.log")
VLLM_URL       = "http://localhost:8001/v1/models"
VLLM_PORT      = 8001
MODEL_VLLM     = HOME / "models" / "Qwen2.5-7B-Instruct-AWQ"
MODEL_VLM      = HOME / "models" / "Qwen3-VL-30B-A3B-Instruct"
BURNLEY_DATA   = Path("data/sn_long/2015-04-11 - Burnley - Arsenal")

VLLM_WAIT_SEC  = 600
VLLM_POLL_SEC  = 5

def log(msg, also_print=True):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
    if also_print:
        print(line, flush=True)

def preflight():
    log("=== Smoke Test Started ===")
    log(f"Host: {os.uname().nodename}")

    if not BURNLEY_DATA.exists():
        log(f"ERROR: Burnley data missing at {BURNLEY_DATA}")
        log("Did you rsync data from DGX? See README.")
        sys.exit(1)
    log(f"OK Burnley data found at {BURNLEY_DATA}")

    if not MODEL_VLLM.exists():
        log(f"ERROR: vLLM model missing at {MODEL_VLLM}")
        log("Did you rsync Qwen2.5-7B-AWQ from DGX? See README.")
        sys.exit(1)
    log(f"OK vLLM model found at {MODEL_VLLM}")

    if not MODEL_VLM.exists():
        log(f"ERROR: VLM model missing at {MODEL_VLM}")
        log("Did you rsync Qwen3-VL-30B from DGX? See README.")
        sys.exit(1)
    log(f"OK VLM model found at {MODEL_VLM}")

    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
        with open(LOG_FILE, "a") as f:
            f.write(result.stdout + "\n")
        log("OK GPU info logged")
    except FileNotFoundError:
        log("WARNING: nvidia-smi not found")

def start_vllm():
    log("=== Starting vLLM ===")
    cmd = [
        "vllm", "serve", str(MODEL_VLLM),
        "--port", str(VLLM_PORT),
        "--quantization", "awq",
        "--enable-auto-tool-choice",
        "--tool-call-parser", "hermes",
        "--gpu-memory-utilization", "0.20",
        "--max-model-len", "4096",
    ]
    log(f"Command: {' '.join(cmd)}")

    vllm_log = open(VLLM_LOG, "w")
    proc = subprocess.Popen(
        cmd,
        stdout=vllm_log,
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid,
    )
    log(f"vLLM started PID={proc.pid}")
    return proc

def wait_vllm():
    log(f"Waiting for vLLM (up to {VLLM_WAIT_SEC}s)...")
    start = time.time()
    while time.time() - start < VLLM_WAIT_SEC:
        try:
            urllib.request.urlopen(VLLM_URL, timeout=2)
            elapsed = int(time.time() - start)
            log(f"OK vLLM ready after {elapsed}s")
            return True
        except (urllib.error.URLError, ConnectionResetError):
            time.sleep(VLLM_POLL_SEC)
    log(f"ERROR: vLLM did not start within {VLLM_WAIT_SEC}s. See vllm.log")
    return False

def run_pipeline():
    log("=== Running smoke test on Burnley ===")
    cmd = ["python", "experiments/level1_baseline.py", "--match", "Burnley"]
    log(f"Command: {' '.join(cmd)}")

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    with open(LOG_FILE, "a") as f:
        for line in proc.stdout:
            print(line, end="", flush=True)
            f.write(line)
    proc.wait()
    if proc.returncode != 0:
        log(f"ERROR: pipeline failed with exit code {proc.returncode}")
        return False
    log("OK Pipeline completed successfully")
    return True

def kill_vllm(proc):
    if proc is None:
        return
    log(f"Stopping vLLM PID={proc.pid}")
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=10)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass

def show_results():
    results = Path("experiments/results.json")
    log("=== Smoke Test Complete ===")
    if results.exists():
        log("Results:")
        with open(results) as f:
            content = f.read()
        print(content)
        with open(LOG_FILE, "a") as f:
            f.write("Results:\n" + content + "\n")
    else:
        log("WARNING: experiments/results.json was not created")

def main():
    LOG_FILE.write_text("")
    VLLM_LOG.write_text("")

    preflight()
    vllm_proc = None
    try:
        vllm_proc = start_vllm()
        if not wait_vllm():
            kill_vllm(vllm_proc)
            sys.exit(1)
        success = run_pipeline()
        kill_vllm(vllm_proc)
        show_results()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        log("Interrupted by user")
        kill_vllm(vllm_proc)
        sys.exit(130)

if __name__ == "__main__":
    main()
