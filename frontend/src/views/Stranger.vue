<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { api, live } from '../lib/api'

const KEY = 'decoy-dm-stranger'
const me = ref(null)
const nickname = ref('')
const messages = ref([])
const draft = ref('')
const scroller = ref(null)
const ideas = ['こんにちは！何年生？', 'どこに住んでるの？', '何小学校？', '今度いっしょにあそぼうよ', 'LINE教えて']
let stop

const save = (v) => { try { v ? localStorage.setItem(KEY, JSON.stringify(v)) : localStorage.removeItem(KEY) } catch {} }
const restore = () => { try { return JSON.parse(localStorage.getItem(KEY)) } catch { return null } }
const scrollDown = () => nextTick(() => scroller.value && (scroller.value.scrollTop = 1e9))
const parts = (t) => t.split(/(https?:\/\/\S+)/g)

function connect() {
  stop && stop()
  stop = live({ role: 'stranger', sid: me.value.id }, (e) => {
    if (e.type === 'message') { messages.value.push(e.message); scrollDown() }
    if (e.type === 'reset') { me.value = null; messages.value = []; save(null) }
  })
}

onMounted(async () => {
  const saved = restore()
  if (saved) {
    try { messages.value = await api(`/api/strangers/${saved.id}/messages`); me.value = saved; connect(); scrollDown() }
    catch { save(null) }
  }
})
onUnmounted(() => stop && stop())

async function join() {
  me.value = await api('/api/strangers', { nickname: nickname.value })
  save(me.value); connect()
}
async function send(text = draft.value) {
  text = text.trim(); if (!text) return
  draft.value = ''
  await api('/api/stranger/say', { stranger_id: me.value.id, text })
}
</script>

<template>
  <div class="min-h-screen bg-slate-100 flex justify-center">
    <div class="w-full max-w-md min-h-screen bg-white flex flex-col">
      <header class="px-4 py-4 border-b border-slate-200 flex items-center gap-3">
        <div class="w-10 h-10 rounded-full bg-mint-200 grid place-items-center font-bold">ひ</div>
        <div class="flex-1">
          <p class="font-bold">ひなた</p>
          <p class="text-xs text-slate-500">小学生のアカウント</p>
        </div>
        <span class="text-[10px] font-bold tracking-widest text-coral border border-coral rounded-full px-2 py-0.5">あやしい大人 役</span>
      </header>

      <!-- 参加 -->
      <section v-if="!me" class="flex-1 px-6 py-10">
        <p class="label-en">Join the demo</p>
        <h1 class="text-2xl font-black mt-2 leading-snug">あなたは今から<br />「あやしい大人」です。</h1>
        <p class="text-slate-600 mt-3 leading-relaxed text-sm">小学生のひなたさんにDMを送って、住所や学校を聞き出してみてください。</p>
        <form @submit.prevent="join" class="mt-8 space-y-3">
          <input v-model="nickname" maxlength="16" placeholder="ニックネーム（例：やさしいお兄さん）" class="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none focus:border-mint-400" />
          <button class="w-full rounded-2xl brand-grad py-3 font-bold">DMをはじめる →</button>
        </form>
      </section>

      <!-- トーク -->
      <template v-else>
        <section ref="scroller" class="flex-1 overflow-y-auto px-4 py-4 space-y-3" style="max-height: calc(100vh - 190px)">
          <p v-if="!messages.length" class="text-center text-slate-400 text-sm mt-10">下の例を押すか、自由にメッセージを送ってください</p>
          <div v-for="m in messages" :key="m.id" :class="['flex', m.sender === 'stranger' ? 'justify-end' : 'justify-start']">
            <p :class="['max-w-[80%] px-4 py-2.5 rounded-2xl whitespace-pre-wrap break-all leading-relaxed text-[15px]',
              m.sender === 'stranger' ? 'bg-slate-800 text-white rounded-br-sm' : 'bg-slate-100 rounded-bl-sm']">
              <template v-for="(p, i) in parts(m.text)" :key="i">
                <a v-if="p.startsWith('http')" :href="p" target="_blank" class="underline text-mint-600 font-bold">{{ p }}</a>
                <template v-else>{{ p }}</template>
              </template>
            </p>
          </div>
        </section>
        <footer class="px-3 pb-4 pt-2 border-t border-slate-100">
          <div class="flex gap-2 overflow-x-auto pb-2">
            <button v-for="t in ideas" :key="t" @click="send(t)" class="shrink-0 px-3 py-1.5 rounded-full bg-slate-100 text-sm">{{ t }}</button>
          </div>
          <form @submit.prevent="send()" class="flex gap-2">
            <input v-model="draft" placeholder="メッセージ" class="flex-1 min-w-0 rounded-full bg-slate-100 px-4 py-3 outline-none" />
            <button class="shrink-0 px-5 rounded-full bg-slate-800 text-white font-bold">送信</button>
          </form>
        </footer>
      </template>
    </div>
  </div>
</template>
