import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'
import { useApp } from '../contexto.jsx'
import { TIPOS, UNIDADES } from '../util.js'
import Icono from '../componentes/Icono.jsx'

export default function Gestion() {
  const { esAdmin } = useApp()
  const [tab, setTab] = useState('catalogo')
  if (!esAdmin) return <p className="msg-error"><Icono n="alerta" size={18} />Esta sección es solo para administradores.</p>
  return (
    <div className="stack">
      <div className="cab-pagina">
        <h1>Gestión</h1>
        <p className="muted">Catálogo, proyectos y empleados que usa la aplicación.</p>
      </div>
      <div className="tabs" role="tablist">
        {[['catalogo', 'Catálogo'], ['proyectos', 'Proyectos'], ['empleados', 'Empleados']].map(([k, t]) => (
          <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? 'activa' : ''} onClick={() => setTab(k)}>{t}</button>
        ))}
      </div>
      {tab === 'catalogo' && <Catalogo />}
      {tab === 'proyectos' && <Simple ruta="/proyectos/" campos={[['nombre', 'Nombre del proyecto']]} />}
      {tab === 'empleados' && <Simple ruta="/empleados/" campos={[['nombre', 'Nombre completo'], ['cedula', 'Cédula']]} />}
    </div>
  )
}

function Catalogo() {
  const { avisar, cargarMaestros } = useApp()
  const [q, setQ] = useState('')
  const [tipo, setTipo] = useState('')
  const [datos, setDatos] = useState({ results: [], count: 0, next: null })
  const [nuevo, setNuevo] = useState({ codigo: '', nombre: '', grupo_nombre: '', unidad: 'UNIDAD', tipo: 'HERRAMIENTA' })
  const [archivo, setArchivo] = useState(null)
  const [desactivar, setDesactivar] = useState(false)
  const [resultado, setResultado] = useState('')

  const cargar = useCallback(() => {
    const p = new URLSearchParams({ todos: '1' })
    if (q) p.set('search', q)
    if (tipo) p.set('tipo', tipo)
    api.get('/materiales/?' + p).then(setDatos).catch((e) => avisar(e.message, 'error'))
  }, [q, tipo, avisar])
  useEffect(() => { const t = setTimeout(cargar, 250); return () => clearTimeout(t) }, [cargar])

  async function cambiar(m, campo, valor) {
    try {
      const r = await api.patch(`/materiales/${m.id}/`, { [campo]: valor })
      setDatos((d) => ({ ...d, results: d.results.map((x) => (x.id === m.id ? r : x)) }))
      cargarMaestros()
    } catch (e) { avisar(e.message, 'error') }
  }

  async function crear(e) {
    e.preventDefault()
    try {
      await api.post('/materiales/', nuevo)
      avisar('Ítem creado.'); setNuevo({ ...nuevo, codigo: '', nombre: '' }); cargar(); cargarMaestros()
    } catch (err) { avisar(err.message, 'error') }
  }

  async function importar(e) {
    e.preventDefault()
    if (!archivo) return
    const f = new FormData()
    f.append('archivo', archivo)
    f.append('desactivar_faltantes', desactivar ? '1' : '')
    try {
      const r = await api.upload('/catalogo/importar/', f)
      setResultado(`Importación lista: ${r.creados} creados, ${r.actualizados} actualizados, ${r.desactivados} desactivados.`)
      cargar(); cargarMaestros()
    } catch (err) { setResultado('Error: ' + err.message) }
  }

  return (
    <>
      <section className="card stack-sm">
        <h2>Importar catálogo (Excel o CSV)</h2>
        <p className="ayuda">Columnas requeridas: <code>sc_detalle_articulo</code>, <code>sc_detalle_grupo</code>, <code>k_sc_codigo_articulo</code>, <code>sc_tipo_unidad</code>. Opcional: <code>tipo</code> (MATERIAL, HERRAMIENTA o EQUIPO). Actualiza por código y nunca borra.</p>
        <form onSubmit={importar} className="fila-form">
          <input type="file" aria-label="Archivo del catálogo (Excel o CSV)" accept=".xls,.xlsx,.xlsm,.csv" onChange={(e) => setArchivo(e.target.files[0])} data-testid="archivo" />
          <label className="check"><input type="checkbox" checked={desactivar} onChange={(e) => setDesactivar(e.target.checked)} /> Desactivar los que no vengan en el archivo</label>
          <button className="btn btn-pri" disabled={!archivo}>Importar</button>
        </form>
        {resultado && <p className={resultado.startsWith('Error') ? 'msg-error' : 'msg-ok'} role="status">{resultado}</p>}
      </section>

      <section className="card stack-sm">
        <h2>Nuevo ítem (por ejemplo, una herramienta sin código impreso)</h2>
        <form onSubmit={crear} className="grid-form">
          <label>Código<input value={nuevo.codigo} onChange={(e) => setNuevo({ ...nuevo, codigo: e.target.value })} required /></label>
          <label>Nombre<input value={nuevo.nombre} onChange={(e) => setNuevo({ ...nuevo, nombre: e.target.value })} required /></label>
          <label>Grupo<input value={nuevo.grupo_nombre} onChange={(e) => setNuevo({ ...nuevo, grupo_nombre: e.target.value })} placeholder="VARIOS" /></label>
          <label>Unidad<select value={nuevo.unidad} onChange={(e) => setNuevo({ ...nuevo, unidad: e.target.value })}>{Object.keys(UNIDADES).map((u) => <option key={u}>{u}</option>)}</select></label>
          <label>Tipo<select value={nuevo.tipo} onChange={(e) => setNuevo({ ...nuevo, tipo: e.target.value })}>{Object.entries(TIPOS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
          <button className="btn btn-pri">Crear</button>
        </form>
      </section>

      <section className="stack-sm">
        <div className="filtros card">
          <label>Buscar<input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Código o nombre" /></label>
          <label>Tipo<select value={tipo} onChange={(e) => setTipo(e.target.value)}><option value="">Todos</option>{Object.entries(TIPOS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
        </div>
        <p className="ayuda">{datos.count} ítem(s). Cambia el tipo para que herramientas y equipos se rastreen hasta su devolución.</p>
        <div className="tabla-scroll card" role="region" aria-label="Catálogo de ítems" tabIndex={0}>
          <table className="tabla">
            <thead><tr><th>Código</th><th>Nombre</th><th>Grupo</th><th>Unidad</th><th>Tipo</th><th>Activo</th></tr></thead>
            <tbody>
              {datos.results.map((m) => (
                <tr key={m.id} className={m.activo ? '' : 'inactivo'}>
                  <td>{m.codigo}</td><td>{m.nombre}</td><td>{m.grupo}</td><td>{m.unidad}</td>
                  <td><select value={m.tipo} onChange={(e) => cambiar(m, 'tipo', e.target.value)} aria-label={`Tipo de ${m.nombre}`}>{Object.entries(TIPOS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></td>
                  <td><input type="checkbox" checked={m.activo} onChange={(e) => cambiar(m, 'activo', e.target.checked)} aria-label={`Activo ${m.nombre}`} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {datos.next && (
          <button className="btn btn-sec" onClick={async () => { const r = await api.get('/materiales/' + new URL(datos.next).search); setDatos((d) => ({ ...r, results: [...d.results, ...r.results] })) }}>
            Cargar más
          </button>
        )}
      </section>
    </>
  )
}

function Simple({ ruta, campos }) {
  const { avisar, cargarMaestros } = useApp()
  const [lista, setLista] = useState([])
  const [form, setForm] = useState({})
  const cargar = useCallback(() => api.get(ruta + '?todos=1').then(setLista).catch((e) => avisar(e.message, 'error')), [ruta, avisar])
  useEffect(() => { cargar() }, [cargar])

  async function crear(e) {
    e.preventDefault()
    try { await api.post(ruta, form); setForm({}); avisar('Creado.'); cargar(); cargarMaestros() } catch (err) { avisar(err.message, 'error') }
  }
  async function alternar(x) {
    try { await api.patch(`${ruta}${x.id}/`, { activo: !x.activo }); cargar(); cargarMaestros() } catch (err) { avisar(err.message, 'error') }
  }
  return (
    <>
      <section className="card">
        <form onSubmit={crear} className="grid-form">
          {campos.map(([k, t]) => <label key={k}>{t}<input value={form[k] || ''} onChange={(e) => setForm({ ...form, [k]: e.target.value })} required /></label>)}
          <button className="btn btn-pri">Agregar</button>
        </form>
      </section>
      <section className="card tabla-scroll" role="region" aria-label="Listado" tabIndex={0}>
        <table className="tabla">
          <thead><tr>{campos.map(([k, t]) => <th key={k}>{t}</th>)}<th>Activo</th></tr></thead>
          <tbody>
            {lista.map((x) => (
              <tr key={x.id} className={x.activo ? '' : 'inactivo'}>
                {campos.map(([k]) => <td key={k}>{x[k]}</td>)}
                <td><input type="checkbox" checked={x.activo} onChange={() => alternar(x)} aria-label={`Activo ${x.nombre}`} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  )
}
