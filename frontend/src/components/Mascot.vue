<script setup>
defineProps({ size: { type: Number, default: 64 }, mood: { type: String, default: 'happy' } })
</script>
<template>
  <svg :width="size" :height="size" viewBox="0 0 100 100" aria-label="まもりん">
    <ellipse cx="50" cy="94" rx="26" ry="4" fill="#13343b" opacity=".08" />
    <path d="M50 8c22 0 38 16 38 40 0 26-17 42-38 42S12 74 12 48C12 24 28 8 50 8z" fill="#45c8ae" />
    <path d="M50 8c22 0 38 16 38 40 0 6-1 11-3 16C80 34 66 18 44 14c2-4 4-6 6-6z" fill="#7fdcc8" opacity=".7" />
    <circle cx="24" cy="18" r="7" fill="#45c8ae" /><circle cx="76" cy="18" r="7" fill="#45c8ae" />
    <template v-if="mood === 'worry'">
      <path d="M32 42q5-4 10 0M58 42q5-4 10 0" stroke="#13343b" stroke-width="4" fill="none" stroke-linecap="round" />
      <path d="M43 60q7-6 14 0" stroke="#13343b" stroke-width="4" fill="none" stroke-linecap="round" />
    </template>
    <template v-else>
      <circle cx="37" cy="44" r="5" fill="#13343b" /><circle cx="63" cy="44" r="5" fill="#13343b" />
      <circle cx="39" cy="42" r="1.6" fill="#fff" /><circle cx="65" cy="42" r="1.6" fill="#fff" />
      <path d="M42 55q8 7 16 0" stroke="#13343b" stroke-width="4" fill="none" stroke-linecap="round" />
    </template>
    <circle cx="27" cy="54" r="5" fill="#ff7a6b" opacity=".45" /><circle cx="73" cy="54" r="5" fill="#ff7a6b" opacity=".45" />
    <path d="M50 64l11 4v7c0 7-5 11-11 13-6-2-11-6-11-13v-7z" fill="#d6f36b" stroke="#13343b" stroke-width="2.5" stroke-linejoin="round" />
    <path d="M45 75l4 4 7-8" stroke="#13343b" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
</template>
