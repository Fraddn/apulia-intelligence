<template>
  <section class="library">
    <PageHeader :title="t('library.title')" :info-title="t('library.infoTitle')" :items="INFO_KEYS.map((key) => t(`library.${key}`))">
      <template v-if="library.loaded.value" #after>
        <span class="muted library__count">{{ t('library.count', { count: n(items.length) }, items.length) }}</span>
      </template>
    </PageHeader>

    <Transition name="reveal">
      <div v-if="library.lastRemoved.value" class="card library__undo" role="status">
        <span>{{ t('library.removed', { name: library.lastRemoved.value.name }) }}</span>
        <button type="button" class="btn btn--small btn--round" @click="undo">{{ t('library.undo') }}</button>
        <button type="button" class="library__undo-close" :aria-label="t('info.close')" @click="library.lastRemoved.value = null">
          <AppIcon name="close" :size="16" />
        </button>
      </div>
    </Transition>

    <LoadState :loading="!library.loaded.value && !library.failed.value" :error="library.failed.value" @retry="library.load(true)">
      <div v-if="!items.length" class="card library__empty">
        <AppIcon name="bookmark" :size="28" />
        <p>{{ t('library.empty') }}</p>
        <RouterLink :to="{ name: 'companies' }" class="btn btn--primary btn--round">
          <AppIcon name="companies" :size="16" />
          {{ t('library.browse') }}
        </RouterLink>
      </div>

      <template v-else>
        <div class="card library__toolbar">
          <div class="library__search">
            <AppIcon name="search" class="library__search-icon" />
            <input
              v-model="filter"
              class="input library__search-input"
              type="search"
              :aria-label="t('library.filterLabel')"
              :placeholder="t('library.filterPlaceholder')"
            >
          </div>
          <select v-model="sort" class="input" :aria-label="t('library.sortLabel')">
            <option value="recent">{{ t('library.sort.recent') }}</option>
            <option value="name">{{ t('library.sort.name') }}</option>
            <option value="funding">{{ t('library.sort.funding') }}</option>
          </select>
          <div class="library__compare">
            <span class="muted">{{ t('library.selected', { count: selected.length, max: MAX_COMPARE }) }}</span>
            <button v-if="selected.length" type="button" class="btn btn--small btn--round" @click="selected = []">
              {{ t('library.clearSelection') }}
            </button>
            <RouterLink
              v-if="selected.length >= 2"
              :to="{ name: 'compare', query: { vats: selected.join(',') } }"
              class="btn btn--primary btn--small btn--round"
            >
              <AppIcon name="compare" :size="16" />
              {{ t('library.compareSelected') }}
            </RouterLink>
            <span v-else class="btn btn--small btn--round library__compare-disabled" aria-disabled="true" :title="t('library.compareHint')">
              <AppIcon name="compare" :size="16" />
              {{ t('library.compareSelected') }}
            </span>
          </div>
        </div>

        <p v-if="!visible.length" class="card library__none muted">{{ t('library.noMatches') }}</p>

        <ul v-else class="library__grid">
          <li
            v-for="item in visible"
            :key="item.vat_number"
            class="card library__item"
            :class="{ 'library__item--selected': selected.includes(item.vat_number) }"
          >
            <div class="library__item-head">
              <label class="library__pick" :title="t('library.pick')">
                <input
                  type="checkbox"
                  :checked="selected.includes(item.vat_number)"
                  :disabled="!selected.includes(item.vat_number) && selected.length >= MAX_COMPARE"
                  :aria-label="t('library.pickNamed', { name: item.name })"
                  @change="pick(item.vat_number)"
                >
              </label>
              <div class="library__item-title">
                <RouterLink :to="{ name: 'company', params: { vat: item.vat_number } }" class="library__name">{{ item.name }}</RouterLink>
                <span class="meta-line library__meta">
                  <span class="mono">{{ item.vat_number }}</span>
                  <span v-if="item.province">{{ item.city ? `${item.city} (${item.province})` : t(`provinces.${item.province}`) }}</span>
                  <span v-if="item.ateco_section">{{ t(`sections.${item.ateco_section}`) }}</span>
                </span>
              </div>
              <button
                type="button"
                class="library__remove"
                :aria-label="t('library.removeNamed', { name: item.name })"
                :title="t('library.removeNamed', { name: item.name })"
                :disabled="library.pending.value.has(item.vat_number)"
                @click="removeItem(item.vat_number)"
              >
                <AppIcon name="trash" :size="18" />
              </button>
            </div>

            <dl class="library__facts">
              <div>
                <dt>{{ t('companies.columns.projects') }}</dt>
                <dd :class="{ muted: !item.beneficiary_projects }">{{ item.beneficiary_projects ? n(item.beneficiary_projects) : '–' }}</dd>
              </div>
              <div>
                <dt>{{ t('companies.columns.funding') }}</dt>
                <dd :class="{ muted: item.sole_beneficiary_funding === null }">{{ item.sole_beneficiary_funding === null ? '–' : money(item.sole_beneficiary_funding) }}</dd>
              </div>
              <div>
                <dt>{{ t('library.savedOn') }}</dt>
                <dd>{{ formatDate(item.saved_at, locale) }}</dd>
              </div>
            </dl>

            <form v-if="editing === item.vat_number" class="library__note-form" @submit.prevent="saveNote(item.vat_number)">
              <textarea
                ref="noteInput"
                v-model="draft"
                class="input library__note-input"
                rows="3"
                :maxlength="NOTE_MAX"
                :aria-label="t('library.noteLabel', { name: item.name })"
                :placeholder="t('library.notePlaceholder')"
                @keydown.esc="editing = ''"
                @keydown.ctrl.enter="saveNote(item.vat_number)"
                @keydown.meta.enter="saveNote(item.vat_number)"
              />
              <div class="library__note-actions">
                <span class="muted library__note-count">{{ draft.length }} / {{ NOTE_MAX }}</span>
                <button type="button" class="btn btn--small btn--round" @click="editing = ''">{{ t('library.cancel') }}</button>
                <button type="submit" class="btn btn--primary btn--small btn--round" :disabled="library.pending.value.has(item.vat_number)">
                  {{ t('library.saveNote') }}
                </button>
              </div>
              <p v-if="noteFailed" class="library__note-error" role="alert">{{ t('library.noteFailed') }}</p>
            </form>
            <div v-else-if="item.note" class="library__note">
              <p class="library__note-text">{{ item.note }}</p>
              <div class="library__note-tools">
                <button type="button" class="library__note-tool" @click="edit(item)">
                  <AppIcon name="edit" :size="16" />
                  {{ t('library.editNote') }}
                </button>
                <button
                  type="button"
                  class="library__note-tool library__note-tool--danger"
                  :disabled="library.pending.value.has(item.vat_number)"
                  @click="deleteNote(item)"
                >
                  <AppIcon name="trash" :size="16" />
                  {{ t('library.deleteNote') }}
                </button>
              </div>
            </div>
            <p v-else-if="deletedNote?.vat === item.vat_number" class="library__note-deleted" role="status">
              <span class="muted">{{ t('library.noteDeleted') }}</span>
              <button type="button" class="btn btn--small btn--round" @click="restoreNote">{{ t('library.undo') }}</button>
            </p>
            <button v-else type="button" class="library__add-note" @click="edit(item)">
              <AppIcon name="plus" :size="16" />
              {{ t('library.addNote') }}
            </button>
            <p v-if="failedVat === item.vat_number" class="library__note-error" role="alert">{{ t('library.saveFailed') }}</p>
          </li>
        </ul>
      </template>
    </LoadState>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, useTemplateRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { SavedCompany } from '../api'
import AppIcon from '../components/AppIcon.vue'
import LoadState from '../components/LoadState.vue'
import PageHeader from '../components/PageHeader.vue'
import { formatCurrency, formatDate, formatNumber } from '../format'
import { useLibrary } from '../library'

type Sort = 'recent' | 'name' | 'funding'

const INFO_KEYS = ['info1', 'info2', 'info3']
const MAX_COMPARE = 4
const NOTE_MAX = 500

const { t, locale } = useI18n()
const library = useLibrary()
const filter = ref('')
const sort = ref<Sort>('recent')
const selected = ref<string[]>([])
const editing = ref('')
const draft = ref('')
const noteFailed = ref(false)
const noteInput = useTemplateRef<HTMLTextAreaElement[]>('noteInput')

onMounted(() => {
  library.lastRemoved.value = null
  library.load()
})

const items = computed(() => library.items.value)

watch(items, (list) => {
  const vats = new Set(list.map((item) => item.vat_number))
  selected.value = selected.value.filter((vat) => vats.has(vat))
})

const n = (value: number) => formatNumber(value, locale.value)
const money = (value: number) => formatCurrency(value, locale.value)

const visible = computed(() => {
  const term = filter.value.trim().toLowerCase()
  const matches = term
    ? items.value.filter((item) =>
        [item.name, item.vat_number, item.city, item.note].some((text) => text.toLowerCase().includes(term)),
      )
    : [...items.value]
  if (sort.value === 'name') matches.sort((a, b) => a.name.localeCompare(b.name, locale.value))
  if (sort.value === 'funding') matches.sort((a, b) => (b.sole_beneficiary_funding ?? -1) - (a.sole_beneficiary_funding ?? -1))
  return matches
})

function pick(vat: string) {
  selected.value = selected.value.includes(vat)
    ? selected.value.filter((v) => v !== vat)
    : [...selected.value, vat].slice(0, MAX_COMPARE)
}

async function edit(item: SavedCompany) {
  deletedNote.value = null
  editing.value = item.vat_number
  draft.value = item.note
  noteFailed.value = false
  await nextTick()
  noteInput.value?.[0]?.focus()
}

const deletedNote = ref<{ vat: string; note: string } | null>(null)
const failedVat = ref('')

async function removeItem(vat: string) {
  failedVat.value = ''
  try {
    await library.remove(vat)
  } catch {
    failedVat.value = vat
  }
}

async function deleteNote(item: SavedCompany) {
  failedVat.value = ''
  try {
    await library.setNote(item.vat_number, '')
    deletedNote.value = { vat: item.vat_number, note: item.note }
  } catch {
    failedVat.value = item.vat_number
  }
}

async function restoreNote() {
  const previous = deletedNote.value
  if (!previous) return
  try {
    await library.setNote(previous.vat, previous.note)
    deletedNote.value = null
  } catch {
    failedVat.value = previous.vat
  }
}

async function undo() {
  try {
    await library.undoRemove()
  } catch {
    library.load(true)
  }
}

async function saveNote(vat: string) {
  noteFailed.value = false
  try {
    await library.setNote(vat, draft.value)
    editing.value = ''
  } catch {
    noteFailed.value = true
  }
}
</script>
