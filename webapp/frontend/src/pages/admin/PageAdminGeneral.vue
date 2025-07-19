<template>
  <v-container>
    <v-row class="text-center">
      <v-col cols="12">
        <h4>Admin</h4>
        <h2>General Settings</h2>
        <p class="subtitle-1 grey--text">Configure system-wide settings and preferences</p>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <v-expansion-panels multiple v-model="expandedPanels">
          
          <!-- General Information & Instructions Section -->
          <v-expansion-panel>
            <v-expansion-panel-header>
              <v-icon class="mr-3">mdi-information-outline</v-icon>
              <span class="font-weight-medium">General Information & Instructions</span>
            </v-expansion-panel-header>
            <v-expansion-panel-content>
              <v-form ref="generalForm" v-model="forms.general.valid">
                
                <!-- Login Page Information -->
                <div class="mb-6">
                  <h6 class="text-h6 mb-2">Login Page Instructions</h6>
                  <p class="body-2 grey--text mb-3">
                    Information text displayed on the login page to provide context or instructions to users.
                  </p>
                  <v-textarea
                    v-model="settings.general.loginPageInfo"
                    placeholder="Enter information text to display on the login page..."
                    rows="3"
                    outlined
                    hide-details
                  ></v-textarea>
                </div>
                
                <!-- Reservation Page Instructions -->
                <div class="mb-6">
                  <h6 class="text-h6 mb-2">Reservation Page Instructions</h6>
                  <p class="body-2 grey--text mb-3">
                    Instructions displayed to users on top of the reservation page about server usage guidelines and restrictions.
                  </p>
                  <v-textarea
                    v-model="settings.general.reservationPageInstructions"
                    placeholder="Enter instructions for users about what they can and cannot do on reserved servers..."
                    rows="4"
                    outlined
                    hide-details
                  ></v-textarea>
                </div>
                
                <!-- Email Template Instructions -->
                <div class="mb-6">
                  <h6 class="text-h6 mb-2">Email Template Instructions</h6>
                  <p class="body-2 grey--text mb-3">
                    Guidelines and instructions included in reservation confirmation emails sent to users (at the end of the email).
                  </p>
                  <v-textarea
                    v-model="settings.general.emailInstructions"
                    placeholder="Enter instructions to be included in reservation confirmation emails..."
                    rows="4"
                    outlined
                    hide-details
                  ></v-textarea>
                </div>
                
                <v-row>
                  <v-col cols="12">
                    <v-btn 
                      color="primary" 
                      :loading="saving.general"
                      @click="saveSection('general')"
                    >
                      <v-icon left>mdi-content-save</v-icon>
                      Save Instructions
                    </v-btn>
                  </v-col>
                </v-row>
              </v-form>
            </v-expansion-panel-content>
          </v-expansion-panel>

          <!-- User Access Control Section -->
          <v-expansion-panel>
            <v-expansion-panel-header>
              <v-icon class="mr-3">mdi-shield-account</v-icon>
              <span class="font-weight-medium">User Access Control</span>
            </v-expansion-panel-header>
            <v-expansion-panel-content>
              <v-form ref="accessForm" v-model="forms.access.valid">
                <v-row>
                  <v-col cols="12" md="6">
                    <v-card outlined class="pa-4">
                      <div class="mb-4">
                        <h6 class="text-h6 mb-2 d-flex align-center">
                          <v-icon left color="red">mdi-account-cancel</v-icon>
                          Email Blacklist
                        </h6>
                        <p class="body-2 grey--text mb-3">
                          Prevent specific email addresses from logging into the system. Users on this list will be denied access.
                        </p>
                      </div>
                      
                      <v-checkbox
                        v-model="settings.access.blacklistEnabled"
                        label="Enable email blacklist"
                        color="red"
                        class="mt-0 mb-4"
                      ></v-checkbox>
                      
                      <!-- Add new email -->
                      <div class="mb-4" v-if="settings.access.blacklistEnabled">
                        <v-text-field
                          v-model="newBlacklistEmail"
                          label="Add email to blacklist"
                          placeholder="user@example.com"
                          outlined
                          dense
                          :rules="[rules.email]"
                          @keyup.enter="addBlacklistEmail"
                          hide-details
                        >
                          <template v-slot:append>
                            <v-btn 
                              icon 
                              color="red"
                              :disabled="!isValidEmail(newBlacklistEmail)"
                              @click="addBlacklistEmail"
                            >
                              <v-icon>mdi-plus</v-icon>
                            </v-btn>
                          </template>
                        </v-text-field>
                      </div>
                      
                      <!-- Existing blacklisted emails -->
                      <div v-if="settings.access.blacklistEnabled && blacklistedEmailsList.length > 0">
                        <p class="caption grey--text mb-2">Blacklisted emails:</p>
                        <v-chip
                          v-for="(email, index) in blacklistedEmailsList"
                          :key="`blacklist-${index}`"
                          class="ma-1"
                          close
                          color="red"
                          text-color="white"
                          @click:close="removeBlacklistEmail(index)"
                        >
                          {{ email }}
                        </v-chip>
                      </div>
                      
                      <div v-else-if="settings.access.blacklistEnabled" class="text-center grey--text">
                        <p class="body-2">No emails blacklisted</p>
                      </div>
                    </v-card>
                  </v-col>
                  
                  <v-col cols="12" md="6">
                    <v-card outlined class="pa-4">
                      <div class="mb-4">
                        <h6 class="text-h6 mb-2 d-flex align-center">
                          <v-icon left color="green">mdi-account-check</v-icon>
                          Email Whitelist
                        </h6>
                        <p class="body-2 grey--text mb-3">
                          Allow only specific email addresses to log into the system. When enabled, only users on this list can access the system.
                        </p>
                      </div>
                      
                      <v-checkbox
                        v-model="settings.access.whitelistEnabled"
                        label="Enable email whitelist"
                        color="green"
                        class="mt-0 mb-4"
                      ></v-checkbox>
                      
                      <!-- Add new email -->
                      <div class="mb-4" v-if="settings.access.whitelistEnabled">
                        <v-text-field
                          v-model="newWhitelistEmail"
                          label="Add email to whitelist"
                          placeholder="admin@example.com"
                          outlined
                          dense
                          :rules="[rules.email]"
                          @keyup.enter="addWhitelistEmail"
                          hide-details
                        >
                          <template v-slot:append>
                            <v-btn 
                              icon 
                              color="green"
                              :disabled="!isValidEmail(newWhitelistEmail)"
                              @click="addWhitelistEmail"
                            >
                              <v-icon>mdi-plus</v-icon>
                            </v-btn>
                          </template>
                        </v-text-field>
                      </div>
                      
                      <!-- Existing whitelisted emails -->
                      <div v-if="settings.access.whitelistEnabled && whitelistedEmailsList.length > 0">
                        <p class="caption grey--text mb-2">Whitelisted emails:</p>
                        <v-chip
                          v-for="(email, index) in whitelistedEmailsList"
                          :key="`whitelist-${index}`"
                          class="ma-1"
                          close
                          color="green"
                          text-color="white"
                          @click:close="removeWhitelistEmail(index)"
                        >
                          {{ email }}
                        </v-chip>
                      </div>
                      
                      <div v-else-if="settings.access.whitelistEnabled" class="text-center grey--text">
                        <p class="body-2">No emails whitelisted</p>
                      </div>
                    </v-card>
                  </v-col>
                </v-row>
                
                <v-row>
                  <v-col cols="12">
                    <v-alert 
                      type="warning" 
                      outlined
                      v-if="settings.access.blacklistEnabled && settings.access.whitelistEnabled"
                    >
                      <strong>Warning:</strong> Both blacklist and whitelist are enabled. Whitelist takes precedence - only whitelisted users can log in.
                    </v-alert>
                  </v-col>
                </v-row>
              </v-form>
            </v-expansion-panel-content>
          </v-expansion-panel>

          <!-- Email Configuration Section -->
          <v-expansion-panel>
            <v-expansion-panel-header>
              <v-icon class="mr-3">mdi-email-outline</v-icon>
              <span class="font-weight-medium">Email Configuration</span>
            </v-expansion-panel-header>
            <v-expansion-panel-content>
              <v-form ref="emailForm" v-model="forms.email.valid">
                
                <!-- SMTP Settings Section -->
                <div class="mb-6">
                  <h6 class="text-h6 mb-2">SMTP Server Configuration</h6>
                  <p class="body-2 grey--text mb-4">
                    Configure the SMTP server settings for sending system emails like reservation confirmations and notifications.
                  </p>
                  
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.email.smtpServer"
                        label="SMTP Server"
                        placeholder="smtp.office365.com"
                        outlined
                        required
                        :rules="[rules.required]"
                      ></v-text-field>
                    </v-col>
                    
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.email.smtpPort"
                        label="SMTP Port"
                        placeholder="587"
                        outlined
                        type="number"
                        required
                        :rules="[rules.required]"
                      ></v-text-field>
                    </v-col>
                    
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.email.smtpUsername"
                        label="SMTP Username"
                        placeholder="email@test.com"
                        outlined
                        required
                        :rules="[rules.required]"
                      ></v-text-field>
                    </v-col>
                    
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.email.smtpPassword"
                        label="SMTP Password"
                        placeholder="Enter password"
                        type="password"
                        outlined
                        required
                        :rules="[rules.required]"
                      ></v-text-field>
                    </v-col>
                    
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.email.fromEmail"
                        label="From Email Address"
                        placeholder="noreply@yourdomain.com"
                        outlined
                        required
                        :rules="[rules.required, rules.email]"
                      ></v-text-field>
                    </v-col>
                  </v-row>
                  
                  <!-- Save SMTP Settings Button -->
                  <v-row>
                    <v-col cols="12">
                      <v-btn 
                        color="primary" 
                        :loading="saving.email"
                        @click="saveSection('email')"
                      >
                        <v-icon left>mdi-content-save</v-icon>
                        Save SMTP Settings
                      </v-btn>
                    </v-col>
                  </v-row>
                </div>
                
                <!-- Contact Information Section -->
                <div class="mb-6">
                  <h6 class="text-h6 mb-2">Contact Email</h6>
                  <p class="body-2 grey--text mb-4">
                    Configure the admin contact email address displayed to users throughout the system.
                  </p>
                  
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.email.contactEmail"
                        label="Admin Contact Email"
                        placeholder="admin@yourdomain.com"
                        outlined
                        required
                        :rules="[rules.required, rules.email]"
                      ></v-text-field>
                      <p class="caption grey--text mt-n2">Email address for users to contact administrators</p>
                    </v-col>
                  </v-row>
                  
                  <!-- Save Contact Info Button -->
                  <v-row>
                    <v-col cols="12">
                      <v-btn 
                        color="primary" 
                        :loading="saving.contact"
                        @click="saveSection('contact')"
                      >
                        <v-icon left>mdi-content-save</v-icon>
                        Save Contact Email
                      </v-btn>
                    </v-col>
                  </v-row>
                </div>
                
                <!-- Test Email Delivery Section -->
                <div class="mb-6">
                  <h6 class="text-h6 mb-2">Test Email Delivery</h6>
                  <p class="body-2 grey--text mb-4">
                    Send a test email to verify that your SMTP configuration is working correctly.
                  </p>
                  
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="testEmail"
                        label="Test Email Address"
                        placeholder="test@example.com"
                        outlined
                        :rules="[rules.email]"
                        @keyup.enter="sendTestEmail"
                      ></v-text-field>
                      <p class="caption grey--text mt-n2">Enter an email address to receive the test message</p>
                    </v-col>
                  </v-row>
                  
                  <!-- Test Email Button -->
                  <v-row>
                    <v-col cols="12">
                      <v-btn 
                        color="primary" 
                        :loading="sendingTest"
                        :disabled="!testEmail || !isValidEmail(testEmail)"
                        @click="sendTestEmail"
                      >
                        <v-icon left>mdi-email-send</v-icon>
                        Test Delivery
                      </v-btn>
                    </v-col>
                  </v-row>
                </div>
                
              </v-form>
            </v-expansion-panel-content>
          </v-expansion-panel>

          <!-- System Notifications Section -->
          <v-expansion-panel>
            <v-expansion-panel-header>
              <v-icon class="mr-3">mdi-bell-alert</v-icon>
              <span class="font-weight-medium">System Notifications</span>
            </v-expansion-panel-header>
            <v-expansion-panel-content>
              <v-form ref="notificationsForm" v-model="forms.notifications.valid">
                
                <!-- Container Failure Alerts -->
                <div class="mb-6">
                  <h6 class="text-h6 mb-2">Container Failure Alerts</h6>
                  <p class="body-2 grey--text mb-4">
                    Configure email notifications when Docker containers fail to start or stop unexpectedly. This helps administrators quickly respond to system issues.
                  </p>
                  
                  <v-checkbox
                    v-model="settings.notifications.containerAlertsEnabled"
                    label="Enable container failure notifications"
                    color="primary"
                    class="mt-0 mb-4"
                  ></v-checkbox>
                  
                  <!-- Add new email -->
                  <div class="mb-4" v-if="settings.notifications.containerAlertsEnabled">
                    <v-text-field
                      v-model="newAlertEmail"
                      label="Add email for alerts"
                      placeholder="admin@example.com"
                      outlined
                      dense
                      :rules="[rules.email]"
                      @keyup.enter="addAlertEmail"
                      hide-details
                    >
                      <template v-slot:append>
                        <v-btn 
                          icon 
                          color="primary"
                          :disabled="!isValidEmail(newAlertEmail)"
                          @click="addAlertEmail"
                        >
                          <v-icon>mdi-plus</v-icon>
                        </v-btn>
                      </template>
                    </v-text-field>
                  </div>
                  
                  <!-- Existing alert emails -->
                  <div v-if="settings.notifications.containerAlertsEnabled && alertEmailsList.length > 0">
                    <p class="caption grey--text mb-2">Alert recipients:</p>
                    <v-chip
                      v-for="(email, index) in alertEmailsList"
                      :key="`alert-${index}`"
                      class="ma-1"
                      close
                      color="primary"
                      text-color="white"
                      @click:close="removeAlertEmail(index)"
                    >
                      {{ email }}
                    </v-chip>
                  </div>
                  
                  <div v-else-if="settings.notifications.containerAlertsEnabled" class="text-center grey--text">
                    <p class="body-2">No alert recipients configured</p>
                  </div>
                </div>
                
                <v-row>
                  <v-col cols="12">
                    <v-btn 
                      color="primary" 
                      :loading="saving.notifications"
                      @click="saveSection('notifications')"
                    >
                      <v-icon left>mdi-content-save</v-icon>
                      Save Notification Settings
                    </v-btn>
                  </v-col>
                </v-row>
              </v-form>
            </v-expansion-panel-content>
          </v-expansion-panel>
          
        </v-expansion-panels>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
// Note: axios import removed since we're implementing frontend first
// const axios = require('axios').default;

export default {
  name: 'PageAdminGeneral',
  data: () => ({
    expandedPanels: [], // All panels collapsed by default
    testEmail: '',
    sendingTest: false,
    
    // New email inputs
    newBlacklistEmail: '',
    newWhitelistEmail: '',
    newAlertEmail: '',
    
    // Form validation states
    forms: {
      general: { valid: true },
      access: { valid: true },
      email: { valid: true },
      notifications: { valid: true }
    },
    
    // Saving states for each section
    saving: {
      general: false,
      access: false,
      email: false,
      contact: false,  // Added contact saving state
      notifications: false
    },
    
    // Form validation rules
    rules: {
      required: value => !!value || 'This field is required',
      email: value => {
        if (!value) return true; // Allow empty for optional fields
        const pattern = /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/
        return pattern.test(value) || 'Invalid email format'
      }
    },
    
    // Dropdown options
    securityOptions: [
      { text: 'None', value: 'none' },
      { text: 'TLS', value: 'tls' },
      { text: 'SSL', value: 'ssl' }
    ],
    
    alertFrequencyOptions: [
      { text: 'Immediately (every failure)', value: 'immediate' },
      { text: 'Every 15 minutes', value: '15min' },
      { text: 'Every hour', value: '1hour' },
      { text: 'Every 6 hours', value: '6hours' },
      { text: 'Once per day', value: 'daily' }
    ],
    
    // Email lists with example data
    blacklistedEmailsList: [
      'blocked@example.com',
      'spam@badsite.com'
    ],
    
    whitelistedEmailsList: [
      'admin@company.com',
      'manager@company.com',
      'developer@company.com'
    ],
    
    alertEmailsList: [
      'admin@company.com',
      'devops@company.com'
    ],
    
    // Settings data structure
    settings: {
      general: {
        loginPageInfo: '',
        reservationPageInstructions: '',
        emailInstructions: ''
      },
      access: {
        blacklistEnabled: true, // Set to true to show example emails
        whitelistEnabled: false
      },
      email: {
        smtpServer: '',        // Changed from smtpHost to match config
        smtpPort: 587,
        smtpUsername: '',
        smtpPassword: '',
        fromEmail: '',
        contactEmail: ''       // Moved here but will have separate save
      },
      notifications: {
        containerAlertsEnabled: true // Set to true to show example emails
      }
    }
  }),
  
  mounted() {
    this.loadSettings();
  },
  
  methods: {
    // Email list management methods
    addBlacklistEmail() {
      if (this.isValidEmail(this.newBlacklistEmail) && !this.blacklistedEmailsList.includes(this.newBlacklistEmail)) {
        this.blacklistedEmailsList.push(this.newBlacklistEmail);
        this.newBlacklistEmail = '';
        // TODO: Save to backend automatically
        console.log('Added to blacklist:', this.blacklistedEmailsList);
      }
    },
    
    removeBlacklistEmail(index) {
      this.blacklistedEmailsList.splice(index, 1);
      // TODO: Save to backend automatically
      console.log('Removed from blacklist:', this.blacklistedEmailsList);
    },
    
    addWhitelistEmail() {
      if (this.isValidEmail(this.newWhitelistEmail) && !this.whitelistedEmailsList.includes(this.newWhitelistEmail)) {
        this.whitelistedEmailsList.push(this.newWhitelistEmail);
        this.newWhitelistEmail = '';
        // TODO: Save to backend automatically
        console.log('Added to whitelist:', this.whitelistedEmailsList);
      }
    },
    
    removeWhitelistEmail(index) {
      this.whitelistedEmailsList.splice(index, 1);
      // TODO: Save to backend automatically
      console.log('Removed from whitelist:', this.whitelistedEmailsList);
    },
    
    addAlertEmail() {
      if (this.isValidEmail(this.newAlertEmail) && !this.alertEmailsList.includes(this.newAlertEmail)) {
        this.alertEmailsList.push(this.newAlertEmail);
        this.newAlertEmail = '';
        // TODO: Save to backend automatically
        console.log('Added alert email:', this.alertEmailsList);
      }
    },
    
    removeAlertEmail(index) {
      this.alertEmailsList.splice(index, 1);
      // TODO: Save to backend automatically
      console.log('Removed alert email:', this.alertEmailsList);
    },
    
    async loadSettings() {
      try {
        // TODO: Load settings from backend when implemented
        console.log('Loading settings from backend...');
        // For now, we'll just initialize with empty values
        // const response = await axios.get('/api/admin/general-settings');
        // this.settings = response.data.settings;
      } catch (error) {
        console.error('Failed to load settings:', error);
        this.$store.commit('showMessage', { 
          text: 'Failed to load settings', 
          color: 'red' 
        });
      }
    },
    
    async saveSection(sectionName) {
      try {
        // Validate the form first
        const formRef = `${sectionName}Form`;
        if (this.$refs[formRef] && !this.$refs[formRef].validate()) {
          this.$store.commit('showMessage', { 
            text: 'Please fix validation errors before saving', 
            color: 'red' 
          });
          return;
        }
        
        this.saving[sectionName] = true;
        
        // TODO: Save to backend when implemented
        console.log(`Saving ${sectionName} settings:`, this.settings[sectionName]);
        
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        /*
        const currentUser = this.$store.getters.user;
        const response = await axios.post('/api/admin/general-settings', {
          section: sectionName,
          settings: this.settings[sectionName]
        }, {
          headers: { Authorization: `Bearer ${currentUser.loginToken}` }
        });
        */
        
        this.$store.commit('showMessage', { 
          text: `${this.getSectionDisplayName(sectionName)} settings saved successfully`, 
          color: 'green' 
        });
        
      } catch (error) {
        console.error(`Failed to save ${sectionName} settings:`, error);
        this.$store.commit('showMessage', { 
          text: `Failed to save ${this.getSectionDisplayName(sectionName)} settings`, 
          color: 'red' 
        });
      } finally {
        this.saving[sectionName] = false;
      }
    },
    
    async sendTestEmail() {
      if (!this.isValidEmail(this.testEmail)) {
        this.$store.commit('showMessage', { 
          text: 'Please enter a valid email address', 
          color: 'red' 
        });
        return;
      }
      
      try {
        this.sendingTest = true;
        
        // TODO: Send test email via backend when implemented
        console.log(`Sending test email to: ${this.testEmail}`);
        
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        /*
        const currentUser = this.$store.getters.user;
        await axios.post('/api/admin/send-test-email', {
          email: this.testEmail,
          smtpSettings: this.settings.email
        }, {
          headers: { Authorization: `Bearer ${currentUser.loginToken}` }
        });
        */
        
        this.$store.commit('showMessage', { 
          text: `Test email sent successfully to ${this.testEmail}`, 
          color: 'green' 
        });
        
      } catch (error) {
        console.error('Failed to send test email:', error);
        this.$store.commit('showMessage', { 
          text: 'Failed to send test email', 
          color: 'red' 
        });
      } finally {
        this.sendingTest = false;
      }
    },
    
    isValidEmail(email) {
      if (!email) return false;
      const pattern = /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
      return pattern.test(email);
    },
    
    getSectionDisplayName(sectionName) {
      const names = {
        general: 'General Information',
        access: 'Access Control',
        email: 'Email Configuration',
        contact: 'Contact Information',  // Added contact
        notifications: 'System Notifications'
      };
      return names[sectionName] || sectionName;
    }
  }
}
</script>

<style scoped lang="scss">
// Override Vuetify's expansion panel header styles
::v-deep .v-expansion-panel-header {
  justify-content: space-between !important;
  text-align: left !important;
  padding: 20px 24px !important;
  font-size: 18px !important;
  font-weight: 500 !important;
  display: flex !important;
  align-items: center !important;
  cursor: pointer !important;  // Added pointer cursor
}

// Create a flex container for icon + text on the left
::v-deep .v-expansion-panel-header > div:first-child {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  flex-grow: 0 !important;
}

::v-deep .v-expansion-panel-header .v-icon:first-child {
  margin-right: 8px !important;
  margin-left: 0 !important;
  flex-shrink: 0 !important;
}

::v-deep .v-expansion-panel-header .font-weight-medium {
  margin: 0 !important;
  white-space: nowrap !important;
}

// Keep the expand/collapse icon on the right
::v-deep .v-expansion-panel-header__icon {
  margin-left: auto !important;
  flex-shrink: 0 !important;
}

.font-weight-medium {
  font-weight: 500 !important;
  font-size: 18px !important;
}

.v-subheader {
  font-size: 18px;
  font-weight: 500;
}

.v-expansion-panel-content {
  padding-top: 16px;
}

.v-card {
  height: 100%;
}

.v-alert {
  margin-top: 16px;
}

// Additional styles for better spacing
.mb-6 {
  margin-bottom: 24px !important;
}

.text-h6 {
  font-weight: 600 !important;
  color: rgba(255, 255, 255, 0.87) !important;
}

.body-2 {
  line-height: 1.5 !important;
}

.caption {
  font-size: 12px !important;
}

// Email chip container styling
.v-chip {
  margin: 2px !important;
}

.v-expansion-panel-header>:not(.v-expansion-panel-header__icon) {
    flex: 0;
}
</style> 