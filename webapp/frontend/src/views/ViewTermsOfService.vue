<template>
  <LayoutLogin>
    <div id="view-terms-of-service">
      <PageTermsOfService />
    </div>
  </LayoutLogin>
</template>

<script>
  /**
   * View wrapper for the terms of service page. Renders PageTermsOfService inside LayoutLogin.
   */
  import LayoutLogin from '/src/layouts/LayoutLogin'
  import PageTermsOfService from '/src/pages/common/PageTermsOfService'

  export default {
    name: 'ViewTermsOfService',

    components: {
      PageTermsOfService,
      LayoutLogin,
    },
  }
</script>

<style scoped lang="scss">
  #view-terms-of-service {
    margin: 30px auto;
    max-width: 900px;
    padding: 0 16px;
  }
</style>
