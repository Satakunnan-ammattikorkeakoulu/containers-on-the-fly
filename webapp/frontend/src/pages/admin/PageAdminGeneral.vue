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
                
                <!-- Application Configuration ---->
                <div class="mb-6">
                  <h6 class="text-h6 mb-2">Application Configuration</h6>
                  <p class="body-2 grey--text mb-4">
                    Configure the basic application settings displayed throughout the system.
                  </p>
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.general.applicationName"
                        label="Application Name"
                        placeholder="Containers on the Fly"
                        outlined
                        required
                        :rules="[rules.required]"
                        hide-details
                      ></v-text-field>
                    </v-col>
                    <v-col cols="12" md="6">
                      <v-select
                        v-model="settings.general.timezone"
                        :items="timezoneOptions"
                        label="System Timezone"
                        outlined
                        required
                        :rules="[rules.required]"
                        hide-details
                        :search-input.sync="timezoneSearch"
                        item-text="label"
                        item-value="value"
                        filterable
                      >
                        <template v-slot:item="{ item }">
                          <div>
                            <div class="font-weight-medium">{{ item.value }}</div>
                            <div class="caption grey--text">{{ item.description }}</div>
                          </div>
                        </template>
                      </v-select>
                    </v-col>
                  </v-row>
                </div>
                
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
                
                <!-- Login Form Field Labels -->
                <div class="mb-6">
                  <h6 class="text-h6 mb-2">Login Form Field Labels</h6>
                  <p class="body-2 grey--text mb-3">
                    Customize the labels for username and password fields on the login page.
                  </p>
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.general.usernameFieldLabel"
                        label="Username Field Label"
                        placeholder="Username"
                        outlined
                        hide-details
                      ></v-text-field>
                    </v-col>
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.general.passwordFieldLabel"
                        label="Password Field Label"
                        placeholder="Password"
                        outlined
                        hide-details
                      ></v-text-field>
                    </v-col>
                  </v-row>
                </div>
                
                <v-row>
                  <v-col cols="12">
                    <v-btn 
                      color="primary" 
                      :loading="saving.general"
                      @click="saveSection('general')"
                    >
                      <v-icon left>mdi-content-save</v-icon>
                      Save General Settings
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
              
              <!-- SMTP Settings Section with its own form -->
              <v-form ref="emailForm" v-model="forms.email.valid">
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
              </v-form>
              
              <!-- Contact Information Section with its own separate form -->
              <v-form ref="contactForm" v-model="forms.contact.valid">
                <div class="mb-6">
                  <h6 class="text-h6 mb-2">Contact Email</h6>
                  <p class="body-2 grey--text mb-4">
                    Configure the admin contact email address displayed to users throughout the system.
                  </p>
                  
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.contact.contactEmail"
                        label="Admin Contact Email"
                        placeholder="admin@yourdomain.com"
                        outlined
                        required
                        :rules="[rules.required, rules.email]"
                      ></v-text-field>
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
              </v-form>
              
              <!-- Test Email Delivery Section (no form needed, just uses validation) -->
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
                      Test Email Delivery
                    </v-btn>
                  </v-col>
                </v-row>
              </div>
              
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
                

              </v-form>
            </v-expansion-panel-content>
          </v-expansion-panel>

          <!-- Monitoring Section -->
          <v-expansion-panel>
            <v-expansion-panel-header>
              <v-icon class="mr-3">mdi-monitor-eye</v-icon>
              <span class="font-weight-medium">Server Monitoring</span>
            </v-expansion-panel-header>
            <v-expansion-panel-content>
              <v-form ref="monitoringForm" v-model="forms.monitoring.valid">
                
                <!-- Server Selection -->
                <div class="mb-6">
                  <h6 class="text-h6 mb-2">Server Selection</h6>
                  <p class="body-2 grey--text mb-4">
                    Select a server to view PM2 logs and hardware metrics.
                  </p>
                  
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-select
                        v-model="selectedServer"
                        :items="availableServers"
                        item-text="name"
                        item-value="id"
                        label="Select Server"
                        outlined
                        :loading="loadingServers"
                        @change="onServerChange"
                      >
                        <template v-slot:item="{ item }">
                          <div>
                            <div class="font-weight-medium">{{ item.name }}</div>
                            <div class="caption grey--text">{{ item.address }}</div>
                          </div>
                        </template>
                      </v-select>
                    </v-col>
                  </v-row>
                </div>
                
                <!-- Server Selected Content -->
                <div v-if="selectedServer">
                  <!-- Refresh Data Section -->
                  <div class="mb-4">
                    <v-btn 
                      color="primary" 
                      :loading="fetchingMetrics || fetchingLogs"
                      @click="fetchHardwareMetrics"
                      class="mb-3"
                    >
                      <v-icon left>mdi-refresh</v-icon>
                      Refresh Data
                    </v-btn>
                    
                    <!-- Last Updated Info -->
                    <div class="mb-3" v-if="lastMetricsUpdate">
                      <p class="caption mb-0">
                        Last Updated: {{ formatTimestamp(lastMetricsUpdate) }}
                      </p>
                    </div>
                    
                    <!-- Description -->
                    <p class="body-2 grey--text mb-4">
                      The logs and statistics are collected every 30 seconds, thus clicking on the refresh button will only update the data if there is new data available.
                    </p><br>
                  </div>
                  
                  <!-- Hardware Metrics Section -->
                  <div class="mb-6">
                    <div class="mb-2">
                      <h6 class="text-h6 mb-0">System Hardware Metrics</h6>
                    </div>
                    
                    <!-- No Data Available Notice -->
                    <v-alert 
                      v-if="metrics.cpu.usage === null && selectedServer"
                      type="info" 
                      outlined
                      class="mb-4"
                    >
                      <div class="d-flex align-center">
                        <v-icon class="mr-2">mdi-information-outline</v-icon>
                        <span>No monitoring data available for this server yet. The server may not have submitted any data, or monitoring might not be running on this server.</span>
                      </div>
                    </v-alert>
                    
                    <v-row>
                      <!-- CPU Usage -->
                      <v-col cols="12" md="3">
                        <v-card outlined class="pa-3">
                          <div class="d-flex align-center mb-2">
                            <v-icon class="mr-2" color="blue">mdi-chip</v-icon>
                            <span class="font-weight-medium">CPU Usage</span>
                          </div>
                          <div class="text-center">
                            <v-progress-circular
                              v-if="metrics.cpu.usage !== null"
                              :value="metrics.cpu.usage"
                              :color="getCpuColor(metrics.cpu.usage)"
                              size="60"
                              width="6"
                              class="mb-2"
                            >
                              <span class="text-h6">{{ Math.round(metrics.cpu.usage || 0) }}%</span>
                            </v-progress-circular>
                            <div v-else class="text-h6 mb-2 grey--text">
                              No data
                            </div>
                            <div class="caption grey--text">
                              {{ metrics.cpu.cores !== null ? `${metrics.cpu.cores} cores` : 'No data' }}
                            </div>
                          </div>
                        </v-card>
                      </v-col>
                      
                      <!-- RAM Usage -->
                      <v-col cols="12" md="3">
                        <v-card outlined class="pa-3">
                          <div class="d-flex align-center mb-2">
                            <v-icon class="mr-2" color="green">mdi-memory</v-icon>
                            <span class="font-weight-medium">Memory</span>
                          </div>
                          <div class="text-center">
                            <v-progress-circular
                              v-if="metrics.memory.percentage !== null"
                              :value="metrics.memory.percentage"
                              :color="getMemoryColor(metrics.memory.percentage)"
                              size="60"
                              width="6"
                              class="mb-2"
                            >
                              <span class="text-h6">{{ Math.round(metrics.memory.percentage || 0) }}%</span>
                            </v-progress-circular>
                            <div v-else class="text-h6 mb-2 grey--text">
                              No data
                            </div>
                            <div class="caption grey--text">
                              {{ metrics.memory.used !== null && metrics.memory.total !== null ? 
                                 `${formatBytes(metrics.memory.used)} / ${formatBytes(metrics.memory.total)}` : 
                                 'No data' }}
                            </div>
                          </div>
                        </v-card>
                      </v-col>
                      
                      <!-- System Load -->
                      <v-col cols="12" md="3">
                        <v-card outlined class="pa-3">
                          <div class="d-flex align-center mb-2">
                            <v-icon class="mr-2" color="orange">mdi-gauge</v-icon>
                            <span class="font-weight-medium">System Load</span>
                          </div>
                          <div class="text-center">
                            <div class="text-h6 mb-1">
                              {{ metrics.load.avg1 !== null ? metrics.load.avg1 : 'No data' }}
                            </div>
                            <div class="caption grey--text">
                              1m: {{ metrics.load.avg1 !== null ? metrics.load.avg1 : '-' }}<br>
                              5m: {{ metrics.load.avg5 !== null ? metrics.load.avg5 : '-' }}<br>
                              15m: {{ metrics.load.avg15 !== null ? metrics.load.avg15 : '-' }}
                            </div>
                          </div>
                        </v-card>
                      </v-col>
                      
                      <!-- Uptime -->
                      <v-col cols="12" md="3">
                        <v-card outlined class="pa-3">
                          <div class="d-flex align-center mb-2">
                            <v-icon class="mr-2" color="purple">mdi-clock-outline</v-icon>
                            <span class="font-weight-medium">Uptime</span>
                          </div>
                          <div class="text-center">
                            <div class="text-h6 mb-1">
                              {{ metrics.uptime.days !== null ? `${metrics.uptime.days}d` : 'No data' }}
                            </div>
                            <div class="caption grey--text">
                              {{ metrics.uptime.hours !== null && metrics.uptime.minutes !== null ? 
                                 `${metrics.uptime.hours}h ${metrics.uptime.minutes}m` : 
                                 'No data' }}
                            </div>
                          </div>
                        </v-card>
                      </v-col>
                    </v-row>
                    
                    <!-- Disk Usage - Root Filesystem Only -->
                    <v-row class="mt-4">
                      <v-col cols="12" md="6">
                        <v-card outlined class="pa-3">
                          <div class="d-flex align-center mb-2">
                            <v-icon class="mr-2" color="teal">mdi-harddisk</v-icon>
                            <span class="font-weight-medium">Root Disk Usage (/)</span>
                          </div>
                          <div class="text-center">
                            <v-progress-circular
                              v-if="metrics.disk.percentage !== null"
                              :value="metrics.disk.percentage"
                              :color="getDiskColor(metrics.disk.percentage)"
                              size="60"
                              width="6"
                              class="mb-2"
                            >
                              <span class="text-h6">{{ Math.round(metrics.disk.percentage || 0) }}%</span>
                            </v-progress-circular>
                            <div v-else class="text-h6 mb-2 grey--text">
                              No data
                            </div>
                            <div class="caption grey--text">
                              {{ metrics.disk.used !== null && metrics.disk.total !== null && metrics.disk.free !== null ? 
                                 `${formatBytes(metrics.disk.used)} / ${formatBytes(metrics.disk.total)}` : 
                                 'No data' }}
                                <br>
                                {{ metrics.disk.free !== null ? `${formatBytes(metrics.disk.free)} free` : 'No data' }}
                            </div>
                          </div>
                        </v-card>
                      </v-col>
                      
                      <!-- Keep Network/Docker in same row -->
                      <v-col cols="12" md="6">
                        <v-card outlined class="pa-3">
                          <div class="d-flex align-center mb-2">
                            <v-icon class="mr-2" color="cyan">mdi-docker</v-icon>
                            <span class="font-weight-medium">Docker Status</span>
                          </div>
                          <div class="d-flex justify-space-between">
                            <div class="text-center">
                              <div class="caption grey--text">Running</div>
                              <div class="text-subtitle-2">{{ metrics.docker.running !== null ? metrics.docker.running : '-' }}</div>
                            </div>
                            <div class="text-center">
                              <div class="caption grey--text">Total</div>
                              <div class="text-subtitle-2">{{ metrics.docker.total !== null ? metrics.docker.total : '-' }}</div>
                            </div>
                          </div>
                        </v-card>
                      </v-col>
                    </v-row>
                    
                  </div>
                  
                  <v-divider class="mb-6"></v-divider>
                  
                  <div class="mb-4">
                    <h6 class="text-h6 mb-2">PM2 Application Logs</h6>
                    <p class="body-2 grey--text mb-4">
                      Logs from PM2 processes. Latest logs are at the top.
                    </p>
                  </div>
                  
                  <!-- Backend Logs -->
                  <div class="mb-6">
                    <div class="d-flex align-center mb-2">
                      <v-icon class="mr-2" color="blue">mdi-server</v-icon>
                      <h6 class="text-subtitle-1 font-weight-medium">Backend Application</h6>
                      <v-spacer></v-spacer>
                      <v-chip 
                        small 
                        :color="logs.backend.length > 0 ? 'green' : 'grey'"
                        text-color="white"
                      >
                        {{ logs.backend.length > 0 ? 'Active' : 'No Data' }}
                      </v-chip>
                    </div>
                    <v-textarea
                      :value="reverseLogOrder(logs.backend)"
                      readonly
                      outlined
                      rows="15"
                      placeholder="Backend logs will appear here..."
                      class="logs-textarea"
                      :loading="fetchingLogs"
                    ></v-textarea>
                  </div>
                  
                  <!-- Frontend Logs -->
                  <div class="mb-6">
                    <div class="d-flex align-center mb-2">
                      <v-icon class="mr-2" color="green">mdi-web</v-icon>
                      <h6 class="text-subtitle-1 font-weight-medium">Frontend Application</h6>
                      <v-spacer></v-spacer>
                      <v-chip 
                        small 
                        :color="logs.frontend.length > 0 ? 'green' : 'grey'"
                        text-color="white"
                      >
                        {{ logs.frontend.length > 0 ? 'Active' : 'No Data' }}
                      </v-chip>
                    </div>
                    <v-textarea
                      :value="reverseLogOrder(logs.frontend)"
                      readonly
                      outlined
                      rows="15"
                      placeholder="Frontend logs will appear here..."
                      class="logs-textarea"
                      :loading="fetchingLogs"
                    ></v-textarea>
                  </div>
                  
                  <!-- Backend Docker Utility Logs -->
                  <div class="mb-6">
                    <div class="d-flex align-center mb-2">
                      <v-icon class="mr-2" color="orange">mdi-docker</v-icon>
                      <h6 class="text-subtitle-1 font-weight-medium">Backend Docker Utility</h6>
                      <v-spacer></v-spacer>
                      <v-chip 
                        small 
                        :color="logs.backendDockerUtil.length > 0 ? 'green' : 'grey'"
                        text-color="white"
                      >
                        {{ logs.backendDockerUtil.length > 0 ? 'Active' : 'No Data' }}
                      </v-chip>
                    </div>
                    <v-textarea
                      :value="reverseLogOrder(logs.backendDockerUtil)"
                      readonly
                      outlined
                      rows="15"
                      placeholder="Backend Docker Utility logs will appear here..."
                      class="logs-textarea"
                      :loading="fetchingLogs"
                    ></v-textarea>
                  </div>
                  
                  <!-- Last Updated Info -->
                  <div class="text-center grey--text" v-if="lastLogUpdate">
                    <p class="caption">
                      Last updated: {{ formatTimestamp(lastLogUpdate) }}
                    </p>
                  </div>
                </div>
                
                <!-- No Server Selected Message -->
                <div v-else class="text-center grey--text pa-8">
                  <v-icon size="48" class="mb-4">mdi-server-off</v-icon>
                  <h6 class="text-h6 mb-2">No Server Selected</h6>
                  <p class="body-2">Please select a server first</p>
                </div>
                
              </v-form>
            </v-expansion-panel-content>
          </v-expansion-panel>
          
        </v-expansion-panels>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
const axios = require('axios').default;

export default {
  name: 'PageAdminGeneral',
  data: () => ({
    expandedPanels: [], // All panels collapsed by default
    initialLoadComplete: false, // Flag to prevent auto-save during initial load
    isLoading: false, // Flag to indicate we're currently loading data
    settingsInitialized: {
      blacklistEnabled: false,
      whitelistEnabled: false,
      containerAlertsEnabled: false
    }, // Track which settings have been initialized from backend
    testEmail: '',
    sendingTest: false,
    
    // New email inputs
    newBlacklistEmail: '',
    newWhitelistEmail: '',
    newAlertEmail: '',
    
    // Timezone search
    timezoneSearch: '',
    
    // Form validation states
    forms: {
      general: { valid: true },
      access: { valid: true },
      email: { valid: true },
      contact: { valid: true },  // Add contact form state
      notifications: { valid: true },
      monitoring: { valid: true }
    },
    
    // Saving states for each section
    saving: {
      general: false,
      access: false,
      email: false,
      contact: false,  // Added contact saving state
      notifications: false,
      monitoring: false // Added monitoring saving state
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
    
    // Timezone options - comprehensive list of TZ identifiers
    timezoneOptions: [
      // UTC and GMT
      { value: 'UTC', label: 'UTC', description: 'Coordinated Universal Time' },
      { value: 'GMT', label: 'GMT', description: 'Greenwich Mean Time' },
      
      // Africa
      { value: 'Africa/Abidjan', label: 'Africa/Abidjan', description: 'Côte d\'Ivoire' },
      { value: 'Africa/Accra', label: 'Africa/Accra', description: 'Ghana' },
      { value: 'Africa/Addis_Ababa', label: 'Africa/Addis_Ababa', description: 'Ethiopia' },
      { value: 'Africa/Algiers', label: 'Africa/Algiers', description: 'Algeria' },
      { value: 'Africa/Cairo', label: 'Africa/Cairo', description: 'Egypt' },
      { value: 'Africa/Casablanca', label: 'Africa/Casablanca', description: 'Morocco' },
      { value: 'Africa/Johannesburg', label: 'Africa/Johannesburg', description: 'South Africa' },
      { value: 'Africa/Lagos', label: 'Africa/Lagos', description: 'Nigeria' },
      { value: 'Africa/Nairobi', label: 'Africa/Nairobi', description: 'Kenya' },
      
      // America
      { value: 'America/New_York', label: 'America/New_York', description: 'US Eastern Time' },
      { value: 'America/Chicago', label: 'America/Chicago', description: 'US Central Time' },
      { value: 'America/Denver', label: 'America/Denver', description: 'US Mountain Time' },
      { value: 'America/Los_Angeles', label: 'America/Los_Angeles', description: 'US Pacific Time' },
      { value: 'America/Toronto', label: 'America/Toronto', description: 'Canada Eastern' },
      { value: 'America/Vancouver', label: 'America/Vancouver', description: 'Canada Pacific' },
      { value: 'America/Mexico_City', label: 'America/Mexico_City', description: 'Mexico' },
      { value: 'America/Sao_Paulo', label: 'America/Sao_Paulo', description: 'Brazil' },
      { value: 'America/Argentina/Buenos_Aires', label: 'America/Argentina/Buenos_Aires', description: 'Argentina' },
      { value: 'America/Bogota', label: 'America/Bogota', description: 'Colombia' },
      { value: 'America/Lima', label: 'America/Lima', description: 'Peru' },
      { value: 'America/Santiago', label: 'America/Santiago', description: 'Chile' },
      
      // Asia
      { value: 'Asia/Tokyo', label: 'Asia/Tokyo', description: 'Japan' },
      { value: 'Asia/Shanghai', label: 'Asia/Shanghai', description: 'China' },
      { value: 'Asia/Hong_Kong', label: 'Asia/Hong_Kong', description: 'Hong Kong' },
      { value: 'Asia/Singapore', label: 'Asia/Singapore', description: 'Singapore' },
      { value: 'Asia/Bangkok', label: 'Asia/Bangkok', description: 'Thailand' },
      { value: 'Asia/Jakarta', label: 'Asia/Jakarta', description: 'Indonesia' },
      { value: 'Asia/Manila', label: 'Asia/Manila', description: 'Philippines' },
      { value: 'Asia/Seoul', label: 'Asia/Seoul', description: 'South Korea' },
      { value: 'Asia/Taipei', label: 'Asia/Taipei', description: 'Taiwan' },
      { value: 'Asia/Kolkata', label: 'Asia/Kolkata', description: 'India' },
      { value: 'Asia/Dubai', label: 'Asia/Dubai', description: 'UAE' },
      { value: 'Asia/Riyadh', label: 'Asia/Riyadh', description: 'Saudi Arabia' },
      { value: 'Asia/Tehran', label: 'Asia/Tehran', description: 'Iran' },
      { value: 'Asia/Jerusalem', label: 'Asia/Jerusalem', description: 'Israel' },
      { value: 'Asia/Istanbul', label: 'Asia/Istanbul', description: 'Turkey' },
      
      // Australia & Pacific
      { value: 'Australia/Sydney', label: 'Australia/Sydney', description: 'Australia Eastern' },
      { value: 'Australia/Melbourne', label: 'Australia/Melbourne', description: 'Australia Eastern' },
      { value: 'Australia/Brisbane', label: 'Australia/Brisbane', description: 'Australia Eastern (no DST)' },
      { value: 'Australia/Perth', label: 'Australia/Perth', description: 'Australia Western' },
      { value: 'Australia/Adelaide', label: 'Australia/Adelaide', description: 'Australia Central' },
      { value: 'Pacific/Auckland', label: 'Pacific/Auckland', description: 'New Zealand' },
      { value: 'Pacific/Fiji', label: 'Pacific/Fiji', description: 'Fiji' },
      { value: 'Pacific/Honolulu', label: 'Pacific/Honolulu', description: 'Hawaii' },
      
      // Europe
      { value: 'Europe/London', label: 'Europe/London', description: 'United Kingdom' },
      { value: 'Europe/Dublin', label: 'Europe/Dublin', description: 'Ireland' },
      { value: 'Europe/Paris', label: 'Europe/Paris', description: 'France' },
      { value: 'Europe/Berlin', label: 'Europe/Berlin', description: 'Germany' },
      { value: 'Europe/Madrid', label: 'Europe/Madrid', description: 'Spain' },
      { value: 'Europe/Rome', label: 'Europe/Rome', description: 'Italy' },
      { value: 'Europe/Amsterdam', label: 'Europe/Amsterdam', description: 'Netherlands' },
      { value: 'Europe/Brussels', label: 'Europe/Brussels', description: 'Belgium' },
      { value: 'Europe/Vienna', label: 'Europe/Vienna', description: 'Austria' },
      { value: 'Europe/Zurich', label: 'Europe/Zurich', description: 'Switzerland' },
      { value: 'Europe/Stockholm', label: 'Europe/Stockholm', description: 'Sweden' },
      { value: 'Europe/Oslo', label: 'Europe/Oslo', description: 'Norway' },
      { value: 'Europe/Copenhagen', label: 'Europe/Copenhagen', description: 'Denmark' },
      { value: 'Europe/Helsinki', label: 'Europe/Helsinki', description: 'Finland' },
      { value: 'Europe/Warsaw', label: 'Europe/Warsaw', description: 'Poland' },
      { value: 'Europe/Prague', label: 'Europe/Prague', description: 'Czech Republic' },
      { value: 'Europe/Budapest', label: 'Europe/Budapest', description: 'Hungary' },
      { value: 'Europe/Bucharest', label: 'Europe/Bucharest', description: 'Romania' },
      { value: 'Europe/Athens', label: 'Europe/Athens', description: 'Greece' },
      { value: 'Europe/Moscow', label: 'Europe/Moscow', description: 'Russia (Moscow)' },
      { value: 'Europe/Kiev', label: 'Europe/Kiev', description: 'Ukraine' },
      { value: 'Europe/Lisbon', label: 'Europe/Lisbon', description: 'Portugal' }
    ],
    
    // Email lists - remove example data, will be loaded from backend
    blacklistedEmailsList: [],
    whitelistedEmailsList: [],
    alertEmailsList: [],
    
    // Settings data structure
    settings: {
      general: {
        applicationName: 'Containers on the Fly',
        timezone: 'UTC',
        loginPageInfo: '',
        reservationPageInstructions: '',
        emailInstructions: '',
        usernameFieldLabel: '',
        passwordFieldLabel: ''
      },
      access: {
        blacklistEnabled: false, 
        whitelistEnabled: false
      },
      email: {
        smtpServer: '',
        smtpPort: 587,
        smtpUsername: '',
        smtpPassword: '',
        fromEmail: ''
      },
      contact: {
        contactEmail: ''
      },
      notifications: {
        containerAlertsEnabled: false
      },
      monitoring: {
        // Placeholder for monitoring settings if any
      }
    },

    // Monitoring specific data
    selectedServer: null,
    availableServers: [],
    loadingServers: false,
    fetchingLogs: false,
    fetchingMetrics: false,
    logs: {
      backend: '',
      frontend: '',
      backendDockerUtil: ''
    },
    lastLogUpdate: null,
    lastMetricsUpdate: null,
    
    // Hardware metrics data
    metrics: {
      cpu: {
        usage: 0,
        cores: 0
      },
      memory: {
        total: 0,
        used: 0,
        percentage: 0
      },
      load: {
        current: 0,
        avg1: 0,
        avg5: 0,
        avg15: 0
      },
      uptime: {
        days: 0,
        hours: 0,
        minutes: 0
      },
      disk: {
        total: 0,
        used: 0,
        free: 0,
        percentage: 0
      },
      docker: {
        running: 0,
        total: 0
      }
    }
  }),
  
  mounted() {
    this.loadSettings();
    this.loadAvailableServers();  // Added this call
  },
  
  methods: {
    // Server monitoring methods
    onServerChange() {
      // Clear old data when switching servers
      this.clearMonitoringData();
      // Fetch new data for the selected server
      if (this.selectedServer) {
        this.fetchHardwareMetrics();
      }
    },

    clearMonitoringData() {
      // Reset metrics to show no data state
      this.metrics = {
        cpu: { usage: null, cores: null },
        memory: { total: null, used: null, percentage: null },
        load: { avg1: null, avg5: null, avg15: null },
        uptime: { days: null, hours: null, minutes: null },
        disk: { total: null, used: null, free: null, percentage: null },
        docker: { running: null, total: null }
      };
      
      // Clear logs
      this.logs = {
        backend: '',
        frontend: '',
        backendDockerUtil: ''
      };
      
      // Clear timestamps
      this.lastMetricsUpdate = null;
      this.lastLogUpdate = null;
    },

    // Email list management methods
    addBlacklistEmail() {
      if (this.isValidEmail(this.newBlacklistEmail) && !this.blacklistedEmailsList.includes(this.newBlacklistEmail)) {
        this.blacklistedEmailsList.push(this.newBlacklistEmail);
        this.newBlacklistEmail = '';
        this.saveEmailLists(); // Auto-save to backend
      }
    },
    
    removeBlacklistEmail(index) {
      this.blacklistedEmailsList.splice(index, 1);
      this.saveEmailLists(); // Auto-save to backend
    },
    
    addWhitelistEmail() {
      if (this.isValidEmail(this.newWhitelistEmail) && !this.whitelistedEmailsList.includes(this.newWhitelistEmail)) {
        this.whitelistedEmailsList.push(this.newWhitelistEmail);
        this.newWhitelistEmail = '';
        this.saveEmailLists(); // Auto-save to backend
      }
    },
    
    removeWhitelistEmail(index) {
      this.whitelistedEmailsList.splice(index, 1);
      this.saveEmailLists(); // Auto-save to backend
    },
    
    addAlertEmail() {
      if (this.isValidEmail(this.newAlertEmail) && !this.alertEmailsList.includes(this.newAlertEmail)) {
        this.alertEmailsList.push(this.newAlertEmail);
        this.newAlertEmail = '';
        this.saveAlertEmails(); // Auto-save to backend
      }
    },
    
    removeAlertEmail(index) {
      this.alertEmailsList.splice(index, 1);
      this.saveAlertEmails(); // Auto-save to backend
    },
    
    async loadSettings() {
      try {
        //console.log('Loading settings from backend...');
        this.isLoading = true; // Set loading flag
        
        let _this = this;
        let currentUser = this.$store.getters.user;

        axios({
          method: "get",
          url: this.AppSettings.APIServer.admin.get_general_settings,
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
          if (response.data.status == true) {
            const data = response.data.data;
            
            // Update settings from backend (update individual properties)
            _this.settings.general.applicationName = data.general.applicationName || 'Containers on the Fly';
            _this.settings.general.timezone = data.general.timezone || 'UTC';
            _this.settings.general.loginPageInfo = data.general.loginPageInfo || '';
            _this.settings.general.reservationPageInstructions = data.general.reservationPageInstructions || '';
            _this.settings.general.emailInstructions = data.general.emailInstructions || '';
            _this.settings.general.usernameFieldLabel = data.general.usernameFieldLabel || '';
            _this.settings.general.passwordFieldLabel = data.general.passwordFieldLabel || '';
            
            _this.settings.access.blacklistEnabled = data.access.blacklistEnabled || false;
            _this.settings.access.whitelistEnabled = data.access.whitelistEnabled || false;
            _this.settings.notifications.containerAlertsEnabled = data.notifications.containerAlertsEnabled || false;
            
            // Update email settings (excluding contactEmail)
            _this.settings.email = {
              smtpServer: data.email.smtpServer || '',
              smtpPort: data.email.smtpPort || 587,
              smtpUsername: data.email.smtpUsername || '',
              smtpPassword: data.email.smtpPassword || '',
              fromEmail: data.email.fromEmail || ''
            };
            
            // Update contact settings separately
            _this.settings.contact = {
              contactEmail: data.email.contactEmail || data.contact?.contactEmail || ''
            };
            
            // Mark settings as initialized after a small delay to ensure watchers don't fire during load
            setTimeout(() => {
              _this.settingsInitialized.blacklistEnabled = true;
              _this.settingsInitialized.whitelistEnabled = true;
              _this.settingsInitialized.containerAlertsEnabled = true;
            }, 200);
            
            // Update email lists
            _this.blacklistedEmailsList = data.access.blacklistedEmails || [];
            _this.whitelistedEmailsList = data.access.whitelistedEmails || [];
            _this.alertEmailsList = data.notifications.alertEmails || [];
            
            // Mark initial load as complete AFTER all updates using a longer timeout to ensure all reactivity is done
            setTimeout(() => {
              _this.isLoading = false;
              _this.initialLoadComplete = true;
            }, 500); // Increased timeout to 500ms
            
          } else {
            console.log("Failed to load settings...");
            _this.$store.commit('showMessage', { 
              text: "There was an error loading settings.", 
              color: "red" 
            });
          }
          // Mark initial load as complete even on error to enable auto-save watchers
          _this.isLoading = false;
          _this.initialLoadComplete = true;
        })
        .catch(function (error) {
          console.error('Failed to load settings:', error);
          if (error.response && (error.response.status == 400 || error.response.status == 401)) {
            _this.$store.commit('showMessage', { text: error.response.data.detail, color: "red" });
          } else {
            _this.$store.commit('showMessage', { 
              text: 'Failed to load settings', 
              color: 'red' 
            });
          }
          // Mark initial load as complete even on error to enable auto-save watchers
          _this.isLoading = false;
          _this.initialLoadComplete = true;
        });
        
      } catch (error) {
        console.error('Failed to load settings:', error);
        this.$store.commit('showMessage', { 
          text: 'Failed to load settings', 
          color: 'red' 
        });
        // Mark initial load as complete even on error to enable auto-save watchers
        this.isLoading = false;
        this.initialLoadComplete = true;
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
        
        // Prepare settings data based on section
        let settingsData = { ...this.settings[sectionName] };
        
        // Add email lists for access section
        if (sectionName === 'access') {
          settingsData.blacklistedEmails = this.blacklistedEmailsList;
          settingsData.whitelistedEmails = this.whitelistedEmailsList;
        }
        
        // Add alert emails for notifications section
        if (sectionName === 'notifications') {
          settingsData.alertEmails = this.alertEmailsList;
        }
        
        let _this = this;
        let currentUser = this.$store.getters.user;

        axios({
          method: "post",
          url: this.AppSettings.APIServer.admin.save_general_settings,
          data: {
            section: sectionName,
            settings: settingsData
          },
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(async function (response) {
          if (response.data.status == true) {
            // Show success notification
            _this.$store.commit('showMessage', { 
              text: `${_this.getSectionDisplayName(sectionName)} settings saved successfully!`, 
              color: 'green' 
            });
            
            // Reload app config for sections that affect public settings
            if (sectionName === 'general' || sectionName === 'contact') {
              try {
                await _this.$store.dispatch('loadAppConfig');
                //console.log('App configuration reloaded after saving', sectionName, 'settings');
              } catch (error) {
                console.error('Failed to reload app config:', error);
                // Don't show error to user as the save was successful
              }
            }
            
          } else {
            console.log(`Failed to save ${sectionName} settings...`);
            _this.$store.commit('showMessage', { 
              text: response.data.message || `There was an error saving ${_this.getSectionDisplayName(sectionName)} settings.`, 
              color: "red" 
            });
          }
          _this.saving[sectionName] = false;
        })
        .catch(function (error) {
          console.error(`Failed to save ${sectionName} settings:`, error);
          if (error.response && (error.response.status == 400 || error.response.status == 401)) {
            _this.$store.commit('showMessage', { text: error.response.data.detail, color: "red" });
          } else {
            _this.$store.commit('showMessage', { 
              text: `Failed to save ${_this.getSectionDisplayName(sectionName)} settings`, 
              color: 'red' 
            });
          }
          _this.saving[sectionName] = false;
        });
        
      } catch (error) {
        console.error(`Failed to save ${sectionName} settings:`, error);
        this.$store.commit('showMessage', { 
          text: `Failed to save ${this.getSectionDisplayName(sectionName)} settings`, 
          color: 'red' 
        });
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
        
        console.log(`Sending test email to: ${this.testEmail}`);
        
        let _this = this;
        let currentUser = this.$store.getters.user;

        axios({
          method: "post",
          url: this.AppSettings.APIServer.admin.test_email,
          data: {
            email: this.testEmail
          },
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
          if (response.data.status == true) {
            _this.$store.commit('showMessage', { 
              text: `Test email sent successfully to ${_this.testEmail}`, 
              color: 'green' 
            });
          } else {
            console.log("Failed to send test email...");
            _this.$store.commit('showMessage', { 
              text: response.data.message || 'Failed to send test email', 
              color: "red" 
            });
          }
          _this.sendingTest = false;
        })
        .catch(function (error) {
          console.error('Failed to send test email:', error);
          if (error.response && (error.response.status == 400 || error.response.status == 401)) {
            _this.$store.commit('showMessage', { text: error.response.data.detail, color: "red" });
          } else {
            _this.$store.commit('showMessage', { 
              text: 'Failed to send test email', 
              color: 'red' 
            });
          }
          _this.sendingTest = false;
        });
        
      } catch (error) {
        console.error('Failed to send test email:', error);
        this.$store.commit('showMessage', { 
          text: 'Failed to send test email', 
          color: 'red' 
        });
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
        notifications: 'System Notifications',
        monitoring: 'Monitoring' // Added monitoring
      };
      return names[sectionName] || sectionName;
    },

    // Monitoring methods
    async loadAvailableServers() {
      try {
        this.loadingServers = true;
        
        //console.log('Loading available servers...');
        
        let _this = this;
        let currentUser = this.$store.getters.user;

        axios({
          method: "get",
          url: this.AppSettings.APIServer.admin.get_servers,
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
          if (response.data.status == true) {
            _this.availableServers = response.data.data.servers.map(server => ({
              id: server.id,
              name: server.name,
              address: server.address
            }));
          } else {
            console.log("Failed getting servers...");
            _this.$store.commit('showMessage', { 
              text: "There was an error getting servers.", 
              color: "red" 
            });
          }
          _this.loadingServers = false;
        })
        .catch(function (error) {
          console.error('Failed to load servers:', error);
          if (error.response && (error.response.status == 400 || error.response.status == 401)) {
            _this.$store.commit('showMessage', { text: error.response.data.detail, color: "red" });
          } else {
            _this.$store.commit('showMessage', { 
              text: 'Failed to load available servers', 
              color: 'red' 
            });
          }
          _this.loadingServers = false;
        });
        
      } catch (error) {
        console.error('Failed to load servers:', error);
        this.$store.commit('showMessage', { 
          text: 'Failed to load available servers', 
          color: 'red' 
        });
        this.loadingServers = false;
      }
    },
    
    async fetchLogs() {
      // Since logs are now fetched together with metrics, just call the main method
      await this.fetchHardwareMetrics();
    },
    
        async fetchHardwareMetrics() {
      if (!this.selectedServer) return;
      
      try {
        this.fetchingMetrics = true;
        this.fetchingLogs = true;
        
        console.log(`Fetching monitoring data for server ${this.selectedServer}`);
        
        let _this = this;
        let currentUser = this.$store.getters.user;

        axios({
          method: "get",
          url: `${this.AppSettings.APIServer.admin.get_server_monitoring}/${this.selectedServer}/monitoring`,
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
          if (response.data.status == true) {
            const data = response.data.data;
            
            // Update metrics
            if (data.metrics) {
              _this.metrics = {
                cpu: data.metrics.cpu,
                memory: data.metrics.memory,
                disk: data.metrics.disk,
                docker: data.metrics.docker,
                load: data.metrics.load,
                uptime: data.metrics.uptime
              };
              
              if (data.metrics.lastUpdated) {
                _this.lastMetricsUpdate = new Date(data.metrics.lastUpdated);
              }
            }
            
            // Update logs (reverse order so latest are on top)
            _this.logs = {
              backend: data.logs.backend?.content || '',
              frontend: data.logs.frontend?.content || '',
              backendDockerUtil: data.logs.docker_utility?.content || ''
            };
          
            _this.lastLogUpdate = new Date();
            
          } else {
            console.log("Failed getting monitoring data...");
            _this.$store.commit('showMessage', { 
              text: response.data.message || 'Failed to fetch monitoring data', 
              color: 'red' 
            });
          }
          _this.fetchingMetrics = false;
          _this.fetchingLogs = false;
        })
        .catch(function (error) {
          console.error('Failed to fetch monitoring data:', error);
          if (error.response && (error.response.status == 400 || error.response.status == 401)) {
            _this.$store.commit('showMessage', { text: error.response.data.detail, color: "red" });
          } else {
            _this.$store.commit('showMessage', { 
              text: 'Failed to fetch monitoring data', 
              color: 'red' 
            });
          }
          _this.fetchingMetrics = false;
          _this.fetchingLogs = false;
        });
        
      } catch (error) {
        console.error('Failed to fetch monitoring data:', error);
        this.$store.commit('showMessage', { 
          text: 'Failed to fetch monitoring data', 
          color: 'red' 
        });
        this.fetchingMetrics = false;
        this.fetchingLogs = false;
      }
    },
    
    // Color helpers for metrics
    getCpuColor(usage) {
      if (usage === null || usage === undefined) return 'grey';
      if (usage < 50) return 'green';
      if (usage < 80) return 'orange';
      return 'red';
    },
    
    getMemoryColor(percentage) {
      if (percentage === null || percentage === undefined) return 'grey';
      if (percentage < 70) return 'green';
      if (percentage < 90) return 'orange';
      return 'red';
    },
    
    getDiskColor(percentage) {
      if (percentage === null || percentage === undefined) return 'grey';
      if (percentage < 80) return 'green';
      if (percentage < 95) return 'orange';
      return 'red';
    },
    
    // Format bytes to human readable
    formatBytes(bytes) {
      if (bytes === null || bytes === undefined) return '0 B';
      if (bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    },
    
    reverseLogOrder(logContent) {
      if (!logContent || logContent.trim() === '') return logContent;
      
      // Split by lines, reverse, and rejoin
      return logContent
        .split('\n')
        .reverse()
        .join('\n');
    },
    
    formatTimestamp(date) {
      return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      }).format(date);
    },

    // Updated email list management methods to auto-save
    async saveEmailLists() {
      // Don't save during initial loading to prevent spurious notifications
      if (!this.initialLoadComplete || this.isLoading) {
        return;
      }
      // Save access settings including email lists
      await this.saveSection('access');
    },

    async saveAlertEmails() {
      // Don't save during initial loading to prevent spurious notifications
      if (!this.initialLoadComplete || this.isLoading) {
        return;
      }
      // Save notification settings including alert emails
      await this.saveSection('notifications');
    }
  },

  watch: {
    // Auto-save when container alerts checkbox is toggled
    'settings.notifications.containerAlertsEnabled': function(newValue, oldValue) {
      if (this.settingsInitialized.containerAlertsEnabled && !this.isLoading && oldValue !== undefined && newValue !== oldValue) {
        this.saveAlertEmails();
      }
    },

    // Auto-save when access control checkboxes are toggled
    'settings.access.blacklistEnabled': function(newValue, oldValue) {
      if (this.settingsInitialized.blacklistEnabled && !this.isLoading && oldValue !== undefined && newValue !== oldValue) {
        this.saveEmailLists();
      }
    },

    'settings.access.whitelistEnabled': function(newValue, oldValue) {
      if (this.settingsInitialized.whitelistEnabled && !this.isLoading && oldValue !== undefined && newValue !== oldValue) {
        this.saveEmailLists();
      }
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

// Logs textarea styling
.logs-textarea {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace !important;
  font-size: 12px !important;
  line-height: 1.4 !important;
}

::v-deep .logs-textarea textarea {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace !important;
  font-size: 12px !important;
  line-height: 1.4 !important;
  color: rgba(255, 255, 255, 0.87) !important;
  background-color: #1e1e1e !important;
}

::v-deep .logs-textarea .v-text-field__details {
  display: none !important;
}

// Status chip styling
.v-chip {
  margin: 2px !important;
  
  &.v-chip--small {
    height: 24px !important;
    font-size: 11px !important;
  }
}

// Server selection styling
::v-deep .v-select__selections {
  min-height: 48px !important;
}
</style> 