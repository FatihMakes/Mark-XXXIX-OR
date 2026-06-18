from __future__ import annotations

import json
import math
import os
import platform
import random
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

from PyQt6.QtCore import (
    QEasingCurve, QMimeData, QObject, QPointF, QRectF, QSize, Qt,
    QTimer, QUrl, pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush, QColor, QDragEnterEvent, QDropEvent, QFont, QFontDatabase,
    QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
    QRadialGradient, QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy, QTextEdit,
    QVBoxLayout, QWidget, QProgressBar, QTabWidget, QListWidget,
    QListWidgetItem, QGridLayout, QGroupBox
)

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR   = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"

_DEFAULT_W, _DEFAULT_H = 980, 700
_MIN_W,     _MIN_H     = 820, 580
_LEFT_W  = 148
_RIGHT_W = 340

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"


class C:
    BG        = "#00060a"
    PANEL     = "#010d14"
    PANEL2    = "#010f18"
    BORDER    = "#0d3347"
    BORDER_B  = "#1a5c7a"
    BORDER_A  = "#0f4060"
    PRI       = "#00d4ff"
    PRI_DIM   = "#007a99"
    PRI_GHO   = "#001f2e"
    ACC       = "#ff6b00"
    ACC2      = "#ffcc00"
    GREEN     = "#00ff88"
    GREEN_D   = "#00aa55"
    RED       = "#ff3355"
    MUTED_C   = "#ff3366"
    TEXT      = "#8ffcff"
    TEXT_DIM  = "#3a8a9a"
    TEXT_MED  = "#5ab8cc"
    WHITE     = "#d8f8ff"
    DARK      = "#000d14"
    BAR_BG    = "#011520"


def qcol(h: str, a: int = 255) -> QColor:
    c = QColor(h); c.setAlpha(a); return c

class _SysMetrics:
    def __init__(self):
        self.cpu  = 0.0
        self.mem  = 0.0
        self.net  = 0.0   
        self.gpu  = -1.0  
        self.tmp  = -1.0  
        self.services = {
            "ollama": False,
            "odysseus": False,
            "gateway": False,
            "ts_jarvis": False,
            "backend": False,
            "frontend": False,
            "wa_forwarder": False,
            "hud_gui": True
        }
        self.ports = {
            "ollama": False,
            "odysseus": False,
            "gateway": False,
            "ts_jarvis": False,
            "frontend": False,
            "mongodb": False
        }
        self._lock = threading.Lock()
        self._last_net = psutil.net_io_counters()
        self._last_net_t = time.time()
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def _loop(self):
        while self._running:
            try:
                self._update()
            except Exception:
                pass
            time.sleep(1.5)

    def _check_port(self, port: int) -> bool:
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.15)
                return s.connect_ex(('127.0.0.1', port)) == 0
        except Exception:
            return False

    def _get_services(self) -> dict:
        status = {
            "ollama": False,
            "odysseus": False,
            "gateway": False,
            "ts_jarvis": False,
            "backend": False,
            "frontend": False,
            "wa_forwarder": False,
            "hud_gui": True
        }
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmd = proc.info.get('cmdline')
                if not cmd:
                    continue
                cmd_str = " ".join(cmd).lower()
                if "ollama" in cmd_str:
                    status["ollama"] = True
                elif "uvicorn" in cmd_str and "7000" in cmd_str:
                    status["odysseus"] = True
                elif "clawdbot" in cmd_str and "gateway" in cmd_str:
                    status["gateway"] = True
                elif "bun" in cmd_str and ("start" in cmd_str or "daemon" in cmd_str or "index.ts" in cmd_str):
                    status["ts_jarvis"] = True
                elif "node" in cmd_str and "server.js" in cmd_str:
                    status["backend"] = True
                elif "node" in cmd_str and "vite.js" in cmd_str:
                    status["frontend"] = True
                elif "node" in cmd_str and "app.js" in cmd_str:
                    status["wa_forwarder"] = True
                elif "python" in cmd_str and "main.py" in cmd_str:
                    status["hud_gui"] = True
            except Exception:
                pass
        return status

    def _update(self):
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent

        nc  = psutil.net_io_counters()
        now = time.time()
        dt  = now - self._last_net_t
        if dt > 0:
            sent = (nc.bytes_sent - self._last_net.bytes_sent) / dt
            recv = (nc.bytes_recv - self._last_net.bytes_recv) / dt
            net  = (sent + recv) / (1024 * 1024)
        else:
            net = 0.0
        self._last_net   = nc
        self._last_net_t = now

        gpu = self._get_gpu()
        tmp = self._get_temp()
        
        services = self._get_services()
        ports = {
            "ollama": self._check_port(11434),
            "odysseus": self._check_port(7000),
            "gateway": self._check_port(18789),
            "ts_jarvis": self._check_port(3142),
            "frontend": self._check_port(3000),
            "mongodb": self._check_port(27017)
        }

        with self._lock:
            self.cpu = cpu
            self.mem = mem
            self.net = net
            self.gpu = gpu
            self.tmp = tmp
            self.services = services
            self.ports = ports

    def _get_gpu(self) -> float:
        # NVIDIA
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2
            )
            if r.returncode == 0:
                vals = [float(v.strip()) for v in r.stdout.strip().split("\n") if v.strip()]
                if vals:
                    return sum(vals) / len(vals)
        except Exception:
            pass

        # AMD (Linux)
        if _OS == "Linux":
            try:
                r = subprocess.run(
                    ["rocm-smi", "--showuse", "--csv"],
                    capture_output=True, text=True, timeout=2
                )
                if r.returncode == 0:
                    for line in r.stdout.strip().split("\n"):
                        parts = line.split(",")
                        if len(parts) >= 2:
                            try:
                                return float(parts[1].strip().replace("%", ""))
                            except ValueError:
                                pass
            except Exception:
                pass

            # Intel GPU (Linux)
            try:
                r = subprocess.run(
                    ["intel_gpu_top", "-J", "-s", "500"],
                    capture_output=True, text=True, timeout=1
                )
                if r.returncode == 0 and "Render/3D" in r.stdout:
                    import re
                    m = re.search(r'"busy":\s*([\d.]+)', r.stdout)
                    if m:
                        return float(m.group(1))
            except Exception:
                pass

        # macOS — powermetrics (GPU Engine)
        if _OS == "Darwin":
            try:
                r = subprocess.run(
                    ["sudo", "-n", "powermetrics", "-n", "1", "-i", "500",
                     "--samplers", "gpu_power"],
                    capture_output=True, text=True, timeout=2
                )
                if r.returncode == 0 and "GPU" in r.stdout:
                    import re
                    m = re.search(r'GPU\s+Active:\s+([\d.]+)%', r.stdout)
                    if m:
                        return float(m.group(1))
            except Exception:
                pass

        return -1.0

    def _get_temp(self) -> float:
        try:
            temps = psutil.sensors_temperatures()
            candidates = ["coretemp", "k10temp", "cpu_thermal", "acpitz",
                          "cpu-thermal", "zenpower", "it8688"]
            for name in candidates:
                if name in temps:
                    entries = temps[name]
                    if entries:
                        return entries[0].current
            for entries in temps.values():
                if entries:
                    return entries[0].current
        except Exception:
            pass
        if _OS == "Darwin":
            try:
                r = subprocess.run(
                    ["osx-cpu-temp"], capture_output=True, text=True, timeout=2
                )
                if r.returncode == 0:
                    import re
                    m = re.search(r"([\d.]+)", r.stdout)
                    if m:
                        return float(m.group(1))
            except Exception:
                pass

        if _OS == "Windows":
            try:
                r = subprocess.run(
                    ["powershell", "-Command",
                     "(Get-WmiObject MSAcpi_ThermalZoneTemperature -Namespace root/wmi).CurrentTemperature"],
                    capture_output=True, text=True, timeout=3
                )
                if r.returncode == 0 and r.stdout.strip():
                    raw = float(r.stdout.strip().split("\n")[0])
                    return (raw / 10.0) - 273.15
            except Exception:
                pass

        return -1.0

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "cpu": self.cpu,
                "mem": self.mem,
                "net": self.net,
                "gpu": self.gpu,
                "tmp": self.tmp,
                "services": self.services,
                "ports": self.ports
            }


_metrics = _SysMetrics()

class HudCanvas(QWidget):
    def __init__(self, face_path: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.muted    = False
        self.speaking = False
        self.state    = "INITIALISING"

        self._tick       = 0
        self._scale      = 1.0
        self._tgt_scale  = 1.0
        self._halo       = 55.0
        self._tgt_halo   = 55.0
        self._last_t     = time.time()
        self._scan       = 0.0
        self._scan2      = 180.0
        self._rings      = [0.0, 120.0, 240.0]
        self._pulses: list[float] = [0.0, 50.0, 100.0]
        self._blink      = True
        self._blink_tick = 0
        self._particles: list[list[float]] = []
        self._face_px: QPixmap | None = None
        self._load_face(face_path)

        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._tmr.start(16)

    def _load_face(self, path: str):
        try:
            from PIL import Image, ImageDraw
            import io
            img = Image.open(path).convert("RGBA")
            sz  = min(img.size)
            img = img.resize((sz, sz), Image.LANCZOS)
            mk  = Image.new("L", (sz, sz), 0)
            ImageDraw.Draw(mk).ellipse((2, 2, sz - 2, sz - 2), fill=255)
            img.putalpha(mk)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            px = QPixmap(); px.loadFromData(buf.getvalue())
            self._face_px = px
        except Exception:
            self._face_px = None

    def _step(self):
        self._tick += 1
        now = time.time()
        if now - self._last_t > (0.12 if self.speaking else 0.5):
            if self.speaking:
                self._tgt_scale = random.uniform(1.06, 1.14)
                self._tgt_halo  = random.uniform(145, 190)
            elif self.muted:
                self._tgt_scale = random.uniform(0.998, 1.002)
                self._tgt_halo  = random.uniform(15, 28)
            else:
                self._tgt_scale = random.uniform(1.001, 1.008)
                self._tgt_halo  = random.uniform(48, 68)
            self._last_t = now

        sp = 0.38 if self.speaking else 0.15
        self._scale += (self._tgt_scale - self._scale) * sp
        self._halo  += (self._tgt_halo  - self._halo)  * sp

        speeds = [1.3, -0.9, 2.0] if self.speaking else [0.55, -0.35, 0.9]
        for i, spd in enumerate(speeds):
            self._rings[i] = (self._rings[i] + spd) % 360

        self._scan  = (self._scan  + (3.0 if self.speaking else 1.3)) % 360
        self._scan2 = (self._scan2 + (-2.0 if self.speaking else -0.75)) % 360

        fw  = min(self.width(), self.height())
        lim = fw * 0.74
        spd = 4.2 if self.speaking else 2.0
        self._pulses = [r + spd for r in self._pulses if r + spd < lim]
        if len(self._pulses) < 3 and random.random() < (0.07 if self.speaking else 0.025):
            self._pulses.append(0.0)

        if self.speaking and random.random() < 0.28:
            cx, cy = self.width() / 2, self.height() / 2
            ang = random.uniform(0, 2 * math.pi)
            r_s = fw * 0.28
            self._particles.append([
                cx + math.cos(ang) * r_s, cy + math.sin(ang) * r_s,
                math.cos(ang) * random.uniform(0.9, 2.4),
                math.sin(ang) * random.uniform(0.9, 2.4) - 0.4, 1.0,
            ])
        self._particles = [
            [p[0]+p[2], p[1]+p[3], p[2]*0.97, p[3]*0.97, p[4]-0.028]
            for p in self._particles if p[4] > 0
        ]

        self._blink_tick += 1
        if self._blink_tick >= 38:
            self._blink = not self._blink
            self._blink_tick = 0
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), qcol(C.BG))

        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2
        fw = min(W, H)

        # Dynamic primary colors based on online/offline state
        if self.state.startswith("OFFLINE"):
            pri_col = C.RED
            pri_dim = "#991f33"
            pri_gho = "#2e050a"
        else:
            pri_col = C.PRI
            pri_dim = C.PRI_DIM
            pri_gho = C.PRI_GHO

        # grid dots
        p.setPen(QPen(qcol(pri_gho), 1))
        for x in range(0, W, 48):
            for y in range(0, H, 48):
                p.drawPoint(x, y)

        r_face = fw * 0.31

        # halo glow
        for i in range(10):
            r   = r_face * (1.8 - i * 0.08)
            frc = 1.0 - i / 10
            a   = max(0, min(255, int(self._halo * 0.085 * frc)))
            col = qcol(C.MUTED_C if self.muted else pri_col, a)
            p.setPen(QPen(col, 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # pulse rings
        for pr in self._pulses:
            a   = max(0, int(230 * (1.0 - pr / (fw * 0.74))))
            col = qcol(C.MUTED_C if self.muted else pri_col, a)
            p.setPen(QPen(col, 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - pr, cy - pr, pr * 2, pr * 2))

        # spinning arc rings
        for idx, (r_frac, w_r, arc_l, gap) in enumerate(
            [(0.48, 3, 115, 78), (0.40, 2, 78, 55), (0.32, 1, 56, 40)]
        ):
            ring_r = fw * r_frac
            base   = self._rings[idx]
            a_val  = max(0, min(255, int(self._halo * (1.0 - idx * 0.18))))
            col    = qcol(C.MUTED_C if self.muted else pri_col, a_val)
            p.setPen(QPen(col, w_r)); p.setBrush(Qt.BrushStyle.NoBrush)
            angle = base
            rect  = QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2)
            while angle < base + 360:
                p.drawArc(rect, int(angle * 16), int(arc_l * 16))
                angle += arc_l + gap

        # scanners
        sr = fw * 0.50
        sa = min(255, int(self._halo * 1.5))
        ex = 75 if self.speaking else 44
        p.setPen(QPen(qcol(C.MUTED_C if self.muted else pri_col, sa), 2.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        srect = QRectF(cx - sr, cy - sr, sr * 2, sr * 2)
        p.drawArc(srect, int(self._scan * 16), int(ex * 16))
        p.setPen(QPen(qcol(C.ACC, sa // 2), 1.5))
        p.drawArc(srect, int(self._scan2 * 16), int(ex * 16))

        # tick marks
        t_out, t_in = fw * 0.497, fw * 0.474
        p.setPen(QPen(qcol(pri_col, 140), 1))
        for deg in range(0, 360, 10):
            rad = math.radians(deg)
            inn = t_in if deg % 30 == 0 else t_in + 6
            p.drawLine(
                QPointF(cx + t_out * math.cos(rad), cy - t_out * math.sin(rad)),
                QPointF(cx + inn  * math.cos(rad), cy - inn  * math.sin(rad)),
            )

        # crosshair
        ch_r, gap_h = fw * 0.51, fw * 0.16
        p.setPen(QPen(qcol(pri_col, int(self._halo * 0.5)), 1))
        p.drawLine(QPointF(cx - ch_r, cy), QPointF(cx - gap_h, cy))
        p.drawLine(QPointF(cx + gap_h, cy), QPointF(cx + ch_r, cy))
        p.drawLine(QPointF(cx, cy - ch_r), QPointF(cx, cy - gap_h))
        p.drawLine(QPointF(cx, cy + gap_h), QPointF(cx, cy + ch_r))

        # corner brackets
        bl = 24
        bc = qcol(pri_col, 210)
        hl, hr = cx - fw // 2, cx + fw // 2
        ht, hb = cy - fw // 2, cy + fw // 2
        p.setPen(QPen(bc, 2))
        for bx, by, dx, dy in [(hl,ht,1,1),(hr,ht,-1,1),(hl,hb,1,-1),(hr,hb,-1,-1)]:
            p.drawLine(QPointF(bx, by), QPointF(bx + dx * bl, by))
            p.drawLine(QPointF(bx, by), QPointF(bx, by + dy * bl))

        # face
        r_face = fw * 0.31
        if self._face_px:
            fsz    = int(fw * 0.60 * self._scale)
            scaled = self._face_px.scaled(
                fsz, fsz,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            # Set opacity depending on thinking/processing
            if self.state in ["THINKING", "PROCESSING", "OFFLINE_THINKING"]:
                p.setOpacity(0.35)
            else:
                p.setOpacity(0.85)
            p.drawPixmap(int(cx - fsz / 2), int(cy - fsz / 2), scaled)
            p.setOpacity(1.0)
            
            # Circular border around user avatar
            p.setPen(QPen(qcol(pri_dim if not self.speaking else C.ACC, 180), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - fsz/2, cy - fsz/2, fsz, fsz))
        else:
            orb_r = int(fw * 0.27 * self._scale)
            if self.state.startswith("OFFLINE"):
                oc = (180, 20, 0) if self.muted else (150, 40, 0)
            else:
                oc = (200, 0, 50) if self.muted else (0, 60, 110)
            for i in range(8, 0, -1):
                r2  = int(orb_r * i / 8)
                frc = i / 8
                a   = max(0, min(255, int(self._halo * 1.1 * frc)))
                p.setBrush(QBrush(QColor(int(oc[0]*frc), int(oc[1]*frc), int(oc[2]*frc), a)))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QRectF(cx - r2, cy - r2, r2 * 2, r2 * 2))
            p.setPen(QPen(qcol(pri_col, min(255, int(self._halo * 2))), 1))
            p.setFont(QFont("Courier New", 13, QFont.Weight.Bold))
            p.drawText(QRectF(cx - 80, cy - 14, 160, 28),
                       Qt.AlignmentFlag.AlignCenter, "J.A.R.V.I.S")

        # --- Dynamic State Visualizations ---
        if self.state in ["THINKING", "PROCESSING", "OFFLINE_THINKING"]:
            # Neural Synapse Brain animation (Glowing synapses)
            p.setPen(Qt.PenStyle.NoPen)
            # Center node
            p.setBrush(QBrush(qcol(C.ACC2, 230)))
            p.drawEllipse(QPointF(cx, cy), 8, 8)
            
            # Outer nodes
            nodes = []
            for i in range(6):
                ang = math.radians(i * 60 + self._scan * 0.3)
                rn  = r_face * 0.72 * (0.8 + 0.15 * math.sin(self._tick * 0.08 + i))
                nx  = cx + rn * math.cos(ang)
                ny  = cy + rn * math.sin(ang)
                nodes.append((nx, ny))
                
            # Draw lines
            p.setBrush(Qt.BrushStyle.NoBrush)
            for idx, (nx, ny) in enumerate(nodes):
                # Connect to center
                p.setPen(QPen(qcol(C.ACC2, 140), 1.5))
                p.drawLine(QPointF(cx, cy), QPointF(nx, ny))
                # Connect to next node
                nxt = nodes[(idx + 1) % 6]
                p.setPen(QPen(qcol(pri_col, 100), 1))
                p.drawLine(QPointF(nx, ny), QPointF(nxt[0], nxt[1]))
                
            # Draw outer node synapse circles
            for idx, (nx, ny) in enumerate(nodes):
                sz = 6 + 3 * math.sin(self._tick * 0.12 + idx)
                p.setPen(QPen(qcol(C.WHITE, 200), 1))
                p.setBrush(QBrush(qcol(C.ACC if idx % 2 == 0 else C.ACC2, 220)))
                p.drawEllipse(QPointF(nx, ny), sz, sz)
                
        elif self.state == "EXECUTING":
            # Spinning cyber target loader and telemetry text
            p.setBrush(Qt.BrushStyle.NoBrush)
            
            # Draw spinning rings
            ring_r = r_face * 0.8
            p.setPen(QPen(qcol(C.ACC, 200), 2, Qt.PenStyle.DashLine))
            p.drawArc(QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2), int(self._scan * 16), 140 * 16)
            p.drawArc(QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2), int((self._scan + 180) * 16), 140 * 16)
            
            # Outer counter-rotating ring
            ring_r2 = r_face * 0.9
            p.setPen(QPen(qcol(pri_col, 160), 1))
            p.drawArc(QRectF(cx - ring_r2, cy - ring_r2, ring_r2 * 2, ring_r2 * 2), int(-self._scan * 12), 220 * 16)
            
            # Telemetry text labels next to the ring
            p.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
            p.setPen(QPen(qcol(C.WHITE, 180), 1))
            p.drawText(int(cx + ring_r * 0.75), int(cy - ring_r * 0.7), "PROC: ACTIVE")
            p.setPen(QPen(qcol(pri_col, 150), 1))
            p.drawText(int(cx + ring_r * 0.75), int(cy - ring_r * 0.7 + 10), "LOCK: LOCKED")
            p.drawText(int(cx + ring_r * 0.75), int(cy - ring_r * 0.7 + 20), "STARK_OS: OK")
            p.setPen(QPen(qcol(C.ACC, 180), 1))
            p.drawText(int(cx - ring_r * 1.3), int(cy + ring_r * 0.8), "TELEMETRY: OK")
            p.drawText(int(cx - ring_r * 1.3), int(cy + ring_r * 0.8 + 10), f"SYS_T: {self._tick}")
            
        elif self.state in ["LISTENING", "OFFLINE_LISTENING"]:
            # Green/Red radar sweep
            p.setBrush(Qt.BrushStyle.NoBrush)
            sweep_col = C.RED if self.state == "OFFLINE_LISTENING" else C.GREEN
            p.setPen(QPen(qcol(sweep_col, 80), 1))
            # Concentric rings
            for r_mul in [0.4, 0.6, 0.8]:
                p.drawEllipse(QRectF(cx - r_face * r_mul, cy - r_face * r_mul, r_face * r_mul * 2, r_face * r_mul * 2))
            
            # Sonar sweep line
            rad = math.radians(self._scan)
            p.setPen(QPen(qcol(sweep_col, 220), 2))
            p.drawLine(QPointF(cx, cy), QPointF(cx + r_face * 0.95 * math.cos(rad), cy + r_face * 0.95 * math.sin(rad)))
            
            # Draw sweep trail
            for idx in range(15):
                trail_rad = math.radians(self._scan - idx * 2.5)
                p.setPen(QPen(qcol(sweep_col, max(0, 180 - idx * 12)), 1))
                p.drawLine(QPointF(cx, cy), QPointF(cx + r_face * 0.95 * math.cos(trail_rad), cy + r_face * 0.95 * math.sin(trail_rad)))
                
        elif self.speaking:
            # Concentric voice wave ripples
            p.setBrush(Qt.BrushStyle.NoBrush)
            for idx in range(3):
                # Ripple radius expands and fades
                rip_r = r_face * 0.5 + ((self._tick * 1.5 + idx * 40) % 100) / 100 * r_face * 0.75
                alpha = int(220 * (1.0 - (rip_r - r_face * 0.5) / (r_face * 0.75)))
                if alpha > 0:
                    p.setPen(QPen(qcol(pri_col if idx % 2 == 0 else C.ACC, alpha), 1.5))
                    # Draw circle with wavy frequency ripples
                    path = QPainterPath()
                    points = 36
                    for p_idx in range(points + 1):
                        deg = p_idx * 10
                        rad = math.radians(deg)
                        # Add a small noise/sine offset to make it look like soundwave
                        offset = 4.5 * math.sin(self._tick * 0.25 + deg * 4) if self.speaking else 0
                        pr = rip_r + offset
                        px = cx + pr * math.cos(rad)
                        py = cy + pr * math.sin(rad)
                        if p_idx == 0:
                            path.moveTo(px, py)
                        else:
                            path.lineTo(px, py)
                    p.drawPath(path)

        # particles
        for pt in self._particles:
            a = max(0, min(255, int(pt[4] * 255)))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(pri_col, a)))
            p.drawEllipse(QPointF(pt[0], pt[1]), 2.5, 2.5)

        # status text
        sy = cy + fw * 0.40
        if self.muted:
            txt, col = "⊘  MUTED",     qcol(C.MUTED_C)
        elif self.state == "OFFLINE_LISTENING":
            sym = "⚠" if self._blink else "○"
            txt, col = f"{sym}  OFFLINE LISTENING", qcol(C.RED)
        elif self.state == "OFFLINE_THINKING":
            sym = "⚠" if self._blink else "◇"
            txt, col = f"{sym}  OFFLINE THINKING", qcol(C.ACC)
        elif self.state == "OFFLINE_SPEAKING":
            sym = "⚠" if self._blink else "●"
            txt, col = f"{sym}  OFFLINE SPEAKING", qcol(C.RED)
        elif self.speaking:
            txt, col = "●  SPEAKING",  qcol(C.ACC)
        elif self.state == "THINKING":
            sym = "◈" if self._blink else "◇"
            txt, col = f"{sym}  THINKING",   qcol(C.ACC2)
        elif self.state == "PROCESSING":
            sym = "▷" if self._blink else "▶"
            txt, col = f"{sym}  PROCESSING", qcol(C.ACC2)
        elif self.state == "EXECUTING":
            sym = "⚙" if self._blink else "⛭"
            txt, col = f"{sym}  EXECUTING TASK", qcol(C.ACC)
        elif self.state == "LISTENING":
            sym = "●" if self._blink else "○"
            txt, col = f"{sym}  LISTENING",  qcol(C.GREEN)
        else:
            sym = "●" if self._blink else "○"
            txt, col = f"{sym}  {self.state}", qcol(pri_col)

        p.setPen(QPen(col, 1))
        p.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        p.drawText(QRectF(0, sy, W, 26), Qt.AlignmentFlag.AlignCenter, txt)

        # waveform
        wy = sy + 30
        N, bw = 36, 8
        wx0 = (W - N * bw) / 2
        for i in range(N):
            if self.muted:
                hgt, cl = 2, qcol(C.MUTED_C)
            elif self.speaking:
                hgt = random.randint(3, 20)
                cl  = qcol(pri_col) if hgt > 12 else qcol(pri_dim)
            else:
                hgt = int(3 + 2 * math.sin(self._tick * 0.09 + i * 0.6))
                cl  = qcol("#7a1a24" if self.state.startswith("OFFLINE") else C.BORDER_B)
            p.fillRect(QRectF(wx0 + i * bw, wy + 20 - hgt, bw - 1, hgt), cl)

class MetricBar(QWidget):

    def __init__(self, label: str, color: str = C.PRI, parent=None):
        super().__init__(parent)
        self._label = label
        self._color = color
        self._value = 0.0       # 0–100
        self._text  = "--"
        self.setFixedHeight(38)
        self.setMinimumWidth(80)

    def set_value(self, pct: float, text: str):
        self._value = max(0.0, min(100.0, pct))
        self._text  = text
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        p.setBrush(QBrush(qcol(C.PANEL2)))
        p.setPen(QPen(qcol(C.BORDER_A), 1))
        p.drawRoundedRect(QRectF(1, 1, W - 2, H - 2), 4, 4)

        bar_h   = 4
        bar_y   = H - bar_h - 5
        bar_w   = W - 12
        bar_x   = 6
        fill_w  = int(bar_w * self._value / 100)

        p.setBrush(QBrush(qcol(C.BAR_BG)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 2, 2)

        if self._value > 85:
            bar_col = qcol(C.RED)
        elif self._value > 65:
            bar_col = qcol(C.ACC)
        else:
            bar_col = qcol(self._color)

        if fill_w > 0:
            p.setBrush(QBrush(bar_col))
            p.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h), 2, 2)

        p.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(8, 5, 50, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._label)

        p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        p.setPen(QPen(bar_col if self._text != "--" else qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(0, 4, W - 6, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._text)

class LogWidget(QTextEdit):
    _sig = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Courier New", 9))
        self.setStyleSheet(f"""
            QTextEdit {{
                background: {C.PANEL};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 4px;
                padding: 6px;
                selection-background-color: {C.PRI_GHO};
            }}
            QScrollBar:vertical {{
                background: {C.BG};
                width: 8px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {C.BORDER_B};
                border-radius: 4px;
                min-height: 20px;
            }}
        """)
        self._queue: list[str] = []
        self._typing  = False
        self._text    = ""
        self._pos     = 0
        self._tag     = "sys"
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._sig.connect(self._enqueue)

    def append_log(self, text: str):
        self._sig.emit(text)

    def _enqueue(self, text: str):
        self._queue.append(text)
        if not self._typing:
            self._next()

    def _next(self):
        if not self._queue:
            self._typing = False
            return
        self._typing = True
        self._text   = self._queue.pop(0)
        self._pos    = 0
        tl = self._text.lower()
        if   tl.startswith("you:"):    self._tag = "you"
        elif tl.startswith("jarvis:"): self._tag = "ai"
        elif tl.startswith("file:"):   self._tag = "file"
        elif tl.startswith("thought:"): self._tag = "thought"
        elif tl.startswith("tool:"):    self._tag = "tool"
        elif tl.startswith("memory:"):  self._tag = "memory"
        elif tl.startswith("task:"):    self._tag = "task"
        elif "err" in tl:              self._tag = "err"
        else:                          self._tag = "sys"
        self._tmr.start(6)

    def _step(self):
        if self._pos < len(self._text):
            ch  = self._text[self._pos]
            cur = self.textCursor()
            fmt = cur.charFormat()
            col = {
                "you":  qcol(C.WHITE),
                "ai":   qcol(C.PRI),
                "err":  qcol(C.RED),
                "file": qcol(C.GREEN),
                "thought": qcol(C.ACC2),
                "tool": qcol("#ff6b00"),
                "memory": qcol("#00ff88"),
                "task": qcol("#cc44ff"),
                "sys":  qcol(C.TEXT_MED),
            }.get(self._tag, qcol(C.TEXT))
            fmt.setForeground(QBrush(col))
            cur.movePosition(cur.MoveOperation.End)
            cur.insertText(ch, fmt)
            self.setTextCursor(cur)
            self.ensureCursorVisible()
            self._pos += 1
        else:
            self._tmr.stop()
            cur = self.textCursor()
            cur.movePosition(cur.MoveOperation.End)
            cur.insertText("\n")
            self.setTextCursor(cur)
            self.ensureCursorVisible()
            QTimer.singleShot(20, self._next)

_FILE_ICONS = {
    "image":   ("🖼", "#00d4ff"), "video":   ("🎬", "#ff6b00"),
    "audio":   ("🎵", "#cc44ff"), "pdf":     ("📄", "#ff4444"),
    "word":    ("📝", "#4488ff"), "excel":   ("📊", "#44bb44"),
    "code":    ("💻", "#ffcc00"), "archive": ("📦", "#ff8844"),
    "pptx":    ("📊", "#ff6622"), "text":    ("📃", "#aaaaaa"),
    "data":    ("🔧", "#88ddff"), "unknown": ("📎", "#888888"),
}
_EXT_TO_CAT = {
    **dict.fromkeys(["jpg","jpeg","png","gif","webp","bmp","tiff","svg","ico"], "image"),
    **dict.fromkeys(["mp4","avi","mov","mkv","wmv","flv","webm","m4v"],         "video"),
    **dict.fromkeys(["mp3","wav","ogg","m4a","aac","flac","wma","opus"],        "audio"),
    **dict.fromkeys(["pdf"],                                                     "pdf"),
    **dict.fromkeys(["doc","docx"],                                              "word"),
    **dict.fromkeys(["xls","xlsx","ods"],                                        "excel"),
    **dict.fromkeys(["ppt","pptx"],                                              "pptx"),
    **dict.fromkeys(["py","js","ts","jsx","tsx","html","css","java","c","cpp",
                     "cs","go","rs","rb","php","swift","kt","sh","sql","lua"],   "code"),
    **dict.fromkeys(["zip","rar","tar","gz","7z","bz2","xz"],                   "archive"),
    **dict.fromkeys(["txt","md","rst","log"],                                    "text"),
    **dict.fromkeys(["csv","tsv","json","xml"],                                  "data"),
}

def _file_category(path: Path) -> str:
    return _EXT_TO_CAT.get(path.suffix.lower().lstrip("."), "unknown")

def _fmt_size(size: int) -> str:
    if   size < 1024:    return f"{size} B"
    elif size < 1024**2: return f"{size/1024:.1f} KB"
    elif size < 1024**3: return f"{size/1024**2:.1f} MB"
    else:                return f"{size/1024**3:.1f} GB"


class FileDropZone(QWidget):
    file_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(100)
        self._current_file: str | None = None
        self._hovering  = False
        self._drag_over = False
        self._dash_offset = 0.0
        self._anim_tmr = QTimer(self)
        self._anim_tmr.timeout.connect(self._animate)
        self._anim_tmr.start(40)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._canvas = _DropCanvas(self)
        layout.addWidget(self._canvas)

    def _animate(self):
        self._dash_offset = (self._dash_offset + 0.8) % 20
        self._canvas.update()

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._drag_over = True; self._canvas.update()

    def dragLeaveEvent(self, e):
        self._drag_over = False; self._canvas.update()

    def dropEvent(self, e: QDropEvent):
        self._drag_over = False
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if Path(path).is_file():
                self._set_file(path)
        self._canvas.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._browse()

    def enterEvent(self, e):
        self._hovering = True; self._canvas.update()

    def leaveEvent(self, e):
        self._hovering = False; self._canvas.update()

    def current_file(self) -> str | None:
        return self._current_file

    def clear_file(self):
        self._current_file = None; self._canvas.update()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select a file for JARVIS", str(Path.home()),
            "All Files (*.*);;"
            "Images (*.jpg *.jpeg *.png *.gif *.webp *.bmp *.svg);;"
            "Documents (*.pdf *.docx *.txt *.md *.pptx);;"
            "Data (*.csv *.xlsx *.json *.xml);;"
            "Code (*.py *.js *.ts *.html *.css *.java *.cpp *.go);;"
            "Audio (*.mp3 *.wav *.ogg *.m4a *.aac *.flac);;"
            "Video (*.mp4 *.avi *.mov *.mkv *.wmv *.webm);;"
            "Archives (*.zip *.rar *.tar *.gz *.7z)",
        )
        if path:
            self._set_file(path)

    def _set_file(self, path: str):
        self._current_file = path
        self._canvas.update()
        self.file_selected.emit(path)


class _DropCanvas(QWidget):
    def __init__(self, zone: FileDropZone):
        super().__init__(zone)
        self._z = zone

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        z    = self._z
        W, H = self.width(), self.height()
        pad  = 6
        rect = QRectF(pad, pad, W - pad * 2, H - pad * 2)

        bg_col = qcol("#001a24" if z._drag_over else ("#001218" if z._hovering else C.PANEL))
        p.setBrush(QBrush(bg_col)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect, 6, 6)

        if z._current_file:   border_col = qcol(C.GREEN, 200)
        elif z._drag_over:    border_col = qcol(C.PRI, 230)
        elif z._hovering:     border_col = qcol(C.BORDER_B, 200)
        else:                 border_col = qcol(C.BORDER, 160)

        pen = QPen(border_col, 1.5, Qt.PenStyle.DashLine)
        pen.setDashOffset(z._dash_offset)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 6, 6)

        if z._current_file:   self._paint_file(p, W, H)
        elif z._drag_over:    self._paint_drag_over(p, W, H)
        else:                 self._paint_idle(p, W, H, z._hovering)

    def _paint_idle(self, p, W, H, hover):
        cx, cy = W / 2, H / 2
        col = qcol(C.PRI_DIM if not hover else C.PRI)
        p.setPen(QPen(col, 2)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(cx, cy - 14), QPointF(cx, cy + 4))
        p.drawLine(QPointF(cx - 8, cy - 6), QPointF(cx, cy - 14))
        p.drawLine(QPointF(cx + 8, cy - 6), QPointF(cx, cy - 14))
        p.drawLine(QPointF(cx - 14, cy + 4), QPointF(cx + 14, cy + 4))
        p.setFont(QFont("Courier New", 8))
        p.setPen(QPen(qcol(C.PRI_DIM if not hover else C.TEXT), 1))
        p.drawText(QRectF(0, cy + 8, W, 16), Qt.AlignmentFlag.AlignCenter,
                   "Drop file here  or  Click to Browse")
        p.setFont(QFont("Courier New", 7))
        p.setPen(QPen(qcol("#1a4a5a"), 1))
        p.drawText(QRectF(0, cy + 24, W, 14), Qt.AlignmentFlag.AlignCenter,
                   "Images · Video · Audio · PDF · Docs · Code · Data")

    def _paint_drag_over(self, p, W, H):
        cx, cy = W / 2, H / 2
        p.setFont(QFont("Courier New", 20))
        p.setPen(QPen(qcol(C.PRI), 1))
        p.drawText(QRectF(0, cy - 24, W, 32), Qt.AlignmentFlag.AlignCenter, "⬇")
        p.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.PRI), 1))
        p.drawText(QRectF(0, cy + 12, W, 16), Qt.AlignmentFlag.AlignCenter, "Release to load")

    def _paint_file(self, p, W, H):
        path = Path(self._z._current_file)
        cat  = _file_category(path)
        icon, icon_col = _FILE_ICONS.get(cat, _FILE_ICONS["unknown"])
        size_str = _fmt_size(path.stat().st_size)
        ext_str  = path.suffix.upper().lstrip(".") or "FILE"

        block_x, block_w = 10, 60
        p.setFont(QFont("Segoe UI Emoji", 22) if _OS == "Windows" else QFont("Arial", 22))
        p.setPen(QPen(qcol(icon_col), 1))
        p.drawText(QRectF(block_x, 0, block_w, H), Qt.AlignmentFlag.AlignCenter, icon)

        tx = block_x + block_w + 6
        tw = W - tx - 38

        p.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.WHITE), 1))
        name = path.name if len(path.name) <= 34 else path.name[:31] + "..."
        p.drawText(QRectF(tx, H * 0.18, tw, 16),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)

        p.setFont(QFont("Courier New", 7))
        p.setPen(QPen(qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(tx, H * 0.18 + 18, tw, 14),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   f"{ext_str}  ·  {size_str}")

        p.setFont(QFont("Courier New", 6))
        p.setPen(QPen(qcol("#1e5c6a"), 1))
        par = str(path.parent)
        if len(par) > 42: par = "…" + par[-41:]
        p.drawText(QRectF(tx, H * 0.18 + 34, tw, 12),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, par)

        p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.RED, 180), 1))
        p.drawText(QRectF(W - 34, 0, 28, H), Qt.AlignmentFlag.AlignCenter, "✕")

    def mousePressEvent(self, e):
        z = self._z
        if z._current_file and e.pos().x() > self.width() - 34:
            z.clear_file()
        else:
            z.mousePressEvent(e)


class SetupOverlay(QWidget):
    done = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            SetupOverlay {{
                background: rgba(0, 6, 10, 245);
                border: 1px solid {C.BORDER_B};
                border-radius: 6px;
            }}
        """)

        detected = {"darwin": "mac", "windows": "windows"}.get(
            _OS.lower(), "linux"
        )
        self._sel_os = detected

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 22, 30, 22)
        layout.setSpacing(8)

        def _lbl(txt, font_size=9, bold=False, color=C.PRI,
                 align=Qt.AlignmentFlag.AlignCenter):
            w = QLabel(txt)
            w.setAlignment(align)
            w.setFont(QFont("Courier New", font_size,
                            QFont.Weight.Bold if bold else QFont.Weight.Normal))
            w.setStyleSheet(f"color: {color}; background: transparent;")
            return w

        layout.addWidget(_lbl("◈  INITIALISATION REQUIRED", 13, True))
        layout.addWidget(_lbl("Configure J.A.R.V.I.S. before first boot.", 9, color=C.PRI_DIM))
        layout.addSpacing(6)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER};"); layout.addWidget(sep)
        layout.addSpacing(4)

        layout.addWidget(_lbl("GEMINI API KEY", 8, color=C.TEXT_DIM,
                               align=Qt.AlignmentFlag.AlignLeft))
        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setPlaceholderText("AIza…")
        self._key_input.setFont(QFont("Courier New", 10))
        self._key_input.setFixedHeight(32)
        self._key_input.setStyleSheet(f"""
            QLineEdit {{
                background: #000d12; color: {C.TEXT};
                border: 1px solid {C.BORDER}; border-radius: 3px; padding: 4px 8px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
        """)
        layout.addWidget(self._key_input)
        layout.addSpacing(8)

        layout.addWidget(_lbl("OPENROUTER API KEY", 8, color=C.TEXT_DIM,
                       align=Qt.AlignmentFlag.AlignLeft))
        self._or_input = QLineEdit()
        self._or_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._or_input.setPlaceholderText("sk-or-…")
        self._or_input.setFont(QFont("Courier New", 10))
        self._or_input.setFixedHeight(32)
        self._or_input.setStyleSheet(f"""
            QLineEdit {{
                background: #000d12; color: {C.TEXT};
                border: 1px solid {C.BORDER}; border-radius: 3px; padding: 4px 8px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.ACC2}; }}
        """)
        layout.addWidget(self._or_input)

        layout.addSpacing(12)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {C.BORDER};"); layout.addWidget(sep2)
        layout.addSpacing(4)

        layout.addWidget(_lbl("OPERATING SYSTEM", 8, color=C.TEXT_DIM,
                               align=Qt.AlignmentFlag.AlignLeft))
        det_name = {"windows": "Windows", "mac": "macOS", "linux": "Linux"}[detected]
        layout.addWidget(_lbl(f"Auto-detected: {det_name}", 8, color=C.ACC2,
                               align=Qt.AlignmentFlag.AlignLeft))

        os_row = QHBoxLayout(); os_row.setSpacing(6)
        self._os_btns: dict[str, QPushButton] = {}
        for key, label in [("windows","⊞  Windows"),("mac","  macOS"),("linux","🐧  Linux")]:
            btn = QPushButton(label)
            btn.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self._sel(k))
            os_row.addWidget(btn)
            self._os_btns[key] = btn
        layout.addLayout(os_row)
        self._sel(detected)
        layout.addSpacing(12)

        init_btn = QPushButton("▸  INITIALISE SYSTEMS")
        init_btn.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        init_btn.setFixedHeight(36)
        init_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        init_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 3px;
            }}
            QPushButton:hover {{
                background: {C.PRI_GHO}; border: 1px solid {C.PRI};
            }}
        """)
        init_btn.clicked.connect(self._submit)
        layout.addWidget(init_btn)

    def _sel(self, key: str):
        self._sel_os = key
        pal = {"windows":(C.PRI,"#001a22"),"mac":(C.ACC2,"#1a1400"),"linux":(C.GREEN,"#001a0d")}
        for k, btn in self._os_btns.items():
            if k == key:
                fg, bg = pal[k]
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {fg}; color: {bg};
                        border: none; border-radius: 3px; font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: #000d12; color: {C.TEXT_DIM};
                        border: 1px solid {C.BORDER}; border-radius: 3px;
                    }}
                    QPushButton:hover {{ color: {C.TEXT}; border: 1px solid {C.BORDER_B}; }}
                """)

    def _submit(self):
        key = self._key_input.text().strip()
        or_key = self._or_input.text().strip()
        if not key:
            self._key_input.setStyleSheet(
                self._key_input.styleSheet() +
                f" QLineEdit {{ border: 1px solid {C.RED}; }}"
            )
            return
        # OpenRouter key is optional
        self.done.emit(key, or_key, self._sel_os)


class MainWindow(QMainWindow):
    _log_sig   = pyqtSignal(str)
    _state_sig = pyqtSignal(str)
    _tool_sig  = pyqtSignal(str, str)
    _thought_sig = pyqtSignal(str)
    _intent_sig = pyqtSignal(str, str)
    _timeline_sig = pyqtSignal(str)
    _clear_thought_sig = pyqtSignal()
    _motherbot_event_sig = pyqtSignal(str)
    _wm_update_sig = pyqtSignal(str, list)   # world-monitor: (category, items)
    _wm_sit_sig = pyqtSignal(str, str)       # world-monitor situation: (weather, outlook)

    def __init__(self, face_path: str):
        super().__init__()
        self.setWindowTitle("Muhammad's J.A.R.V.I.S")
        self.setMinimumSize(_MIN_W, _MIN_H)
        self.resize(_DEFAULT_W, _DEFAULT_H)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width()  - _DEFAULT_W) // 2,
            (screen.height() - _DEFAULT_H) // 2,
        )

        self.on_text_command  = None
        self._muted           = False
        self._current_file: str | None = None

        central = QWidget()
        central.setStyleSheet(f"background: {C.BG};")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._left_panel = self._build_left_panel()
        body.addWidget(self._left_panel, stretch=0)

        self.hud = HudCanvas(face_path)
        self.hud.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        body.addWidget(self.hud, stretch=5)

        self._right_panel = self._build_right_panel()
        body.addWidget(self._right_panel, stretch=0)

        root.addLayout(body, stretch=1)
        root.addWidget(self._build_footer())

        self._clock_tmr = QTimer(self)
        self._clock_tmr.timeout.connect(self._tick_clock)
        self._clock_tmr.start(1000)
        self._tick_clock()

        # Metrik güncelleme timer'ı
        self._metric_tmr = QTimer(self)
        self._metric_tmr.timeout.connect(self._update_metrics)
        self._metric_tmr.start(2000)
        self._update_metrics()

        self._log_sig.connect(self._log.append_log)
        self._state_sig.connect(self._apply_state)
        self._tool_sig.connect(self.set_tool_state)
        self._thought_sig.connect(self._add_thought)
        self._intent_sig.connect(self._update_intent)
        self._timeline_sig.connect(self._add_timeline_event)
        self._clear_thought_sig.connect(self._clear_thoughts)
        self._motherbot_event_sig.connect(self._handle_motherbot_event)
        self._wm_update_sig.connect(self._apply_world_monitor)
        self._wm_sit_sig.connect(self._apply_situation)

        self._overlay: SetupOverlay | None = None
        self._ready = self._check_config()
        if not self._ready:
            self._show_setup()

        sc_mute = QShortcut(QKeySequence("F4"), self)
        sc_mute.activated.connect(self._toggle_mute)
        sc_full = QShortcut(QKeySequence("F11"), self)
        sc_full.activated.connect(self._toggle_fullscreen)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._overlay and self._overlay.isVisible():
            ow, oh = 460, 390
            cw = self.centralWidget()
            self._overlay.setGeometry(
                (cw.width()  - ow) // 2,
                (cw.height() - oh) // 2,
                ow, oh,
            )

    def _update_metrics(self):
        snap = _metrics.snapshot()

        # CPU
        cpu = snap["cpu"]
        self._bar_cpu.set_value(cpu, f"{cpu:.0f}%")

        # MEM
        mem = snap["mem"]
        self._bar_mem.set_value(mem, f"{mem:.0f}%")

        # NET
        net = snap["net"]
        if net < 1.0:
            net_str = f"{net*1024:.0f}KB/s"
        else:
            net_str = f"{net:.1f}MB/s"
        net_pct = min(100, net * 10)  # 10 MB/s = %100
        self._bar_net.set_value(net_pct, net_str)

        # GPU
        gpu = snap["gpu"]
        if gpu >= 0:
            self._bar_gpu.set_value(gpu, f"{gpu:.0f}%")
        else:
            self._bar_gpu.set_value(0, "N/A")

        # TMP
        tmp = snap["tmp"]
        if tmp >= 0:
            tmp_pct = min(100, (tmp / 100) * 100)
            self._bar_tmp.set_value(tmp_pct, f"{tmp:.0f}°C")
        else:
            self._bar_tmp.set_value(0, "N/A")

        try:
            boot_t  = psutil.boot_time()
            elapsed = time.time() - boot_t
            h = int(elapsed // 3600)
            m = int((elapsed % 3600) // 60)
            self._uptime_lbl.setText(f"UP  {h:02d}:{m:02d}")
        except Exception:
            self._uptime_lbl.setText("UP  --:--")

        try:
            proc_count = len(psutil.pids())
            self._proc_lbl.setText(f"PROC  {proc_count}")
        except Exception:
            self._proc_lbl.setText("PROC  --")

        # --- PC DIAGNOSTICS: flag real problems (where/what is wrong) ---
        try:
            problems = []
            if cpu >= 90:
                problems.append(f"CPU critical {cpu:.0f}%")
            elif cpu >= 75:
                problems.append(f"CPU high {cpu:.0f}%")
            if mem >= 90:
                problems.append(f"RAM critical {mem:.0f}%")
            elif mem >= 80:
                problems.append(f"RAM high {mem:.0f}%")
            try:
                disk = psutil.disk_usage("C:\\").percent
                if disk >= 92:
                    problems.append(f"Disk C: full {disk:.0f}%")
                elif disk >= 85:
                    problems.append(f"Disk C: low {disk:.0f}%")
            except Exception:
                pass
            if tmp is not None and tmp >= 85:
                problems.append(f"Temp hot {tmp:.0f}°C")
            svc = snap.get("services", {})
            down = [n for k, n in (
                ("ollama", "Ollama"), ("odysseus", "Odysseus"), ("gateway", "Gateway"),
                ("ts_jarvis", "TS-Jarvis"), ("backend", "Studio-BE"),
                ("frontend", "Studio-FE"), ("wa_forwarder", "WhatsApp"),
            ) if not svc.get(k, False)]
            if down:
                problems.append("Down: " + ", ".join(down))

            if not problems:
                self._diag_lbl.setText("● ALL SYSTEMS NOMINAL")
                self._diag_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent; border: none;")
            else:
                crit = any("critical" in p or "full" in p for p in problems)
                col = C.RED if crit else C.ACC2
                self._diag_lbl.setText("⚠ " + "\n⚠ ".join(problems))
                self._diag_lbl.setStyleSheet(f"color: {col}; background: transparent; border: none;")
        except Exception:
            pass

        # Update services status labels
        try:
            services = snap.get("services", {})
            for s_id, status_lbl in self.service_labels.items():
                is_running = services.get(s_id, False)
                if is_running:
                    status_lbl.setText("● ONLINE")
                    status_lbl.setStyleSheet(f"color: {C.GREEN}; border: none;")
                else:
                    status_lbl.setText("○ OFFLINE")
                    status_lbl.setStyleSheet(f"color: {C.RED}; border: none;")
        except Exception:
            pass

        # Update live WhatsApp connection badge (gateway + forwarder = linked)
        try:
            svc = snap.get("services", {})
            prt = snap.get("ports", {})
            gw = bool(svc.get("gateway") or prt.get("gateway"))
            fwd = bool(svc.get("wa_forwarder"))
            if gw and fwd:
                wa_txt, wa_col = "WHATSAPP\n● LINKED", C.GREEN
            elif gw or fwd:
                wa_txt, wa_col = "WHATSAPP\n◐ PARTIAL", C.PRI
            else:
                wa_txt, wa_col = "WHATSAPP\n○ OFFLINE", C.RED
            self._wa_badge.setText(wa_txt)
            self._wa_badge.setStyleSheet(
                f"color: {wa_col}; background: {C.PANEL2};"
                f"border: 1px solid {C.BORDER_A}; border-radius: 3px; padding: 4px;"
            )
        except Exception:
            pass

        # Update ports visualization
        try:
            ports = snap.get("ports", {})
            ports_text = (
                f"● PORT 11434 (Ollama)    : {'ACTIVE' if ports.get('ollama') else 'INACTIVE'}\n"
                f"● PORT 7000  (Odysseus)  : {'ACTIVE' if ports.get('odysseus') else 'INACTIVE'}\n"
                f"● PORT 27017 (MongoDB)   : {'ACTIVE' if ports.get('mongodb') else 'INACTIVE'}\n"
                f"● PORT 18789 (Gateway)   : {'ACTIVE' if ports.get('gateway') else 'INACTIVE'}\n"
                f"● PORT 3142  (TS Jarvis) : {'ACTIVE' if ports.get('ts_jarvis') else 'INACTIVE'}\n"
                f"● PORT 3000  (Studio Web): {'ACTIVE' if ports.get('frontend') else 'INACTIVE'}"
            )
            self.ports_widget.setPlainText(ports_text)
        except Exception:
            pass


    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(54)
        w.setStyleSheet(f"background: {C.DARK}; border-bottom: 1px solid {C.BORDER_B};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 0, 16, 0)

        def _badge(txt, color=C.TEXT_MED):
            l = QLabel(txt)
            l.setFont(QFont("Courier New", 8))
            l.setStyleSheet(f"color: {color}; background: transparent;")
            return l

        lay.addWidget(_badge("MUHAMMAD'S JARVIS", C.PRI))
        lay.addStretch()

        mid = QVBoxLayout(); mid.setSpacing(1)
        title = QLabel("J.A.R.V.I.S")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Courier New", 17, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        mid.addWidget(title)
        sub = QLabel("Just A Rather Very Intelligent System")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setFont(QFont("Courier New", 7))
        sub.setStyleSheet(f"color: {C.PRI_DIM}; background: transparent;")
        mid.addWidget(sub)
        lay.addLayout(mid)
        lay.addStretch()

        right_col = QVBoxLayout(); right_col.setSpacing(2)
        self._clock_lbl = QLabel("00:00:00")
        self._clock_lbl.setFont(QFont("Courier New", 14, QFont.Weight.Bold))
        self._clock_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        self._clock_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self._clock_lbl)
        self._date_lbl = QLabel("")
        self._date_lbl.setFont(QFont("Courier New", 7))
        self._date_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        self._date_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self._date_lbl)
        lay.addLayout(right_col)
        return w

    def _tick_clock(self):
        self._clock_lbl.setText(time.strftime("%H:%M:%S"))
        self._date_lbl.setText(time.strftime("%a %d %b %Y"))

    def _build_left_panel(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(_LEFT_W)
        w.setStyleSheet(f"background: {C.DARK}; border-right: 1px solid {C.BORDER};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 10, 8, 10)
        lay.setSpacing(6)

        hdr = QLabel("◈ SYS MONITOR")
        hdr.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {C.PRI}; background: transparent; "
                          f"border-bottom: 1px solid {C.BORDER}; padding-bottom: 4px;")
        lay.addWidget(hdr)
        lay.addSpacing(2)

        self._bar_cpu = MetricBar("CPU", C.PRI)
        self._bar_mem = MetricBar("MEM", C.ACC2)
        self._bar_net = MetricBar("NET", C.GREEN)
        self._bar_gpu = MetricBar("GPU", C.ACC)
        self._bar_tmp = MetricBar("TMP", "#ff6688")

        for bar in [self._bar_cpu, self._bar_mem, self._bar_net,
                    self._bar_gpu, self._bar_tmp]:
            lay.addWidget(bar)

        lay.addSpacing(4)

        # --- PC DIAGNOSTICS / PROBLEM RADAR ---
        diag_hdr = QLabel("◈ DIAGNOSTICS")
        diag_hdr.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        diag_hdr.setStyleSheet(f"color: {C.PRI}; background: transparent; "
                               f"border-bottom: 1px solid {C.BORDER}; padding-bottom: 3px;")
        lay.addWidget(diag_hdr)

        diag_panel = QWidget()
        diag_panel.setStyleSheet(f"background: {C.PANEL2}; border: 1px solid {C.BORDER}; border-radius: 4px;")
        diag_lay = QVBoxLayout(diag_panel)
        diag_lay.setContentsMargins(6, 5, 6, 5)
        diag_lay.setSpacing(1)
        self._diag_lbl = QLabel("● SCANNING…")
        self._diag_lbl.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        self._diag_lbl.setWordWrap(True)
        self._diag_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; border: none;")
        diag_lay.addWidget(self._diag_lbl)
        lay.addWidget(diag_panel)

        lay.addSpacing(4)

        info_panel = QWidget()
        info_panel.setStyleSheet(
            f"background: {C.PANEL2}; border: 1px solid {C.BORDER}; border-radius: 4px;"
        )
        ip_lay = QVBoxLayout(info_panel)
        ip_lay.setContentsMargins(6, 5, 6, 5)
        ip_lay.setSpacing(3)

        self._uptime_lbl = QLabel("UP  --:--")
        self._uptime_lbl.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self._uptime_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent; border: none;")
        ip_lay.addWidget(self._uptime_lbl)

        self._proc_lbl = QLabel("PROC  --")
        self._proc_lbl.setFont(QFont("Courier New", 8))
        self._proc_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
        ip_lay.addWidget(self._proc_lbl)

        os_name = {"Windows": "WIN", "Darwin": "macOS", "Linux": "LINUX"}.get(_OS, _OS.upper())
        os_lbl = QLabel(f"OS  {os_name}")
        os_lbl.setFont(QFont("Courier New", 8))
        os_lbl.setStyleSheet(f"color: {C.ACC2}; background: transparent; border: none;")
        ip_lay.addWidget(os_lbl)

        lay.addWidget(info_panel)
        lay.addStretch()

        for txt, col in [
            ("AI CORE\nACTIVE",     C.GREEN),
            ("SEC\nCLEARED",        C.PRI),
        ]:
            lbl = QLabel(txt)
            lbl.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                f"color: {col}; background: {C.PANEL2};"
                f"border: 1px solid {C.BORDER_A}; border-radius: 3px; padding: 4px;"
            )
            lay.addWidget(lbl)

        # Live WhatsApp connection status badge (updated by the motherbot refresh loop).
        self._wa_badge = QLabel("WHATSAPP\n○ CHECKING")
        self._wa_badge.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        self._wa_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._wa_badge.setStyleSheet(
            f"color: {C.TEXT_DIM}; background: {C.PANEL2};"
            f"border: 1px solid {C.BORDER_A}; border-radius: 3px; padding: 4px;"
        )
        lay.addWidget(self._wa_badge)

        return w
    def _build_right_panel(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(_RIGHT_W)
        w.setStyleSheet(f"background: {C.DARK}; border-left: 1px solid {C.BORDER};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {C.BORDER};
                background: {C.BG};
            }}
            QTabBar::tab {{
                background: {C.PANEL};
                color: {C.TEXT_DIM};
                border: 1px solid {C.BORDER};
                border-bottom: none;
                padding: 6px 14px;
                font-family: 'Courier New';
                font-size: 8px;
                font-weight: bold;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background: {C.PANEL2};
                color: {C.PRI};
                border: 1px solid {C.PRI};
                border-bottom: none;
            }}
            QTabBar::tab:hover {{
                color: {C.WHITE};
            }}
        """)

        # --- HUD Tab ---
        hud_tab = QWidget()
        hud_lay = QVBoxLayout(hud_tab)
        hud_lay.setContentsMargins(6, 6, 6, 6)
        hud_lay.setSpacing(6)

        # 1. Intent interpretation
        intent_box = QGroupBox("◈ INTENT INTERPRETATION")
        intent_box.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        intent_box.setStyleSheet(f"""
            QGroupBox {{
                color: {C.PRI};
                border: 1px solid {C.BORDER};
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 5px;
                background: {C.PANEL};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 3px;
            }}
        """)
        intent_lay = QVBoxLayout(intent_box)
        intent_lay.setContentsMargins(6, 6, 6, 6)
        intent_lay.setSpacing(4)

        self._lbl_user_input = QLabel("USER INPUT: (Listening...)")
        self._lbl_user_input.setFont(QFont("Courier New", 8))
        self._lbl_user_input.setStyleSheet(f"color: {C.WHITE};")
        self._lbl_user_input.setWordWrap(True)
        intent_lay.addWidget(self._lbl_user_input)

        self._lbl_interpretation = QLabel("INTERPRETATION: Waiting for input...")
        self._lbl_interpretation.setFont(QFont("Courier New", 8))
        self._lbl_interpretation.setStyleSheet(f"color: {C.TEXT_MED};")
        self._lbl_interpretation.setWordWrap(True)
        intent_lay.addWidget(self._lbl_interpretation)
        hud_lay.addWidget(intent_box, stretch=0)

        # 2. Cognitive Thinking Stream
        thought_box = QGroupBox("◈ COGNITIVE THINKING STREAM")
        thought_box.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        thought_box.setStyleSheet(f"""
            QGroupBox {{
                color: {C.ACC2};
                border: 1px solid {C.BORDER};
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 5px;
                background: {C.PANEL};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 3px;
            }}
        """)
        thought_lay = QVBoxLayout(thought_box)
        thought_lay.setContentsMargins(4, 4, 4, 4)

        self._thought_text = QTextEdit()
        self._thought_text.setReadOnly(True)
        self._thought_text.setFont(QFont("Courier New", 8))
        self._thought_text.setStyleSheet(f"""
            QTextEdit {{
                background: #000a0f;
                color: {C.ACC2};
                border: none;
                padding: 4px;
            }}
        """)
        thought_lay.addWidget(self._thought_text)
        hud_lay.addWidget(thought_box, stretch=3)

        # 3. Execution flow timeline
        flow_box = QGroupBox("◈ SYSTEM EXECUTION FLOW")
        flow_box.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        flow_box.setStyleSheet(f"""
            QGroupBox {{
                color: {C.GREEN};
                border: 1px solid {C.BORDER};
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 5px;
                background: {C.PANEL};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 3px;
            }}
        """)
        flow_lay = QVBoxLayout(flow_box)
        flow_lay.setContentsMargins(4, 4, 4, 4)

        self._flow_list = QListWidget()
        self._flow_list.setFont(QFont("Courier New", 8))
        self._flow_list.setStyleSheet(f"""
            QListWidget {{
                background: #000a0f;
                color: {C.TEXT};
                border: none;
                padding: 4px;
            }}
        """)
        flow_lay.addWidget(self._flow_list)
        hud_lay.addWidget(flow_box, stretch=3)

        console_tab = QWidget()
        console_lay = QVBoxLayout(console_tab)
        console_lay.setContentsMargins(6, 6, 6, 6)
        console_lay.setSpacing(6)

        def _sec(txt):
            l = QLabel(f"▸ {txt}")
            l.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
            l.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
            return l

        console_lay.addWidget(_sec("ACTIVITY LOG"))
        self._log = LogWidget()
        console_lay.addWidget(self._log, stretch=1)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER}; margin: 2px 0;")
        console_lay.addWidget(sep)

        console_lay.addWidget(_sec("FILE UPLOAD"))
        self._drop_zone = FileDropZone()
        self._drop_zone.file_selected.connect(self._on_file_selected)
        console_lay.addWidget(self._drop_zone)

        self._file_hint = QLabel("No file loaded — drop or click above to upload")
        self._file_hint.setFont(QFont("Courier New", 7))
        self._file_hint.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        self._file_hint.setWordWrap(True)
        console_lay.addWidget(self._file_hint)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {C.BORDER}; margin: 2px 0;")
        console_lay.addWidget(sep2)

        console_lay.addWidget(_sec("COMMAND INPUT"))
        console_lay.addLayout(self._build_input_row())

        self._mute_btn = QPushButton("🎙  MICROPHONE ACTIVE")
        self._mute_btn.setFixedHeight(30)
        self._mute_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self._mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mute_btn.clicked.connect(self._toggle_mute)
        self._style_mute_btn()
        console_lay.addWidget(self._mute_btn)

        fs_btn = QPushButton("⛶  FULLSCREEN  [F11]")
        fs_btn.setFixedHeight(26)
        fs_btn.setFont(QFont("Courier New", 7))
        fs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fs_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 3px;
            }}
            QPushButton:hover {{
                color: {C.PRI}; border: 1px solid {C.BORDER_B};
            }}
        """)
        fs_btn.clicked.connect(self._toggle_fullscreen)
        console_lay.addWidget(fs_btn)

        brain_tab = QWidget()
        brain_lay = QVBoxLayout(brain_tab)
        brain_lay.setContentsMargins(6, 6, 6, 6)
        brain_lay.setSpacing(6)

        brain_lay.addWidget(_sec("MEMORY REGISTRY"))
        self._mem_list = QListWidget()
        self._mem_list.setFont(QFont("Courier New", 8))
        self._mem_list.setStyleSheet(f"""
            QListWidget {{
                background: {C.PANEL};
                color: {C.GREEN};
                border: 1px solid {C.BORDER};
                border-radius: 4px;
                padding: 4px;
            }}
        """)
        brain_lay.addWidget(self._mem_list, stretch=2)

        brain_lay.addWidget(_sec("ACTIVE GOALS / TASKS"))
        self._task_list = QListWidget()
        self._task_list.setFont(QFont("Courier New", 8))
        self._task_list.setStyleSheet(f"""
            QListWidget {{
                background: {C.PANEL};
                color: {C.PRI};
                border: 1px solid {C.BORDER};
                border-radius: 4px;
                padding: 4px;
            }}
        """)
        brain_lay.addWidget(self._task_list, stretch=1)

        brain_lay.addWidget(_sec("AUTOMATED TOOLS MATRIX"))
        self._tools_widget = QWidget()
        self._tools_widget.setStyleSheet(f"background: {C.PANEL2}; border: 1px solid {C.BORDER}; border-radius: 4px;")
        tools_grid = QGridLayout(self._tools_widget)
        tools_grid.setContentsMargins(6, 6, 6, 6)
        tools_grid.setSpacing(4)
        
        self.tool_labels = {}
        tool_names = [
            ("open_app", "App Opener"), ("weather_report", "Weather"), ("browser_control", "Browser"),
            ("file_controller", "Files"), ("send_message", "WhatsApp"), ("reminder", "Reminder"),
            ("youtube_video", "YouTube"), ("file_processor", "DocProc"), ("screen_process", "Vision"),
            ("code_helper", "Coder"), ("dev_agent", "DevAgent"), ("agent_task", "Planner"),
            ("web_search", "Search"), ("computer_control", "OS Control"), ("cmd_control", "PowerShell")
        ]
        
        for idx, (t_id, t_name) in enumerate(tool_names):
            row = idx // 3
            col = idx % 3
            lbl = QLabel(t_name)
            lbl.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"""
                QLabel {{
                    color: {C.TEXT_DIM};
                    background: {C.PANEL};
                    border: 1px solid {C.BORDER_A};
                    border-radius: 2px;
                    padding: 3px;
                }}
            """)
            tools_grid.addWidget(lbl, row, col)
            self.tool_labels[t_id] = lbl
            
        brain_lay.addWidget(self._tools_widget, stretch=2)

        self.tabs.addTab(hud_tab, "HUD")
        self.tabs.addTab(console_tab, "CONSOLE")
        self.tabs.addTab(brain_tab, "BRAIN CORE")

        # --- MOTHERBOT Tab ---
        motherbot_tab = QWidget()
        motherbot_lay = QVBoxLayout(motherbot_tab)
        motherbot_lay.setContentsMargins(6, 6, 6, 6)
        motherbot_lay.setSpacing(6)

        motherbot_lay.addWidget(_sec("MOTHERBOT CORE SERVICES"))
        
        self.services_widget = QWidget()
        self.services_widget.setStyleSheet(f"background: {C.PANEL2}; border: 1px solid {C.BORDER}; border-radius: 4px;")
        services_grid = QGridLayout(self.services_widget)
        services_grid.setContentsMargins(6, 6, 6, 6)
        services_grid.setSpacing(4)
        
        self.service_labels = {}
        service_names = [
            ("ollama", "Ollama Local LLM"),
            ("odysseus", "Odysseus AI Server"),
            ("gateway", "Moltbot Gateway"),
            ("ts_jarvis", "TS Jarvis Daemon"),
            ("backend", "AI Studio Backend"),
            ("frontend", "AI Studio Frontend"),
            ("wa_forwarder", "WhatsApp Forwarder"),
            ("hud_gui", "PyQt6 HUD GUI")
        ]
        
        for idx, (s_id, s_name) in enumerate(service_names):
            row = idx // 2
            col = idx % 2
            
            box = QFrame()
            box.setFrameShape(QFrame.Shape.Box)
            box.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER_A}; border-radius: 2px; padding: 4px;")
            box_lay = QVBoxLayout(box)
            box_lay.setContentsMargins(4, 4, 4, 4)
            box_lay.setSpacing(1)
            
            name_lbl = QLabel(s_name)
            name_lbl.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
            name_lbl.setStyleSheet(f"color: {C.TEXT_MED}; border: none;")
            box_lay.addWidget(name_lbl)
            
            status_lbl = QLabel("○ OFFLINE")
            status_lbl.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
            status_lbl.setStyleSheet(f"color: {C.RED}; border: none;")
            box_lay.addWidget(status_lbl)
            
            services_grid.addWidget(box, row, col)
            self.service_labels[s_id] = status_lbl
            
        motherbot_lay.addWidget(self.services_widget, stretch=2)

        # Add Telemetry info
        motherbot_lay.addWidget(_sec("NETWORK & CORE LISTENER PORTS"))
        self.ports_widget = QTextEdit()
        self.ports_widget.setReadOnly(True)
        self.ports_widget.setFont(QFont("Courier New", 7))
        self.ports_widget.setStyleSheet(f"background: #000a0f; color: {C.PRI}; border: 1px solid {C.BORDER}; border-radius: 4px; padding: 4px;")
        motherbot_lay.addWidget(self.ports_widget, stretch=1)

        # Controls Group
        motherbot_lay.addWidget(_sec("MOTHERBOT CORE ACTIONS"))
        self.controls_widget = QWidget()
        self.controls_widget.setStyleSheet(f"background: {C.PANEL2}; border: 1px solid {C.BORDER}; border-radius: 4px;")
        ctrl_lay = QHBoxLayout(self.controls_widget)
        ctrl_lay.setContentsMargins(4, 4, 4, 4)
        ctrl_lay.setSpacing(4)

        btn_onboard = QPushButton("ONBOARD")
        btn_health = QPushButton("HEALTH")
        btn_train = QPushButton("TRAIN")
        
        for btn in [btn_onboard, btn_health, btn_train]:
            btn.setFixedHeight(22)
            btn.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C.PANEL}; color: {C.TEXT};
                    border: 1px solid {C.BORDER}; border-radius: 2px;
                }}
                QPushButton:hover {{
                    background: {C.PRI_GHO}; color: {C.PRI}; border: 1px solid {C.PRI};
                }}
            """)
            ctrl_lay.addWidget(btn)
            
        btn_onboard.clicked.connect(lambda: self._run_motherbot_cmd("clawdbot onboard"))
        btn_health.clicked.connect(lambda: self._run_motherbot_cmd("clawdbot health"))
        btn_train.clicked.connect(lambda: self._run_motherbot_cmd("self_training"))
        
        motherbot_lay.addWidget(self.controls_widget, stretch=0)

        # Recent events
        motherbot_lay.addWidget(_sec("MOTHERBOT SYSTEM EVENTS"))
        self._motherbot_events = QListWidget()
        self._motherbot_events.setFont(QFont("Courier New", 7))
        self._motherbot_events.setStyleSheet(f"background: #000a0f; color: {C.TEXT_MED}; border: 1px solid {C.BORDER}; border-radius: 4px; padding: 4px;")
        motherbot_lay.addWidget(self._motherbot_events, stretch=2)

        self.tabs.addTab(motherbot_tab, "MOTHERBOT")

        # --- WORLD MONITOR Tab (worldmonitor integration) ---
        wm_tab = QWidget()
        wm_lay = QVBoxLayout(wm_tab)
        wm_lay.setContentsMargins(6, 6, 6, 6)
        wm_lay.setSpacing(6)

        wm_lay.addWidget(_sec("WORLD MONITOR — LIVE GLOBAL INTELLIGENCE"))

        # Situation panel: Islamabad weather + AI world outlook
        sit_panel = QWidget()
        sit_panel.setStyleSheet(f"background: {C.PANEL2}; border: 1px solid {C.BORDER}; border-radius: 4px;")
        sit_lay = QVBoxLayout(sit_panel)
        sit_lay.setContentsMargins(8, 6, 8, 6)
        sit_lay.setSpacing(3)

        self._wm_weather = QLabel("⛅  Islamabad — loading weather…")
        self._wm_weather.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self._wm_weather.setStyleSheet(f"color: {C.ACC2}; background: transparent; border: none;")
        sit_lay.addWidget(self._wm_weather)

        self._wm_outlook = QLabel("Situation & outlook loading…")
        self._wm_outlook.setFont(QFont("Courier New", 8))
        self._wm_outlook.setWordWrap(True)
        self._wm_outlook.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
        sit_lay.addWidget(self._wm_outlook)

        wm_lay.addWidget(sit_panel, stretch=0)

        # Category buttons
        self._wm_cats = [
            ("world", "WORLD"), ("us", "US"), ("europe", "EUROPE"),
            ("middleeast", "MID-EAST"), ("asia", "ASIA"), ("finance", "FINANCE"),
            ("tech", "TECH"), ("ai", "AI"), ("defense", "DEFENSE"), ("crisis", "CRISIS"),
        ]
        cat_widget = QWidget()
        cat_widget.setStyleSheet(f"background: {C.PANEL2}; border: 1px solid {C.BORDER}; border-radius: 4px;")
        cat_grid = QGridLayout(cat_widget)
        cat_grid.setContentsMargins(4, 4, 4, 4)
        cat_grid.setSpacing(3)
        for idx, (cid, label) in enumerate(self._wm_cats):
            b = QPushButton(label)
            b.setFixedHeight(20)
            b.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"""
                QPushButton {{ background: {C.PANEL}; color: {C.TEXT};
                    border: 1px solid {C.BORDER}; border-radius: 2px; }}
                QPushButton:hover {{ background: {C.PRI_GHO}; color: {C.PRI}; border: 1px solid {C.PRI}; }}
            """)
            b.clicked.connect(lambda _=False, c=cid: self._wm_fetch(c))
            cat_grid.addWidget(b, idx // 5, idx % 5)
        wm_lay.addWidget(cat_widget, stretch=0)

        self._wm_status = QLabel("Select a category or ask Jarvis for a world brief.")
        self._wm_status.setFont(QFont("Courier New", 7))
        self._wm_status.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        wm_lay.addWidget(self._wm_status)

        self._wm_list = QListWidget()
        self._wm_list.setFont(QFont("Courier New", 8))
        self._wm_list.setWordWrap(True)
        self._wm_list.setStyleSheet(f"background: #000a0f; color: {C.PRI}; border: 1px solid {C.BORDER}; border-radius: 4px; padding: 4px;")
        self._wm_list.itemActivated.connect(self._wm_open_item)
        wm_lay.addWidget(self._wm_list, stretch=3)

        self.tabs.addTab(wm_tab, "WORLD MONITOR")

        self.tabs.setCurrentIndex(3)
        lay.addWidget(self.tabs)

        self._brain_refresh_tmr = QTimer(self)
        self._brain_refresh_tmr.timeout.connect(self._refresh_brain_tab)
        self._brain_refresh_tmr.start(4000)

        # World Monitor: initial load shortly after startup, then auto-refresh.
        QTimer.singleShot(6000, lambda: self._wm_fetch("world"))
        QTimer.singleShot(7000, self._wm_load_situation)
        self._wm_refresh_tmr = QTimer(self)
        self._wm_refresh_tmr.timeout.connect(lambda: (self._wm_fetch("world"), self._wm_load_situation()))
        self._wm_refresh_tmr.start(300000)  # every 5 minutes

        return w

    def _build_input_row(self) -> QHBoxLayout:
        row = QHBoxLayout(); row.setSpacing(5)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a command or question…")
        self._input.setFont(QFont("Courier New", 9))
        self._input.setFixedHeight(30)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: #000d14; color: {C.WHITE};
                border: 1px solid {C.BORDER}; border-radius: 3px; padding: 3px 7px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
        """)
        self._input.returnPressed.connect(self._send)
        row.addWidget(self._input)

        send = QPushButton("▸")
        send.setFixedSize(30, 30)
        send.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        send.setCursor(Qt.CursorShape.PointingHandCursor)
        send.setStyleSheet(f"""
            QPushButton {{
                background: {C.PANEL}; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 3px;
            }}
            QPushButton:hover {{ background: {C.PRI_GHO}; border: 1px solid {C.PRI}; }}
        """)
        send.clicked.connect(self._send)
        row.addWidget(send)
        return row

    def _build_footer(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(22)
        w.setStyleSheet(f"background: {C.DARK}; border-top: 1px solid {C.BORDER};")
        lay = QHBoxLayout(w); lay.setContentsMargins(14, 0, 14, 0)

        def _fl(txt, color=C.TEXT_MED):
            l = QLabel(txt); l.setFont(QFont("Courier New", 7))
            l.setStyleSheet(f"color: {color}; background: transparent;")
            return l

        lay.addWidget(_fl("[F4] Mute  ·  [F11] Fullscreen"))
        lay.addStretch()
        lay.addWidget(_fl("MUHAMMAD'S JARVIS  ·  CLASSIFIED"))
        lay.addStretch()
        lay.addWidget(_fl("© MUHAMMAD AI", C.PRI_DIM))
        return w

    def _on_file_selected(self, path: str):
        self._current_file = path
        p    = Path(path)
        cat  = _file_category(p)
        icon, _ = _FILE_ICONS.get(cat, _FILE_ICONS["unknown"])
        size = _fmt_size(p.stat().st_size)
        self._file_hint.setText(f"{icon}  {p.name}  ·  {size}  ·  Tell JARVIS what to do with it")
        self._log.append_log(f"FILE: {p.name} ({size}) loaded")
        if self.on_text_command:
            msg = (
                f"[FILE_UPLOADED] path={path} | name={p.name} | "
                f"type={p.suffix.lstrip('.')} | size={size} | "
                f"Briefly tell the user you can see the file '{p.name}' "
                f"({size}) has been uploaded and ask what they'd like to do with it."
            )
            threading.Thread(target=self.on_text_command, args=(msg,), daemon=True).start()

    def _toggle_mute(self):
        self._muted = not self._muted
        self.hud.muted = self._muted
        self._style_mute_btn()
        if self._muted:
            self._apply_state("MUTED")
            self._log.append_log("SYS: Microphone muted.")
        else:
            if self.hud.state.startswith("OFFLINE"):
                self._apply_state("OFFLINE_LISTENING")
            else:
                self._apply_state("LISTENING")
            self._log.append_log("SYS: Microphone active.")

    def _style_mute_btn(self):
        if self._muted:
            self._mute_btn.setText("🔇  MICROPHONE MUTED")
            self._mute_btn.setStyleSheet(f"""
                QPushButton {{
                    background: #140006; color: {C.MUTED_C};
                    border: 1px solid {C.MUTED_C}; border-radius: 3px;
                }}
            """)
        else:
            self._mute_btn.setText("🎙  MICROPHONE ACTIVE")
            self._mute_btn.setStyleSheet(f"""
                QPushButton {{
                    background: #00140a; color: {C.GREEN};
                    border: 1px solid {C.GREEN}; border-radius: 3px;
                }}
                QPushButton:hover {{ background: #001f10; }}
            """)

    def _send(self):
        txt = self._input.text().strip()
        if not txt: return
        self._input.clear()
        self._log.append_log(f"You: {txt}")
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(txt,), daemon=True).start()

    def _apply_state(self, state: str):
        self.hud.state    = state
        self.hud.speaking = (state == "SPEAKING" or state == "OFFLINE_SPEAKING")

    def _check_config(self) -> bool:
        if not API_FILE.exists(): return False
        try:
            d = json.loads(API_FILE.read_text(encoding="utf-8"))
            return (bool(d.get("gemini_api_key")) and
                    bool(d.get("os_system")))
        except Exception:
            return False

    def _show_setup(self):
        ov = SetupOverlay(self.centralWidget())
        cw = self.centralWidget()
        ow, oh = 460, 430
        ov.setGeometry(
            (cw.width()  - ow) // 2,
            (cw.height() - oh) // 2,
            ow, oh,
        )
        ov.done.connect(self._on_setup_done)
        ov.show()
        self._overlay = ov

    # Change signature:
    def _on_setup_done(self, key: str, or_key: str, os_name: str):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        API_FILE.write_text(
            json.dumps({
                "gemini_api_key":    key,
                "openrouter_api_key": or_key,
                "os_system":         os_name,
            }, indent=4),
            encoding="utf-8",
        )
        self._ready = True
        if self._overlay:
            self._overlay.hide()
            self._overlay = None
        self._apply_state("LISTENING")
        self._log.append_log(f"SYS: Initialised. OS={os_name.upper()}. JARVIS online.")

    def set_tool_state(self, tool_id: str, state: str):
        lbl = self.tool_labels.get(tool_id)
        if not lbl: return
        if state == "active":
            lbl.setStyleSheet(f"""
                QLabel {{
                    color: {C.WHITE};
                    background: {C.PRI_GHO};
                    border: 1px solid {C.PRI};
                    border-radius: 2px;
                    padding: 3px;
                }}
            """)
        elif state == "failed":
            lbl.setStyleSheet(f"""
                QLabel {{
                    color: {C.WHITE};
                    background: #1a0006;
                    border: 1px solid {C.RED};
                    border-radius: 2px;
                    padding: 3px;
                }}
            """)
        else:
            lbl.setStyleSheet(f"""
                QLabel {{
                    color: {C.TEXT_DIM};
                    background: {C.PANEL};
                    border: 1px solid {C.BORDER_A};
                    border-radius: 2px;
                    padding: 3px;
                }}
            """)

    def _refresh_brain_tab(self):
        try:
            from memory.memory_manager import load_memory
            mem = load_memory()
            self._mem_list.clear()
            for cat, items in mem.items():
                if isinstance(items, dict):
                    for k, v in items.items():
                        val = v.get("value", "") if isinstance(v, dict) else str(v)
                        if len(val) > 28: val = val[:26] + "..."
                        self._mem_list.addItem(f"[{cat.upper()}] {k}: {val}")
        except Exception:
            pass

        try:
            from agent.task_queue import get_queue
            tasks = get_queue().get_all_statuses()
            self._task_list.clear()
            if not tasks:
                self._task_list.addItem("No active system goals.")
            else:
                for t in tasks:
                    status_indicator = "●" if t["status"] == "running" else "○"
                    goal_text = t["goal"]
                    if len(goal_text) > 30: goal_text = goal_text[:28] + "..."
                    item = QListWidgetItem(f"{status_indicator} [{t['task_id']}] {goal_text} ({t['status'].upper()})")
                    st = t["status"]
                    if st == "running":
                        item.setForeground(QBrush(qcol(C.PRI)))
                    elif st in ("done", "completed", "success"):
                        item.setForeground(QBrush(qcol(C.GREEN)))
                    elif st in ("failed", "error"):
                        item.setForeground(QBrush(qcol(C.RED)))
                    else:
                        item.setForeground(QBrush(qcol(C.TEXT_MED)))
                    self._task_list.addItem(item)
        except Exception:
            pass

    def _handle_motherbot_event(self, text: str):
        t_str = time.strftime("[%H:%M:%S] ")
        item = QListWidgetItem(t_str + text)
        el = text.lower()
        if "error" in el or "failed" in el:
            item.setForeground(QBrush(qcol(C.RED)))
        elif "learned" in el or "success" in el or "complete" in el:
            item.setForeground(QBrush(qcol(C.GREEN)))
        elif "invoking" in el or "running" in el:
            item.setForeground(QBrush(qcol(C.PRI)))
        else:
            item.setForeground(QBrush(qcol(C.TEXT_MED)))
        self._motherbot_events.insertItem(0, item)
        if self._motherbot_events.count() > 50:
            self._motherbot_events.takeItem(50)

    # ---------------- WORLD MONITOR ----------------
    def update_world_monitor(self, category, items):
        """Thread-safe entry point the world_monitor tool calls from a worker thread."""
        try:
            self._wm_update_sig.emit(str(category), list(items or []))
        except Exception:
            pass

    def _wm_fetch(self, category: str):
        """Fetch headlines in a background thread, then update via signal."""
        try:
            self._wm_status.setText(f"Pulling live {category} intelligence…")
        except Exception:
            pass

        def _run():
            try:
                from actions.world_monitor import get_headlines
                items = get_headlines(category, 14)
            except Exception as e:
                items = []
                print(f"[WorldMonitor UI] fetch error: {e}")
            self._wm_update_sig.emit(category, items)

        threading.Thread(target=_run, daemon=True).start()

    def _apply_world_monitor(self, category: str, items: list):
        """Render headlines into the WORLD MONITOR list (runs on GUI thread)."""
        self._wm_list.clear()
        if not items:
            self._wm_status.setText(f"No fresh {category} headlines available.")
            return
        self._wm_status.setText(
            f"{category.upper()} — {len(items)} live headlines · updated {time.strftime('%H:%M:%S')}"
        )
        for it in items:
            src = it.get("source", "")
            title = it.get("title", "")
            item = QListWidgetItem(f"●  {title}\n     — {src}")
            item.setForeground(QBrush(qcol(C.PRI)))
            item.setData(Qt.ItemDataRole.UserRole, it.get("link", ""))
            self._wm_list.addItem(item)

    def _wm_open_item(self, item):
        link = item.data(Qt.ItemDataRole.UserRole)
        if link:
            try:
                import webbrowser
                webbrowser.open(link)
            except Exception:
                pass

    def _wm_load_situation(self):
        """Background-load Islamabad weather + world outlook into the situation panel."""
        def _run():
            weather_txt, outlook_txt = "⛅  Islamabad — weather unavailable", ""
            try:
                from actions.world_monitor import get_weather, get_situation_brief
                w = get_weather("Islamabad")
                if w:
                    weather_txt = (
                        f"⛅  ISLAMABAD  {w.get('temp_c','?')}°C "
                        f"(feels {w.get('feels_c','?')}°C) · {w.get('desc','')} · "
                        f"hum {w.get('humidity','?')}% · wind {w.get('wind_kph','?')}km/h"
                    )
                outlook_txt = get_situation_brief()
            except Exception as e:
                print(f"[WorldMonitor UI] situation error: {e}")
            self._wm_sit_sig.emit(weather_txt, outlook_txt)
        threading.Thread(target=_run, daemon=True).start()

    def _apply_situation(self, weather_txt: str, outlook_txt: str):
        if weather_txt:
            self._wm_weather.setText(weather_txt)
        if outlook_txt:
            self._wm_outlook.setText(outlook_txt)

    def _run_motherbot_cmd(self, command: str):
        self._motherbot_event_sig.emit(f"Invoking: {command}...")
        
        if command == "self_training":
            def _run():
                try:
                    from actions.self_training import run_self_training
                    res = run_self_training(limit=100)
                    for line in res.splitlines():
                        if line.strip():
                            self._motherbot_event_sig.emit(line)
                except Exception as e:
                    self._motherbot_event_sig.emit(f"Training failed: {e}")
            threading.Thread(target=_run, daemon=True).start()
            return

        def _run_sys():
            try:
                r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
                out = r.stdout.strip()
                err = r.stderr.strip()
                if out:
                    for line in out.splitlines():
                        if line.strip():
                            self._motherbot_event_sig.emit(line)
                if err:
                    for line in err.splitlines():
                        if line.strip():
                            self._motherbot_event_sig.emit(f"Error: {line}")
                self._motherbot_event_sig.emit(f"Command finished (Exit Code {r.returncode})")
            except Exception as e:
                self._motherbot_event_sig.emit(f"Failed to execute command: {e}")
        threading.Thread(target=_run_sys, daemon=True).start()

    def _add_thought(self, text: str):
        cur = self._thought_text.textCursor()
        cur.movePosition(cur.MoveOperation.End)
        cur.insertText(text)
        self._thought_text.setTextCursor(cur)
        self._thought_text.ensureCursorVisible()

    def _clear_thoughts(self):
        self._thought_text.clear()

    def _update_intent(self, user_input: str, interpretation: str):
        if user_input:
            self._lbl_user_input.setText(f"USER INPUT: {user_input}")
        if interpretation:
            self._lbl_interpretation.setText(f"INTERPRETED GOAL: {interpretation}")

    def _add_timeline_event(self, event_text: str):
        t_str = time.strftime("[%H:%M:%S] ")
        item = QListWidgetItem(t_str + event_text)
        el = event_text.lower()
        if "speech" in el or "you:" in el or "user" in el:
            item.setForeground(QBrush(qcol(C.WHITE)))
        elif "thought" in el:
            item.setForeground(QBrush(qcol(C.ACC2)))
        elif "tool running" in el or "tool: running" in el:
            item.setForeground(QBrush(qcol(C.ACC)))
        elif "success" in el or "finished" in el:
            item.setForeground(QBrush(qcol(C.GREEN)))
        elif "failed" in el or "error" in el:
            item.setForeground(QBrush(qcol(C.RED)))
        elif "memory" in el:
            item.setForeground(QBrush(qcol("#00ff88")))
        elif "task" in el:
            item.setForeground(QBrush(qcol("#cc44ff")))
        else:
            item.setForeground(QBrush(qcol(C.TEXT_MED)))
        self._flow_list.insertItem(0, item)
        if self._flow_list.count() > 50:
            self._flow_list.takeItem(50)

class _RootShim:
    def __init__(self, app: QApplication):
        self._app = app
    def mainloop(self):
        self._app.exec()
    def protocol(self, *_):
        pass


class JarvisUI:
    def __init__(self, face_path: str, size=None):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle("Fusion")
        self._win = MainWindow(face_path)
        self._win.show()
        self.root = _RootShim(self._app)

    @property
    def muted(self) -> bool:
        return self._win._muted

    @muted.setter
    def muted(self, v: bool):
        if v != self._win._muted:
            self._win._toggle_mute()

    @property
    def current_file(self) -> str | None:
        return self._win._drop_zone.current_file()

    @property
    def on_text_command(self):
        return self._win.on_text_command

    @on_text_command.setter
    def on_text_command(self, cb):
        self._win.on_text_command = cb

    def set_state(self, state: str):
        self._win._state_sig.emit(state)

    def set_tool_state(self, tool_id: str, state: str):
        self._win._tool_sig.emit(tool_id, state)

    def write_log(self, text: str):
        self._win._log_sig.emit(text)

    def write_thought(self, text: str):
        self._win._thought_sig.emit(text)

    def clear_thoughts(self):
        self._win._clear_thought_sig.emit()

    def update_intent(self, user_input: str, interpretation: str):
        self._win._intent_sig.emit(user_input, interpretation)

    def write_timeline(self, text: str):
        self._win._timeline_sig.emit(text)

    def wait_for_api_key(self):
        while not self._win._ready:
            time.sleep(0.1)

    def start_speaking(self):
        if self._win.hud.state.startswith("OFFLINE"):
            self.set_state("OFFLINE_SPEAKING")
        else:
            self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            if self._win.hud.state.startswith("OFFLINE"):
                self.set_state("OFFLINE_LISTENING")
            else:
                self.set_state("LISTENING")