from dataclasses import dataclass
from typing import List, Tuple
import numpy as np

@dataclass
class ProcessingSettings:
    method: str = "automatic"
    threshold: int = 150
    denoise: int = 1
    close_gaps: int = 1
    min_area: int = 20
    simplify: float = 0.35
    invert: bool = False
    auto_crop: bool = True
    mode: str = "fill"
    width_mm: float = 100.0

@dataclass
class ProcessingResult:
    original_bgr: np.ndarray
    cropped_bgr: np.ndarray
    binary: np.ndarray
    vector_preview_bgr: np.ndarray
    contours: List[np.ndarray]
    open_paths: List[np.ndarray]
    geometry_paths: List[np.ndarray]
    hierarchy: np.ndarray | None
    image_size: Tuple[int, int]
    crop_rect: Tuple[int, int, int, int]
    warnings: List[str]
