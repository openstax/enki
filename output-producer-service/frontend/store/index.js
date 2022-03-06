import flattenObject from '@/store/utils.js'

export const state = () => ({
  jobs: [],
  content_servers: []
})

export const mutations = {
  REFRESH_JOBS: (state, value) => {
    state.jobs = value
  },
  REFRESH_CONTENT_SERVERS: (state, value) => {
    state.content_servers = value
  }
}

export const getters = {
  content_servers (state) {
    return state.content_servers
  },
  content_servers_items (state) {
    const data = []
    state.content_servers.forEach(function (item) {
      data.push({
        text: item.name,
        value: item.id
      })
    })
    return data
  }
}

function handleErrorAxios (error) {
  // this is optional and mostly for debugging on dev mode
  if (error.response) {
    // Request made and server responded
    console.log(error.response.data)
    console.log(error.response.status)
    console.log(error.response.headers)
  } else if (error.request) {
    // The request was made but no response was received
    console.log(error.request)
  } else {
    // Something happened in setting up the request that triggered an Error
    console.log('Error', error.message)
  }
  throw error
}

export const actions = {
  async nuxtServerInit ({ dispatch }, { error }) {
    try {
      await dispatch('getJobsForPage', { page: 0, limit: 50 })
      await dispatch('getContentServers')
    } catch (e) {
      error({ statusCode: 504, message: 'Backend is unreachable! Is the backend server up and running?' })
    }
  },
  async getJobsForPage ({ commit }, { page, limit }) {
    try {
      const response = await this.$axios.$get(`/api/jobs/pages/${page}?limit=${limit}`)
      const data = []
      response.forEach(function (item) {
        data.push(flattenObject(item))
      })
      // if (data.hasOwnProperty('collection_id')) {
      commit('REFRESH_JOBS', data)
    } catch (error) {
      handleErrorAxios(error)
    }
  },
  async getContentServers ({ commit }) {
    try {
      const response = await this.$axios.$get('/api/content-servers')
      commit('REFRESH_CONTENT_SERVERS', response)
    } catch (error) {
      handleErrorAxios(error)
    }
  }
}
