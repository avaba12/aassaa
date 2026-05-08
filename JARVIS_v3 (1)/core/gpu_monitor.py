"""AMD ROCm + NVIDIA + Intel GPU-Monitor mit VRAM-Clear."""
import subprocess, platform, os, re, threading, json
from pathlib import Path
from memory.config_manager import ConfigManager

class GPUMonitor:
    def __init__(self):
        self._lock = threading.Lock()
        self._cache = {}
        self._cache_time = 0
        self.cfg = ConfigManager()
        self.os_name = platform.system()
        self._gpu_name = "Unknown"
        self._init_gpu_name()

    def _init_gpu_name(self):
        try:
            if self.os_name == "Windows":
                import wmi
                c = wmi.WMI()
                for gpu in c.Win32_VideoController():
                    if gpu.Name:
                        self._gpu_name = gpu.Name
                        return
        except Exception:
            pass
        try:
            result = subprocess.run(["wmic", "path", "win32_VideoController", "get", "Name"],
                                  capture_output=True, text=True, timeout=5)
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip() and "Name" not in l]
            if lines:
                self._gpu_name = lines[0]
        except Exception:
            pass

    def _run_cmd(self, cmd, timeout=5):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=True)
            return result.stdout
        except Exception:
            return ""

    def get_info(self):
        with self._lock:
            import time
            if time.time() - self._cache_time < 2:
                return self._cache

            info = {
                "vendor": "unknown",
                "name": self._gpu_name,
                "vram_total_mb": 0,
                "vram_used_mb": 0,
                "vram_free_mb": 0,
                "temperature_c": 0,
                "load_percent": 0,
                "has_rocm": False,
                "has_cuda": False,
            }

            # AMD ROCm
            rocm_path = self.cfg.get("rocm_path", "")
            if rocm_path:
                rocm_smi = Path(rocm_path) / "rocm-smi.exe"
                if rocm_smi.exists():
                    info["has_rocm"] = True
                    out = self._run_cmd(f'"{rocm_smi}" --showmeminfo VRAM --showtemp --showuse')
                    for line in out.splitlines():
                        if "VRAM" in line and "Total" in line:
                            m = re.search(r"(\d+)\s*MiB", line)
                            if m: info["vram_total_mb"] = int(m.group(1))
                        elif "VRAM" in line and "Used" in line:
                            m = re.search(r"(\d+)\s*MiB", line)
                            if m: info["vram_used_mb"] = int(m.group(1))
                        elif "Temperature" in line:
                            m = re.search(r"(\d+)\s*c", line, re.I)
                            if m: info["temperature_c"] = int(m.group(1))
                        elif "GPU use" in line:
                            m = re.search(r"(\d+)\s*%", line)
                            if m: info["load_percent"] = int(m.group(1))

            # NVIDIA
            if info["vram_total_mb"] == 0:
                nvidia_out = self._run_cmd("nvidia-smi --query-gpu=name,memory.total,memory.used,temperature.gpu,utilization.gpu --format=csv,noheader,nounits")
                if nvidia_out and "not found" not in nvidia_out.lower():
                    info["has_cuda"] = True
                    parts = [p.strip() for p in nvidia_out.split(",")]
                    if len(parts) >= 5:
                        info["name"] = parts[0]
                        info["vram_total_mb"] = int(float(parts[1]))
                        info["vram_used_mb"] = int(float(parts[2]))
                        info["temperature_c"] = int(float(parts[3])) if parts[3] != "[Not Supported]" else 0
                        info["load_percent"] = int(float(parts[4])) if parts[4] != "[Not Supported]" else 0

            # Windows WMI Fallback
            if info["vram_total_mb"] == 0 and self.os_name == "Windows":
                try:
                    import wmi
                    c = wmi.WMI()
                    for gpu in c.Win32_VideoController():
                        if gpu.AdapterRAM:
                            info["name"] = gpu.Name or self._gpu_name
                            info["vram_total_mb"] = int(gpu.AdapterRAM) // (1024 * 1024)
                            break
                except Exception:
                    pass

            # Ollama VRAM-Schätzung
            if info["vram_used_mb"] == 0:
                try:
                    import ollama
                    client = ollama.Client(host=self.cfg.get("ollama_host", "http://localhost:11434"))
                    ps = client.ps()
                    if hasattr(ps, "models"):
                        for m in ps.models:
                            info["vram_used_mb"] += getattr(m, "size_vram", 0) // (1024 * 1024)
                except Exception:
                    pass

            info["vram_free_mb"] = max(0, info["vram_total_mb"] - info["vram_used_mb"])
            self._cache = info
            self._cache_time = time.time()
            return info

    def clear_vram(self):
        try:
            import ollama
            client = ollama.Client(host=self.cfg.get("ollama_host", "http://localhost:11434"))
            ps = client.ps()
            if hasattr(ps, "models"):
                unloaded = []
                for m in ps.models:
                    model_name = getattr(m, "model", "")
                    if model_name:
                        try:
                            client.stop(model_name)
                            unloaded.append(model_name)
                        except Exception:
                            pass
                if unloaded:
                    return f"VRAM geleert: {len(unloaded)} Modell(e) entladet: {', '.join(unloaded)}"
            return "VRAM ist bereits leer."
        except Exception as e:
            return f"VRAM-Clear: {e}"

    def estimate_ai_vram(self, model_name):
        name = model_name.lower()
        if "70b" in name: return 43000
        if "34b" in name or "32b" in name: return 22000
        if "13b" in name or "14b" in name: return 9000
        if "8b" in name or "7b" in name: return 5500
        if "3b" in name: return 2500
        if "1b" in name: return 1500
        return 4000
