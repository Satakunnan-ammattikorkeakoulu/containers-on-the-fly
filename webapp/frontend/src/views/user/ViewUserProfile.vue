<template>
  <LayoutApp>
    <PageUserProfile />
  </LayoutApp>
</template>

<script>
  import LayoutApp from '@/layouts/LayoutApp.vue'
  import PageUserProfile from '@/pages/user/PageUserProfile.vue'

  export default {
    name: 'ViewUserProfile',
    components: {
      LayoutApp,
      PageUserProfile,
    }
  }
</script>