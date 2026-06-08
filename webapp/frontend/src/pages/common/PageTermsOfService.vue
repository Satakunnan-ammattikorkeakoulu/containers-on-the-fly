<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <div class="text-center mb-4">
          <h1 class="text-h4">Terms of Service</h1>
          <p v-if="organizationName" class="text-subtitle-1 text-grey mt-1">{{ organizationName }}</p>
        </div>

        <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4"></v-progress-linear>

        <v-alert v-if="error" type="warning" variant="outlined" class="mb-4">
          {{ errorMessage }}
        </v-alert>

        <div v-if="renderedContent" class="legal-content" v-html="renderedContent"></div>

        <div v-if="!loading && !error && !renderedContent" class="text-center text-grey pa-4">
          No content has been configured yet.
        </div>

        <div class="text-center mt-6">
          <v-btn variant="text" color="primary" prepend-icon="mdi-arrow-left" @click="goBack">Back</v-btn>
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
  /**
   * Terms of service page. Fetches Markdown content from the legal API
   * and renders it as HTML. Accessible without authentication.
   */
  import axios from 'axios'
  import { marked } from 'marked'
  import DOMPurify from 'dompurify'
  import { fillTemplate } from '/src/helpers/legalTemplates'

  export default {
    name: 'PageTermsOfService',

    data: () => ({
      loading: true,
      error: false,
      errorMessage: '',
      rawContent: '',
      organizationName: '',
      contactEmail: '',
      lastUpdated: ''
    }),

    computed: {
      renderedContent() {
        if (!this.rawContent) return ''
        const filled = fillTemplate(this.rawContent, this.organizationName, this.contactEmail, this.lastUpdated)
        return DOMPurify.sanitize(marked.parse(filled))
      }
    },

    mounted() {
      this.fetchContent()
    },

    methods: {
      goBack() {
        if (window.history.length > 1) {
          this.$router.back()
        } else {
          this.$router.push('/')
        }
      },

      fetchContent() {
        this.loading = true
        this.error = false

        axios.get(this.$appSettings.APIServer.legal.get_terms_of_service)
          .then((response) => {
            if (response.data && response.data.status) {
              this.rawContent = response.data.data.content || ''
              this.organizationName = response.data.data.organizationName || ''
              this.contactEmail = response.data.data.contactEmail || ''
              this.lastUpdated = response.data.data.lastUpdated || ''
            } else {
              this.error = true
              this.errorMessage = response.data?.message || 'Terms of service are not available.'
            }
          })
          .catch(() => {
            this.error = true
            this.errorMessage = 'Could not load the terms of service.'
          })
          .finally(() => {
            this.loading = false
          })
      }
    }
  }
</script>

<style scoped>
.legal-content {
  text-align: left;
  line-height: 1.7;
}

.legal-content :deep(h1) {
  font-size: 1.5rem;
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
}

.legal-content :deep(h2) {
  font-size: 1.25rem;
  margin-top: 1.25rem;
  margin-bottom: 0.5rem;
}

.legal-content :deep(h3) {
  font-size: 1.1rem;
  margin-top: 1rem;
  margin-bottom: 0.5rem;
}

.legal-content :deep(p) {
  margin-bottom: 0.75rem;
}

.legal-content :deep(ul),
.legal-content :deep(ol) {
  margin-bottom: 0.75rem;
  padding-left: 1.5rem;
}

.legal-content :deep(li) {
  margin-bottom: 0.25rem;
}
</style>
