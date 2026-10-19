"""
TechSift AI - Phase 4A: Edge-TTS Verification Script
Generates and rigorously validates 4 technical audio samples:
1. Arabic Male (ar-EG-ShakirNeural)
2. Arabic Female (ar-EG-SalmaNeural)
3. English Male (en-US-GuyNeural)
4. English Female (en-US-JennyNeural)
"""

import asyncio
import json
from pathlib import Path
import subprocess
import time
import edge_tts

SAMPLES = [
    {
        "id": "ar_male",
        "language": "Arabic",
        "gender": "Male",
        "voice": "ar-EG-ShakirNeural",
        "text": "تعتمد البنية التحتية لتطبيق تيك سيفت على فصل طبقة التخزين عن معالجة البيانات، مما يسمح بتحليل المستندات الكبيرة بكفاءة عالية وبدون أي تكلفة تشغيلية.",
        "filename": "arabic_male_shakir.mp3",
    },
    {
        "id": "ar_female",
        "language": "Arabic",
        "gender": "Female",
        "voice": "ar-EG-SalmaNeural",
        "text": "تتيح خوارزميات التقطيع الدلالي المتداخل تقسيم النصوص التقنية مع الحفاظ على السياق الكامل للفقرات والمصطلحات البرمجية المعقدة.",
        "filename": "arabic_female_salma.mp3",
    },
    {
        "id": "en_male",
        "language": "English",
        "gender": "Male",
        "voice": "en-US-GuyNeural",
        "text": "TechSift AI implements an asynchronous pipeline using FastAPI and SQLite, ensuring zero-cost document ingestion and high-throughput processing.",
        "filename": "english_male_guy.mp3",
    },
    {
        "id": "en_female",
        "language": "English",
        "gender": "Female",
        "voice": "en-US-JennyNeural",
        "text": "By leveraging sliding-window chunking algorithms, the ingestion engine preserves critical architectural context across complex technical specifications.",
        "filename": "english_female_jenny.mp3",
    },
]

def analyze_audio_file(file_path: Path) -> dict:
    """Uses ffprobe and ffmpeg to analyze audio integrity and loudness."""
    # 1. ffprobe format and stream data
    probe_cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]
    probe_res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    probe_data = json.loads(probe_res.stdout)
    
    stream = probe_data["streams"][0]
    format_info = probe_data["format"]
    
    duration = float(format_info.get("duration", 0.0))
    sample_rate = int(stream.get("sample_rate", 0))
    channels = int(stream.get("channels", 0))
    codec_name = stream.get("codec_name", "")
    bit_rate = int(format_info.get("bit_rate", 0))
    
    # 2. ffmpeg decoding check
    decode_cmd = ["ffmpeg", "-v", "error", "-i", str(file_path), "-f", "null", "-"]
    decode_res = subprocess.run(decode_cmd, capture_output=True, text=True)
    is_decodable = (decode_res.returncode == 0 and len(decode_res.stderr.strip()) == 0)
    
    # 3. ffmpeg volume detect to ensure audible sound
    vol_cmd = ["ffmpeg", "-i", str(file_path), "-filter:a", "volumedetect", "-f", "null", "/dev/null"]
    vol_res = subprocess.run(vol_cmd, capture_output=True, text=True)
    
    max_volume = None
    mean_volume = None
    for line in vol_res.stderr.splitlines():
        if "max_volume:" in line:
            max_volume = float(line.split("max_volume:")[1].split("dB")[0].strip())
        elif "mean_volume:" in line:
            mean_volume = float(line.split("mean_volume:")[1].split("dB")[0].strip())
            
    is_audible = (max_volume is not None and max_volume > -50.0 and duration > 0.5)

    return {
        "duration_seconds": round(duration, 2),
        "sample_rate_hz": sample_rate,
        "channels": channels,
        "codec": codec_name,
        "bit_rate_kbps": round(bit_rate / 1000, 1),
        "is_decodable": is_decodable,
        "max_volume_db": max_volume,
        "mean_volume_db": mean_volume,
        "is_audible": is_audible,
    }

async def generate_and_verify_samples():
    output_dir = Path("storage/audio_feasibility/edge_tts")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    print("=== Generating Edge-TTS Audio Samples ===")
    
    for item in SAMPLES:
        out_file = output_dir / item["filename"]
        print(f"\nProcessing [{item['id']}] {item['language']} {item['gender']} ({item['voice']})...")
        
        start_time = time.perf_counter()
        comm = edge_tts.Communicate(text=item["text"], voice=item["voice"])
        await comm.save(str(out_file))
        elapsed = time.perf_counter() - start_time
        
        size_bytes = out_file.stat().st_size
        analysis = analyze_audio_file(out_file)
        rtf = round(elapsed / analysis["duration_seconds"], 3) if analysis["duration_seconds"] > 0 else 0
        
        result_entry = {
            "id": item["id"],
            "language": item["language"],
            "gender": item["gender"],
            "voice": item["voice"],
            "text": item["text"],
            "file_path": str(out_file),
            "size_bytes": size_bytes,
            "generation_time_s": round(elapsed, 2),
            "real_time_factor": rtf,
            **analysis
        }
        results.append(result_entry)
        
        print(f"  File: {out_file.name} ({size_bytes} bytes)")
        print(f"  Duration: {analysis['duration_seconds']}s | Gen Time: {round(elapsed, 2)}s | RTF: {rtf}")
        print(f"  Codec: {analysis['codec']} @ {analysis['sample_rate_hz']}Hz, {analysis['bit_rate_kbps']} kbps")
        print(f"  Loudness: max={analysis['max_volume_db']} dB, mean={analysis['mean_volume_db']} dB")
        print(f"  Decodable: {analysis['is_decodable']} | Audible: {analysis['is_audible']}")
        
        # Rigorous assertions
        assert out_file.exists(), f"File {out_file} was not created"
        assert size_bytes > 1000, f"File {out_file} size too small ({size_bytes} bytes)"
        assert analysis["duration_seconds"] > 0, "Duration must be greater than zero"
        assert analysis["is_decodable"], "Audio file must be decodable without errors"
        assert analysis["is_audible"], "Audio file must contain audible speech"

    print("\n✅ All 4 edge-tts samples successfully generated and verified!")
    return results

if __name__ == "__main__":
    asyncio.run(generate_and_verify_samples())
