# Sistema de diseño – ILUX SCM

Guía corta para quien toque el front-end. Todo vive en `src/styles.css` (tokens en `:root`); los componentes
no usan colores sueltos. **Solo se cambió la capa visual: la lógica, las rutas y la API siguen igual.**

## Principios

- **Es una herramienta de trabajo** (bodega, obra, celular con una mano): primero claridad, consistencia y lectura rápida; el color y los detalles de marca van en lo preciso, no en efectos.
- **Identidad de ILUX**: logo real (`public/logo-ilux*.png`), banda de navegación ámbar como en ilux.com.co, pestaña activa en negro y la flor del logo en los íconos de la app. El ingreso es una tarjeta blanca centrada con el logo, filete ámbar fino arriba y un fondo de puntos (grises abajo a la izquierda, ámbar arriba a la derecha) que aparece con un fundido corto.
- **El número de la remisión es el ancla tipográfica** (Barlow Semi Condensed, grande); el resto es sobrio.
- Solo tema claro (se usa a pleno sol).

## Paleta

| Token | Valor | Uso |
|---|---|---|
| `--ambar` | `#F3B600` | Relleno de acciones primarias y banda de navegación. **Nunca como color de texto** sobre claro (1,8:1). Texto sobre ámbar: negro (11,5:1) |
| `--ambar-fuerte` | `#DAA300` | Hover del botón primario |
| `--ambar-borde` | `#B98A00` | Borde del botón primario |
| `--ambar-tinte` | `#FFF4CC` | Fondos suaves (avisos, ícono de estado) |
| `--tinta` | `#1C1B1B` | Texto, pestaña activa, panel de ingreso |
| `--tinta-2` / `--tinta-3` | `#4A4946` / `#66645F` | Texto secundario (≥ 5,3:1) |
| `--fondo` / `--fondo-2` / `--linea` | `#F3F3F0` / `#EAEAE6` / `#DDDCD7` | Fondo, superficies y separadores |
| `--borde` | `#85847F` | Bordes de campos (3,4:1, requisito de componentes) |
| `--gris-ilux` | `#A3A3A3` | Línea de firma, detalles |
| Estados | ok `#1F7A4D` · mal `#B42318` · aviso `#7A5200` | Siempre con ícono y texto, nunca solo color |

Amarillo limón `#F3E300` aparece solo dentro del logo.

## Tipografía

- **Barlow** (400/500/600/700) para interfaz y **Barlow Semi Condensed** (600/700) para títulos y cifras.
- Incluidas en la app (`@fontsource`, subconjunto latino): no dependen de internet y quedan en la caché de la PWA para funcionar sin conexión.
- Escala fija en `rem`; cifra principal del panel 3,5 rem; cuerpo ≥ 1 rem; cifras tabulares (`tabular-nums`) en tablas y cantidades.

## Espaciado, forma y movimiento

- Base de 4 px: `--s1 … --s7` (4, 8, 12, 16, 24, 32, 48). Radios 4 / 6 / 10 px.
- Movimiento corto (160–200 ms) solo para responder a una acción (abrir, confirmar, avisar). `prefers-reduced-motion` lo apaga.

## Accesibilidad (verificada)

- Contraste de texto ≥ 4,5:1 y de componentes ≥ 3:1.
- **Foco siempre visible**: contorno negro de 3 px con separación de 2 px (en campos, contorno negro + halo ámbar).
- **Teclado**: enlace "Saltar al contenido", orden lógico, diálogos con foco atrapado, `Esc` para cerrar y retorno del foco al elemento que los abrió.
- Objetivos táctiles de 44 px; etiquetas visibles en todos los campos; `role`/`aria-*` en medidor, barra segmentada y regiones con scroll.
- Estados con ícono + texto (Firmada, Borrador, Anulada, Vencida, En campo).
- Pruebas: axe-core sin violaciones en escritorio y móvil (incluido el modal de firma); sin desbordamiento horizontal a 360, 390, 768 y 1280 px; detector de impeccable sin hallazgos.

## Visualización de datos (Panel, tablas)

- **Cifra principal**: % de remisiones con firma (KPI 2 de la Entrega 2) con medidor y marca de la meta (95 %); decimales con coma.
- **KPI**: baldosas de una cifra con etiqueta corta; 2 columnas en móvil.
- **Estado de las remisiones**: una barra segmentada con porcentajes impresos, tooltip al pasar el mouse o enfocar, y leyenda con conteos. Colores validados (daltonismo y contraste): firmada `#1F7A4D`, borrador `#C98500`, anulada `#B42318`; la identidad nunca depende solo del color.
- **Tablas**: cifras alineadas a la derecha con `tabular-nums`, líneas finas entre filas, encabezado fijo en estilo y regiones con scroll enfocables por teclado.

## PDF y Excel descargables

Mismos datos de siempre; solo cambia la presentación (`remisiones/services/pdf.py` y `excel.py`).

- **PDF:** logo de ILUX a la izquierda y banda ámbar debajo (como en ilux.com.co), título con Barlow Semi Condensed, estado en una pastilla con texto (Firmada / Borrador / Anulada), tabla con encabezado ámbar y texto negro, QR de verificación y pie con fecha y página. Las fuentes Barlow (licencia OFL) y el logo están en `remisiones/services/assets/`; si las fuentes no cargan, usa Helvetica y el PDF se genera igual. Un carácter que la fuente no tenga se imprime como `?` en lugar de un recuadro.
- **Excel:** encabezado ámbar con texto negro, líneas finas, cifras a la derecha, estados con color **y** texto, anchos ajustados al contenido y configuración de impresión (horizontal, a lo ancho de una hoja, encabezado repetido, pie de ILUX). El encabezado sigue en la fila 1 y las tablas conservan su nombre (`Remisiones`, `RemisionesPendientes`, `HerramientasEntregadas`) para Power Automate, por eso el logo no va dentro de la hoja.

## Cómo seguir

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxy al servidor Django)
npm run build      # compila a frontend/dist, que Django sirve en "/"
```

Al agregar pantallas: usar los tokens, mantener el botón primario ámbar con texto negro, y probar con el teclado antes de dar por terminado.
