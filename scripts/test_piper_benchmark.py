"""
TechSift AI - Phase 4A: Piper TTS Local Benchmark Script
Measures local ONNX CPU performance, RTF, latency, and audio decodability on macOS Apple Silicon.
"""

import json
from pathlib import Path
import subprocess
import time
import wave
from piper import PiperVoice

def run_piper_benchmark():
    model_path = Path("storage/piper_models/en_US-lessac-low.onnx")
    config_path = Path("storage/piper_models/en_US-lessac-low.onnx.json")
    output_dir = Path("storage/audio_feasibility/piper")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_wav = output_dir / "piper_sample_en.wav"

    assert model_path.exists(), f"Model not found: {model_path}"
    assert config_path.exists(), f"Config not found: {config_path}"

    text = "TechSift AI evaluates Piper TTS locally on Apple Silicon for offline, zero-cost audio synthesis."
    print("=== Piper TTS Benchmark on Apple Silicon CPU ===")
    print(f"Model: {model_path.name} ({round(model_path.stat().st_size / (1024*1024), 1)} MB)")

    # 1. Measure model load time
    start_load = time.perf_counter()
    voice = PiperVoice.load(str(model_path), config_path=str(config_path))
    load_time = time.perf_counter() - start_load
    print(f"Model Load Time: {round(load_time, 3)}s")

    # 2. Measure audio synthesis time
    start_syn = time.perf_counter()
    with wave.open(str(out_wav), "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)
    syn_time = time.perf_counter() - start_syn
    print(f"Synthesis Time: {round(syn_time, 3)}s")

    # 3. Analyze output with ffprobe
    probe_cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(out_wav),
    ]
    probe_res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    probe_data = json.loads(probe_res.stdout)
    duration = float(probe_data["format"]["duration"])
    sample_rate = int(probe_data["streams"][0]["sample_rate"])
    channels = int(probe_data["streams"][0]["channels"])
    file_size = out_wav.stat().st_size

    rtf = round(syn_time / duration, 3) if duration > 0 else 0

    # 4. ffmpeg volume detect
    vol_cmd = ["ffmpeg", "-i", str(out_wav), "-filter:a", "volumedetect", "-f", "null", "/dev/null"]
    vol_res = subprocess.run(vol_cmd, capture_output=True, text=True)
    max_vol = None
    mean_vol = None
    for line in vol_res.stderr.splitlines():
        if "max_volume:" in line:
            max_vol = float(line.split("max_volume:")[1].split("dB")[0].strip())
        elif "mean_volume:" in line:
            mean_vol = float(line.split("mean_volume:")[1].split("dB")[0].strip())

    print(f"Output File: {out_wav} ({file_size} bytes)")
    print(f"Audio Duration: {round(duration, 2)}s")
    print(f"Real-Time Factor (RTF): {rtf} (Lower is faster, <1.0 means faster than real-time)")
    print(f"Format: WAV, {sample_rate}Hz, {channels} channel(s)")
    print(f"Loudness: max={max_vol} dB, mean={mean_vol} dB")

    assert out_wav.exists() and file_size > 1000
    assert duration > 0
    assert rtf < 1.0, f"RTF {rtf} is too slow (expected < 1.0)"

    print("✅ Piper TTS local benchmark successfully passed!")

    return {
        "engine": "Piper TTS (ONNX / CPU)",
        "model": "en_US-lessac-low",
        "model_size_mb": round(model_path.stat().st_size / (1024*1024), 1),
        "load_time_s": round(load_time, 3),
        "synthesis_time_s": round(syn_time, 3),
        "audio_duration_s": round(duration, 2),
        "real_time_factor": rtf,
        "sample_rate_hz": sample_rate,
        "channels": channels,
        "max_vol_db": max_vol,
        "mean_vol_db": mean_vol,
    }

if __name__ == "__main__":
    run_piper_benchmark()
