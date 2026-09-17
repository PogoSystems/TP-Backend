import contextlib
import ctypes
from dataclasses import dataclass, field
from datetime import datetime
import gc
import os
from pathlib import Path
import sys
import time
import tracemalloc
from typing import Any, Dict, List, Optional

# Tipos Windows para lectura nativa de memoria del proceso
if sys.platform == "win32":
    from ctypes import wintypes

    class _PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]


def get_current_process_memory_mb() -> tuple[float, float]:
    """
    Retorna (working_set_mb, peak_working_set_mb).
    Intenta usar psutil si está disponible; de lo contrario, usa la API nativa de Windows (o getrusage en Unix).
    """
    try:
        import psutil  # type: ignore

        proc = psutil.Process(os.getpid())
        mem_info = proc.memory_info()
        rss_mb = mem_info.rss / (1024 * 1024)
        peak_mb = getattr(mem_info, "peak_wset", mem_info.rss) / (1024 * 1024)
        return rss_mb, peak_mb
    except ImportError:
        pass

    if sys.platform == "win32":
        try:
            pmc = _PROCESS_MEMORY_COUNTERS_EX()
            pmc.cb = ctypes.sizeof(_PROCESS_MEMORY_COUNTERS_EX)
            kernel32 = ctypes.windll.kernel32
            psapi = ctypes.windll.psapi
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            psapi.GetProcessMemoryInfo.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(_PROCESS_MEMORY_COUNTERS_EX),
                wintypes.DWORD,
            ]
            psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
            if psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
                rss_mb = pmc.WorkingSetSize / (1024 * 1024)
                peak_mb = pmc.PeakWorkingSetSize / (1024 * 1024)
                return rss_mb, peak_mb
        except Exception:
            pass

    # Fallback básico si ninguna API del SO está disponible
    return 0.0, 0.0


@dataclass
class StepMetric:
    step_number: int
    name: str
    duration_sec: float
    ram_start_mb: float
    ram_end_mb: float
    ram_delta_mb: float
    ram_peak_mb: float
    heap_peak_mb: float
    details: Dict[str, Any] = field(default_factory=dict)


class PipelineMemoryProfiler:
    """
    Orquestador de profiling para medir tiempo, memoria del sistema operativo (RAM / Working Set)
    y memoria del intérprete Python (heap tracemalloc) por cada etapa del pipeline.
    """

    def __init__(self, pipeline_name: str = "Pipeline RAG de Generación de Cuestionarios") -> None:
        self.pipeline_name = pipeline_name
        self.steps: List[StepMetric] = []
        self.results_meta: Dict[str, Any] = {}
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.initial_ram_mb: float = 0.0
        self.final_ram_mb: float = 0.0
        self.gc_released_ram_mb: Optional[float] = None
        self.gc_released_heap_mb: Optional[float] = None

    def start_profiling(self) -> None:
        """Inicia el monitoreo global."""
        if not tracemalloc.is_tracing():
            tracemalloc.start()
        self.start_time = time.perf_counter()
        self.initial_ram_mb, _ = get_current_process_memory_mb()

    def set_result_data(self, key: str, value: Any) -> None:
        """Registra metadatos adicionales del resultado (título, cantidad preguntas, etc.)."""
        self.results_meta[key] = value

    @contextlib.contextmanager
    def track_step(self, step_name: str, **kwargs: Any):
        """Context manager para medir una etapa o método individual."""
        step_idx = len(self.steps) + 1
        ram_start, _ = get_current_process_memory_mb()
        tracemalloc.reset_peak()
        t_start = time.perf_counter()

        yield

        t_end = time.perf_counter()
        ram_end, ram_peak = get_current_process_memory_mb()
        _, heap_peak_bytes = tracemalloc.get_traced_memory()

        duration = t_end - t_start
        delta_ram = ram_end - ram_start
        heap_peak_mb = heap_peak_bytes / (1024 * 1024)

        metric = StepMetric(
            step_number=step_idx,
            name=step_name,
            duration_sec=duration,
            ram_start_mb=ram_start,
            ram_end_mb=ram_end,
            ram_delta_mb=delta_ram,
            ram_peak_mb=max(ram_peak, ram_end),
            heap_peak_mb=heap_peak_mb,
            details=kwargs,
        )
        self.steps.append(metric)

    def evaluate_gc(self) -> None:
        """Prueba la efectividad de una recolección de basura explícita."""
        with self.track_step("Evaluación de Garbage Collection (gc.collect)"):
            ram_before, _ = get_current_process_memory_mb()
            heap_before, _ = tracemalloc.get_traced_memory()

            unreachable_objects = gc.collect()

            ram_after, _ = get_current_process_memory_mb()
            heap_after, _ = tracemalloc.get_traced_memory()

            self.gc_released_ram_mb = max(0.0, ram_before - ram_after)
            self.gc_released_heap_mb = max(0.0, (heap_before - heap_after) / (1024 * 1024))
            self.set_result_data("Objetos inalcanzables recolectados", unreachable_objects)

    def stop_profiling(self) -> None:
        """Detiene el monitoreo y consolida métricas finales."""
        self.end_time = time.perf_counter()
        self.final_ram_mb, _ = get_current_process_memory_mb()

    def generate_markdown_report(self, output_path: Optional[Path] = None) -> str:
        """Genera el reporte Markdown detallado y lo guarda en disco si se provee output_path."""
        total_duration = max(0.001, self.end_time - self.start_time)
        max_ram_peak = max([s.ram_peak_mb for s in self.steps], default=self.final_ram_mb)
        max_heap_peak = max([s.heap_peak_mb for s in self.steps], default=0.0)
        net_ram_delta = self.final_ram_mb - self.initial_ram_mb

        lines = [
            f"# Reporte de Benchmark: {self.pipeline_name}",
            "",
            f"- **Fecha y Hora:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
            f"- **Plataforma:** `{sys.platform.capitalize()}` (Python `{sys.version.split()[0]}`)",
            f"- **Proceso PID:** `{os.getpid()}`",
        ]

        if self.results_meta:
            lines.append("- **Metadatos de Ejecución:**")
            for k, v in self.results_meta.items():
                lines.append(f"  - **{k}:** `{v}`")

        lines.extend([
            "",
            "---",
            "",
            "## 1. Resumen Ejecutivo de Recursos",
            "",
            "| Métrica Global | Valor Medido | Observación |",
            "| :--- | :--- | :--- |",
            f"| **Tiempo Total de Ejecución** | **{total_duration:.2f} s** | Duración completa del pipeline |",
            f"| **RAM Inicial del Proceso** | **{self.initial_ram_mb:.2f} MB** | Estado base antes del pipeline |",
            f"| **RAM Final del Proceso** | **{self.final_ram_mb:.2f} MB** | Estado al finalizar todas las etapas |",
            f"| **Variación Neta de RAM (Δ Total)** | **{'+' if net_ram_delta >= 0 else ''}{net_ram_delta:.2f} MB** | Crecimiento residual del proceso |",
            f"| **Pico Máximo de RAM (Working Set)** | **{max_ram_peak:.2f} MB** | Consumo máximo de memoria física (SO + C/C++) |",
            f"| **Pico Máximo Heap Python** | **{max_heap_peak:.2f} MB** | Memoria máxima alojada en estructuras Python |",
            "",
            "---",
            "",
            "## 2. Desglose Detallado por Método / Etapa",
            "",
            "| # | Etapa / Método | Tiempo (s) | % Tiempo | RAM Inicio (MB) | RAM Fin (MB) | Δ RAM (MB) | Pico RAM (MB) | Heap Python Pico (MB) |",
            "| :-: | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: |",
        ])

        for s in self.steps:
            pct_time = (s.duration_sec / total_duration) * 100
            delta_sign = "+" if s.ram_delta_mb >= 0 else ""
            lines.append(
                f"| {s.step_number} | {s.name} | {s.duration_sec:.2f}s | {pct_time:.1f}% | "
                f"{s.ram_start_mb:.2f} | {s.ram_end_mb:.2f} | {delta_sign}{s.ram_delta_mb:.2f} | "
                f"{s.ram_peak_mb:.2f} | {s.heap_peak_mb:.2f} |"
            )

        # Análisis y diagnóstico de Garbage Collection
        lines.extend([
            "",
            "---",
            "",
            "## 3. Diagnóstico y Análisis de Garbage Collection",
            "",
        ])

        # Encontrar etapa más pesada en memoria y tiempo
        step_heaviest_ram = max(self.steps, key=lambda x: x.ram_peak_mb, default=None)
        step_slowest = max(self.steps, key=lambda x: x.duration_sec, default=None)

        if step_heaviest_ram:
            lines.append(
                f"- **Etapa con mayor consumo de memoria:** `{step_heaviest_ram.name}` "
                f"(Pico: `{step_heaviest_ram.ram_peak_mb:.2f} MB`, Δ: `{step_heaviest_ram.ram_delta_mb:+.2f} MB`)."
            )
        if step_slowest:
            lines.append(
                f"- **Etapa con mayor tiempo de CPU/I/O:** `{step_slowest.name}` "
                f"(`{step_slowest.duration_sec:.2f} s` representando el `{(step_slowest.duration_sec / total_duration) * 100:.1f}%` del total)."
            )

        if self.gc_released_ram_mb is not None:
            lines.append(
                f"- **Resultado de `gc.collect()` explícito:**\n"
                f"  - RAM del Proceso liberada: `{self.gc_released_ram_mb:.2f} MB`\n"
                f"  - Heap de Python liberado: `{self.gc_released_heap_mb:.2f} MB`"
            )

            if max_ram_peak >= 500.0:
                alert_type = "CAUTION"
                gc_verdict = (
                    f"🚨 **RIESGO CRÍTICO DE OOM (Out of Memory):**\n"
                    f"- El pico de RAM alcanzó **{max_ram_peak:.2f} MB**, sobrepasando el límite estándar de contenedores/servidores de **512 MB**.\n"
                    f"- En un entorno con 512 MB de RAM, este proceso activará el **OOM Killer** del sistema operativo y colapsará el servicio.\n"
                    f"- Como `gc.collect()` liberó solo **{self.gc_released_ram_mb:.2f} MB** (porque el 90%+ del consumo proviene del motor C/C++ de PyMuPDF y no del heap de Python), meter un Garbage Collector manual **NO resolverá este problema**.\n"
                    f"- **Acción requerida:** Optimizar la extracción nativa (ej. `fitz.TOOLS.store_shrink(100)`), descargar buffers intermedios, o dimensionar los servidores con mínimo **1 GB a 2 GB de RAM** si se procesan documentos concurrentes."
                )
            elif max_ram_peak >= 300.0:
                alert_type = "WARNING"
                gc_verdict = (
                    f"⚠️ **CONSUMO DE MEMORIA ELEVADO:**\n"
                    f"- El pico de RAM alcanzó **{max_ram_peak:.2f} MB**.\n"
                    f"- Aunque cabe en un contenedor de 512 MB si ejecuta una sola tarea aislada, generará **alta contención u OOM** si existen 2 o más workers concurrentes de Uvicorn/FastAPI procesando documentos en paralelo.\n"
                    f"- `gc.collect()` liberó **{self.gc_released_ram_mb:.2f} MB** en Python, confirmando que la mayor parte de la retención reside en C/C++.\n"
                    f"- **Recomendación:** Mantener workers dedicados con al menos 1 GB de RAM por proceso o procesar archivos en colas asíncronas."
                )
            elif self.gc_released_ram_mb > 25.0:
                alert_type = "WARNING"
                gc_verdict = (
                    f"⚠️ **SE RECOMIENDA GARBAGE COLLECTION EXPLÍCITO O SCOPING:**\n"
                    f"- El pipeline acumuló más de 25 MB ({self.gc_released_ram_mb:.2f} MB) en referencias cíclicas u objetos de Python intermedios.\n"
                    f"- Inyectar `gc.collect()` tras el chunking o la extracción es beneficioso para liberar memoria antes de pasar a la fase de LLM."
                )
            else:
                alert_type = "TIP"
                gc_verdict = (
                    f"✅ **EL PROCESO AGUANTA EFICIENTEMENTE SIN GC MANUAL:**\n"
                    f"- El pico de RAM (**{max_ram_peak:.2f} MB**) y el crecimiento residual (**{net_ram_delta:+.2f} MB**) son bajos y seguros.\n"
                    f"- El recolector generacional automático de Python y el conteo de referencias manejan el ciclo de vida sin necesidad de forzar `gc.collect()`."
                )
            lines.append(f"\n> [!{alert_type}]\n> **Veredicto Técnico de Infraestructura:**\n> {gc_verdict}\n")

        report_content = "\n".join(lines)

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report_content, encoding="utf-8")

        return report_content
