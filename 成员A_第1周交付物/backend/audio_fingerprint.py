# -*- coding: utf-8 -*-
"""
音频指纹提取与比对模块（成员A · 第1周）
----------------------------------------
方案（可解释、无外部模型依赖）：
  1. 读取 WAV，单声道化；
  2. 分帧计算各频段能量，把整段音频切为 16 个时间步；
  3. 每步记录：主导频段、能量档位（0–3），生成 CRC32 指纹哈希；
  4. 两段音频按「步长 ±1 容差」比对指纹，得到音频相似度。

后续接入生产方案时，可将本模块替换为 Shazam 式 constellation 峰值指纹，
上层比对接口（compare_fingerprints）保持不变。
"""

import wave
import hashlib
import zlib
import struct
import numpy as np

N_STEPS = 16
N_BANDS = 4


def read_wav(path: str) -> tuple[np.ndarray, int]:
    """读取单声道 WAV，返回归一化浮点波形与采样率。"""
    with wave.open(path, "rb") as wf:
        sr = wf.getframerate()
        n = wf.getnframes()
        raw = wf.readframes(n)
        width = wf.getsampwidth()
        if width == 2:
            data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        elif width == 1:
            data = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128) / 128.0
        else:
            raise ValueError(f"不支持的采样位宽：{width} 字节")
        if wf.getnchannels() == 2:
            data = data.reshape(-1, 2).mean(axis=1)
    return data, sr


def _frame_band_energies(data: np.ndarray, frame_len: int = 256, hop: int = 128) -> np.ndarray:
    """逐帧 FFT，返回 (帧数, 频段数) 能量矩阵。"""
    rows = []
    for start in range(0, max(1, len(data) - frame_len + 1), hop):
        frame = data[start : start + frame_len]
        if len(frame) < frame_len:
            break
        spec = np.abs(np.fft.rfft(frame))
        bands = np.array_split(spec, N_BANDS)
        rows.append([b.mean() for b in bands])
    return np.array(rows) if rows else np.zeros((1, N_BANDS))


def fingerprint(path: str) -> dict:
    """提取音频指纹：16 步节奏包络 + 主导频段 + 能量档位。"""
    data, sr = read_wav(path)
    duration = round(len(data) / sr, 3)
    energies = _frame_band_energies(data)

    # 聚合到 N_STEPS 个时间步
    step_frames = np.array_split(energies, N_STEPS)
    steps = []
    for i, frames in enumerate(step_frames):
        if len(frames) == 0:
            steps.append(np.zeros(N_BANDS))
            continue
        steps.append(frames.mean(axis=0))
    steps = np.array(steps)

    level_bins = np.quantile(steps.mean(axis=1), [0.25, 0.5, 0.75])
    hashes: set[int] = set()
    points: list[dict] = []
    for i, band_e in enumerate(steps):
        dominant = int(np.argmax(band_e))
        level = int(np.digitize(band_e.mean(), level_bins))  # 0..3
        points.append({"step": i, "band": dominant, "level": level})
        payload = struct.pack("BBB", i, dominant, level)
        hashes.add(zlib.crc32(payload) & 0xFFFFFFFF)

    raw_sha = hashlib.sha256(data.tobytes()).hexdigest()

    return {
        "source_file": path,
        "sample_rate": sr,
        "duration_sec": duration,
        "step_count": N_STEPS,
        "band_count": N_BANDS,
        "peak_count": len(points),
        "hash_count": len(hashes),
        "points": points,
        "hashes": sorted(hashes),
        "waveform_sha256": raw_sha,
    }


def _tolerant_match(points_a: list[dict], points_b: list[dict], tol: int = 1) -> int:
    """步长 ±1 内容差匹配，返回命中的步数。"""
    matched = 0
    used = set()
    for pa in points_a:
        for j, pb in enumerate(points_b):
            if j in used:
                continue
            if abs(pa["step"] - pb["step"]) <= tol and pa["band"] == pb["band"] \
               and pa["level"] == pb["level"]:
                used.add(j)
                matched += 1
                break
    return matched


def compare_fingerprints(fp_a: dict, fp_b: dict) -> dict:
    """两段音频指纹比对：步长容差命中比 + 哈希 Jaccard。"""
    set_a, set_b = set(fp_a["hashes"]), set(fp_b["hashes"])
    if not set_a or not set_b:
        return {"match_ratio": 0.0, "jaccard": 0.0, "matched_hashes": 0, "audio_similarity": 0.0}
    matched = _tolerant_match(fp_a["points"], fp_b["points"])
    ratio = matched / min(len(fp_a["points"]), len(fp_b["points"]))
    jac = len(set_a & set_b) / len(set_a | set_b)
    return {
        "matched_hashes": matched,
        "jaccard": round(jac, 4),
        "match_ratio": round(ratio, 4),
        "audio_similarity": round(min(100.0, 100 * (0.7 * ratio + 0.3 * jac)), 1),
    }


# ---- 演示音频生成（仅用于首批底库入库与流程联调，正式环境替换为真实素材） ----

def generate_demo_wav(path: str, sr: int = 8000, duration: float = 3.0,
                      base_freq: float = 220.0, seed: int = 0) -> None:
    """生成带独立节奏包络的演示音频 WAV（节奏型作为可区分的指纹特征）。"""
    rng = np.random.default_rng(seed)
    n = int(sr * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    wave_data = (np.sin(2 * np.pi * base_freq * t) * 0.5
                 + np.sin(2 * np.pi * base_freq * 2.0 * t) * 0.25
                 + np.sin(2 * np.pi * base_freq * 0.5 * t) * 0.15)
    # 按 seed 生成 16 步通断节奏，形成不同的能量起伏轮廓
    pattern = rng.integers(0, 2, size=N_STEPS)
    step = n // N_STEPS
    rhythm = np.zeros(n)
    for i, on in enumerate(pattern):
        rhythm[i * step : (i + 1) * step] = 0.35 + 0.65 * on
    envelope = np.clip(t / 0.3, 0, 1) * np.clip((duration - t) / 0.3, 0, 1)
    wave_data = wave_data * envelope * rhythm + rng.normal(0, 0.02, n)
    pcm = np.clip(wave_data, -1, 1)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((pcm * 32767).astype(np.int16).tobytes())


def make_query_variant(src_path: str, dst_path: str, stretch: float = 1.05,
                       noise: float = 0.08, seed: int = 1) -> None:
    """对底库音频做轻微变速 + 加噪，模拟待测录音变体。"""
    data, sr = read_wav(src_path)
    n_new = int(len(data) / stretch)
    old_idx = np.linspace(0, len(data) - 1, n_new)
    stretched = np.interp(old_idx, np.arange(len(data)), data)
    rng = np.random.default_rng(seed)
    variant = stretched + rng.normal(0, noise, len(stretched))
    variant = np.clip(variant, -1, 1)
    with wave.open(dst_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((variant * 32767).astype(np.int16).tobytes())
