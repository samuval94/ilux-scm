import { useEffect, useRef } from 'react'

const FOCUSABLES = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

// Contenedor de diálogos: Escape cierra, el foco queda dentro (Tab/Shift+Tab) y vuelve al elemento que lo abrió.
// foco: 'campo' (primer campo de texto; por defecto) o 'caja' (el propio diálogo, para no abrir el teclado del celular).
export default function Dialogo({ titulo, onCerrar, foco = 'campo', children }) {
  const caja = useRef(null)
  const cerrar = useRef(onCerrar)
  cerrar.current = onCerrar

  useEffect(() => {
    const previo = document.activeElement
    const el = caja.current
    const primero = foco === 'caja' ? el : (el.querySelector('input, textarea, select') || el.querySelector(FOCUSABLES))
    primero?.focus({ preventScroll: true })
    function alTeclear(e) {
      if (e.key === 'Escape') { e.stopPropagation(); cerrar.current?.(); return }
      if (e.key !== 'Tab') return
      const lista = [...el.querySelectorAll(FOCUSABLES)].filter((x) => x.offsetParent !== null)
      if (!lista.length) return
      const a = lista[0], z = lista[lista.length - 1]
      if (e.shiftKey && document.activeElement === a) { e.preventDefault(); z.focus() }
      else if (!e.shiftKey && document.activeElement === z) { e.preventDefault(); a.focus() }
    }
    document.addEventListener('keydown', alTeclear)
    return () => { document.removeEventListener('keydown', alTeclear); previo?.focus?.() }
  }, [])

  return (
    <div className="modal-fondo" role="dialog" aria-modal="true" aria-label={titulo}>
      <div className="modal" ref={caja} tabIndex={-1}>{children}</div>
    </div>
  )
}
