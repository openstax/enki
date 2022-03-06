export default function ({ $axios, redirect }) {
  $axios.onRequest((config) => {
    console.log('Making request to ' + config.url)
    config.headers['Content-Type'] = 'application/json'
    return config
  })
}
