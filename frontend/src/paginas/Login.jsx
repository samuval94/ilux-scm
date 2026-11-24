import { useState } from 'react'
import { useApp } from '../contexto.jsx'
import Icono from '../componentes/Icono.jsx'

export default function Login() {
  const { login } = useApp()
  const [u, setU] = useState('')
  const [p, setP] = useState('')
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    setError(''); setCargando(true)
    try { await login(u, p) } catch (err) { setError(err.sinConexion ? 'No hay conexión con el servidor.' : err.message) } finally { setCargando(false) }
  }

  return (
    <div className="acceso">
      <main className="acceso-panel">
        <form className="acceso-caja" onSubmit={enviar}>
          <img className="acceso-logo-movil" src="/logo-ilux.png" alt="ILUX · Ingeniería, diseño y mantenimiento eléctrico" />
          <div className="cab-pagina">
            <h1>Ingresar al sistema</h1>
            <p className="muted">Sistema de Control de Materiales (SCM)</p>
          </div>
          <label>Usuario<input value={u} onChange={(e) => setU(e.target.value)} autoCapitalize="off" autoComplete="username" autoFocus /></label>
          <label>Contraseña<input type="password" value={p} onChange={(e) => setP(e.target.value)} autoComplete="current-password" /></label>
          {error && <p className="msg-error" role="alert"><Icono n="alerta" size={18} />{error}</p>}
          <button className="btn btn-pri ancho" disabled={cargando || !u || !p}>{cargando ? 'Ingresando…' : 'Ingresar'}</button>
          <p className="acceso-nota">¿Necesitas acceso? Solicítalo al administrador del sistema.</p>
        </form>
      </main>
    </div>
  )
}
