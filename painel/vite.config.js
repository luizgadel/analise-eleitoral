import { spawn } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

function gravarSnapshot() {
  return {
    name: 'gravar-snapshot-apuracao',
    configureServer(server) {
      server.middlewares.use('/api/apuracao-snapshot', (req, res, next) => {
        if (req.method !== 'POST') return next()
        const pedido = new URL(req.url || '', 'http://localhost')
        const estadual = pedido.searchParams.get('destino') === 'estadual'
        const partes = []
        req.on('data', (parte) => partes.push(parte))
        req.on('end', () => {
          const proc = spawn('python', ['scripts/gravar_apuracao_2026.py', '--stdin'], {
            cwd: raiz,
            env: {
              ...process.env,
              APURACAO_DESTINO: path.join(
                raiz,
                'painel',
                'public',
                'dados',
                estadual ? 'amazonas-estadual.json' : 'amazonas.json',
              ),
              APURACAO_CARGO: estadual ? '7' : '6',
            },
          })
          let saida = ''
          proc.stdout.on('data', (parte) => {
            saida += parte
          })
          proc.stderr.on('data', (parte) => {
            saida += parte
          })
          proc.on('close', (codigo) => {
            res.statusCode = codigo === 0 ? 200 : 500
            res.end(saida)
          })
          proc.stdin.end(Buffer.concat(partes))
        })
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), gravarSnapshot()],
})
