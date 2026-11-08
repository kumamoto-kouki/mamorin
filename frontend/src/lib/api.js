export async function api(path, body) {
  const res = await fetch(path, body === undefined ? {} : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// 自動で再接続する WebSocket
export function live(params, onEvent) {
  let ws, closed = false
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const connect = () => {
    ws = new WebSocket(`${proto}://${location.host}/ws?${new URLSearchParams(params)}`)
    ws.onmessage = (e) => onEvent(JSON.parse(e.data))
    ws.onclose = () => { if (!closed) setTimeout(connect, 1000) }
  }
  connect()
  return () => { closed = true; ws && ws.close() }
}

export const time = (ts) => new Date(ts * 1000).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
