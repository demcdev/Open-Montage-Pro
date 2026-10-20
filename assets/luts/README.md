# LUTs (.cube)

LUTs 3D para `film_look` (`lut_path`) y `color_grade` (`lut_path`). Un nombre sin extensión (por ejemplo `warm_film`) se resuelve a `assets/luts/<nombre>.cube` en `film_look`.

| Archivo | Uso | Intensidad sugerida (`lut_intensity`) |
|---|---|---|
| `identity.cube` | Sin cambio. Para probar la ruta del LUT | 1.0 |
| `warm_film.cube` | Película cálida: negros levantados, curva S suave, altas luces cálidas | 0.5–0.8 |
| `teal_orange_soft.cube` | Sombras verdeazuladas y altas luces cálidas, suave | 0.4–0.7 |
| `bleach_bypass_soft.cube` | Desaturado y contrastado: tensión, archivo, noche | 0.4–0.7 |

## Reglas

- Todos son de 17×17×17, dominio 0–1, entrada y salida Rec.709 (SDR). No son LUTs de conversión desde log: las fuentes del proyecto son MP4 Rec.709 de 8 bits.
- Los cuatro se generaron para OpenMontage y se publican como **CC0 1.0** (dominio público). Se pueden usar en videos monetizados.
- Para agregar un LUT de terceros: comprobar que su licencia permite uso comercial, guardar la licencia junto al archivo (`<nombre>.LICENSE.txt`) y registrarlo en el `asset_manifest` como asset de tipo `lut` con `license` y `original_url`.
- Un LUT es una decisión de toda la pieza o de toda la serie: se fija en la biblia de producción (`skills/meta/production-bible.md`) y no se cambia entre capítulos.
