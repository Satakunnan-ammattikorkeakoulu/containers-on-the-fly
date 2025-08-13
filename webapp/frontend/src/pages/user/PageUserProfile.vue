<template>
  <div>
    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            Profile
          </v-card-title>
          <v-card-text>
            <div class="user-info mb-4">
              <p><strong>Email:</strong> {{ userEmail }}</p>
              <p><strong>Member since:</strong> {{ userCreatedAt }}</p>
              <p v-if="userRoles.length > 0"><strong>Roles:</strong> {{ userRoles.join(', ') }}</p>
            </div>
            
            <v-divider class="my-4"></v-divider>
            
            <div class="password-section">
              <h3 class="subtitle-1 mb-3">Change Password</h3>
              
              <v-alert v-if="!hasPassword" type="info" outlined>
                Internal system login password is not set for your account (you probably used LDAP or external login). It is not possible to change password for this account (at least from here).
              </v-alert>
              
              <v-form v-else ref="passwordForm" v-model="passwordFormValid" @submit.prevent="changePassword">
                <v-text-field
                  v-model="currentPassword"
                  :append-icon="showCurrent ? 'mdi-eye' : 'mdi-eye-off'"
                  :type="showCurrent ? 'text' : 'password'"
                  @click:append="showCurrent = !showCurrent"
                  label="Current Password"
                  :rules="[rules.required]"
                  outlined
                  dense
                ></v-text-field>
                
                <v-text-field
                  v-model="newPassword"
                  :append-icon="showNew ? 'mdi-eye' : 'mdi-eye-off'"
                  :type="showNew ? 'text' : 'password'"
                  @click:append="showNew = !showNew"
                  label="New Password"
                  :rules="[rules.required, rules.minLength]"
                  outlined
                  dense
                ></v-text-field>
                
                <v-text-field
                  v-model="confirmPassword"
                  :append-icon="showConfirm ? 'mdi-eye' : 'mdi-eye-off'"
                  :type="showConfirm ? 'text' : 'password'"
                  @click:append="showConfirm = !showConfirm"
                  label="Confirm New Password"
                  :rules="[rules.required, rules.passwordMatch]"
                  outlined
                  dense
                ></v-text-field>
                
                <v-btn
                  color="primary"
                  type="submit"
                  :disabled="!passwordFormValid || loading"
                  :loading="loading"
                >
                  Change Password
                </v-btn>
              </v-form>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script>
import axios from 'axios'
import dayjs from 'dayjs'

export default {
  name: 'PageUserProfile',
  data() {
    return {
      hasPassword: false,
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
      showCurrent: false,
      showNew: false,
      showConfirm: false,
      passwordFormValid: false,
      loading: false,
      userProfile: null,
      rules: {
        required: v => !!v || 'This field is required',
        minLength: v => (v && v.length >= 5) || 'Password must be at least 5 characters',
        passwordMatch: v => v === this.newPassword || 'Passwords do not match'
      }
    }
  },
  computed: {
    userEmail() {
      return this.$store.state.user?.email || ''
    },
    userCreatedAt() {
      const createdAt = this.userProfile?.createdAt
      return createdAt ? dayjs(createdAt).format('MMMM D, YYYY') : ''
    },
    userRoles() {
      return this.$store.state.user?.roles || []
    }
  },
  mounted() {
    this.loadUserProfile()
    this.checkPasswordStatus()
  },
  methods: {
    async loadUserProfile() {
      const currentUser = this.$store.state.user
      if (!currentUser || !currentUser.loginToken) {
        console.error('No login token available')
        return
      }
      
      try {
        const response = await axios.get('/api/user/profile', {
          headers: {
            'Authorization': `Bearer ${currentUser.loginToken}`
          }
        })
        if (response.data.status && response.data.data.user) {
          this.userProfile = response.data.data.user
        }
      } catch (error) {
        console.error('Error loading user profile:', error)
      }
    },
    async checkPasswordStatus() {
      const currentUser = this.$store.state.user
      if (!currentUser || !currentUser.loginToken) {
        console.error('No login token available')
        return
      }
      
      try {
        const response = await axios.get('/api/user/has_password', {
          headers: {
            'Authorization': `Bearer ${currentUser.loginToken}`
          }
        })
        this.hasPassword = response.data.data.hasPassword
      } catch (error) {
        console.error('Error checking password status:', error)
        this.$store.commit('showMessage', {
          text: 'Error checking password status',
          color: 'red'
        })
      }
    },
    async changePassword() {
      if (!this.$refs.passwordForm.validate()) {
        return
      }
      
      const currentUser = this.$store.state.user
      if (!currentUser || !currentUser.loginToken) {
        console.error('No login token available')
        return
      }
      
      this.loading = true
      try {
        const response = await axios.post('/api/user/change_password', {
          currentPassword: this.currentPassword,
          newPassword: this.newPassword
        }, {
          headers: {
            'Authorization': `Bearer ${currentUser.loginToken}`
          }
        })
        
        if (response.data.status) {
          this.$store.commit('showMessage', {
            text: 'Password changed successfully',
            color: 'green'
          })
          // Clear form
          this.currentPassword = ''
          this.newPassword = ''
          this.confirmPassword = ''
          this.$refs.passwordForm.resetValidation()
        } else {
          this.$store.commit('showMessage', {
            text: response.data.message || 'Failed to change password',
            color: 'red'
          })
        }
      } catch (error) {
        console.error('Error changing password:', error)
        let errorMessage = 'Error changing password'
        if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message
        }
        this.$store.commit('showMessage', {
          text: errorMessage,
          color: 'red'
        })
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.user-info p {
  margin-bottom: 8px;
}
</style>