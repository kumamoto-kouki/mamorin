<script setup>
const links = [
  { to: '/kid', en: 'Kid', jp: '子どもの画面', note: '発表者がタブレットやスマホで開く' },
  { to: '/stranger', en: 'Stranger', jp: '「あやしい大人」の画面', note: '会場の人がQRから開く' },
  { to: '/parent', en: 'Parent', jp: '保護者の画面', note: 'スクリーンに映す' },
]
</script>
<template>
  <main class="min-h-screen px-4 py-12 max-w-3xl mx-auto">
    <p class="label-en">Demo</p>
    <h1 class="text-4xl md:text-5xl font-black leading-tight mt-2">気づかないうちに、<br />まもられている。</h1>
    <p class="mt-4 text-ink-soft leading-relaxed">知らない人に本当の住所を教えてしまっても、届くのは「おとり」。小学生向けSNSの個人情報まもりのモックアップです。</p>
    <div class="mt-10 grid gap-4">
      <RouterLink v-for="l in links" :key="l.to" :to="l.to"
        class="group bg-white rounded-3xl p-6 flex items-center justify-between shadow-sm hover:shadow-md transition">
        <div>
          <p class="label-en">{{ l.en }}</p>
          <p class="text-xl font-bold mt-1">{{ l.jp }}</p>
          <p class="text-sm text-ink-soft mt-1">{{ l.note }}</p>
        </div>
        <span class="w-11 h-11 rounded-full brand-grad grid place-items-center text-ink text-xl group-hover:translate-x-1 transition">→</span>
      </RouterLink>
    </div>
    <p class="mt-10 text-xs text-ink-soft">登場する人物・住所・電話番号はすべて架空です。</p>
  </main>
</template>
