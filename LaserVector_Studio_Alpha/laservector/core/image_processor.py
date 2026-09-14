
import cv2
import numpy as np
import math
from .models import ProcessingSettings, ProcessingResult

def _odd_kernel(value: int) -> int:
    value = max(0, int(value))
    return 0 if value == 0 else value * 2 + 1

def _darkness_map(image_bgr: np.ndarray) -> np.ndarray:
    """
    Detecta traços escuros sobre fundos claros, inclusive bege ou cinza.
    Compara cada pixel com uma estimativa suave do fundo local.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    background = cv2.GaussianBlur(gray, (0, 0), sigmaX=25, sigmaY=25)
    darkness = cv2.subtract(background, gray)
    darkness = cv2.normalize(darkness, None, 0, 255, cv2.NORM_MINMAX)
    return darkness

def _auto_crop(image_bgr: np.ndarray) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    darkness = _darkness_map(image_bgr)
    _, mask = cv2.threshold(
        darkness, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    mask = cv2.morphologyEx(
        mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)
    )

    points = cv2.findNonZero(mask)
    h, w = darkness.shape
    if points is None:
        return image_bgr.copy(), (0, 0, w, h)

    x, y, cw, ch = cv2.boundingRect(points)
    pad = max(12, int(max(cw, ch) * 0.06))
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(w, x + cw + pad)
    y2 = min(h, y + ch + pad)
    return image_bgr[y1:y2, x1:x2].copy(), (x1, y1, x2 - x1, y2 - y1)

def _remove_small_components(binary: np.ndarray, min_area: int) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
    output = np.zeros_like(binary)
    for idx in range(1, count):
        if stats[idx, cv2.CC_STAT_AREA] >= max(1, int(min_area)):
            output[labels == idx] = 255
    return output

def _prepare_gray(image_bgr: np.ndarray, denoise: int) -> np.ndarray:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    k = _odd_kernel(denoise)
    if k >= 3:
        gray = cv2.medianBlur(gray, k)
    return gray


def _score_binary(binary: np.ndarray) -> float:
    """
    Escolhe resultados que preservem a arte sem transformar o fundo inteiro em desenho.
    """
    coverage = np.count_nonzero(binary) / binary.size
    if coverage < 0.001 or coverage > 0.65:
        return -1e9

    count, _, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
    areas = stats[1:, cv2.CC_STAT_AREA] if count > 1 else np.array([])
    meaningful = areas[areas >= 8]

    if meaningful.size == 0:
        return -1e9

    # Favorece uma cobertura razoável e componentes significativos.
    target_coverage = 0.12
    coverage_score = -abs(coverage - target_coverage) * 80.0
    component_score = min(len(meaningful), 300) * 0.02
    area_score = min(float(meaningful.sum()) / binary.size, 0.40) * 10.0
    return coverage_score + component_score + area_score


def _automatic_logo_binary(image_bgr: np.ndarray, settings: ProcessingSettings) -> np.ndarray:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    if settings.denoise > 0:
        k = _odd_kernel(settings.denoise)
        gray = cv2.medianBlur(gray, k)

    candidates = []

    # 1. Otsu global: ótimo para logos pretos em fundo claro.
    _, otsu = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    candidates.append(otsu)

    # 2. Limiar por percentis: útil para desenhos cinza ou com pouco contraste.
    for percentile in (5, 10, 15, 20, 25, 30):
        threshold_value = int(np.percentile(gray, percentile))
        _, candidate = cv2.threshold(
            gray, threshold_value, 255, cv2.THRESH_BINARY_INV
        )
        candidates.append(candidate)

    # 3. Fundo local: útil para fundo bege, iluminação e sombras.
    darkness = _darkness_map(image_bgr)
    for threshold_value in (20, 30, 40, 50, 60, 75, 90):
        _, candidate = cv2.threshold(
            darkness, threshold_value, 255, cv2.THRESH_BINARY
        )
        candidates.append(candidate)

    # 4. Adaptativo para linhas finas.
    adaptive = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 41, 7
    )
    candidates.append(adaptive)

    best = max(candidates, key=_score_binary)

    if settings.invert:
        best = cv2.bitwise_not(best)

    return best

def _binarize(image_bgr: np.ndarray, settings: ProcessingSettings) -> np.ndarray:
    gray = _prepare_gray(image_bgr, settings.denoise)
    polarity = cv2.THRESH_BINARY if settings.invert else cv2.THRESH_BINARY_INV

    if settings.method == "manual":
        _, binary = cv2.threshold(gray, settings.threshold, 255, polarity)
    elif settings.method == "otsu":
        _, binary = cv2.threshold(
            gray, 0, 255, polarity | cv2.THRESH_OTSU
        )
    elif settings.method == "adaptive":
        adaptive_type = cv2.THRESH_BINARY if settings.invert else cv2.THRESH_BINARY_INV
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            adaptive_type, 31, 6
        )
    else:
        binary = _automatic_logo_binary(image_bgr, settings)

    binary = _remove_small_components(binary, settings.min_area)

    k = _odd_kernel(settings.close_gaps)
    if k >= 3:
        element = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, element)

    return binary


def _zhang_suen_thinning(binary: np.ndarray) -> np.ndarray:
    """
    Afinamento Zhang-Suen implementado em NumPy.
    Entrada e saída: imagem binária 0/255.
    """
    img = (binary > 0).astype(np.uint8)
    changed = True

    while changed:
        changed = False

        for step in (0, 1):
            p2 = np.roll(img, -1, axis=0)
            p3 = np.roll(np.roll(img, -1, axis=0), 1, axis=1)
            p4 = np.roll(img, 1, axis=1)
            p5 = np.roll(np.roll(img, 1, axis=0), 1, axis=1)
            p6 = np.roll(img, 1, axis=0)
            p7 = np.roll(np.roll(img, 1, axis=0), -1, axis=1)
            p8 = np.roll(img, -1, axis=1)
            p9 = np.roll(np.roll(img, -1, axis=0), -1, axis=1)

            neighbors = p2+p3+p4+p5+p6+p7+p8+p9
            transitions = (
                ((p2 == 0) & (p3 == 1)).astype(np.uint8) +
                ((p3 == 0) & (p4 == 1)).astype(np.uint8) +
                ((p4 == 0) & (p5 == 1)).astype(np.uint8) +
                ((p5 == 0) & (p6 == 1)).astype(np.uint8) +
                ((p6 == 0) & (p7 == 1)).astype(np.uint8) +
                ((p7 == 0) & (p8 == 1)).astype(np.uint8) +
                ((p8 == 0) & (p9 == 1)).astype(np.uint8) +
                ((p9 == 0) & (p2 == 1)).astype(np.uint8)
            )

            common = (
                (img == 1) &
                (neighbors >= 2) &
                (neighbors <= 6) &
                (transitions == 1)
            )

            if step == 0:
                marker = common & ((p2*p4*p6) == 0) & ((p4*p6*p8) == 0)
            else:
                marker = common & ((p2*p4*p8) == 0) & ((p2*p6*p8) == 0)

            # Ignore wrapped borders caused by np.roll.
            marker[0, :] = marker[-1, :] = 0
            marker[:, 0] = marker[:, -1] = 0

            if np.any(marker):
                img[marker] = 0
                changed = True

    return (img * 255).astype(np.uint8)


_NEIGHBORS_8 = [
    (-1,-1), (-1,0), (-1,1),
    (0,-1),           (0,1),
    (1,-1),  (1,0),  (1,1)
]


def _pixel_neighbors(point, pixels):
    y, x = point
    result = []
    for dy, dx in _NEIGHBORS_8:
        candidate = (y + dy, x + dx)
        if candidate in pixels:
            result.append(candidate)
    return result


def _trace_skeleton_paths(skeleton: np.ndarray, min_length: int = 6) -> list[np.ndarray]:
    """
    Converte o esqueleto em caminhos abertos, iniciando em extremidades e junções.
    """
    ys, xs = np.where(skeleton > 0)
    pixels = set(zip(ys.tolist(), xs.tolist()))
    if not pixels:
        return []

    degree = {p: len(_pixel_neighbors(p, pixels)) for p in pixels}
    nodes = {p for p, d in degree.items() if d != 2}
    visited_edges = set()
    paths = []

    def edge_key(a, b):
        return tuple(sorted((a, b)))

    def walk(start, nxt):
        path = [start, nxt]
        visited_edges.add(edge_key(start, nxt))
        previous, current = start, nxt

        while True:
            if current in nodes and current != start:
                break

            options = [
                p for p in _pixel_neighbors(current, pixels)
                if p != previous and edge_key(current, p) not in visited_edges
            ]
            if not options:
                break

            following = options[0]
            visited_edges.add(edge_key(current, following))
            path.append(following)
            previous, current = current, following

        return path

    # Trace paths from endpoints and junctions.
    for node in nodes:
        for nxt in _pixel_neighbors(node, pixels):
            if edge_key(node, nxt) in visited_edges:
                continue
            path = walk(node, nxt)
            if len(path) >= min_length:
                points = np.array([(x, y) for y, x in path], dtype=np.float32)
                paths.append(points)

    # Trace remaining closed loops.
    for pixel in pixels:
        for nxt in _pixel_neighbors(pixel, pixels):
            if edge_key(pixel, nxt) in visited_edges:
                continue
            path = walk(pixel, nxt)
            if len(path) >= min_length:
                points = np.array([(x, y) for y, x in path], dtype=np.float32)
                paths.append(points)

    return paths


def _simplify_open_paths(paths: list[np.ndarray], simplify: float) -> list[np.ndarray]:
    output = []
    for path in paths:
        if len(path) < 2:
            continue
        curve = path.reshape(-1, 1, 2)
        length = cv2.arcLength(curve, False)
        epsilon = max(0.0, simplify) / 100.0 * length
        simplified = cv2.approxPolyDP(curve, epsilon, False).reshape(-1, 2)
        if len(simplified) >= 2:
            output.append(simplified.astype(float))
    return output



def _line_angle(line):
    x1, y1, x2, y2 = line
    return math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180.0

def _line_length(line):
    x1, y1, x2, y2 = line
    return math.hypot(x2 - x1, y2 - y1)

def _point_line_distance(px, py, line):
    x1, y1, x2, y2 = line
    dx, dy = x2 - x1, y2 - y1
    denom = math.hypot(dx, dy)
    if denom == 0:
        return 1e9
    return abs(dy * px - dx * py + x2 * y1 - y2 * x1) / denom

def _merge_collinear_lines(lines, angle_tol=3.0, dist_tol=8.0, gap_tol=25.0):
    """
    Une segmentos aproximadamente colineares em uma única linha.
    """
    if not lines:
        return []

    lines = [tuple(map(float, l)) for l in lines if _line_length(l) >= 8]
    used = [False] * len(lines)
    merged = []

    for i, base in enumerate(lines):
        if used[i]:
            continue

        group = [base]
        used[i] = True
        base_angle = _line_angle(base)

        changed = True
        while changed:
            changed = False
            # current reference from all endpoints
            points = [(l[0], l[1]) for l in group] + [(l[2], l[3]) for l in group]
            arr = np.array(points, dtype=np.float32)
            vx, vy, x0, y0 = cv2.fitLine(arr, cv2.DIST_L2, 0, 0.01, 0.01).flatten()
            ref = (x0 - vx * 1000, y0 - vy * 1000, x0 + vx * 1000, y0 + vy * 1000)
            ref_angle = _line_angle(ref)

            for j, cand in enumerate(lines):
                if used[j]:
                    continue
                angle_diff = abs(_line_angle(cand) - ref_angle)
                angle_diff = min(angle_diff, 180 - angle_diff)
                if angle_diff > angle_tol:
                    continue

                d1 = _point_line_distance(cand[0], cand[1], ref)
                d2 = _point_line_distance(cand[2], cand[3], ref)
                if max(d1, d2) > dist_tol:
                    continue

                # projection gap test
                direction = np.array([vx, vy], dtype=float)
                projections_group = [np.dot(np.array(p) - np.array([x0, y0]), direction) for p in points]
                cand_points = [(cand[0], cand[1]), (cand[2], cand[3])]
                projections_cand = [np.dot(np.array(p) - np.array([x0, y0]), direction) for p in cand_points]
                gmin, gmax = min(projections_group), max(projections_group)
                cmin, cmax = min(projections_cand), max(projections_cand)
                gap = max(gmin - cmax, cmin - gmax, 0)
                if gap > gap_tol:
                    continue

                group.append(cand)
                used[j] = True
                changed = True

        points = [(l[0], l[1]) for l in group] + [(l[2], l[3]) for l in group]
        arr = np.array(points, dtype=np.float32)
        vx, vy, x0, y0 = cv2.fitLine(arr, cv2.DIST_L2, 0, 0.01, 0.01).flatten()
        direction = np.array([vx, vy], dtype=float)
        origin = np.array([x0, y0], dtype=float)
        projections = [np.dot(np.array(p) - origin, direction) for p in points]
        p1 = origin + direction * min(projections)
        p2 = origin + direction * max(projections)
        merged.append((float(p1[0]), float(p1[1]), float(p2[0]), float(p2[1])))

    return merged

def _detect_geometry_paths(binary: np.ndarray) -> tuple[list[np.ndarray], np.ndarray]:
    """
    Detecta linhas retas e devolve caminhos reconstruídos e uma máscara dessas linhas.
    """
    edges = cv2.Canny(binary, 50, 150, apertureSize=3)
    min_len = max(20, int(min(binary.shape) * 0.06))
    raw = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 1800,
        threshold=max(25, min_len // 2),
        minLineLength=min_len,
        maxLineGap=18
    )

    lines = []
    if raw is not None:
        for item in raw[:, 0, :]:
            lines.append(tuple(map(float, item)))

    merged = _merge_collinear_lines(lines)

    paths = []
    mask = np.zeros_like(binary)
    for x1, y1, x2, y2 in merged:
        path = np.array([[x1, y1], [x2, y2]], dtype=float)
        paths.append(path)
        cv2.line(
            mask,
            (int(round(x1)), int(round(y1))),
            (int(round(x2)), int(round(y2))),
            255,
            5,
            cv2.LINE_AA
        )

    return paths, mask

def process_image(path: str, settings: ProcessingSettings) -> ProcessingResult:
    original = cv2.imread(path, cv2.IMREAD_COLOR)
    if original is None:
        raise ValueError("Não foi possível abrir a imagem.")

    cropped, crop_rect = (
        _auto_crop(original) if settings.auto_crop
        else (original.copy(), (0, 0, original.shape[1], original.shape[0]))
    )

    binary = _binarize(cropped, settings)

    contours, hierarchy = cv2.findContours(
        binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE
    )

    final_contours = []
    open_paths = []
    geometry_paths = []
    final_hierarchy = []
    flat_hierarchy = hierarchy[0] if hierarchy is not None else None

    for index, contour in enumerate(contours):
        area = abs(cv2.contourArea(contour))
        if area < settings.min_area:
            continue

        perimeter = cv2.arcLength(contour, True)
        epsilon = max(0.0, settings.simplify) / 100.0 * perimeter
        simplified = cv2.approxPolyDP(contour, epsilon, True)
        points = simplified.reshape(-1, 2)

        if len(points) >= 3:
            final_contours.append(points.astype(float))
            if flat_hierarchy is not None:
                final_hierarchy.append(flat_hierarchy[index])



    residual_contours = final_contours
    if settings.mode == "geometry":
        geometry_paths, geometry_mask = _detect_geometry_paths(binary)

        # Remove detected straight structures from the raster before tracing the remainder.
        residual = cv2.bitwise_and(binary, cv2.bitwise_not(geometry_mask))
        residual = _remove_small_components(residual, max(settings.min_area, 12))
        rem_contours, _ = cv2.findContours(
            residual, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE
        )

        residual_contours = []
        for contour in rem_contours:
            if abs(cv2.contourArea(contour)) < settings.min_area:
                continue
            perimeter = cv2.arcLength(contour, True)
            epsilon = max(0.0, settings.simplify) / 100.0 * perimeter
            simplified = cv2.approxPolyDP(contour, epsilon, True)
            pts = simplified.reshape(-1, 2)
            if len(pts) >= 3:
                residual_contours.append(pts.astype(float))

    if settings.mode == "centerline":
        skeleton = _zhang_suen_thinning(binary)
        open_paths = _trace_skeleton_paths(
            skeleton, min_length=max(4, int(settings.min_area / 2))
        )
        open_paths = _simplify_open_paths(open_paths, settings.simplify)

    if settings.mode == "fill":
        preview = cv2.cvtColor(
            cv2.bitwise_not(binary), cv2.COLOR_GRAY2BGR
        )
    elif settings.mode == "centerline":
        preview = np.full_like(cropped, 255)
        for path in open_paths:
            pts = path.astype(np.int32).reshape(-1, 1, 2)
            cv2.polylines(preview, [pts], False, (0, 0, 0), 1)
    elif settings.mode == "geometry":
        preview = np.full_like(cropped, 255)
        for path in geometry_paths:
            pts = path.astype(np.int32).reshape(-1, 1, 2)
            cv2.polylines(preview, [pts], False, (0, 0, 0), 2)
        draw_contours = [
            c.astype(np.int32).reshape(-1, 1, 2) for c in residual_contours
        ]
        cv2.drawContours(preview, draw_contours, -1, (0, 0, 0), 1)
    else:
        preview = np.full_like(cropped, 255)
        draw_contours = [
            c.astype(np.int32).reshape(-1, 1, 2) for c in final_contours
        ]
        cv2.drawContours(preview, draw_contours, -1, (0, 0, 0), 1)

    warnings = []
    coverage = np.count_nonzero(binary) / binary.size

    if settings.mode == "centerline" and not open_paths:
        warnings.append("Nenhuma linha central foi detectada. Reduza a área mínima ou use outro método.")
    elif not final_contours:
        warnings.append(
            "Nenhum caminho foi detectado. Reduza a área mínima ou teste o método Adaptativo."
        )
    if coverage > 0.70:
        warnings.append(
            "Grande parte da imagem foi considerada desenho. Verifique a opção Inverter."
        )
    if coverage < 0.001:
        warnings.append(
            "Pouquíssimos pixels foram detectados. Reduza a área mínima ou use o método Manual."
        )
    if len(final_contours) > 1500:
        warnings.append(
            "Muitos caminhos foram detectados. Aumente a área mínima ou a simplificação."
        )

    h, w = binary.shape
    return ProcessingResult(
        original_bgr=original,
        cropped_bgr=cropped,
        binary=binary,
        vector_preview_bgr=preview,
        contours=(residual_contours if settings.mode == "geometry" else final_contours),
        open_paths=open_paths,
        geometry_paths=geometry_paths,
        hierarchy=np.array(final_hierarchy) if final_hierarchy else None,
        image_size=(w, h),
        crop_rect=crop_rect,
        warnings=warnings,
    )
