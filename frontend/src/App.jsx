import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './componentes/Layout.jsx'
import Login from './paginas/Login.jsx'
import NuevaRemision from './paginas/NuevaRemision.jsx'
import Historial from './paginas/Historial.jsx'
import Detalle from './paginas/Detalle.jsx'
import Herramientas from './paginas/Herramientas.jsx'
import Panel from './paginas/Panel.jsx'
import Gestion from './paginas/Gestion.jsx'
import Pendientes from './paginas/Pendientes.jsx'
import Verificar from './paginas/Verificar.jsx'
import { useApp } from './contexto.jsx'

export default function App() {
  const { user } = useApp()
  return (
    <Routes>
      <Route path="/verificar/:id" element={<Verificar />} />
      {!user ? (
        <Route path="*" element={<Login />} />
      ) : (
        <Route element={<Layout />}>
          <Route path="/" element={<NuevaRemision />} />
          <Route path="/remisiones" element={<Historial />} />
          <Route path="/remisiones/:id" element={<Detalle />} />
          <Route path="/herramientas" element={<Herramientas />} />
          <Route path="/panel" element={<Panel />} />
          <Route path="/gestion" element={<Gestion />} />
          <Route path="/pendientes" element={<Pendientes />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      )}
    </Routes>
  )
}
