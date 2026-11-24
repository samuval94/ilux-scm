import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, descargar } from '../api.js'
import { useApp } from '../contexto.jsx'
import Estado from '../componentes/Estado.jsx'
import Icono from '../componentes/Icono.jsx'
import { fmtFecha } from '../util.js'

export default function Historial() {
  const { maestros, version, avisar } = useApp()
  const [f, setF] = useState({ q: '', estado: '', proyecto: '', mias: '', desde: '', hasta: '' })
  const [datos, setDatos] = useState({ results: [], count: 0, next: null })
  const [cargando, setCargando] = useState(true)
  const [verFiltros, setVerFiltros] = useState(false)
  const [error, setError] = useState('')

  const consulta = useCallback((extra = {}) => {
    const p = new URLSearchParams()
    Object.entries({ ...f, ...extra }).forEach(([k, v]) => v && p.set(k, v))
    return p.toString()
  }, [f])

  useEffect(() => {
    setCargando(true); setError('')
    const t = setTimeout(() => {
      api.get('/remisiones/?' + consulta()).then(setDatos).catch((e) => setError(e.message)).finally(() => setCargando(false))
    }, 250)
    return () => clearTimeout(t)
  }, [consulta, version])

  async function mas() {
    if (!datos.next) return
    const url = new URL(datos.next)
    const r = await api.get('/remisiones/' + url.search)
    setDatos((d) => ({ ...r, results: [...d.results, ...r.results] }))
  }

  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === 'checkbox' ? (e.target.checked ? '1' : '') : e.target.value })

  return (
    <div className="stack">
      <div className="fila-titulo">
        <div className="cab-pagina">
          <h1>Historial de remisiones</h1>
          <p className="muted">Busca por número, proyecto o receptor. Abre una remisión para ver su firma y descargarla.</p>
        </div>
        <button className="btn btn-sec" onClick={() => descargar('/remisiones/exportar/?' + consulta()).catch((e) => avisar(e.message, 'error'))}>
          <Icono n="excel" /> Exportar Excel
        </button>
      </div>
      <section className="card filtros">
        <label>Buscar<input value={f.q} onChange={set('q')} placeholder="Número, proyecto o receptor" /></label>
        <button type="button" className="btn btn-sec filtros-toggle" aria-expanded={verFiltros} onClick={() => setVerFiltros((v) => !v)}>
          {verFiltros ? 'Ocultar filtros' : 'Más filtros'}
        </button>
        <div className={'filtros-extra' + (verFiltros ? ' abierto' : '')}>
        <label>Estado
          <select value={f.estado} onChange={set('estado')}>
            <option value="">Todos</option><option value="FIRMADA">Firmadas</option><option value="BORRADOR">Borradores</option><option value="ANULADA">Anuladas</option>
          </select>
        </label>
        <label>Proyecto
          <select value={f.proyecto} onChange={set('proyecto')}>
            <option value="">Todos</option>
            {maestros.proyectos.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
          </select>
        </label>
        <label>Desde<input type="date" value={f.desde} onChange={set('desde')} /></label>
        <label>Hasta<input type="date" value={f.hasta} onChange={set('hasta')} /></label>
        <label className="check"><input type="checkbox" checked={!!f.mias} onChange={set('mias')} /> Solo mis remisiones</label>
        </div>
      </section>
      {error && <p className="msg-error" role="alert"><Icono n="alerta" size={18} />{error}</p>}
      {!cargando && datos.results.length === 0 && !error && (
        <div className="vacio">
          <Icono n="lista" size={28} />
          <strong>No hay remisiones con esos filtros</strong>
          <span>Cambia o quita algún filtro para ver más resultados.</span>
        </div>
      )}
      {datos.results.length > 0 && (
        <div className="lista" aria-busy={cargando}>
          <div className="lista-cab" aria-hidden="true">
            <span>Número</span><span>Proyecto</span><span>Recibe</span><span className="c-items">Ítems</span><span>Fecha</span><span>Estado</span>
          </div>
          {datos.results.map((r) => (
            <Link key={r.id} to={`/remisiones/${r.id}`} className="fila-rem" data-testid="fila-rem">
              <div className="fila-rem-num">{r.numero_formato ? `No. ${r.numero_formato}` : 'Sin número'}</div>
              <div className="fila-rem-proy">{r.proyecto_nombre}</div>
              <div className="fila-rem-meta">
                <span className="fila-rem-recibe"><span className="oculto-visual">Recibe </span>{r.recibida_por_nombre}</span>
                <span className="fila-rem-items">{r.total_items} ítem(s)</span>
                <span className="fila-rem-fecha">{fmtFecha(r.firmada_en || r.creada_en)}</span>
              </div>
              <Estado estado={r.estado} />
            </Link>
          ))}
        </div>
      )}
      {datos.next && <button className="btn btn-sec" onClick={mas}>Cargar más ({datos.count - datos.results.length} restantes)</button>}
    </div>
  )
}
