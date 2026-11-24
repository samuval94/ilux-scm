import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, blobUrl, descargar } from '../api.js'
import { useApp } from '../contexto.jsx'
import Estado from '../componentes/Estado.jsx'
import Icono from '../componentes/Icono.jsx'
import Dialogo from '../componentes/Dialogo.jsx'
import Esqueleto from '../componentes/Esqueleto.jsx'
import { etiquetaUnidad, fmtDia, fmtFecha } from '../util.js'

export default function Detalle() {
  const { id } = useParams()
  const { esAdmin, user, avisar, refrescar } = useApp()
  const nav = useNavigate()
  const [r, setR] = useState(null)
  const [firma, setFirma] = useState('')
  const [error, setError] = useState('')
  const [anulando, setAnulando] = useState(false)
  const [motivo, setMotivo] = useState('')
  const [ocupado, setOcupado] = useState(false)

  useEffect(() => {
    let url = ''
    api.get(`/remisiones/${id}/`).then(async (x) => {
      setR(x)
      if (x.tiene_firma) { try { url = await blobUrl(`/remisiones/${id}/firma/`); setFirma(url) } catch { /* sin imagen */ } }
    }).catch((e) => setError(e.message))
    return () => { if (url) URL.revokeObjectURL(url) }
  }, [id])

  const intentar = (fn) => fn().catch((e) => avisar(e.message, 'error'))

  async function anular() {
    setOcupado(true)
    try {
      setR(await api.post(`/remisiones/${id}/anular/`, { motivo }))
      setAnulando(false); refrescar(); avisar('Remisión anulada.')
    } catch (e) { avisar(e.message, 'error') } finally { setOcupado(false) }
  }

  async function eliminar() {
    if (!window.confirm('¿Eliminar este borrador?')) return
    try { await api.del(`/remisiones/${id}/`); refrescar(); nav('/remisiones') } catch (e) { avisar(e.message, 'error') }
  }

  if (error) return <div className="stack"><p className="msg-error" role="alert"><Icono n="alerta" size={18} />{error}</p><Link to="/remisiones" className="volver">Volver al historial</Link></div>
  if (!r) return <Esqueleto />

  return (
    <div className="stack">
      <Link to="/remisiones" className="volver"><Icono n="atras" size={18} /> Historial</Link>
      <div className="fila-titulo">
        <h1>{r.numero_formato ? <>Remisión <span className="num">No. {r.numero_formato}</span></> : 'Borrador sin firmar'}</h1>
        <Estado estado={r.estado} />
      </div>

      <section className="card">
        <dl className="datos">
          <div><dt>Proyecto</dt><dd>{r.proyecto_nombre}</dd></div>
          <div><dt>Entregado por</dt><dd>{r.entregada_por_nombre}</dd></div>
          <div><dt>Recibe</dt><dd>{r.recibida_por_nombre} · C.C. {r.recibida_por_cedula}</dd></div>
          <div><dt>Creada</dt><dd className="num">{fmtFecha(r.creada_en)}</dd></div>
          {r.firmada_en && <div><dt>Firmada</dt><dd className="num">{fmtFecha(r.firmada_en)}</dd></div>}
          {r.observaciones && <div><dt>Observaciones</dt><dd>{r.observaciones}</dd></div>}
        </dl>
        {r.estado === 'ANULADA' && (
          <p className="aviso-anulada"><Icono n="alerta" size={18} /><span>Anulada el {fmtFecha(r.anulada_en)} por {r.anulada_por_nombre}. Motivo: {r.motivo_anulacion}</span></p>
        )}
      </section>

      <section className="card tabla-scroll" role="region" aria-label="Ítems de la remisión" tabIndex={0}>
        <table className="tabla">
          <caption className="oculto-visual">Ítems ({r.items.length})</caption>
          <thead><tr><th>Código</th><th>Descripción ({r.items.length})</th><th className="num">Cantidad</th><th>Unidad</th></tr></thead>
          <tbody>
            {r.items.map((i) => (
              <tr key={i.id}>
                <td>{i.codigo}</td>
                <td>{i.nombre}{i.observacion && <small className="bloque muted">{i.observacion}</small>}
                  {i.devolver_antes_de && <small className="bloque muted">Devolver antes del {fmtDia(i.devolver_antes_de)}{i.devuelto ? ' · devuelto' : ''}</small>}</td>
                <td className="num"><strong>{Number(i.cantidad).toLocaleString('es-CO')}</strong></td>
                <td>{etiquetaUnidad(i.unidad)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {r.tiene_firma && (
        <section className="card">
          <h2>Firma de quien recibe</h2>
          {firma ? <img className="firma-img" src={firma} alt="Firma de quien recibe" /> : <Esqueleto />}
          <p><strong>{r.firma_nombre}</strong> · C.C. {r.firma_cedula}</p>
        </section>
      )}

      <div className="fila-botones">
        <button className="btn btn-sec" onClick={() => intentar(() => descargar(`/remisiones/${id}/pdf/`))}><Icono n="pdf" /> Descargar PDF</button>
        <button className="btn btn-sec" onClick={() => intentar(() => descargar(`/remisiones/${id}/excel/`))}><Icono n="excel" /> Descargar Excel</button>
        {r.estado === 'BORRADOR' && (
          <>
            <Link className="btn btn-pri" to={`/?borrador=${r.id}`}>Continuar y firmar</Link>
            {(esAdmin || r.entregada_por === user.id) && <button className="btn btn-sec txt-bad" onClick={eliminar}>Eliminar borrador</button>}
          </>
        )}
        {r.estado === 'FIRMADA' && esAdmin && <button className="btn btn-sec txt-bad" onClick={() => setAnulando(true)}>Anular</button>}
      </div>

      {anulando && (
        <Dialogo titulo={`Anular remisión No. ${r.numero_formato}`} onCerrar={() => !ocupado && setAnulando(false)}>
          <div className="modal-cab"><h2>Anular remisión No. {r.numero_formato}</h2></div>
          <p className="muted">La anulación es definitiva y queda registrada con tu usuario. La remisión no se puede modificar ni borrar.</p>
          <label>Motivo (obligatorio)<textarea rows="3" value={motivo} onChange={(e) => setMotivo(e.target.value)} /></label>
          <div className="fila-botones">
            <button className="btn btn-sec" onClick={() => setAnulando(false)} disabled={ocupado}>Cancelar</button>
            <button className="btn btn-bad" onClick={anular} disabled={ocupado || motivo.trim().length < 5} data-testid="confirmar-anular">Anular remisión</button>
          </div>
        </Dialogo>
      )}
    </div>
  )
}
