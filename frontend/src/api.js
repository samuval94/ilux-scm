// Cliente de la API. El token se guarda en localStorage; cualquier 401 cierra la sesión.
const KEY = 'ilux_token'
let token = null
try { token = localStorage.getItem(KEY) } catch { /* sin almacenamiento */ }

export const getToken = () => token
export function setToken(t) {
  token = t
  try { t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY) } catch { /* ignorar */ }
}

export class ApiError extends Error {
  constructor(msg, status = 0) {
    super(msg)
    this.status = status
    this.sinConexion = status === 0
  }
}

async function request(path, { method = 'GET', json, form, auth = true } = {}) {
  const headers = {}
  if (auth && token) headers.Authorization = 'Token ' + token
  let body
  if (json !== undefined) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(json) }
  else if (form) body = form
  let res
  try {
    res = await fetch('/api' + path, { method, headers, body })
  } catch {
    throw new ApiError('Sin conexión con el servidor.', 0)
  }
  if (res.status === 401 && auth) window.dispatchEvent(new Event('ilux:sesion-vencida'))
  if (res.status === 204) return null
  const tipo = res.headers.get('content-type') || ''
  const data = tipo.includes('json') ? await res.json().catch(() => null) : null
  if (!res.ok) throw new ApiError(data?.detail || `Error del servidor (${res.status}).`, res.status)
  return data
}

export const api = {
  get: (p) => request(p),
  post: (p, json = {}) => request(p, { method: 'POST', json }),
  patch: (p, json) => request(p, { method: 'PATCH', json }),
  del: (p) => request(p, { method: 'DELETE' }),
  upload: (p, form) => request(p, { method: 'POST', form }),
  publico: (p) => request(p, { auth: false }),
}

// Descarga un archivo protegido (PDF / Excel) usando el token.
export async function descargar(path, nombreSugerido = 'archivo') {
  let res
  try {
    res = await fetch('/api' + path, { headers: { Authorization: 'Token ' + token } })
  } catch {
    throw new ApiError('Sin conexión con el servidor.', 0)
  }
  if (!res.ok) {
    const d = await res.json().catch(() => null)
    throw new ApiError(d?.detail || `No se pudo descargar (${res.status}).`, res.status)
  }
  const cd = res.headers.get('content-disposition') || ''
  const m = /filename="?([^";]+)"?/.exec(cd)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = m ? m[1] : nombreSugerido
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 10000)
}

export async function blobUrl(path) {
  const res = await fetch('/api' + path, { headers: { Authorization: 'Token ' + token } })
  if (!res.ok) throw new ApiError('No se pudo cargar la imagen.', res.status)
  return URL.createObjectURL(await res.blob())
}
