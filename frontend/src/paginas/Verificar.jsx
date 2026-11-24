import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api.js'
import { fmtFecha } from '../util.js'
import Icono from '../componentes/Icono.jsx'
import Esqueleto from '../componentes/Esqueleto.jsx'

// Página pública a la que lleva el QR impreso en el PDF.
export default function Verificar() {
  const { id } = useParams()
  const [d, setD] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { api.publico(`/verificar/${id}/`).then(setD).catch((e) => setError(e.message)) }, [id])
  return (
    <div className="acceso" style={{ gridTemplateColumns: '1fr' }}>
      <main className="acceso-panel">
        <div className="acceso-caja">
          <img className="acceso-logo-movil" style={{ display: 'block' }} src="/logo-ilux.png" alt="ILUX · Ingeniería, diseño y mantenimiento eléctrico" />
          <div className="cab-pagina">
            <h1>Verificación de remisión</h1>
            <p className="muted">Consulta pública del estado de una remisión emitida por ILUX.</p>
          </div>
          {error && <p className="msg-error" role="alert"><Icono n="alerta" size={18} />{error}</p>}
          {!d && !error && <Esqueleto />}
          {d && (
            <>
              <p className={'verif-estado ' + (d.anulada ? 'verif-mal' : 'verif-ok')}>
                <Icono n={d.anulada ? 'x' : 'check'} size={22} trazo={2.4} />
                {d.anulada ? 'Remisión anulada' : 'Firmada y vigente'}
              </p>
              <dl className="datos" style={{ gridTemplateColumns: '1fr 1fr' }}>
                <div><dt>Remisión</dt><dd className="num">No. {d.numero_formato}</dd></div>
                
                <div><dt>Proyecto</dt><dd>{d.proyecto_nombre}</dd></div>
                <div><dt>Firmada</dt><dd className="num">{fmtFecha(d.firmada_en)}</dd></div>
                <div><dt>Ítems</dt><dd className="num">{d.total_items}</dd></div>
              </dl>
            </>
          )}
        </div>
      </main>
    </div>
  )
}
