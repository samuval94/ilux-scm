export const ZONA = 'America/Bogota'
export const fmtFecha = (iso) =>
  iso ? new Date(iso).toLocaleString('es-CO', { timeZone: ZONA, dateStyle: 'short', timeStyle: 'short' }) : '—'
export const fmtDia = (iso) => (iso ? new Date(iso + (iso.length === 10 ? 'T12:00:00' : '')).toLocaleDateString('es-CO', { timeZone: ZONA }) : '—')

// "12,5" o "12.5" -> número. Devuelve NaN si no es válido.
export function aNumero(texto) {
  const t = String(texto ?? '').trim().replace(',', '.')
  if (!/^\d+(\.\d{1,2})?$/.test(t)) return NaN
  return Number(t)
}

export function errorCantidad(texto, admiteDecimales) {
  const n = aNumero(texto)
  if (Number.isNaN(n)) return 'Cantidad no válida (máx. 2 decimales).'
  if (n <= 0) return 'Debe ser mayor que cero.'
  if (!admiteDecimales && !Number.isInteger(n)) return 'Solo se permiten enteros en esta unidad.'
  return ''
}

export const UNIDADES = { UNIDAD: 'und', MT: 'm', TR: 'tramo', KG: 'kg', CANECA: 'caneca' }
export const etiquetaUnidad = (u) => UNIDADES[u] || u
export const TIPOS = { MATERIAL: 'Material', HERRAMIENTA: 'Herramienta', EQUIPO: 'Equipo' }

export function uuid() {
  if (crypto.randomUUID) return crypto.randomUUID()
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}

export function leer(clave, defecto) {
  try { const v = localStorage.getItem(clave); return v ? JSON.parse(v) : defecto } catch { return defecto }
}
export function guardar(clave, valor) {
  try { valor === undefined || valor === null ? localStorage.removeItem(clave) : localStorage.setItem(clave, JSON.stringify(valor)) } catch { /* lleno o bloqueado */ }
}

export function pitido() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const o = ctx.createOscillator()
    const g = ctx.createGain()
    o.type = 'square'; o.frequency.value = 1100; g.gain.value = 0.06
    o.connect(g); g.connect(ctx.destination)
    o.start(); o.stop(ctx.currentTime + 0.09)
    setTimeout(() => ctx.close(), 300)
  } catch { /* sin audio */ }
  try { navigator.vibrate?.(50) } catch { /* sin vibración */ }
}
