import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { api, setToken, getToken } from './api'
import { leer, guardar } from './util'

const Ctx = createContext(null)
export const useApp = () => useContext(Ctx)

export function AppProvider({ children }) {
  const [user, setUser] = useState(() => (getToken() ? leer('ilux_user', null) : null))
  const [maestros, setMaestros] = useState(() => ({
    catalogo: leer('ilux_catalogo', []),
    proyectos: leer('ilux_proyectos', []),
    empleados: leer('ilux_empleados', []),
  }))
  const [online, setOnline] = useState(navigator.onLine)
  const [cola, setColaEstado] = useState(() => leer('ilux_cola', []))
  const [toast, setToast] = useState(null)
  const [version, setVersion] = useState(0) // sube cuando algo cambia en el servidor (para refrescar listas)
  const enviando = useRef(false)
  const colaRef = useRef(cola)

  const avisar = useCallback((texto, tipo = 'ok') => {
    setToast({ texto, tipo, id: Date.now() })
  }, [])
  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 4200)
    return () => clearTimeout(t)
  }, [toast])

  const setCola = useCallback((c) => {
    colaRef.current = c
    setColaEstado(c)
    guardar('ilux_cola', c)
  }, [])

  // ---- sesión
  const login = useCallback(async (username, password) => {
    const r = await api.post('/auth/login/', { username, password })
    setToken(r.token)
    guardar('ilux_user', r.user)
    setUser(r.user)
  }, [])

  const salir = useCallback(async () => {
    try { await api.post('/auth/logout/') } catch { /* sin red: se cierra igual en este dispositivo */ }
    setToken(null)
    guardar('ilux_user', null)
    guardar('ilux_borrador_actual', null)
    setUser(null)
  }, [])

  useEffect(() => {
    const f = () => { setToken(null); guardar('ilux_user', null); setUser(null) }
    window.addEventListener('ilux:sesion-vencida', f)
    return () => window.removeEventListener('ilux:sesion-vencida', f)
  }, [])

  // ---- conexión
  useEffect(() => {
    const on = () => setOnline(true)
    const off = () => setOnline(false)
    window.addEventListener('online', on)
    window.addEventListener('offline', off)
    return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off) }
  }, [])

  // ---- catálogo, proyectos y empleados (se guardan en el dispositivo para trabajar sin señal)
  const cargarMaestros = useCallback(async () => {
    try {
      const [catalogo, proyectos, empleados] = await Promise.all([
        api.get('/materiales/catalogo/'), api.get('/proyectos/'), api.get('/empleados/'),
      ])
      guardar('ilux_catalogo', catalogo); guardar('ilux_proyectos', proyectos); guardar('ilux_empleados', empleados)
      setMaestros({ catalogo, proyectos, empleados })
      return true
    } catch { return false }
  }, [])

  useEffect(() => { if (user && online) cargarMaestros() }, [user, online, cargarMaestros])

  const porCodigo = useMemo(() => {
    const m = new Map()
    maestros.catalogo.forEach((x) => m.set(String(x.codigo).toUpperCase(), x))
    return m
  }, [maestros.catalogo])

  // ---- cola de remisiones firmadas sin señal
  const encolar = useCallback((payload) => {
    setCola([...colaRef.current, { payload, creada: new Date().toISOString(), error: '' }])
  }, [setCola])

  const enviarCola = useCallback(async () => {
    if (enviando.current || !getToken()) return 0
    enviando.current = true
    let enviadas = 0
    try {
      for (const item of [...colaRef.current]) {
        try {
          await api.post('/remisiones/guardar/', item.payload)
          setCola(colaRef.current.filter((x) => x.payload.id !== item.payload.id))
          enviadas += 1
        } catch (e) {
          if (e.sinConexion || e.status === 401) break
          setCola(colaRef.current.map((x) => (x.payload.id === item.payload.id ? { ...x, error: e.message } : x)))
        }
      }
    } finally {
      enviando.current = false
    }
    if (enviadas) { setVersion((v) => v + 1); avisar(`${enviadas} remisión(es) enviada(s) al servidor.`) }
    return enviadas
  }, [avisar, setCola])

  const descartarCola = useCallback((id) => setCola(colaRef.current.filter((x) => x.payload.id !== id)), [setCola])

  useEffect(() => {
    if (!user || !online || !cola.length) return
    enviarCola()
    const t = setInterval(enviarCola, 30000)
    return () => clearInterval(t)
  }, [user, online, cola.length, enviarCola])

  const valor = {
    user, login, salir, maestros, cargarMaestros, porCodigo, online, cola, encolar, enviarCola, descartarCola,
    toast, avisar, version, refrescar: () => setVersion((v) => v + 1), esAdmin: user?.rol === 'ADMIN',
  }
  return <Ctx.Provider value={valor}>{children}</Ctx.Provider>
}
