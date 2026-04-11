<template>
  <div>
    <label v-if="label" :for="inputId" class="label">{{ label }}</label>
    <input
      :id="inputId"
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :class="['input', error ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : '']"
      v-bind="$attrs"
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    />
    <p v-if="error" class="mt-1 text-xs text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'

  interface Props {
    modelValue: string
    type?: string
    label?: string
    placeholder?: string
    disabled?: boolean
    error?: string
  }

  withDefaults(defineProps<Props>(), {
    type: 'text',
    disabled: false,
  })

  defineEmits<{ 'update:modelValue': [value: string] }>()

  // 為每個 input 產生唯一 ID 以正確建立 <label for="..."> 關聯，
  // 確保點擊 label 能聚焦對應的 input（無障礙需求）。
  // 使用亂數而非 prop 是為了讓元件自給自足，呼叫端無需手動傳入 id。
  const inputId = computed(() => `input-${Math.random().toString(36).slice(2, 9)}`)
</script>
