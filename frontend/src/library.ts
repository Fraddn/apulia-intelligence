import { computed, ref, watch } from 'vue'
import { api, type SavedCompany } from './api'
import { useSession } from './session'

const items = ref<SavedCompany[]>([])
const loaded = ref(false)
const loading = ref(false)
const failed = ref(false)
const pending = ref(new Set<string>())
const lastRemoved = ref<SavedCompany | null>(null)
let request: Promise<void> | null = null

export function resetLibrary() {
  items.value = []
  lastRemoved.value = null
  loaded.value = false
  failed.value = false
  request = null
}

const { user } = useSession()
watch(() => user.value?.id, resetLibrary)

const savedVats = computed(() => new Set(items.value.map((item) => item.vat_number)))

function load(force = false): Promise<void> {
  if (loaded.value && !force) return Promise.resolve()
  if (request && !force) return request
  loading.value = true
  failed.value = false
  request = api
    .library()
    .then((list) => {
      items.value = list
      loaded.value = true
    })
    .catch(() => {
      failed.value = true
    })
    .finally(() => {
      loading.value = false
      request = null
    })
  return request
}

async function busy<T>(vat: string, work: () => Promise<T>): Promise<T> {
  pending.value = new Set(pending.value).add(vat)
  try {
    return await work()
  } finally {
    const next = new Set(pending.value)
    next.delete(vat)
    pending.value = next
  }
}

async function save(vat: string) {
  if (lastRemoved.value?.vat_number === vat) lastRemoved.value = null
  const item = await busy(vat, () => api.save(vat))
  items.value = [item, ...items.value.filter((i) => i.vat_number !== vat)]
}

async function remove(vat: string) {
  await busy(vat, () => api.unsave(vat))
  lastRemoved.value = items.value.find((i) => i.vat_number === vat) ?? null
  items.value = items.value.filter((i) => i.vat_number !== vat)
}

async function undoRemove() {
  const item = lastRemoved.value
  if (!item) return
  lastRemoved.value = null
  await save(item.vat_number)
  if (item.note) await setNote(item.vat_number, item.note)
}

async function toggle(vat: string) {
  return savedVats.value.has(vat) ? remove(vat) : save(vat)
}

async function setNote(vat: string, note: string) {
  const item = await busy(vat, () => api.saveNote(vat, note))
  items.value = items.value.map((i) => (i.vat_number === vat ? item : i))
}

export function useLibrary() {
  return {
    items,
    loaded,
    loading,
    failed,
    pending,
    lastRemoved,
    savedVats,
    load,
    save,
    remove,
    toggle,
    setNote,
    undoRemove,
    isSaved: (vat: string) => savedVats.value.has(vat),
  }
}
