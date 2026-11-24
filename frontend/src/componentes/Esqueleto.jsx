// Marcador de carga con la forma del contenido (en lugar de un "Cargando…" suelto).
export default function Esqueleto() {
  return (
    <div className="esqueleto" role="status" aria-busy="true" aria-label="Cargando">
      <span /><span /><span />
    </div>
  )
}
