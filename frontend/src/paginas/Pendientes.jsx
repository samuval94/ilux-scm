import { useApp } from '../contexto.jsx'
import { fmtFecha } from '../util.js'
import Icono from '../componentes/Icono.jsx'

export default function Pendientes() {
  const { cola, enviarCola, descartarCola, online, avisar } = useApp()
  return (
    <div className="stack">
      <div className="cab-pagina">
        <h1>Pendientes de enviar</h1>
        <p className="muted">Remisiones firmadas sin señal. Se envían solas al volver la conexión.</p>
      </div>
      {cola.length === 0 && (
        <div className="vacio">
          <Icono n="check" size={28} />
          <strong>No hay remisiones pendientes</strong>
          <span>Todo lo firmado ya está en el servidor.</span>
        </div>
      )}
      {cola.length > 0 && (
        <div className="lista">
          {cola.map((c) => (
            <article className="fila-herr" key={c.payload.id}>
              <div className="fila-herr-info">
                <strong>{c.payload.items.length} ítem(s) · firmada {fmtFecha(c.creada)}</strong>
                <small>ID {c.payload.id}</small>
                {c.error && <p className="msg-error"><Icono n="alerta" size={16} />El servidor la rechazó: {c.error}</p>}
              </div>
              <button className="btn btn-sec txt-bad" onClick={() => window.confirm('¿Descartar esta remisión? No se podrá recuperar.') && descartarCola(c.payload.id)}>Descartar</button>
            </article>
          ))}
        </div>
      )}
      {cola.length > 0 && (
        <button className="btn btn-pri" disabled={!online} onClick={async () => { const n = await enviarCola(); if (!n) avisar('No se pudo enviar todavía.', 'error') }}>
          Reintentar ahora
        </button>
      )}
    </div>
  )
}
