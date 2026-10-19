"""
TechSift AI - Phase 4A: Podcast Dialogue Feasibility Script
Generates dual-voice technical dialogues (Host & Co-host) in English and Arabic:
1. Generates individual turn segments with distinct voices.
2. Injects conversational silence pauses (450ms).
3. Stitches segments using pydub & ffmpeg into a unified production podcast episode.
4. Performs rigorous audio inspection (decodability, duration, RMS volume, bitrate).
"""

import asyncio
from pathlib import Path
import subprocess
import time
import json
import edge_tts
from pydub import AudioSegment

ENGLISH_DIALOGUE = [
    {
        "turn": 1,
        "speaker": "Host (Alex)",
        "voice": "en-US-GuyNeural",
        "text": "Welcome back to TechSift Deep Dives. Today, we're exploring why B-Trees remain the gold standard data structure for relational database storage engines.",
    },
    {
        "turn": 2,
        "speaker": "Co-host (Sarah)",
        "voice": "en-US-JennyNeural",
        "text": "That's a classic topic, Alex. But with all the hype around LSM-trees and columnar stores, why do traditional relational databases still default to B-Trees for primary indexing?",
    },
    {
        "turn": 3,
        "speaker": "Host (Alex)",
        "voice": "en-US-GuyNeural",
        "text": "Because B-Trees maintain balanced logarithmic search complexity while optimizing for disk page locality. Their wide fan-out ensures lookups, range scans, and updates require minimal disk I/O operations.",
    },
    {
        "turn": 4,
        "speaker": "Co-host (Sarah)",
        "voice": "en-US-JennyNeural",
        "text": "So the big takeaway is that B-Trees provide predictable read latency and low fragmentation, making them ideal for transaction-heavy, mixed-workload architectures.",
    },
]

ARABIC_DIALOGUE = [
    {
        "turn": 1,
        "speaker": "Host (Tariq)",
        "voice": "ar-EG-ShakirNeural",
        "text": "أهلاً بكم في بودكاست تيك سيفت التقني. موضوعنا اليوم هو دور طوابير الرسائل غير المتزامنة في فك الترابط بين الخدمات المصغرة.",
    },
    {
        "turn": 2,
        "speaker": "Co-host (Nour)",
        "voice": "ar-EG-SalmaNeural",
        "text": "مرحباً طارق. هذا موضوع حيوي بالفعل. لكن ما هو الفارق الجوهري بين استدعاءات واجهات برمجة التطبيقات المتزامنة وبين استخدام طوابير الرسائل؟",
    },
    {
        "turn": 3,
        "speaker": "Host (Tariq)",
        "voice": "ar-EG-ShakirNeural",
        "text": "الفارق الأساسي يكمن في مرونة النظام وقدرته على تحمل الأحمال المفاجئة. الطوابير غير المتزامنة تمنع تراكم الاختناقات، وتضمن استمرارية معالجة البيانات حتى في حال تعطل بعض الخدمات مؤقتاً.",
    },
    {
        "turn": 4,
        "speaker": "Co-host (Nour)",
        "voice": "ar-EG-SalmaNeural",
        "text": "إذن، الخلاصة التقنية هي أن معمارية الرسائل غير المتزامنة تضمن عزل الأعطال وتحقق قابلية التوسع الأفقي العالية دون التأثير على استجابة النظام للمستخدم.",
    },
]

def analyze_audio_file(file_path: Path) -> dict:
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
    
    decode_cmd = ["ffmpeg", "-v", "error", "-i", str(file_path), "-f", "null", "-"]
    decode_res = subprocess.run(decode_cmd, capture_output=True, text=True)
    is_decodable = (decode_res.returncode == 0 and len(decode_res.stderr.strip()) == 0)
    
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

async def build_podcast_episode(dialogue_script: list, lang_code: str, output_folder: Path) -> dict:
    output_folder.mkdir(parents=True, exist_ok=True)
    segment_files = []
    combined_audio = AudioSegment.empty()
    pause_between_turns = AudioSegment.silent(duration=450) # 450ms conversational pause
    
    total_gen_time = 0.0
    print(f"\n--- Generating {lang_code.upper()} Podcast Dialogue (4 Turns) ---")
    
    for turn in dialogue_script:
        seg_filename = f"turn_{turn['turn']}_{turn['speaker'].split()[0].lower()}.mp3"
        seg_path = output_folder / seg_filename
        
        print(f"Generating Turn {turn['turn']}: {turn['speaker']} ({turn['voice']})...")
        t0 = time.perf_counter()
        comm = edge_tts.Communicate(text=turn["text"], voice=turn["voice"])
        await comm.save(str(seg_path))
        elapsed = time.perf_counter() - t0
        total_gen_time += elapsed
        
        analysis = analyze_audio_file(seg_path)
        print(f"  Saved: {seg_filename} ({seg_path.stat().st_size} bytes, {analysis['duration_seconds']}s)")
        segment_files.append((seg_path, analysis))
        
        # Load into pydub and stitch
        turn_segment = AudioSegment.from_file(str(seg_path), format="mp3")
        if len(combined_audio) > 0:
            combined_audio += pause_between_turns
        combined_audio += turn_segment

    # Export combined full episode
    combined_path = output_folder / f"podcast_{lang_code}_episode.mp3"
    print(f"Exporting concatenated episode: {combined_path.name}...")
    combined_audio.export(str(combined_path), format="mp3", bitrate="48k")
    
    combined_analysis = analyze_audio_file(combined_path)
    combined_size = combined_path.stat().st_size
    rtf = round(total_gen_time / combined_analysis["duration_seconds"], 3) if combined_analysis["duration_seconds"] > 0 else 0
    
    print(f"  Combined Episode: {combined_path.name} ({combined_size} bytes)")
    print(f"  Total Duration: {combined_analysis['duration_seconds']}s | Generation Time: {round(total_gen_time, 2)}s | RTF: {rtf}")
    print(f"  Codec: {combined_analysis['codec']} @ {combined_analysis['sample_rate_hz']}Hz, {combined_analysis['bit_rate_kbps']} kbps")
    print(f"  Loudness: max={combined_analysis['max_volume_db']} dB, mean={combined_analysis['mean_volume_db']} dB")
    print(f"  Decodable: {combined_analysis['is_decodable']} | Audible: {combined_analysis['is_audible']}")
    
    assert combined_path.exists(), "Combined podcast file was not created"
    assert combined_size > 10000, f"Combined file size too small ({combined_size} bytes)"
    assert combined_analysis["duration_seconds"] > 10.0, "Episode duration must exceed 10 seconds"
    assert combined_analysis["is_decodable"], "Combined file must be decodable"
    assert combined_analysis["is_audible"], "Combined file must contain audible speech"
    
    return {
        "language": lang_code,
        "num_turns": len(dialogue_script),
        "combined_file": str(combined_path),
        "size_bytes": combined_size,
        "duration_seconds": combined_analysis["duration_seconds"],
        "generation_time_s": round(total_gen_time, 2),
        "real_time_factor": rtf,
        "loudness_max_db": combined_analysis["max_volume_db"],
        "loudness_mean_db": combined_analysis["mean_volume_db"],
        "segments": [str(p) for p, _ in segment_files]
    }

async def main():
    base_dir = Path("storage/audio_feasibility")
    en_results = await build_podcast_episode(ENGLISH_DIALOGUE, "en", base_dir / "podcast_en")
    ar_results = await build_podcast_episode(ARABIC_DIALOGUE, "ar", base_dir / "podcast_ar")
    
    print("\n==========================================")
    print("✅ Podcast Dialogue Feasibility PASSED for English and Arabic!")
    print(f"EN Episode: {en_results['combined_file']} ({en_results['duration_seconds']}s, RTF {en_results['real_time_factor']})")
    print(f"AR Episode: {ar_results['combined_file']} ({ar_results['duration_seconds']}s, RTF {ar_results['real_time_factor']})")
    print("==========================================")

if __name__ == "__main__":
    asyncio.run(main())
