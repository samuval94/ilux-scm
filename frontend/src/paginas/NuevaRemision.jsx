import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api, descargar } from '../api.js'
import { useApp } from '../contexto.jsx'
import FirmaModal from '../componentes/FirmaModal.jsx'
import Icono from '../componentes/Icono.jsx'
import Scanner from '../componentes/Scanner.jsx'
import { aNumero, errorCantidad, etiquetaUnidad, guardar, leer, uuid } from '../util.js'

const vacia = () => ({ id: uuid(), proyecto: '', recibida_por: '', observaciones: '', items: [], servidor: false })

export default function NuevaRemision() {
  const { maestros, porCodigo, online, avisar, encolar } = useApp()
  const [params, setParams] = useSearchParams()
  const nav = useNavigate()
  const [rem, setRem] = useState(() => leer('ilux_borrador_actual', null) || vacia())
  const [texto, setTexto] = useState('')
  const [camara, setCamara] = useState(false)
  const [firmando, setFirmando] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [errorFirma, setErrorFirma] = useState('')
  const [resultado, setResultado] = useState(null)
  const [resaltado, setResaltado] = useState(null)
  const entrada = useRef(null)

  // El borrador de trabajo se conserva en el dispositivo (si se cierra la pestaña o se va la señal).
  useEffect(() => {
    guardar('ilux_borrador_actual', rem.items.length || rem.proyecto || rem.recibida_por ? rem : null)
  }, [rem])

  // Continuar un borrador guardado en el servidor: /?borrador=ID
  useEffect(() => {
    const id = params.get('borrador')
    if (!id) return
    setParams({}, { replace: true })
    api.get(`/remisiones/${id}/`).then((r) => {
      if (r.estado !== 'BORRADOR') return avisar('Esa remisión ya no es un borrador.', 'error')
      setRem({
        id: r.id, proyecto: String(r.proyecto), recibida_por: String(r.recibida_por), observaciones: r.observaciones || '', servidor: true,
        items: r.items.map((i) => ({
          material: i.material, codigo: i.codigo, nombre: i.nombre, unidad: i.unidad, tipo: i.tipo, admite_decimales: i.admite_decimales,
          cantidad: String(Number(i.cantidad)), observacion: i.observacion || '', devolver_antes_de: i.devolver_antes_de || '',
        })),
      })
    }).catch((e) => avisar(e.message, 'error'))
  }, [params, setParams, avisar])

  const receptor = maestros.empleados.find((e) => String(e.id) === String(rem.recibida_por))
  const cambiar = (campo, valor) => setRem((r) => ({ ...r, [campo]: valor }))

  const sugerencias = useMemo(() => {
    const q = texto.trim().toLowerCase()
    if (q.length < 2) return []
    const palabras = q.split(/\s+/)
    return maestros.catalogo
      .filter((m) => palabras.every((p) => m.nombre.toLowerCase().includes(p) || m.codigo.toLowerCase().includes(p)))
      .slice(0, 8)
  }, [texto, maestros.catalogo])

  function agregar(m) {
    setRem((r) => {
      const i = r.items.findIndex((x) => x.material === m.id)
      if (i >= 0) {
        const items = [...r.items]
        const n = aNumero(items[i].cantidad)
        items[i] = { ...items[i], cantidad: String((Number.isNaN(n) ? 0 : n) + 1) }
        return { ...r, items }
      }
      return {
        ...r,
        items: [...r.items, {
          material: m.id, codigo: m.codigo, nombre: m.nombre, unidad: m.unidad, tipo: m.tipo,
          admite_decimales: m.admite_decimales, cantidad: '1', observacion: '', devolver_antes_de: '',
        }],
      }
    })
    setResaltado(m.id)
    setTimeout(() => setResaltado(null), 1600)
    avisar(`${m.nombre} agregado`, 'ok')
    setTexto('')
    entrada.current?.focus()
  }

  async function buscarCodigo(codigo) {
    const c = String(codigo).trim()
    if (!c) return
    let m = porCodigo.get(c.toUpperCase())
    if (!m && online) {
      try { m = await api.get(`/materiales/por-codigo/${encodeURIComponent(c)}/`) } catch (e) { return avisar(e.message, 'error') }
    }
    if (!m) return avisar(`El código ${c} no está en el catálogo.`, 'error')
    agregar(m)
  }

  function alEnter(e) {
    if (e.key !== 'Enter') return
    e.preventDefault()
    const c = texto.trim()
    if (!c) return
    if (porCodigo.has(c.toUpperCase())) return buscarCodigo(c)
    if (sugerencias.length === 1) return agregar(sugerencias[0])
    if (sugerencias.length === 0) return buscarCodigo(c)
    avisar('Elige un material de la lista.', 'error')
  }

  function cambiarItem(id, campo, valor) {
    setRem((r) => ({ ...r, items: r.items.map((i) => (i.material === id ? { ...i, [campo]: valor } : i)) }))
  }
  function sumar(id, delta) {
    setRem((r) => ({
      ...r,
      items: r.items.map((i) => {
        if (i.material !== id) return i
        const n = aNumero(i.cantidad)
        const nuevo = Math.max(1, (Number.isNaN(n) ? 0 : n) + delta)
        return { ...i, cantidad: String(Math.round(nuevo * 100) / 100) }
      }),
    }))
  }
  const quitar = (id) => setRem((r) => ({ ...r, items: r.items.filter((i) => i.material !== id) }))

  const problemas = useMemo(() => {
    const p = []
    if (!rem.proyecto) p.push('Selecciona el proyecto.')
    if (!rem.recibida_por) p.push('Selecciona quién recibe.')
    if (!rem.items.length) p.push('Escanea o agrega al menos un ítem.')
    if (rem.items.some((i) => errorCantidad(i.cantidad, i.admite_decimales))) p.push('Corrige las cantidades marcadas en rojo.')
    return p
  }, [rem])

  const construirPayload = (extra = {}) => ({
    id: rem.id, proyecto: Number(rem.proyecto), recibida_por: Number(rem.recibida_por), observaciones: rem.observaciones,
    items: rem.items.map((i) => ({
      material: i.material, cantidad: String(aNumero(i.cantidad)), observacion: i.observacion || '',
      devolver_antes_de: i.tipo !== 'MATERIAL' && i.devolver_antes_de ? i.devolver_antes_de : null,
    })),
    firmar: false, ...extra,
  })

  async function guardarBorrador() {
    if (problemas.length) return avisar(problemas[0], 'error')
    try {
      await api.post('/remisiones/guardar/', construirPayload())
      setRem((r) => ({ ...r, servidor: true }))
      avisar('Borrador guardado en el servidor.')
    } catch (e) {
      avisar(e.sinConexion ? 'Sin conexión: el borrador quedó guardado en este dispositivo.' : e.message, e.sinConexion ? 'ok' : 'error')
    }
  }

  async function confirmarFirma(firma) {
    setEnviando(true); setErrorFirma('')
    const payload = construirPayload({ firmar: true, firma })
    try {
      const r = await api.post('/remisiones/guardar/', payload)
      setResultado({ tipo: 'enviada', remision: r })
      setFirmando(false); setRem(vacia())
    } catch (e) {
      if (e.sinConexion) {
        encolar(payload)
        setResultado({ tipo: 'cola' })
        setFirmando(false); setRem(vacia())
      } else setErrorFirma(e.message)
    } finally { setEnviando(false) }
  }

  async function descartar() {
    if (!window.confirm('¿Vaciar esta remisión? Se perderán los ítems cargados.')) return
    if (rem.servidor) { try { await api.del(`/remisiones/${rem.id}/`) } catch { /* ya no existe o sin red */ } }
    setRem(vacia())
  }

  if (resultado) return <Resultado r={resultado} onNueva={() => setResultado(null)} nav={nav} avisar={avisar} />

  const nombreProyecto = maestros.proyectos.find((p) => String(p.id) === String(rem.proyecto))?.nombre || ''

  return (
    <div className="stack">
      <div className="cab-pagina">
        <h1>Nueva remisión</h1>
        <p className="muted">Elige el proyecto y quién recibe, escanea los ítems y recoge la firma.</p>
      </div>

      <section className="card">
        <h2>Destino</h2>
        <div className="grid2">
          <label>Proyecto
            <select value={rem.proyecto} onChange={(e) => cambiar('proyecto', e.target.value)}>
              <option value="">Selecciona…</option>
              {maestros.proyectos.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
            </select>
          </label>
          <label>Recibe
            <select value={rem.recibida_por} onChange={(e) => cambiar('recibida_por', e.target.value)}>
              <option value="">Selecciona…</option>
              {maestros.empleados.map((p) => <option key={p.id} value={p.id}>{p.nombre} · {p.cedula}</option>)}
            </select>
          </label>
        </div>
      </section>

      <section className="card">
        <h2>Agregar ítems</h2>
        <div className="scan-fila">
          <div className="buscador">
            <label>Código de barras o nombre
              <input
                ref={entrada} value={texto} onChange={(e) => setTexto(e.target.value)} onKeyDown={alEnter}
                placeholder="Escanea con lector, escribe el código o busca por nombre" autoComplete="off" autoCapitalize="off" data-testid="buscar"
              />
            </label>
            {sugerencias.length > 0 && (
              <ul className="sugerencias" role="listbox">
                {sugerencias.map((m) => (
                  <li key={m.id}>
                    <button type="button" onClick={() => agregar(m)}>
                      <strong>{m.nombre}</strong>
                      <small>{m.codigo} · {etiquetaUnidad(m.unidad)}{m.tipo !== 'MATERIAL' ? ` · ${m.tipo.toLowerCase()}` : ''}</small>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <button className="btn btn-dark" onClick={() => setCamara((c) => !c)} aria-pressed={camara}>
            <Icono n="camara" /> {camara ? 'Cerrar cámara' : 'Escanear'}
          </button>
        </div>
        {camara && <Scanner onCodigo={buscarCodigo} onCerrar={() => setCamara(false)} />}
        {!maestros.catalogo.length && <p className="msg-error"><Icono n="alerta" size={18} />El catálogo aún no se ha descargado. Conéctate una vez para guardarlo en el dispositivo.</p>}
      </section>

      <section className="stack-sm">
        <div className="fila-titulo">
          <h2>Ítems ({rem.items.length})</h2>
          {rem.items.length > 0 && <button className="btn-link" onClick={descartar}>Vaciar</button>}
        </div>
        {rem.items.length === 0 && (
          <div className="vacio">
            <Icono n="caja" size={28} />
            <strong>Aún no hay ítems</strong>
            <span>Escanea un código de barras o busca por nombre para empezar.</span>
          </div>
        )}
        {rem.items.length > 0 && (
          <div className="items">
            {rem.items.map((i) => {
              const err = errorCantidad(i.cantidad, i.admite_decimales)
              return (
                <article key={i.material} className={'item' + (resaltado === i.material ? ' item-nuevo' : '')} data-testid="item">
                  <div className="item-info">
                    <strong>{i.nombre}</strong>
                    <small>{i.codigo} · {etiquetaUnidad(i.unidad)}{i.tipo !== 'MATERIAL' ? ` · ${i.tipo.toLowerCase()}` : ''}</small>
                  </div>
                  <div className="cantidad">
                    <button className="btn-icono" onClick={() => sumar(i.material, -1)} aria-label={`Restar uno a ${i.nombre}`}><Icono n="menos" /></button>
                    <input
                      value={i.cantidad} onChange={(e) => cambiarItem(i.material, 'cantidad', e.target.value)} inputMode="decimal"
                      className={err ? 'invalido' : ''} aria-label={`Cantidad de ${i.nombre}`} aria-invalid={!!err} data-testid="cantidad"
                    />
                    <button className="btn-icono" onClick={() => sumar(i.material, 1)} aria-label={`Sumar uno a ${i.nombre}`}><Icono n="mas" /></button>
                    <span className="unidad">{etiquetaUnidad(i.unidad)}</span>
                    <button className="btn-icono btn-quitar" onClick={() => quitar(i.material)} aria-label={`Quitar ${i.nombre}`}><Icono n="x" /></button>
                  </div>
                  {err && <p className="msg-error"><Icono n="alerta" size={16} />{err}</p>}
                  {i.tipo !== 'MATERIAL' && (
                    <label className="inline">Devolver antes de
                      <input type="date" value={i.devolver_antes_de} onChange={(e) => cambiarItem(i.material, 'devolver_antes_de', e.target.value)} style={{ width: 'auto' }} />
                    </label>
                  )}
                </article>
              )
            })}
          </div>
        )}
      </section>

      <section className="card">
        <label>Observaciones
          <textarea rows="2" value={rem.observaciones} onChange={(e) => cambiar('observaciones', e.target.value)} placeholder="Opcional" />
        </label>
      </section>

      <div className="barra-accion">
        {problemas.length > 0 && rem.items.length > 0
          ? <p><strong>Para firmar:</strong> {problemas[0]}</p>
          : <p>{rem.items.length} ítem(s){nombreProyecto ? ` · ${nombreProyecto}` : ''}</p>}
        <div className="fila-botones">
          <button className="btn btn-sec" onClick={guardarBorrador}>Guardar borrador</button>
          <button className="btn btn-pri" onClick={() => { setErrorFirma(''); setFirmando(true) }} disabled={problemas.length > 0} data-testid="firmar">
            <Icono n="firma" /> Firmar remisión
          </button>
        </div>
      </div>

      {firmando && (
        <FirmaModal
          receptor={receptor} enviando={enviando} error={errorFirma}
          resumen={`${rem.items.length} ítem(s) para ${nombreProyecto}. Al firmar la remisión queda bloqueada.`}
          onCancelar={() => setFirmando(false)} onConfirmar={confirmarFirma}
        />
      )}
    </div>
  )
}

function Resultado({ r, onNueva, nav, avisar }) {
  const intentar = (fn) => fn().catch((e) => avisar(e.message, 'error'))
  if (r.tipo === 'cola') {
    return (
      <div className="card centrado stack resultado">
        <div className="sello sello-warn"><Icono n="sinred" size={30} /></div>
        <h1>Firmada y guardada en el dispositivo</h1>
        <p className="muted">No hay conexión con el servidor. La remisión se enviará automáticamente cuando vuelva la señal y recibirá su número oficial en ese momento.</p>
        <div className="fila-botones centro">
          <Link className="btn btn-sec" to="/pendientes">Ver pendientes</Link>
          <button className="btn btn-pri" onClick={onNueva}>Nueva remisión</button>
        </div>
      </div>
    )
  }
  const x = r.remision
  return (
    <div className="card centrado stack resultado">
      <div className="sello sello-ok"><Icono n="check" size={30} trazo={2.4} /></div>
      <h1>Remisión No. <span className="num-grande">{x.numero_formato}</span> firmada</h1>
      <p className="muted">{x.total_items} ítem(s) · {x.proyecto_nombre}<br />Recibió: {x.recibida_por_nombre}</p>
      <div className="fila-botones centro">
        <button className="btn btn-sec" onClick={() => intentar(() => descargar(`/remisiones/${x.id}/pdf/`))}><Icono n="pdf" /> PDF</button>
        <button className="btn btn-sec" onClick={() => intentar(() => descargar(`/remisiones/${x.id}/excel/`))}><Icono n="excel" /> Excel</button>
        <button className="btn btn-sec" onClick={() => nav(`/remisiones/${x.id}`)}>Ver detalle</button>
        <button className="btn btn-pri" onClick={onNueva} data-testid="otra">Nueva remisión</button>
      </div>
    </div>
  )
}
