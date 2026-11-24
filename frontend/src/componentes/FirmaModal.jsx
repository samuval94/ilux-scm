import { useEffect, useRef, useState } from 'react'
import SignaturePad from 'signature_pad'
import Dialogo from './Dialogo.jsx'
import Icono from './Icono.jsx'

export default function FirmaModal({ receptor, resumen, enviando, error, onCancelar, onConfirmar }) {
  const canvas = useRef(null)
  const pad = useRef(null)
  const [nombre, setNombre] = useState(receptor?.nombre || '')
  const [cedula, setCedula] = useState(receptor?.cedula || '')
  const [vacia, setVacia] = useState(true)
  const [aviso, setAviso] = useState('')

  useEffect(() => {
    const c = canvas.current
    const ajustar = () => {
      const ratio = Math.max(window.devicePixelRatio || 1, 1)
      const datos = pad.current && !pad.current.isEmpty() ? pad.current.toData() : null
      c.width = c.offsetWidth * ratio
      c.height = c.offsetHeight * ratio
      c.getContext('2d').scale(ratio, ratio)
      pad.current?.clear()
      if (datos) pad.current.fromData(datos)
    }
    pad.current = new SignaturePad(c, { penColor: '#000000', minWidth: 1, maxWidth: 2.8 })
    pad.current.addEventListener('endStroke', () => setVacia(pad.current.isEmpty()))
    ajustar()
    window.addEventListener('resize', ajustar)
    return () => { window.removeEventListener('resize', ajustar); pad.current.off() }
  }, [])

  function confirmar() {
    if (pad.current.isEmpty()) return setAviso('Quien recibe debe firmar en el recuadro.')
    if (!nombre.trim() || !cedula.trim()) return setAviso('Escribe el nombre y la cédula de quien recibe.')
    setAviso('')
    onConfirmar({ imagen: pad.current.toDataURL('image/png'), nombre: nombre.trim(), cedula: cedula.trim() })
  }

  return (
    <Dialogo titulo="Firma de quien recibe" foco="caja" onCerrar={() => !enviando && onCancelar()}>
      <div className="modal-cab">
        <div className="cab-pagina">
          <h2>Firma de quien recibe</h2>
          <p className="muted">{resumen}</p>
        </div>
      </div>
      <div className="grid2">
        <label>Nombre<input value={nombre} onChange={(e) => setNombre(e.target.value)} autoComplete="off" /></label>
        <label>Cédula<input value={cedula} onChange={(e) => setCedula(e.target.value)} inputMode="numeric" autoComplete="off" /></label>
      </div>
      <div className="firma-caja">
        <canvas ref={canvas} className="firma-canvas" data-testid="firma-canvas" aria-label="Recuadro de firma. Dibuja con el dedo o el mouse." />
        {vacia && <span className="firma-hint">Firme aquí</span>}
      </div>
      {(aviso || error) && <p className="msg-error" role="alert"><Icono n="alerta" size={18} />{aviso || error}</p>}
      <div className="fila-botones">
        <button className="btn btn-sec" onClick={() => { pad.current.clear(); setVacia(true) }} disabled={enviando}>Limpiar</button>
        <button className="btn btn-sec" onClick={onCancelar} disabled={enviando}>Cancelar</button>
        <button className="btn btn-pri" onClick={confirmar} disabled={enviando}>{enviando ? 'Guardando…' : 'Firmar y guardar'}</button>
      </div>
    </Dialogo>
  )
}
