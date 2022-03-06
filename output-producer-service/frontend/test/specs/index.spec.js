import { createLocalVue, shallowMount } from '@vue/test-utils'
import test from 'ava'
import Index from '@/pages/index'
import Vuetify from 'vuetify'
import Vuex from 'vuex'

const localVue = createLocalVue()
localVue.use(Vuex)
localVue.use(Vuetify)

let vuetify
let store
test.beforeEach((t) => {
  vuetify = new Vuetify()
  store = new Vuex.Store({
    state: () => {},
    actions: () => {},
    mutations: () => {},
    getters: () => {}
  })
})

test('properly parses pdf_url', (t) => {
  const wrapper = shallowMount(Index, {
    localVue,
    vuetify,
    store
  })
  const getUrlEntries = wrapper.vm.getUrlEntries

  const nothing = null
  t.deepEqual(getUrlEntries(nothing), [])

  const exampleSite = 'https://www.example.com'
  t.deepEqual(getUrlEntries(exampleSite), [{ text: 'View', href: exampleSite }])

  const multipleEntries = [
    { text: 'text', href: 'href' },
    { text: 'text2', href: 'href2' }
  ]
  t.deepEqual(getUrlEntries(JSON.stringify(multipleEntries)), multipleEntries)
})
