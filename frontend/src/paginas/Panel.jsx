import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useApp } from '../contexto.jsx'
import Icono from '../componentes/Icono.jsx'
import Esqueleto from '../componentes/Esqueleto.jsx'

const META = 95 // KPI 2: ≥ 95 % de remisiones con firma

// Panel de seguimiento. Formas elegidas por el trabajo de cada dato:
//  - una cifra principal contra una meta  -> cifra grande + medidor con marca de meta
//  - cifras sueltas                       -> fichas
//  - un todo repartido en 3 partes        -> barra segmentada (cada parte con su porcentaje y leyenda)
export default function Panel() {
  const { version } = useApp()
  const [d, setD] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { api.get('/resumen/').then(setD).catch((e) => setError(e.message)) }, [version])
  if (error) return <p className="msg-error" role="alert"><Icono n="alerta" size={18} />{error}</p>
  if (!d) return <Esqueleto />

  const pct = d.porcentaje_firmadas
  const cumple = pct !== null && pct >= META
  const partes = [
    { k: 'firmada', t: 'Firmadas', n: d.firmadas_total },
    { k: 'borrador', t: 'Borradores', n: d.borradores },
    { k: 'anulada', t: 'Anuladas', n: d.anuladas },
  ]
  const total = partes.reduce((a, p) => a + p.n, 0)

  const Ficha = ({ titulo, valor, nota, tono, icono }) => (
    <div className={'kpi' + (tono ? ' kpi-' + tono : '')}>
      <span className="kpi-t">{titulo}</span>
      <span className="kpi-v">{valor}</span>
      <span className="kpi-n">{icono && <Icono n={icono} size={16} trazo={2.2} />}{nota}</span>
    </div>
  )

  return (
    <div className="stack">
      <div className="cab-pagina">
        <h1>Panel de seguimiento</h1>
        <p className="muted">Estado de las remisiones y de las herramientas en campo. La meta de firmas corresponde al KPI 2 del proyecto.</p>
      </div>

      <section className="card hero" aria-labelledby="hero-t">
        <div className="hero-izq">
          <h2 id="hero-t">Remisiones con firma</h2>
          <p className="hero-valor">{pct === null ? '—' : String(pct).replace('.', ',')}{pct !== null && <span>%</span>}</p>
        </div>
        <div className="hero-der">
          {pct !== null && (
            <div className={'medidor' + (cumple ? ' ok' : '')} role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow={pct} aria-label="Porcentaje de remisiones con firma">
              <div className="medidor-relleno" style={{ width: Math.min(pct, 100) + '%' }} />
              <span className="medidor-meta" style={{ left: META + '%' }} />
            </div>
          )}
          <div className="medidor-escala"><span>0%</span><span>100%</span></div>
          <p className="hero-nota">
            {pct === null
              ? 'Aún no hay remisiones para medir.'
              : cumple
                ? <><Icono n="check" size={18} trazo={2.4} />Meta cumplida. La línea marca el {META}%.</>
                : <><Icono n="alerta" size={18} trazo={2.2} />Por debajo de la meta del {META}% (línea en el medidor).</>}
          </p>
        </div>
      </section>

      <div className="kpis">
        <Ficha titulo="Firmadas hoy" valor={d.firmadas_hoy} />
        <Ficha titulo="Firmadas en total" valor={d.firmadas_total} />
        <Ficha
          titulo="Borradores sin firmar" valor={d.borradores}
          nota={`${d.borradores_antiguos} con más de 24 h`} tono={d.borradores_antiguos ? 'warn' : ''} icono={d.borradores_antiguos ? 'alerta' : undefined}
        />
        <Ficha titulo="Herramientas en campo" valor={d.herramientas_pendientes} />
        <Ficha
          titulo="Devoluciones vencidas" valor={d.herramientas_vencidas}
          nota={d.herramientas_vencidas ? 'Pide su devolución' : 'Todo al día'} tono={d.herramientas_vencidas ? 'bad' : 'ok'} icono={d.herramientas_vencidas ? 'alerta' : 'check'}
        />
        <Ficha titulo="Remisiones anuladas" valor={d.anuladas} />
      </div>

      <section className="card" aria-labelledby="seg-t">
        <h2 id="seg-t">Estado de las remisiones</h2>
        {total === 0 ? (
          <p className="muted">Todavía no hay remisiones registradas.</p>
        ) : (
          <>
            <div className="segmentada" role="img" aria-label={partes.map((p) => `${p.t}: ${p.n} (${Math.round((p.n / total) * 100)}%)`).join('; ')}>
              {partes.filter((p) => p.n > 0).map((p) => {
                const cuota = Math.round((p.n / total) * 100)
                return (
                  <div
                    key={p.k} className={'seg seg-' + p.k} style={{ flex: `${p.n} 1 0` }} tabIndex={0}
                    data-tip={`${p.t} · ${p.n} · ${cuota}%`} aria-label={`${p.t}: ${p.n} (${cuota}%)`}
                  >
                    {cuota >= 10 ? cuota + '%' : ''}
                  </div>
                )
              })}
            </div>
            <div className="leyenda">
              {partes.map((p) => <span key={p.k}><i style={{ background: `var(--dato-${p.k})` }} />{p.t} ({p.n})</span>)}
            </div>
          </>
        )}
      </section>
    </div>
  )
}
