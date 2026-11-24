// Iconos de línea (cuadrícula 24, trazo uniforme). Todos decorativos: el texto vecino da el nombre accesible.
const P = {
  scan: <><path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3" /><path d="M7 12h10" /></>,
  lista: <><path d="M8 6h12M8 12h12M8 18h12" /><circle cx="4" cy="6" r="1" /><circle cx="4" cy="12" r="1" /><circle cx="4" cy="18" r="1" /></>,
  llave: <path d="M14.5 6.5a4 4 0 1 0-3.9 5l-7.1 7.1 2 2 2-2 1.5 1.5 2-2-1.5-1.5 3.4-3.4a4 4 0 0 0 1.6-6.7z" />,
  grafica: <><path d="M4 20V4" /><path d="M4 20h16" /><path d="M8 16v-5M12 16V8M16 16v-8" /></>,
  ajustes: <><circle cx="12" cy="12" r="3" /><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" /></>,
  mas: <path d="M12 5v14M5 12h14" />,
  menos: <path d="M5 12h14" />,
  x: <path d="M6 6l12 12M18 6L6 18" />,
  camara: <><path d="M4 8h3l1.5-2h7L17 8h3v11H4z" /><circle cx="12" cy="13" r="3.5" /></>,
  pdf: <><path d="M6 3h8l5 5v13H6z" /><path d="M14 3v5h5" /></>,
  excel: <><rect x="4" y="4" width="16" height="16" rx="1" /><path d="M4 10h16M4 15h16M10 4v16" /></>,
  firma: <><path d="M3 18c3-6 5-9 7-9s0 6 2 6 3-4 4-4 1 2 3 2" /><path d="M3 21h18" /></>,
  check: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  salir: <><path d="M9 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h4" /><path d="M16 8l4 4-4 4M20 12H9" /></>,
  lapiz: <><path d="M4 20l1-4L16.5 4.5a2.1 2.1 0 0 1 3 3L8 19z" /><path d="M14.5 6.5l3 3" /></>,
  alerta: <><path d="M12 4l9 16H3z" /><path d="M12 10v4M12 17.2v.1" /></>,
  sinred: <><path d="M3 3l18 18" /><path d="M8.5 16.5a5 5 0 0 1 7 0M5 12.9a10 10 0 0 1 4.2-2.4M19 12.9a10 10 0 0 0-3.2-2.2M2 8.8a15 15 0 0 1 5-3" /><path d="M12 20h.01" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 7.8v.1" /></>,
  reloj: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  atras: <path d="M15 5l-7 7 7 7" />,
  buscar: <><circle cx="11" cy="11" r="6.5" /><path d="M20 20l-4.2-4.2" /></>,
  caja: <><path d="M3 7.5L12 3l9 4.5v9L12 21l-9-4.5z" /><path d="M3 7.5l9 4.5 9-4.5M12 12v9" /></>,
}
export default function Icono({ n, size = 20, trazo = 1.9 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={trazo} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {P[n]}
    </svg>
  )
}
