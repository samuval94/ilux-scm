import { useEffect, useRef, useState } from 'react'
import { Html5Qrcode, Html5QrcodeSupportedFormats as F } from 'html5-qrcode'
import { pitido } from '../util.js'

// Lector por cámara. Requiere HTTPS o localhost (regla del navegador).
export default function Scanner({ onCodigo, onCerrar }) {
  const [error, setError] = useState('')
  const ultimo = useRef({ codigo: '', t: 0 })
  const cb = useRef(onCodigo)
  cb.current = onCodigo

  useEffect(() => {
    if (!window.isSecureContext) {
      setError('La cámara solo funciona con HTTPS o en localhost. Usa un lector USB/Bluetooth, escribe el código, o abre la app con "npm run dev:https".')
      return
    }
    const lector = new Html5Qrcode('lector-camara', {
      formatsToSupport: [F.CODE_128, F.CODE_39, F.CODE_93, F.EAN_13, F.EAN_8, F.UPC_A, F.UPC_E, F.ITF, F.CODABAR, F.QR_CODE],
      useBarCodeDetectorIfSupported: true,
      verbose: false,
    })
    let vivo = true
    lector
      .start(
        { facingMode: 'environment' },
        {
          fps: 12,
          // Resolución alta: los códigos de barras finos la necesitan
          videoConstraints: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
          qrbox: (w, h) => ({ width: Math.max(160, w - 24), height: Math.max(90, Math.min(Math.round(h * 0.5), 180)) }),
        },
        (texto) => {
          const ahora = Date.now()
          if (texto === ultimo.current.codigo && ahora - ultimo.current.t < 2500) return
          ultimo.current = { codigo: texto, t: ahora }
          pitido()
          cb.current(texto)
        },
        () => {},
      )
      .catch((e) => {
        if (vivo) setError('No se pudo abrir la cámara: ' + (e?.message || e) + '. Revisa el permiso del navegador.')
      })
    return () => {
      vivo = false
      lector.isScanning ? lector.stop().then(() => lector.clear()).catch(() => {}) : (() => { try { lector.clear() } catch { /* nada */ } })()
    }
  }, [])

  return (
    <div className="scanner">
      <div id="lector-camara" />
      {error && <p className="msg-error">{error}</p>}
      <button className="btn btn-sec" onClick={onCerrar}>Cerrar cámara</button>
    </div>
  )
}
