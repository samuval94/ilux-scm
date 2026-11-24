import { Link, NavLink, Outlet } from 'react-router-dom'
import { useApp } from '../contexto.jsx'
import Icono from './Icono.jsx'

export default function Layout() {
  const { user, salir, online, cola, esAdmin, toast } = useApp()
  return (
    <div className="app">
      <a className="saltar" href="#contenido">Saltar al contenido</a>
      <header className="cabecera">
        <div className="cabecera-fila">
          <Link to="/" className="marca" aria-label="ILUX Ingeniería – Nueva remisión">
            <img src="/logo-ilux.png" alt="ILUX · Ingeniería, diseño y mantenimiento eléctrico" width="137" height="41" />
          </Link>
          <div className="usuario">
            <span className={'estado-red' + (online ? '' : ' sin')}>{online ? 'En línea' : 'Sin conexión'}</span>
            <span className="usuario-nombre">{user.nombre}</span>
            <span className={'pill ' + (esAdmin ? 'pill-amber' : 'pill-gray')}>{esAdmin ? 'Administrador' : 'Operador'}</span>
            <button className="btn-salir" onClick={salir}><Icono n="salir" size={18} /> Salir</button>
          </div>
        </div>
      </header>
      <nav className="nav" aria-label="Principal">
        <div className="nav-interno">
          <NavLink to="/" end><Icono n="scan" /><span>Nueva<span className="solo-escritorio"> remisión</span></span></NavLink>
          <NavLink to="/remisiones"><Icono n="lista" /><span>Historial</span></NavLink>
          <NavLink to="/herramientas"><Icono n="llave" /><span>Herramientas</span></NavLink>
          <NavLink to="/panel"><Icono n="grafica" /><span>Panel</span></NavLink>
          {esAdmin && <NavLink to="/gestion"><Icono n="ajustes" /><span>Gestión</span></NavLink>}
        </div>
      </nav>
      {!online && (
        <div className="banner-caja">
          <div className="banner banner-warn" role="status">
            <Icono n="sinred" size={20} />
            <span>Sin conexión. Puedes seguir trabajando: las remisiones firmadas se enviarán al volver la señal.</span>
          </div>
        </div>
      )}
      {cola.length > 0 && (
        <div className="banner-caja">
          <div className="banner banner-info">
            <Icono n="info" size={20} />
            <span>{cola.length} remisión(es) firmada(s) pendiente(s) de enviar. <Link to="/pendientes">Ver</Link></span>
          </div>
        </div>
      )}
      <main className="main" id="contenido" tabIndex={-1}><Outlet /></main>
      {toast && (
        <div className={'toast toast-' + toast.tipo} role={toast.tipo === 'error' ? 'alert' : 'status'} key={toast.id}>
          <Icono n={toast.tipo === 'error' ? 'alerta' : 'check'} size={20} />
          <span>{toast.texto}</span>
        </div>
      )}
    </div>
  )
}
