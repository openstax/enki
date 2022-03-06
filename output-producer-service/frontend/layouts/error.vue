<template>
  <v-app>
    <div class="errorcontainer">
      <img
        src="/corgihat.png"
        style="width: 300px"
      ></img>
      <h1>
        {{ error.statusCode }}
      </h1>
      <h2 v-if="error.statusCode === 404">
        {{ pageNotFound }}
      </h2>
      <h2 v-else>
        {{ error.message }}
      </h2>
      <br>
      <br>
      <NuxtLink to="/">
        Home page
      </NuxtLink>
    </div>
  </v-app>
</template>

<script>
export default {
  layout: 'empty',
  props: {
    error: {
      type: Object,
      default: null
    }
  },
  data () {
    return {
      pageNotFound: 'Page not found',
      otherError: 'An error occurred'
    }
  },
  head () {
    const title =
      this.error.statusCode === 404 ? this.pageNotFound : this.otherError
    return {
      title
    }
  }
}
</script>

<style scoped>
body {
  background-color: white;
  color: black;
}
h1 {
  font-size: 38px;
  line-height: 200%;
}
h2 {
  font-size: 20px;
  line-height: 200%;
}
.errorcontainer {
    position: absolute;
    top: 50%;
    left: 50%;
    -moz-transform: translateX(-50%) translateY(-50%);
    -webkit-transform: translateX(-50%) translateY(-50%);
    transform: translateX(-50%) translateY(-50%);
    text-align: center;
}
</style>
