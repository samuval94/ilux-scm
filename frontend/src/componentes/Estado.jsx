import Icono from './Icono.jsx'

const TXT = { BORRADOR: 'Borrador', FIRMADA: 'Firmada', ANULADA: 'Anulada' }
const ICONO = { BORRADOR: 'lapiz', FIRMADA: 'check', ANULADA: 'x' }

// El estado nunca se comunica solo con color: icono + texto.
export default function Estado({ estado }) {
  return (
    <span className={'estado estado-' + estado.toLowerCase()}>
      <Icono n={ICONO[estado] || 'info'} size={14} trazo={2.4} />
      {TXT[estado] || estado}
    </span>
  )
}
