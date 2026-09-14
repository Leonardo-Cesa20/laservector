from pathlib import Path

def _dimensions(image_size, width_mm):
    width_px, height_px = image_size
    scale = width_mm / width_px
    return scale, height_px * scale

def export_svg(path, contours, image_size, width_mm, mode, open_paths=None, geometry_paths=None):
    scale, height_mm = _dimensions(image_size, width_mm)

    if mode == "cut":
        max_width = 600.0
    else:
        max_width = 550.0

    if width_mm > max_width or height_mm > 400:
        raise ValueError(
            f"A arte ultrapassa o limite da máquina: {width_mm:.1f} × {height_mm:.1f} mm."
        )

    if mode == "fill":
        style = 'fill="#000" stroke="none" fill-rule="evenodd"'
    else:
        style = 'fill="none" stroke="#000" stroke-width="0.1"'

    items = []
    open_paths = open_paths or []
    geometry_paths = geometry_paths or []
    for contour in contours:
        commands = []
        for index, (x, y) in enumerate(contour):
            commands.append(
                f"{'M' if index == 0 else 'L'} {x * scale:.4f} {y * scale:.4f}"
            )
        commands.append("Z")
        items.append(f'<path d="{" ".join(commands)}" {style}/>')

    if mode == "geometry":
        for path_points in geometry_paths:
            commands = []
            for index, (x, y) in enumerate(path_points):
                commands.append(
                    f"{'M' if index == 0 else 'L'} {x * scale:.4f} {y * scale:.4f}"
                )
            items.append(
                f'<path d="{" ".join(commands)}" fill="none" '
                f'stroke="#000" stroke-width="0.15" stroke-linecap="round"/>'
            )

    if mode == "centerline":
        for path_points in open_paths:
            commands = []
            for index, (x, y) in enumerate(path_points):
                commands.append(
                    f"{'M' if index == 0 else 'L'} {x * scale:.4f} {y * scale:.4f}"
                )
            items.append(
                f'<path d="{" ".join(commands)}" fill="none" '
                f'stroke="#000" stroke-width="0.1" stroke-linecap="round" '
                f'stroke-linejoin="round"/>'
            )

    svg = "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg"',
        f' width="{width_mm:.4f}mm" height="{height_mm:.4f}mm"',
        f' viewBox="0 0 {width_mm:.4f} {height_mm:.4f}">',
        f'<g id="{mode}">',
        *items,
        '</g>',
        '</svg>',
    ])
    Path(path).write_text(svg, encoding="utf-8")
