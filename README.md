# Mandíbula 3D → guía quirúrgica para ortodoncia

Flujo reproducible: **3D Slicer → Blender → 3D Slicer**, a partir del CBCT dental de muestra `CBCTDentalSurgery` (Sample Data de 3D Slicer 5.12).

1. `recA_slicer.py` – segmenta la mandíbula (umbral + Grow from seeds + suavizado) y exporta `mandibula_slicer.stl`.
2. `recB_blender.py` – limpia fragmentos, cierra huecos, suaviza y optimiza (270 k → 93 k triángulos) → `mandibula_blender.stl`.
3. `recC_guia.py` – diseña la guía dentosoportada con manguito Ø2.2 mm para mini-implante (TAD) → `guia_quirurgica_ortodoncia.stl`.
4. `compose.py` – arma los videos (completo y resumen). `rec_common.py` – grabación con ffmpeg.

Videos: `VIDEO_COMPLETO_mandibula_guia.mp4`, `VIDEO_RESUMEN_redes_mandibula_guia.mp4`. Texto de LinkedIn: `POST_LINKEDIN.txt`.

El CBCT no se incluye; se descarga con `SampleData.downloadSample("CBCTDentalSurgery")` (los scripts esperan `cbct.nrrd`, que `recA_slicer.py` guarda/`s0_load.py` genera).

> Diseño demostrativo con datos de muestra. No apto para uso clínico sin validación.
