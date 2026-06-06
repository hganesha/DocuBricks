import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'
import { IncomingMessage, ServerResponse } from 'http'

const SCHEMAS_ROOT = path.resolve(__dirname, '../../Schemas')

function schemasStaticPlugin() {
  return {
    name: 'schemas-static',
    configureServer(server: { middlewares: { use: (path: string, handler: (req: IncomingMessage, res: ServerResponse, next: () => void) => void) => void } }) {
      server.middlewares.use('/schemas', (req: IncomingMessage, res: ServerResponse, next: () => void) => {
        const urlPath = (req.url || '').split('?')[0]
        const filePath = path.join(SCHEMAS_ROOT, urlPath)
        if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
          res.setHeader('Content-Type', 'application/json')
          res.setHeader('Cache-Control', 'no-cache')
          res.end(fs.readFileSync(filePath, 'utf-8'))
        } else {
          next()
        }
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), schemasStaticPlugin()],
})
