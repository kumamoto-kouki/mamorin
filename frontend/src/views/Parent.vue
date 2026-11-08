<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import QRCode from 'qrcode'
import { api, live, time } from '../lib/api'
import Mascot from '../components/Mascot.vue'

const strangers = ref([])
const messages = ref([])
const traces = ref([])
const qr = ref('')
const joinUrl = `${location.origin}/stranger`
const reveal = ref(null)
const friends = ref([])
let stop, revealTimer

const swaps = computed(() => messages.value.filter((m) => m.swapped?.length))
const tracesOf = (s) => traces.value.filter((t) => t.stranger_id === s.id).map((t) => ({ ...t, d: JSON.parse(t.detail) }))
const lastSwap = (s) => [...swaps.value].reverse().find((m) => m.stranger_id === s.id)
const sorted = computed(() => [...strangers.value].sort((a, b) => (tracesOf(b).length - tracesOf(a).length) || (b.risk - a.risk)))
const level = (r) => r >= 60 ? { t: 'とても あやしい', c: 'bg-coral' } : r >= 25 ? { t: 'ちょっと あやしい', c: 'bg-sun' } : { t: 'ようすを見ています', c: 'bg-mint-300' }

async function load() {
  const st = await api('/api/state')
  strangers.value = st.strangers; messages.value = st.messages; traces.value = st.traces
  friends.value = (await api('/api/config')).friends
}

onMounted(async () => {
  qr.value = await QRCode.toDataURL(joinUrl, { margin: 1, width: 360, color: { dark: '#13343b', light: '#ffffff' } })
  await load()
  stop = live({ role: 'parent' }, (e) => {
    if (e.type === 'stranger') strangers.value.push(e.stranger)
    if (e.type === 'message') {
      messages.value.push(e.message)
      if (e.risk !== undefined) { const s = strangers.value.find((x) => x.id === e.message.stranger_id); if (s) s.risk = e.risk }
    }
    if (e.type === 'trace') {
      traces.value.push(e.trace)
      const s = strangers.value.find((x) => x.id === e.trace.stranger_id)
      reveal.value = { name: s?.nickname, d: JSON.parse(e.trace.detail), kind: e.trace.kind }
      clearTimeout(revealTimer); revealTimer = setTimeout(() => (reveal.value = null), 9000)
    }
    if (e.type === 'reset') { strangers.value = []; messages.value = []; traces.value = [] }
  })
})
onUnmounted(() => stop && stop())

const leak = (s) => api(`/api/demo/leak/${s.id}`, {})
const reset = () => confirm('デモをリセットしますか？') && api('/api/reset', {})
</script>

<template>
  <div class="min-h-screen px-4 md:px-8 py-6">
    <header class="flex items-center gap-3">
      <Mascot :size="48" />
      <div class="flex-1">
        <p class="label-en">Parent Dashboard</p>
        <h1 class="text-2xl md:text-3xl font-black">ひなたを まもった記録</h1>
      </div>
      <button @click="reset" class="text-xs text-ink-soft underline">リセット</button>
    </header>

    <div class="mt-6 grid gap-6 lg:grid-cols-[340px_1fr]">
      <!-- 左: 参加QRと数字 -->
      <aside class="space-y-4">
        <div class="bg-white rounded-3xl p-5 shadow-sm text-center">
          <p class="label-en">Join Us!</p>
          <p class="font-bold mt-1">「あやしい大人」になって<br />ひなたにDMしてみよう</p>
          <img v-if="qr" :src="qr" alt="参加用QRコード" class="mx-auto mt-3 w-56 h-56 rounded-2xl" />
          <p class="text-xs text-ink-soft break-all mt-2">{{ joinUrl }}</p>
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div class="bg-white rounded-3xl p-4 text-center shadow-sm"><p class="text-4xl font-black">{{ strangers.length }}</p><p class="text-xs text-ink-soft mt-1">近づいてきた<br />大人</p></div>
          <div class="bg-white rounded-3xl p-4 text-center shadow-sm"><p class="text-4xl font-black text-mint-600">{{ swaps.length }}</p><p class="text-xs text-ink-soft mt-1">おとりに<br />すりかえ</p></div>
          <div class="bg-white rounded-3xl p-4 text-center shadow-sm"><p class="text-4xl font-black text-coral">{{ traces.length }}</p><p class="text-xs text-ink-soft mt-1">つかんだ<br />足取り</p></div>
        </div>
        <div class="bg-white rounded-3xl p-5 shadow-sm text-sm leading-relaxed">
          <p class="label-en">Rule</p>
          <p class="mt-1">知らない人には、いつでも おとり。<br />本物が届くのは、親が会って確認した友だちだけ。</p>
          <p class="mt-2 text-ink-soft">確認ずみ：{{ friends.join('、') || 'なし' }}</p>
        </div>
      </aside>

      <!-- 右: 相手ごとの記録 -->
      <section class="space-y-4">
        <div v-if="!strangers.length" class="bg-white rounded-3xl p-10 text-center text-ink-soft shadow-sm">QRコードから参加すると、ここに記録が出ます</div>
        <article v-for="s in sorted" :key="s.id" class="bg-white rounded-3xl p-5 shadow-sm pop">
          <div class="flex items-center gap-3 flex-wrap">
            <p class="text-xl font-black">{{ s.nickname }}</p>
            <span :class="['text-xs font-bold px-3 py-1 rounded-full', level(s.risk).c]">{{ level(s.risk).t }}</span>
            <div class="flex-1 min-w-24 h-2 bg-mint-100 rounded-full overflow-hidden"><div class="h-full bg-coral transition-all" :style="{ width: s.risk + '%' }" /></div>
            <button @click="leak(s)" class="text-xs px-3 py-1.5 rounded-full border border-mint-300 font-bold">流出を検知（デモ）</button>
          </div>

          <div v-if="lastSwap(s)" class="mt-4 grid md:grid-cols-2 gap-3 text-sm">
            <div class="rounded-2xl bg-mint-50 p-4"><p class="label-en">Kid typed</p><p class="mt-1 whitespace-pre-wrap">{{ lastSwap(s).original }}</p></div>
            <div class="rounded-2xl bg-ink text-white p-4"><p class="label-en !text-lime">Stranger got（おとり）</p><p class="mt-1 whitespace-pre-wrap break-all">{{ lastSwap(s).delivered }}</p></div>
          </div>
          <p v-else class="mt-3 text-sm text-ink-soft">まだ個人情報は聞かれていません</p>

          <ol v-if="tracesOf(s).length" class="mt-4 border-l-4 border-coral/60 pl-4 space-y-3">
            <li v-for="t in tracesOf(s)" :key="t.id" class="text-sm">
              <p class="font-bold">{{ time(t.ts) }}　{{ t.d.label }}</p>
              <p v-if="t.kind === 'open'" class="text-ink-soft">地域：{{ t.d.region }} ／ 端末：{{ t.d.device }} ／ IP：{{ t.d.ip }}</p>
              <p v-else class="text-ink-soft">場所：{{ t.d.where }} ／ 見つかった情報：{{ t.d.found }}</p>
            </li>
          </ol>
        </article>
      </section>
    </div>

    <!-- 種明かし -->
    <div v-if="reveal" @click="reveal = null" class="fixed inset-0 bg-ink/80 grid place-items-center p-6 z-50">
      <div class="bg-white rounded-[40px] p-10 max-w-2xl w-full text-center pop">
        <p class="text-7xl">🪤</p>
        <p class="label-en mt-4">Gotcha</p>
        <p class="text-4xl md:text-5xl font-black mt-2">それ、おとりです。</p>
        <p class="mt-4 text-lg">「{{ reveal.name }}」さんに渡したのは、本物ではない住所。</p>
        <p class="mt-1 text-ink-soft">{{ reveal.kind === 'open' ? `${reveal.d.region} の ${reveal.d.device} からアクセスがありました。` : `${reveal.d.where} に流れたのを見つけました。` }}</p>
      </div>
    </div>
  </div>
</template>
