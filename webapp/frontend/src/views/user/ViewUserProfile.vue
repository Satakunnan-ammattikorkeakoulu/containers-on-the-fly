<template>
  <LayoutApp>
    <PageUserProfile />
  </LayoutApp>
</template>

<script>
  /**
   * View wrapper for the user profile page. Renders PageUserProfile inside LayoutApp.
   */
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