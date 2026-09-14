from pathlib import Path

def _dimensions(image_size, width_mm):
    width_px, height_px = image_size
    scale = width_mm / width_px
    return scale, height_px * scale

def export_dxf(path, contours, image_size, width_mm, mode, open_paths=None, geometry_paths=None):
    scale, height_mm = _dimensions(image_size, width_mm)
    max_width = 600.0 if mode == "cut" else 550.0

    if width_mm > max_width or height_mm > 400:
        raise ValueError(
            f"A arte ultrapassa o limite da máquina: {width_mm:.1f} × {height_mm:.1f} mm."
        )

    layer = mode.upper()
    open_paths = open_paths or []
    geometry_paths = geometry_paths or []
    lines = [
        "0","SECTION","2","HEADER",
        "9","$ACADVER","1","AC1009",
        "9","$INSUNITS","70","4",
        "0","ENDSEC",
        "0","SECTION","2","TABLES",
        "0","TABLE","2","LAYER","70","1",
        "0","LAYER","2",layer,"70","0","62","7","6","CONTINUOUS",
        "0","ENDTAB","0","ENDSEC",
        "0","SECTION","2","ENTITIES",
    ]

    for contour in contours:
        lines += ["0","POLYLINE","8",layer,"66","1","70","1"]
        for x, y in contour:
            lines += [
                "0","VERTEX","8",layer,
                "10",f"{x * scale:.6f}",
                "20",f"{height_mm - y * scale:.6f}",
                "30","0.0",
            ]
        lines += ["0","SEQEND","8",layer]

    if mode == "geometry":
        for path_points in geometry_paths:
            lines += ["0","POLYLINE","8",layer,"66","1","70","0"]
            for x, y in path_points:
                lines += [
                    "0","VERTEX","8",layer,
                    "10",f"{x * scale:.6f}",
                    "20",f"{height_mm - y * scale:.6f}",
                    "30","0.0",
                ]
            lines += ["0","SEQEND","8",layer]

    if mode == "centerline":
        for path_points in open_paths:
            lines += ["0","POLYLINE","8",layer,"66","1","70","0"]
            for x, y in path_points:
                lines += [
                    "0","VERTEX","8",layer,
                    "10",f"{x * scale:.6f}",
                    "20",f"{height_mm - y * scale:.6f}",
                    "30","0.0",
                ]
            lines += ["0","SEQEND","8",layer]

    lines += ["0","ENDSEC","0","EOF"]
    Path(path).write_text("\n".join(lines), encoding="ascii")
