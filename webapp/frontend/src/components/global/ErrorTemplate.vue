<!--
  Error template for critical system failures like config loading errors.
-->
<template>
  <v-container class="error-container" fill-height>
    <v-row justify="center" align="center">
      <v-col cols="12" sm="8" md="6" lg="4">
        <v-card class="error-card pa-8" outlined>
          <div class="text-center">
            <!-- Error Icon -->
            <v-icon 
              size="80" 
              color="error" 
              class="mb-4"
            >
              mdi-alert-circle-outline
            </v-icon>
            
            <!-- Error Title -->
            <h2 class="text-h4 mb-4 error--text">
              Configuration Error
            </h2>
            
            <!-- Error Message -->
            <p class="text-h6 mb-4 grey--text text--darken-1">
              Unable to load application configuration
            </p>
            
            <!-- Error Description -->
            <p class="body-1 mb-6 grey--text">
              {{ errorMessage || 'The application could not connect to the server to load its configuration. Please check your internet connection and try again.' }}
            </p>
            
            <!-- Action Buttons -->
            <div class="d-flex flex-column align-center">
              <v-btn 
                color="primary" 
                large
                class="mb-4"
                @click="refreshPage"
                :loading="refreshing"
              >
                <v-icon left>mdi-refresh</v-icon>
                Refresh Page
              </v-btn>
              
              <v-btn 
                text 
                color="primary"
                @click="goToLogin"
              >
                <v-icon left>mdi-login</v-icon>
                Go to Login Page
              </v-btn>
            </div>
          </div>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
export default {
  name: 'ErrorTemplate',
  props: {
    errorMessage: {
      type: String,
      default: null
    }
  },
  data() {
    return {
      refreshing: false
    }
  },
  methods: {
    refreshPage() {
      this.refreshing = true;
      window.location.reload();
    },
    goToLogin() {
      this.$router.push('/').catch(() => {
        // If routing fails, just navigate directly
        window.location.href = '/';
      });
    }
  }
}
</script>

<style scoped>
.error-container {
  min-height: 100vh;
  background: black;
}

.error-card {
  border-radius: 16px !important;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1) !important;
  background: rgba(255, 255, 255, 0.95) !important;
  backdrop-filter: blur(10px);
}

.v-icon {
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.text-h4 {
  font-weight: 600 !important;
}

.text-h6 {
  font-weight: 500 !important;
}

.v-btn {
  border-radius: 8px !important;
  text-transform: none !important;
  font-weight: 600 !important;
  min-width: 200px;
}
</style> 