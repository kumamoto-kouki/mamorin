<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { api, live } from '../lib/api'
import Mascot from '../components/Mascot.vue'

const kid = ref(null)
const strangers = ref([])
const messages = ref([])
const current = ref(null)
const draft = ref('')
const unread = ref({})
const nudge = ref(null) // まもりんのふりかえり
const scroller = ref(null)

const colors = ['bg-sun', 'bg-coral/70', 'bg-mint-300', 'bg-lime']
const avatar = (s) => colors[s.id % colors.length]
const thread = computed(() => messages.value.filter((m) => m.stranger_id === current.value?.id))
const lastOf = (s) => [...messages.value].reverse().find((m) => m.stranger_id === s.id)

async function load() {
  kid.value = (await api('/api/config')).kid
  const st = await api('/api/state')
  strangers.value = st.strangers
  messages.value = st.messages.map((m) => ({ id: m.id, sender: m.sender, text: m.original, stranger_id: m.stranger_id }))
}

const scrollDown = () => nextTick(() => scroller.value && (scroller.value.scrollTop = 1e9))

let stop
onMounted(async () => {
  await load()
  stop = live({ role: 'kid' }, (e) => {
    if (e.type === 'stranger') strangers.value.push(e.stranger)
    if (e.type === 'message') {
      messages.value.push(e.message)
      if (e.message.stranger_id !== current.value?.id && e.message.sender === 'stranger')
        unread.value[e.message.stranger_id] = (unread.value[e.message.stranger_id] || 0) + 1
      scrollDown()
    }
    if (e.type === 'trace') {
      const s = strangers.value.find((x) => x.id === e.stranger_id)
      // 少し時間をおいて、さりげなくふりかえる
      setTimeout(() => (nudge.value = s?.nickname || 'さっきの人'), 2500)
    }
    if (e.type === 'reset') { strangers.value = []; messages.value = []; current.value = null; nudge.value = null }
  })
})
onUnmounted(() => stop && stop())

function open(s) { current.value = s; unread.value[s.id] = 0; scrollDown() }
async function send() {
  const text = draft.value.trim()
  if (!text || !current.value) return
  draft.value = ''
  await api('/api/kid/say', { stranger_id: current.value.id, text })
}
const chips = computed(() => kid.value ? [
  { label: 'おうち', text: `${kid.value.address} だよ` },
  { label: 'がっこう', text: `${kid.value.school}の${kid.value.grade}！` },
  { label: 'でんわ', text: `${kid.value.phone} だよ` },
  { label: 'スタンプ', text: '😊👍' },
] : [])
</script>

<template>
  <div class="min-h-screen bg-mint-100 flex justify-center font-round">
    <div class="w-full max-w-md min-h-screen bg-mint-50 flex flex-col relative">
      <!-- ヘッダー -->
      <header class="brand-grad px-4 pt-5 pb-4 rounded-b-[28px] shadow-sm">
        <div class="flex items-center gap-3">
          <button v-if="current" @click="current = null" class="w-10 h-10 rounded-full bg-white/70 text-xl font-bold" aria-label="もどる">←</button>
          <Mascot v-else :size="44" class="bob" />
          <div class="flex-1">
            <p class="text-xs font-bold text-ink/70">{{ current ? 'メッセージ' : 'なかよしトーク' }}</p>
            <p class="text-xl font-extrabold">{{ current ? current.nickname : `${kid?.name ?? ''}のトーク` }}</p>
          </div>
        </div>
      </header>

      <!-- トーク一覧 -->
      <section v-if="!current" class="flex-1 px-4 py-4 space-y-3">
        <p v-if="!strangers.length" class="text-center text-ink-soft mt-16 leading-loose">
          まだメッセージはないよ<br /><span class="text-sm">だれかから とどくのを まってるね</span>
        </p>
        <button v-for="s in strangers" :key="s.id" @click="open(s)"
          class="w-full bg-white rounded-3xl p-4 flex items-center gap-3 shadow-sm text-left active:scale-[.98] transition pop">
          <div :class="['w-12 h-12 rounded-full grid place-items-center text-lg font-extrabold', avatar(s)]">{{ s.nickname.slice(0, 1) }}</div>
          <div class="flex-1 min-w-0">
            <p class="font-extrabold">{{ s.nickname }}</p>
            <p class="text-sm text-ink-soft truncate">{{ lastOf(s)?.text ?? 'あたらしい ともだち？' }}</p>
          </div>
          <span v-if="unread[s.id]" class="min-w-6 h-6 px-2 rounded-full bg-coral text-white text-xs font-bold grid place-items-center">{{ unread[s.id] }}</span>
        </button>
      </section>

      <!-- トーク画面 -->
      <template v-else>
        <section ref="scroller" class="flex-1 overflow-y-auto px-4 py-4 space-y-3" style="max-height: calc(100vh - 210px)">
          <div v-for="m in thread" :key="m.id" :class="['flex', m.sender === 'kid' ? 'justify-end' : 'justify-start']">
            <p :class="['max-w-[78%] px-4 py-3 rounded-3xl whitespace-pre-wrap leading-relaxed pop',
              m.sender === 'kid' ? 'bg-mint-400 text-white rounded-br-md' : 'bg-white rounded-bl-md shadow-sm']">{{ m.text }}</p>
          </div>
        </section>
        <footer class="px-3 pb-4 pt-2 bg-mint-50">
          <div class="flex gap-2 overflow-x-auto pb-2">
            <button v-for="c in chips" :key="c.label" @click="draft = c.text"
              class="shrink-0 px-3 py-1.5 rounded-full bg-white border border-mint-200 text-sm font-bold">{{ c.label }}</button>
          </div>
          <form @submit.prevent="send" class="flex gap-2">
            <input v-model="draft" placeholder="メッセージを かく" class="flex-1 min-w-0 rounded-full bg-white px-5 py-3 outline-none border-2 border-transparent focus:border-mint-300" />
            <button class="shrink-0 w-12 h-12 rounded-full brand-grad text-xl font-extrabold" aria-label="おくる">➤</button>
          </form>
        </footer>
      </template>

      <!-- まもりんの ふりかえり -->
      <div v-if="nudge" class="absolute inset-x-3 bottom-28 bg-white rounded-3xl p-4 shadow-lg flex gap-3 items-start pop border-2 border-mint-200">
        <Mascot :size="56" mood="worry" />
        <div class="flex-1">
          <p class="font-extrabold">まもりん</p>
          <p class="text-sm leading-relaxed mt-1">さっきの「{{ nudge }}」さん、ちょっと あやしかったね。おうちや がっこうは、しらない人には ないしょに しようね。</p>
          <button @click="nudge = null" class="mt-2 px-4 py-1.5 rounded-full bg-mint-100 text-sm font-bold">わかった！</button>
        </div>
      </div>
    </div>
  </div>
</template>
