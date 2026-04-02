<template>
  <div>
    <v-row class="mt-4">
      <v-col cols="12">
        <h2 class="mb-0">Profile</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <div class="user-info mb-4">
          <p class="mt-0"><strong>Name:</strong> {{ userName || 'Not set' }}</p>
          <p><strong>Email:</strong> {{ userEmail }}</p>
          <p><strong>Member since:</strong> {{ userCreatedAt }}</p>
          <p v-if="userRoles.length > 0"><strong>Roles:</strong> {{ userRoles.join(', ') }}</p>
        </div>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-text>
            <div class="name-section">
              <h3 class="subtitle-18">Display Name</h3>
              <v-alert type="info" variant="tonal" density="compact" class="mb-8">
                If you log in through AD/LDAP, this name will be automatically overwritten on each login.
              </v-alert>
              <v-text-field
                v-model="userName"
                label="Name"
                placeholder="Your display name"
                outlined
                dense
              ></v-text-field>
              <v-btn
                color="primary"
                :disabled="nameLoading"
                :loading="nameLoading"
                @click="updateName"
              >
                Save Name
              </v-btn>
              <v-btn
                v-if="userName"
                text
                class="ml-2"
                @click="removeName"
              >
                Remove Name
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-text>
            <div class="password-section">
              <h3 class="subtitle-1 mb-8">Change Password</h3>
              
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
    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-text>
            <div class="ssh-key-section">
              <h3 class="subtitle-1 mb-1">SSH Public Key</h3>
              <a class="text-caption" style="cursor: pointer; color: #2196f3;" @click="sshConfigDialog = true">
                <v-icon size="x-small" class="mr-1">mdi-information-outline</v-icon>
                How to configure SSH
              </a>
              <div class="mb-3"></div>
              <p class="text-caption mb-8">
                Paste your SSH public key here. It will be automatically deployed to your containers on launch.
              </p>
              <v-textarea
                v-model="sshPublicKey"
                label="SSH Public Key"
                placeholder="ssh-rsa AAAA... or ssh-ed25519 AAAA..."
                outlined
                dense
                rows="4"
                auto-grow
              ></v-textarea>
              <v-btn
                color="primary"
                :disabled="sshKeyLoading"
                :loading="sshKeyLoading"
                @click="updateSshKey"
              >
                Save SSH Key
              </v-btn>
              <v-btn
                v-if="sshPublicKey"
                text
                class="ml-2"
                @click="removeSshKey"
              >
                Remove Key
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-text>
            <div class="script-paths-section">
              <h3 class="subtitle-1 mb-1">Container Lifecycle Scripts</h3>
              <p class="text-caption mb-8">
                Set default scripts to run when your containers start or stop.
                These must be absolute paths inside the container (e.g. <code><i>/home/user/persistent/start.sh</i></code>).
                Per-reservation overrides can be set in Advanced Settings when creating a reservation.
              </p>
              <v-text-field
                v-model="startScriptPath"
                label="Start Script Path (optional)"
                placeholder=""
                :rules="[rules.scriptPath]"
              ></v-text-field>
              <v-text-field
                v-model="stopScriptPath"
                label="Stop Script Path (optional)"
                placeholder=""
                :rules="[rules.scriptPath]"
              ></v-text-field>
              <v-btn
                color="primary"
                :disabled="scriptPathLoading"
                :loading="scriptPathLoading"
                @click="updateScriptPaths"
              >
                Save Script Paths
              </v-btn>
              <v-btn
                v-if="startScriptPath || stopScriptPath"
                text
                class="ml-2"
                @click="removeScriptPaths"
              >
                Remove All
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

    </v-row>

    <!-- SSH Config Help Dialog -->
    <v-dialog v-model="sshConfigDialog" max-width="600px">
      <v-card class="pa-4">
        <v-card-title class="text-h6">SSH Configuration Guide</v-card-title>
        <v-card-text>
          <p class="mb-4">Add the following to your <code>~/.ssh/config</code> file to enable key-based authentication with reservations:</p>

          <div class="ssh-config-block mb-2">
            <pre class="ssh-config-pre">Host aiserver
    HostName SERVER_ADDRESS
    IdentityFile ~/.ssh/id_rsa</pre>
            <v-btn
              icon
              size="x-small"
              variant="text"
              class="copy-btn"
              @click="copySshConfig"
            >
              <v-icon size="small">mdi-content-copy</v-icon>
            </v-btn>
          </div>

          <v-alert type="info" variant="tonal" density="compact" class="mb-4">
            <div class="mb-1"><strong>Host</strong> — a nickname you choose for this connection (e.g. "aiserver")</div>
            <div class="mb-1"><strong>HostName</strong> — the server address, shown in your reservation connection details</div>
            <div class="mb-1"><strong>IdentityFile</strong> — path to your private key (matches the public key you added above)</div>
          </v-alert>


        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" variant="text" @click="sshConfigDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
/**
 * User profile page for managing account settings.
 * Displays user info (email, roles, member since) and provides forms for
 * changing the login password and managing an SSH public key that gets
 * auto-deployed to containers on launch.
 */
import axios from 'axios'
import dayjs from 'dayjs'
import { useMainStore } from '@/store/store'

export default {
  name: 'PageUserProfile',

  setup() {
    const store = useMainStore()
    return { store }
  },

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
      userName: '',
      nameLoading: false,
      sshPublicKey: '',
      sshKeyLoading: false,
      sshConfigDialog: false,
      startScriptPath: '',
      stopScriptPath: '',
      scriptPathLoading: false,
      userProfile: null,
      rules: {
        required: v => !!v || 'This field is required',
        minLength: v => (v && v.length >= 5) || 'Password must be at least 5 characters',
        passwordMatch: v => v === this.newPassword || 'Passwords do not match',
        scriptPath: v => !v || !v.trim() || v.trim().startsWith('/') || 'Must be an absolute path (starting with /)'
      }
    }
  },
  computed: {
    userEmail() {
      return this.store.user?.email || ''
    },
    userCreatedAt() {
      const createdAt = this.userProfile?.createdAt
      return createdAt ? dayjs(createdAt).format('MMMM D, YYYY') : ''
    },
    userRoles() {
      return this.store.user?.roles || []
    }
  },
  mounted() {
    this.loadUserProfile()
    this.checkPasswordStatus()
  },
  methods: {
    async loadUserProfile() {
      const currentUser = this.store.user
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
          this.userName = response.data.data.user.name || ''
          this.sshPublicKey = response.data.data.user.sshPublicKey || ''
          this.startScriptPath = response.data.data.user.startScriptPath || ''
          this.stopScriptPath = response.data.data.user.stopScriptPath || ''
        }
      } catch (error) {
        console.error('Error loading user profile:', error)
      }
    },
    /** Checks whether the user has a local password set (vs. LDAP-only auth). */
    async checkPasswordStatus() {
      const currentUser = this.store.user
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
        this.store.showMessage({
          text: 'Error checking password status',
          color: 'red'
        })
      }
    },
    async changePassword() {
      if (!this.$refs.passwordForm.validate()) {
        return
      }
      
      const currentUser = this.store.user
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
          this.store.showMessage({
            text: 'Password changed successfully',
            color: 'green'
          })
          // Clear form
          this.currentPassword = ''
          this.newPassword = ''
          this.confirmPassword = ''
          this.$refs.passwordForm.resetValidation()
        } else {
          this.store.showMessage({
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
        this.store.showMessage({
          text: errorMessage,
          color: 'red'
        })
      } finally {
        this.loading = false
      }
    },
    async updateSshKey() {
      const currentUser = this.store.user
      if (!currentUser || !currentUser.loginToken) {
        console.error('No login token available')
        return
      }

      this.sshKeyLoading = true
      try {
        const response = await axios.post('/api/user/update_ssh_key', {
          sshPublicKey: this.sshPublicKey || null
        }, {
          headers: {
            'Authorization': `Bearer ${currentUser.loginToken}`
          }
        })

        if (response.data.status) {
          this.store.showMessage({
            text: 'SSH public key updated successfully',
            color: 'green'
          })
        } else {
          this.store.showMessage({
            text: response.data.message || 'Failed to update SSH key',
            color: 'red'
          })
        }
      } catch (error) {
        console.error('Error updating SSH key:', error)
        let errorMessage = 'Error updating SSH key'
        if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message
        }
        this.store.showMessage({
          text: errorMessage,
          color: 'red'
        })
      } finally {
        this.sshKeyLoading = false
      }
    },
    async removeSshKey() {
      this.sshPublicKey = ''
      await this.updateSshKey()
    },
    async updateName() {
      const currentUser = this.store.user
      if (!currentUser || !currentUser.loginToken) return

      this.nameLoading = true
      try {
        const response = await axios.post(this.$appSettings.APIServer.user.update_name, {
          name: this.userName || null
        }, {
          headers: {
            'Authorization': `Bearer ${currentUser.loginToken}`
          }
        })

        if (response.data.status) {
          this.store.setUser({ loginToken: currentUser.loginToken })
          this.store.showMessage({
            text: 'Name updated successfully',
            color: 'green'
          })
        } else {
          this.store.showMessage({
            text: response.data.message || 'Failed to update name',
            color: 'red'
          })
        }
      } catch (error) {
        console.error('Error updating name:', error)
        let errorMessage = 'Error updating name'
        if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message
        }
        this.store.showMessage({
          text: errorMessage,
          color: 'red'
        })
      } finally {
        this.nameLoading = false
      }
    },
    async removeName() {
      this.userName = ''
      await this.updateName()
    },
    async updateScriptPaths() {
      const currentUser = this.store.user
      if (!currentUser || !currentUser.loginToken) {
        console.error('No login token available')
        return
      }

      this.scriptPathLoading = true
      try {
        const response = await axios.post('/api/user/update_script_paths', {
          startScriptPath: this.startScriptPath || null,
          stopScriptPath: this.stopScriptPath || null
        }, {
          headers: {
            'Authorization': `Bearer ${currentUser.loginToken}`
          }
        })

        if (response.data.status) {
          this.store.setUser({ loginToken: currentUser.loginToken })
          this.store.showMessage({
            text: 'Script paths updated successfully',
            color: 'green'
          })
        } else {
          this.store.showMessage({
            text: response.data.message || 'Failed to update script paths',
            color: 'red'
          })
        }
      } catch (error) {
        console.error('Error updating script paths:', error)
        let errorMessage = 'Error updating script paths'
        if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail
        } else if (error.response?.data?.message) {
          errorMessage = error.response.data.message
        }
        this.store.showMessage({
          text: errorMessage,
          color: 'red'
        })
      } finally {
        this.scriptPathLoading = false
      }
    },
    async removeScriptPaths() {
      this.startScriptPath = ''
      this.stopScriptPath = ''
      await this.updateScriptPaths()
    },
    copySshConfig() {
      const config = `Host aiserver\n    HostName SERVER_ADDRESS\n    IdentityFile ~/.ssh/id_rsa`;
      navigator.clipboard.writeText(config);
      this.store.showMessage({ text: 'SSH config copied to clipboard', color: 'green' });
    }
  }
}
</script>

<style scoped>
.user-info p {
  margin-bottom: 8px;
}

.ssh-config-block {
  position: relative;
  background: #1e1e1e;
  border-radius: 4px;
  padding: 16px;
}

.ssh-config-pre {
  font-family: monospace;
  font-size: 14px;
  color: #fff;
  margin: 0;
  white-space: pre;
}

.ssh-config-block .copy-btn {
  position: absolute;
  top: 8px;
  right: 8px;
}
</style>