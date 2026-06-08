<template>
  <LayoutLogin>
    <div id="view-privacy-policy">
      <PagePrivacyPolicy />
    </div>
  </LayoutLogin>
</template>

<script>
  /**
   * View wrapper for the privacy policy page. Renders PagePrivacyPolicy inside LayoutLogin.
   */
  import LayoutLogin from '/src/layouts/LayoutLogin'
  import PagePrivacyPolicy from '/src/pages/common/PagePrivacyPolicy'

  export default {
    name: 'ViewPrivacyPolicy',

    components: {
      PagePrivacyPolicy,
      LayoutLogin,
    },
  }
</script>

<style scoped lang="scss">
  #view-privacy-policy {
    margin: 30px auto;
    max-width: 900px;
    padding: 0 16px;
  }
</style>
