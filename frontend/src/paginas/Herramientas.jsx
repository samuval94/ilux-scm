import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, descargar } from '../api.js'
import { useApp } from '../contexto.jsx'
import Icono from '../componentes/Icono.jsx'
import Esqueleto from '../componentes/Esqueleto.jsx'
import { fmtDia } from '../util.js'

export default function Herramientas() {
  const { avisar, version, refrescar } = useApp()
  const [lista, setLista] = useState(null)
  const [error, setError] = useState('')

  const cargar = useCallback(() => {
    api.get('/herramientas/pendientes/').then(setLista).catch((e) => setError(e.message))
  }, [])
  useEffect(() => { cargar() }, [cargar, version])

  async function devolver(it) {
    if (!window.confirm(`¿Registrar la devolución de ${it.nombre}?`)) return
    try { await api.post(`/items/${it.id}/devolver/`, {}); avisar('Devolución registrada.'); cargar(); refrescar() } catch (e) { avisar(e.message, 'error') }
  }

  return (
    <div className="stack">
      <div className="fila-titulo">
        <div className="cab-pagina">
          <h1>Herramientas y equipos en campo</h1>
          <p className="muted">Entregados con remisión firmada y aún sin devolver. Para que aparezcan, el ítem debe estar clasificado como herramienta o equipo en el catálogo.</p>
        </div>
        <button className="btn btn-sec" onClick={() => descargar('/herramientas/pendientes/excel/').catch((e) => avisar(e.message, 'error'))}><Icono n="excel" /> Excel</button>
      </div>
      {error && <p className="msg-error" role="alert"><Icono n="alerta" size={18} />{error}</p>}
      {lista === null && !error && <Esqueleto />}
      {lista && lista.length === 0 && (
        <div className="vacio">
          <Icono n="check" size={28} />
          <strong>No hay herramientas ni equipos pendientes de devolución</strong>
          <span>Cuando entregues una herramienta con una remisión firmada, aparecerá aquí hasta su devolución.</span>
        </div>
      )}
      {lista && lista.length > 0 && (
        <div className="lista">
          {lista.map((it) => (
            <article className={'fila-herr' + (it.vencida ? ' vencida' : '')} key={it.id} data-testid="herramienta">
              <div className="fila-herr-info">
                <div className="fila-herr-nombre">
                  <strong>{it.nombre}</strong>
                  <span className="cant-chip">× {Number(it.cantidad)}</span>
                  {it.vencida
                    ? <span className="chip chip-mal"><Icono n="alerta" size={14} trazo={2.2} />Vencida</span>
                    : <span className="chip"><Icono n="reloj" size={14} trazo={2.2} />En campo</span>}
                </div>
                <small>{it.codigo} · Remisión <Link to={`/remisiones/${it.remision_id}`}>No. {it.remision_numero}</Link> · {it.proyecto_nombre}</small>
                <small>En poder de {it.recibida_por_nombre}</small>
                {it.devolver_antes_de && <small className={it.vencida ? 'txt-bad' : ''}>Devolver antes del {fmtDia(it.devolver_antes_de)}</small>}
              </div>
              <button className="btn btn-sec" onClick={() => devolver(it)}>Registrar devolución</button>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
