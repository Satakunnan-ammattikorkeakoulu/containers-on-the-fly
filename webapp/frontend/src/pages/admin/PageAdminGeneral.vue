<template>
  <v-container>
    <v-row class="text-center">
      <v-col cols="12">
        <h4 class="m-0">Admin</h4>
        <h2 class="m-0">General Settings</h2>
        <p class="subtitle-1 text-grey m-0 mb-40">Configure system-wide settings and preferences</p>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <h2 class="settings-group-header settings-group-header--first">General</h2>
        <v-expansion-panels v-model="openPanel">

          <!-- General Information & Instructions Section -->
          <v-expansion-panel id="panel-general" value="general">
            <v-expansion-panel-title>
              <v-icon class="mr-3">mdi-information-outline</v-icon>
              <span class="font-weight-bold">General Information & Instructions</span>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-form ref="generalForm" v-model="forms.general.valid">
                
                <!-- Application Configuration ---->
                <div class="mb-6">
                  <h3 class="text-h3 mb-2">Application Configuration</h3>
                  <p class="body-2 text-grey mb-4">
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
                      <v-autocomplete
                        v-model="settings.general.timezone"
                        :items="timezoneOptions"
                        label="System Timezone"
                        outlined
                        required
                        :rules="[rules.required]"
                        hide-details
                        item-title="label"
                        item-value="value"
                      >
                        <template v-slot:item="{ item, props }">
                          <v-list-item v-bind="props" :subtitle="item.raw?.description || ''">
                          </v-list-item>
                        </template>
                      </v-autocomplete>
                    </v-col>
                  </v-row>
                </div>
                
                <!-- Login Page Information -->
                <div class="mb-6">
                  <h3 class="text-h3 mb-2">Login Page Instructions</h3>
                  <p class="body-2 text-grey mb-3">
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
                  <h3 class="text-h3 mb-2">Reservation Page Instructions</h3>
                  <p class="body-2 text-grey mb-3">
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
                  <h3 class="text-h3 mb-2">Container Reserved Instructions</h3>
                  <p class="body-2 text-grey mb-3">
                    Guidelines and instructions included in reservation confirmation emails sent to users (at the end of the email) and displayed when clicking "Show Details" on reservations.
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
                  <h3 class="text-h3 mb-2">Login Form Field Labels</h3>
                  <p class="body-2 text-grey mb-3">
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
            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- Legal Documents Section -->
          <v-expansion-panel id="panel-legal" value="legal">
            <v-expansion-panel-title>
              <v-icon class="mr-3">mdi-file-document-outline</v-icon>
              <span class="font-weight-bold">Legal Documents</span>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-form ref="legalForm" v-model="forms.legal.valid">

                <div class="mb-6">
                  <h3 class="text-h3 mb-2">Privacy Policy & Terms of Service</h3>
                  <p class="body-2 text-grey mb-4">
                    Configure legal documents displayed to users. When enabled, links appear on the login page and in the application footer.
                    Content supports Markdown formatting.
                  </p>

                  <v-switch
                    v-model="settings.legal.enabled"
                    label="Enable privacy policy and terms of service pages"
                    color="primary"
                    class="mt-0 mb-4"
                  ></v-switch>
                </div>

                <div v-if="settings.legal.enabled">
                  <!-- Organization Info -->
                  <div class="mb-6">
                    <h3 class="text-h3 mb-2">Organization Information</h3>
                    <p class="body-2 text-grey mb-3">
                      Organization name and data protection contact email used in the legal documents.
                    </p>
                    <v-row>
                      <v-col cols="12" md="6">
                        <v-text-field
                          v-model="settings.legal.organizationName"
                          label="Organization Name"
                          placeholder="e.g. University of Example"
                          outlined
                          hide-details
                        ></v-text-field>
                      </v-col>
                      <v-col cols="12" md="6">
                        <v-text-field
                          v-model="settings.legal.contactEmail"
                          label="Data Protection Contact Email"
                          placeholder="dpo@example.com"
                          outlined
                          hide-details
                        ></v-text-field>
                      </v-col>
                    </v-row>
                  </div>

                  <!-- Privacy Policy -->
                  <div class="mb-6">
                    <h3 class="text-h3 mb-2">Privacy Policy</h3>
                    <p class="body-2 text-grey mb-3">
                      Content displayed on the public privacy policy page. Supports Markdown formatting.<br>
                      Available variables: <code v-pre>{{ORGANIZATION_NAME}}</code>, <code v-pre>{{CONTACT_EMAIL}}</code>, <code v-pre>{{DATE}}</code> (last saved date).
                    </p>
                    <div class="d-flex mb-3">
                      <v-btn
                        variant="outlined"
                        size="small"
                        color="primary"
                        prepend-icon="mdi-file-document-edit-outline"
                        @click="confirmLoadTemplate('privacyPolicy')"
                      >Load Template</v-btn>
                      <v-btn
                        variant="outlined"
                        size="small"
                        :color="legalPreview.privacyPolicy ? 'grey' : 'primary'"
                        :prepend-icon="legalPreview.privacyPolicy ? 'mdi-pencil' : 'mdi-eye'"
                        class="ml-2"
                        @click="legalPreview.privacyPolicy = !legalPreview.privacyPolicy"
                      >{{ legalPreview.privacyPolicy ? 'Edit' : 'Preview' }}</v-btn>
                    </div>
                    <div v-if="legalPreview.privacyPolicy" class="legal-preview pa-4 rounded" v-html="renderedPrivacyPolicy"></div>
                    <v-textarea
                      v-else
                      v-model="settings.legal.privacyPolicyContent"
                      placeholder="Enter privacy policy content in Markdown format..."
                      rows="12"
                      outlined
                      hide-details
                    ></v-textarea>
                  </div>

                  <!-- Terms of Service -->
                  <div class="mb-6">
                    <h3 class="text-h3 mb-2">Terms of Service</h3>
                    <p class="body-2 text-grey mb-3">
                      Content displayed on the public terms of service page. Supports Markdown formatting.<br>
                      Available variables: <code v-pre>{{ORGANIZATION_NAME}}</code>, <code v-pre>{{CONTACT_EMAIL}}</code>, <code v-pre>{{DATE}}</code> (last saved date).
                    </p>
                    <div class="d-flex mb-3">
                      <v-btn
                        variant="outlined"
                        size="small"
                        color="primary"
                        prepend-icon="mdi-file-document-edit-outline"
                        @click="confirmLoadTemplate('termsOfService')"
                      >Load Template</v-btn>
                      <v-btn
                        variant="outlined"
                        size="small"
                        :color="legalPreview.termsOfService ? 'grey' : 'primary'"
                        :prepend-icon="legalPreview.termsOfService ? 'mdi-pencil' : 'mdi-eye'"
                        class="ml-2"
                        @click="legalPreview.termsOfService = !legalPreview.termsOfService"
                      >{{ legalPreview.termsOfService ? 'Edit' : 'Preview' }}</v-btn>
                    </div>
                    <div v-if="legalPreview.termsOfService" class="legal-preview pa-4 rounded" v-html="renderedTermsOfService"></div>
                    <v-textarea
                      v-else
                      v-model="settings.legal.termsOfServiceContent"
                      placeholder="Enter terms of service content in Markdown format..."
                      rows="12"
                      outlined
                      hide-details
                    ></v-textarea>
                  </div>

                  <!-- Load Template Confirmation Dialog -->
                  <v-dialog v-model="legalTemplateDialog.visible" max-width="450">
                    <v-card>
                      <v-card-title>Load Template</v-card-title>
                      <v-card-text>
                        This will replace the current {{ legalTemplateDialog.type === 'privacyPolicy' ? 'privacy policy' : 'terms of service' }} content with the default template. Are you sure?
                      </v-card-text>
                      <v-card-actions>
                        <v-spacer></v-spacer>
                        <v-btn variant="text" @click="legalTemplateDialog.visible = false">Cancel</v-btn>
                        <v-btn color="primary" variant="flat" @click="loadTemplate(legalTemplateDialog.type)">Replace</v-btn>
                      </v-card-actions>
                    </v-card>
                  </v-dialog>
                </div>

                <v-row>
                  <v-col cols="12">
                    <v-btn
                      color="primary"
                      :loading="saving.legal"
                      @click="saveSection('legal')"
                    >
                      <v-icon left>mdi-content-save</v-icon>
                      Save Legal Settings
                    </v-btn>
                  </v-col>
                </v-row>
              </v-form>
            </v-expansion-panel-text>
          </v-expansion-panel>

        </v-expansion-panels>

        <h2 class="settings-group-header">Access &amp; Security</h2>
        <v-expansion-panels v-model="openPanel">

          <!-- Authentication Section -->
          <v-expansion-panel id="panel-auth" value="auth">
            <v-expansion-panel-title>
              <v-icon class="mr-3">mdi-account-key</v-icon>
              <span class="font-weight-bold">Authentication</span>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-form ref="authForm" v-model="forms.auth.valid">
                
                <!-- Login Type Settings -->
                <div class="mb-6">
                  <h3 class="text-h3 mb-2">Login Method</h3>
                  <p class="body-2 text-grey mb-4">
                    Choose how users authenticate with the system.
                  </p>
                  <v-radio-group
                    v-model="settings.auth.loginType"
                    row
                    class="mt-0"
                  >
                    <v-radio
                      label="Password Only"
                      value="password"
                      color="primary"
                    ></v-radio>
                    <v-radio
                      label="Password + LDAP"
                      value="hybrid"
                      color="primary"
                    ></v-radio>
                  </v-radio-group>
                  
                  <!-- Password + LDAP explanation -->
                  <v-alert
                    v-if="settings.auth.loginType === 'hybrid'"
                    variant="outlined"
                    type="info"
                    class="mt-2 mb-4"
                  >
                    <p class="body-2 mb-0">
                      <strong>Password + LDAP Mode</strong>: If a user has a password set, it will try password authentication first. 
                      If the password is incorrect or not set, it will attempt LDAP authentication. Users can still log in with their password even if LDAP is enabled.
                    </p>
                  </v-alert>
                </div>
                
                <!-- Session Timeout -->
                <div class="mb-6">
                  <h3 class="text-h3 mb-2">Session Settings</h3>
                  <p class="body-2 text-grey mb-4">
                    Configure how long user sessions remain active before requiring re-login.
                  </p>
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.auth.sessionTimeoutMinutes"
                        label="Session Timeout (minutes)"
                        type="number"
                        min="5"
                        outlined
                        required
                        :rules="[rules.required, rules.positiveNumber]"
                        hide-details
                        placeholder="1440"
                      ></v-text-field>
                    </v-col>
                  </v-row>
                </div>
                
                <!-- LDAP Configuration -->
                <div class="mb-6" v-if="settings.auth.loginType === 'hybrid'">
                  <h3 class="text-h3 mb-2">LDAP Server Configuration</h3>
                  <p class="body-2 text-grey mb-4">
                    Configure connection to your LDAP directory server for user authentication.
                  </p>
                  
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.auth.ldap.url"
                        label="LDAP Server URL"
                        placeholder="ldaps://your-ldap-server-address"
                        outlined
                        required
                        :rules="[rules.required]"
                      ></v-text-field>
                    </v-col>
                    
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.auth.ldap.domain"
                        label="LDAP Domain"
                        placeholder="dc=ad,dc=local"
                        outlined
                        required
                        :rules="[rules.required]"
                      ></v-text-field>
                    </v-col>
                    
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.auth.ldap.usernameFormat"
                        label="LDAP Username Format"
                        placeholder="{username}@ad.local"
                        outlined
                        required
                        :rules="[rules.required]"
                      ></v-text-field>
                    </v-col>
                    
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.auth.ldap.passwordFormat"
                        label="LDAP Password Format"
                        placeholder="{password}"
                        outlined
                        required
                        :rules="[rules.required]"
                      ></v-text-field>
                    </v-col>
                    
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.auth.ldap.searchMethod"
                        label="LDAP Search Method"
                        placeholder="(sAMAccountName={username})"
                        outlined
                        required
                        :rules="[rules.required]"
                      ></v-text-field>
                    </v-col>
                    
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.auth.ldap.accountField"
                        label="LDAP Account Field"
                        placeholder="sAMAccountName"
                        outlined
                        required
                        :rules="[rules.required]"
                      ></v-text-field>
                    </v-col>
                    
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.auth.ldap.emailField"
                        label="LDAP Email Field"
                        placeholder="mail"
                        outlined
                        required
                        :rules="[rules.required]"
                      ></v-text-field>
                    </v-col>

                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.auth.ldap.nameField"
                        label="LDAP Name Field (optional)"
                        placeholder="displayName"
                        outlined
                      ></v-text-field>
                    </v-col>
                  </v-row>
                </div>
                
                <v-row>
                  <v-col cols="12">
                    <v-btn 
                      color="primary" 
                      :loading="saving.auth"
                      @click="saveSection('auth')"
                    >
                      <v-icon left>mdi-content-save</v-icon>
                      Save Authentication Settings
                    </v-btn>
                  </v-col>
                </v-row>
              </v-form>

              <!-- Test AD/LDAP Connection Section -->
              <div class="mb-6" v-if="settings.auth.loginType === 'hybrid'">
                <v-divider class="my-4"></v-divider>
                <h3 class="text-h3 mb-2">Test AD/LDAP Connection</h3>
                <p class="body-2 text-grey mb-4">
                  Test your LDAP configuration by authenticating with a real username and password.
                  The full LDAP server response (all attributes) will be displayed below.
                </p>

                <v-row>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model="testAdUsername"
                      label="LDAP Username"
                      placeholder="jdoe"
                      outlined
                    ></v-text-field>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model="testAdPassword"
                      label="LDAP Password"
                      type="password"
                      outlined
                      @keyup.enter="testAdConnection"
                    ></v-text-field>
                  </v-col>
                </v-row>

                <v-row>
                  <v-col cols="12">
                    <v-btn
                      color="primary"
                      :loading="testingAd"
                      :disabled="!testAdUsername || !testAdPassword"
                      @click="testAdConnection"
                    >
                      Test AD Connection
                    </v-btn>
                  </v-col>
                </v-row>

                <v-row v-if="testAdResult">
                  <v-col cols="12">
                    <v-textarea
                      v-model="testAdResult"
                      label="LDAP Server Response"
                      readonly
                      outlined
                      auto-grow
                      rows="10"
                    ></v-textarea>
                  </v-col>
                </v-row>
              </div>

            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- User Access Control Section -->
          <v-expansion-panel id="panel-access" value="access">
            <v-expansion-panel-title>
              <v-icon class="mr-3">mdi-shield-account</v-icon>
              <span class="font-weight-bold">User Access Control</span>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-form ref="accessForm" v-model="forms.access.valid">
                <v-row>
                  <v-col cols="12" md="6">
                    <v-card variant="outlined" class="pa-4">
                      <div class="mb-4">
                        <h3 class="text-h3 mb-2 d-flex align-center">
                          <v-icon left color="red">mdi-account-cancel</v-icon>
                          Email Blacklist
                        </h3>
                        <p class="body-2 text-grey mb-3">
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
                        <p class="caption text-grey mb-2">Blacklisted emails:</p>
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
                      
                      <div v-else-if="settings.access.blacklistEnabled" class="text-center text-grey">
                        <p class="body-2">No emails blacklisted</p>
                      </div>
                    </v-card>
                  </v-col>
                  
                  <v-col cols="12" md="6">
                    <v-card variant="outlined" class="pa-4">
                      <div class="mb-4">
                        <h3 class="text-h3 mb-2 d-flex align-center">
                          <v-icon left color="green">mdi-account-check</v-icon>
                          Email Whitelist
                        </h3>
                        <p class="body-2 text-grey mb-3">
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
                        <p class="caption text-grey mb-2">Whitelisted emails:</p>
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
                      
                      <div v-else-if="settings.access.whitelistEnabled" class="text-center text-grey">
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
            </v-expansion-panel-text>
          </v-expansion-panel>

        </v-expansion-panels>

        <h2 class="settings-group-header">Email &amp; Notifications</h2>
        <v-expansion-panels v-model="openPanel">

          <!-- Email Configuration Section -->
          <v-expansion-panel id="panel-email" value="email">
            <v-expansion-panel-title>
              <v-icon class="mr-3">mdi-email-outline</v-icon>
              <span class="font-weight-bold">Email Configuration</span>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              
              <!-- Contact Information Section with its own separate form -->
              <v-form ref="contactForm" v-model="forms.contact.valid">
                <div class="mb-6">
                  <h3 class="text-h3 mb-2">Contact Email</h3>
                  <p class="body-2 text-grey mb-4">
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
              
              <!-- Master Email Enable Section with its own form -->
              <v-form ref="emailEnableForm" v-model="forms.emailEnable.valid">
                <div class="mb-6">
                  <h3 class="text-h3 mb-2">Email System</h3>
                  <p class="body-2 text-grey mb-4">
                    Enable or disable email sending from the system. When disabled, no emails will be sent for reservations or notifications.
                  </p>
                  
                  <v-checkbox
                    v-model="settings.emailEnable.sendEmail"
                    label="Enable sending emails from the system"
                    color="primary"
                    class="mt-0"
                  ></v-checkbox>
                </div>
              </v-form>
              
              <!-- SMTP Settings Section with its own form -->
              <v-form ref="emailForm" v-model="forms.email.valid">
                <div class="mb-6" v-if="settings.emailEnable.sendEmail">
                  <h3 class="text-h3 mb-2">SMTP Server Configuration</h3>
                  <p class="body-2 text-grey mb-4">
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
              
              <!-- Test Email Delivery Section (no form needed, just uses validation) -->
              <div class="mb-6" v-if="settings.emailEnable.sendEmail">
                <h3 class="text-h3 mb-2">Test Email Delivery</h3>
                <p class="body-2 text-grey mb-4">
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
              
            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- Email Templates Section -->
          <v-expansion-panel id="panel-emailTemplates" value="emailTemplates">
            <v-expansion-panel-title>
              <v-icon class="mr-3">mdi-email-edit-outline</v-icon>
              <span class="font-weight-bold">Email Templates</span>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-form ref="emailTemplatesForm" v-model="forms.emailTemplates.valid">
                <p class="body-2 text-grey mb-4">
                  Customize the subject lines and introductory text for emails sent to users
                  during container lifecycle events. Leave body intro fields empty to use the default text.
                </p>

                <!-- Container Started Email -->
                <div class="mb-6">
                  <h3 class="text-h3 mb-2">Container Started</h3>
                  <p class="body-2 text-grey mb-3">
                    Sent when a user's container reservation starts successfully.
                  </p>
                  <v-checkbox
                    v-model="settings.emailTemplates.enableContainerStarted"
                    label="Enable this email"
                    color="primary"
                    class="mt-0 mb-2"
                    hide-details
                  ></v-checkbox>
                  <v-text-field
                    v-model="settings.emailTemplates.subjectContainerStarted"
                    label="Subject Line"
                    placeholder="Server is ready to use!"
                    :rules="[rules.required]"
                    variant="outlined"
                    hide-details="auto"
                    :disabled="!settings.emailTemplates.enableContainerStarted"
                    class="mb-3"
                  ></v-text-field>
                  <v-textarea
                    v-model="settings.emailTemplates.bodyIntroContainerStarted"
                    label="Optional Body Intro Text"
                    placeholder=""
                    rows="2"
                    variant="outlined"
                    hide-details="auto"
                    :disabled="!settings.emailTemplates.enableContainerStarted"
                  ></v-textarea>
                </div>

                <v-divider class="mb-6"></v-divider>

                <!-- Container Error Email -->
                <div class="mb-6">
                  <h3 class="text-h3 mb-2">Container Error</h3>
                  <p class="body-2 text-grey mb-3">
                    Sent when a user's container fails to start.
                  </p>
                  <v-checkbox
                    v-model="settings.emailTemplates.enableContainerError"
                    label="Enable this email"
                    color="primary"
                    class="mt-0 mb-2"
                    hide-details
                  ></v-checkbox>
                  <v-text-field
                    v-model="settings.emailTemplates.subjectContainerError"
                    label="Subject Line"
                    placeholder="Server did not start"
                    :rules="[rules.required]"
                    variant="outlined"
                    hide-details="auto"
                    :disabled="!settings.emailTemplates.enableContainerError"
                    class="mb-3"
                  ></v-text-field>
                  <v-textarea
                    v-model="settings.emailTemplates.bodyIntroContainerError"
                    label="Optional Body Intro Text"
                    placeholder=""
                    rows="2"
                    variant="outlined"
                    hide-details="auto"
                    :disabled="!settings.emailTemplates.enableContainerError"
                  ></v-textarea>
                </div>

                <v-divider class="mb-6"></v-divider>

                <!-- Container Paused Email -->
                <div class="mb-6">
                  <h3 class="text-h3 mb-2">Container Paused</h3>
                  <p class="body-2 text-grey mb-3">
                    Sent when a low-priority container is paused for a higher-priority reservation.
                  </p>
                  <v-checkbox
                    v-model="settings.emailTemplates.enableContainerPaused"
                    label="Enable this email"
                    color="primary"
                    class="mt-0 mb-2"
                    hide-details
                  ></v-checkbox>
                  <v-text-field
                    v-model="settings.emailTemplates.subjectContainerPaused"
                    label="Subject Line"
                    placeholder="Low-priority container paused"
                    :rules="[rules.required]"
                    variant="outlined"
                    hide-details="auto"
                    :disabled="!settings.emailTemplates.enableContainerPaused"
                    class="mb-3"
                  ></v-text-field>
                  <v-textarea
                    v-model="settings.emailTemplates.bodyIntroContainerPaused"
                    label="Optional Body Intro Text"
                    placeholder=""
                    rows="2"
                    variant="outlined"
                    hide-details="auto"
                    :disabled="!settings.emailTemplates.enableContainerPaused"
                  ></v-textarea>
                </div>

                <v-divider class="mb-6"></v-divider>

                <!-- Container Resumed Email -->
                <div class="mb-6">
                  <h3 class="text-h3 mb-2">Container Resumed</h3>
                  <p class="body-2 text-grey mb-3">
                    Sent when a paused low-priority container is resumed.
                  </p>
                  <v-checkbox
                    v-model="settings.emailTemplates.enableContainerResumed"
                    label="Enable this email"
                    color="primary"
                    class="mt-0 mb-2"
                    hide-details
                  ></v-checkbox>
                  <v-text-field
                    v-model="settings.emailTemplates.subjectContainerResumed"
                    label="Subject Line"
                    placeholder="Low-priority container resumed"
                    :rules="[rules.required]"
                    variant="outlined"
                    hide-details="auto"
                    :disabled="!settings.emailTemplates.enableContainerResumed"
                    class="mb-3"
                  ></v-text-field>
                  <v-textarea
                    v-model="settings.emailTemplates.bodyIntroContainerResumed"
                    label="Optional Body Intro Text"
                    placeholder=""
                    rows="2"
                    variant="outlined"
                    hide-details="auto"
                    :disabled="!settings.emailTemplates.enableContainerResumed"
                  ></v-textarea>
                </div>

                <v-divider class="mb-6"></v-divider>

                <!-- Container Resume Failed Email -->
                <div class="mb-6">
                  <h3 class="text-h3 mb-2">Container Resume Failed</h3>
                  <p class="body-2 text-grey mb-3">
                    Sent when a paused low-priority container fails to resume. The reservation reaches a terminal error state and the user must create a new reservation to recover their work.
                  </p>
                  <v-checkbox
                    v-model="settings.emailTemplates.enableContainerResumeFailed"
                    label="Enable this email"
                    color="primary"
                    class="mt-0 mb-2"
                    hide-details
                  ></v-checkbox>
                  <v-text-field
                    v-model="settings.emailTemplates.subjectContainerResumeFailed"
                    label="Subject Line"
                    placeholder="Low-priority container failed to resume"
                    :rules="[rules.required]"
                    variant="outlined"
                    hide-details="auto"
                    :disabled="!settings.emailTemplates.enableContainerResumeFailed"
                    class="mb-3"
                  ></v-text-field>
                  <v-textarea
                    v-model="settings.emailTemplates.bodyIntroContainerResumeFailed"
                    label="Optional Body Intro Text"
                    placeholder=""
                    rows="2"
                    variant="outlined"
                    hide-details="auto"
                    :disabled="!settings.emailTemplates.enableContainerResumeFailed"
                  ></v-textarea>
                </div>

                <v-divider class="mb-6"></v-divider>

                <!-- Low-Priority Notice -->
                <div class="mb-6">
                  <h3 class="text-h3 mb-2">Low-Priority Reservation Notice</h3>
                  <p class="body-2 text-grey mb-3">
                    Notice text added to the container started and resumed emails when the user's reservation is low-priority.
                    Warns the user that their container may be paused if a higher-priority reservation needs the resources.
                  </p>
                  <v-textarea
                    v-model="settings.emailTemplates.lowPriorityNotice"
                    label="Low-Priority Notice Text"
                    placeholder=""
                    rows="3"
                    variant="outlined"
                    hide-details="auto"
                  ></v-textarea>
                </div>

                <!-- Save Button -->
                <v-row>
                  <v-col cols="12">
                    <v-btn
                      color="primary"
                      :loading="saving.emailTemplates"
                      @click="saveSection('emailTemplates')"
                    >
                      <v-icon start>mdi-content-save</v-icon>
                      Save Email Templates
                    </v-btn>
                  </v-col>
                </v-row>
              </v-form>
            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- System Notifications Section -->
          <v-expansion-panel id="panel-notifications" value="notifications">
            <v-expansion-panel-title>
              <v-icon class="mr-3">mdi-bell-alert</v-icon>
              <span class="font-weight-bold">System Notifications</span>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-form ref="notificationsForm" v-model="forms.notifications.valid">
                
                <!-- Container Failure Alerts -->
                <div class="mb-6">
                  <h3 class="text-h3 mb-2">Container Failure Alerts</h3>
                  <p class="body-2 text-grey mb-4">
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
                    <p class="caption text-grey mb-2">Alert recipients:</p>
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
                  
                  <div v-else-if="settings.notifications.containerAlertsEnabled" class="text-center text-grey">
                    <p class="body-2">No alert recipients configured</p>
                  </div>
                </div>
                

              </v-form>
            </v-expansion-panel-text>
          </v-expansion-panel>

        </v-expansion-panels>

        <h2 class="settings-group-header">Integrations &amp; Connections</h2>
        <v-expansion-panels v-model="openPanel">

          <!-- Connection Methods Section -->
          <v-expansion-panel id="panel-connection" value="connection">
            <v-expansion-panel-title>
              <v-icon class="mr-3">mdi-connection</v-icon>
              <span class="font-weight-bold">SSH Connection Methods</span>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-form ref="connectionForm" v-model="forms.connection.valid">

                <div class="mb-6">
                  <h3 class="text-h3 mb-2">SSH Connection Methods</h3>
                  <p class="body-2 text-grey mb-4">
                    Define which connection methods are shown to users when connecting to containers via SSH.
                    These appear as toggle options in the connection details modal.
                    Icons use Material Design Icons — <a href="https://pictogrammers.com/library/mdi/" target="_blank" rel="noopener noreferrer">browse available icons</a>.
                    <a href="#" @click.prevent="confirmResetSshMethods">Reset to defaults</a>
                  </p>

                  <v-card
                    v-for="(method, index) in settings.connection.sshMethods"
                    :key="index"
                    variant="outlined"
                    class="pa-4 mb-3"
                  >
                    <v-row dense>
                      <v-col cols="12" md="5" class="d-flex align-center">
                        <v-icon size="large" class="mr-2">{{ method.icon || 'mdi-help-circle-outline' }}</v-icon>
                        <v-text-field
                          v-model="method.icon"
                          label="Icon"
                          placeholder="mdi-console"
                          density="compact"
                          hide-details
                        ></v-text-field>
                      </v-col>
                      <v-col cols="12" md="5">
                        <v-text-field
                          v-model="method.name"
                          label="Name"
                          placeholder="Terminal"
                          :rules="[rules.required]"
                          density="compact"
                          hide-details
                        ></v-text-field>
                      </v-col>
                      <v-col cols="12" md="2" class="d-flex align-center justify-end" style="gap: 12px;">
                        <v-tooltip v-if="index !== 0" location="top" text="Move up">
                          <template v-slot:activator="{ props }">
                            <v-icon v-bind="props" size="small" style="cursor: pointer;" @click="moveSshMethod(index, -1)">mdi-arrow-up</v-icon>
                          </template>
                        </v-tooltip>
                        <v-icon v-else size="small" style="opacity: 0.3;">mdi-arrow-up</v-icon>

                        <v-tooltip v-if="index !== settings.connection.sshMethods.length - 1" location="top" text="Move down">
                          <template v-slot:activator="{ props }">
                            <v-icon v-bind="props" size="small" style="cursor: pointer;" @click="moveSshMethod(index, 1)">mdi-arrow-down</v-icon>
                          </template>
                        </v-tooltip>
                        <v-icon v-else size="small" style="opacity: 0.3;">mdi-arrow-down</v-icon>

                        <v-tooltip v-if="settings.connection.sshMethods.length > 1" location="top" text="Remove this method">
                          <template v-slot:activator="{ props }">
                            <v-icon v-bind="props" size="small" color="red" style="cursor: pointer;" @click="removeSshMethod(index)">mdi-close</v-icon>
                          </template>
                        </v-tooltip>
                        <v-icon v-else size="small" color="red" style="opacity: 0.3;">mdi-close</v-icon>
                      </v-col>
                    </v-row>
                    <v-row dense class="mt-2">
                      <v-col cols="12" md="6">
                        <v-text-field
                          v-model="method.template"
                          label="Connection string template"
                          placeholder="ssh {username}@{ip} -p {port}"
                          :rules="[rules.required]"
                          density="compact"
                          hide-details
                        ></v-text-field>
                      </v-col>
                      <v-col cols="12" md="6">
                        <v-text-field
                          v-model="method.helpText"
                          label="Help text shown above connection string"
                          placeholder="Run this command in your terminal"
                          density="compact"
                          hide-details
                        ></v-text-field>
                      </v-col>
                    </v-row>
                  </v-card>

                  <v-btn color="primary" variant="text" class="mt-2" @click="addSshMethod">
                    <v-icon start>mdi-plus</v-icon>
                    Add Method
                  </v-btn>

                  <p class="text-medium-emphasis mt-4" style="font-size: 12px;">
                    Available template variables: <code>{username}</code>, <code>{ip}</code>, <code>{port}</code>
                  </p>
                </div>

                <div class="mt-4">
                  <v-btn
                    color="primary"
                    :loading="saving.connection"
                    @click="saveSection('connection')"
                  >
                    <v-icon left>mdi-content-save</v-icon>
                    Save Connection Settings
                  </v-btn>
                </div>

              </v-form>
            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- Analytics Section -->
          <v-expansion-panel id="panel-analytics" value="analytics">
            <v-expansion-panel-title>
              <v-icon class="mr-3">mdi-chart-line</v-icon>
              <span class="font-weight-bold">Analytics</span>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-form ref="analyticsForm" v-model="forms.analytics.valid">

                <p class="body-2 text-grey mb-6">
                  Configure optional web analytics to track page views and user activity. Both services are independent and can be enabled separately.
                </p>

                <!-- Rybbit Analytics -->
                <div class="mb-6">
                  <h3 class="text-h3 mb-2">Rybbit Analytics</h3>
                  <p class="body-2 text-grey mb-4">
                    Privacy-friendly, open-source analytics. Provide your Rybbit instance URL and site ID to enable tracking.
                  </p>
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.analytics.rybbitUrl"
                        label="Rybbit Instance URL"
                        placeholder="https://app.rybbit.io"
                        hint="Your Rybbit instance URL (e.g. https://app.rybbit.io or self-hosted)"
                        persistent-hint
                        outlined
                        hide-details="auto"
                      ></v-text-field>
                    </v-col>
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.analytics.rybbitSiteId"
                        label="Rybbit Site ID"
                        placeholder="1"
                        hint="Your site ID from the Rybbit dashboard"
                        persistent-hint
                        outlined
                        hide-details="auto"
                      ></v-text-field>
                    </v-col>
                  </v-row>
                </div>

                <!-- Google Analytics -->
                <div class="mb-6">
                  <h3 class="text-h3 mb-2">Google Analytics</h3>
                  <p class="body-2 text-grey mb-4">
                    Google Analytics 4 integration. Provide your measurement ID to enable tracking.
                  </p>
                  <v-row>
                    <v-col cols="12" md="6">
                      <v-text-field
                        v-model="settings.analytics.googleAnalyticsId"
                        label="GA4 Measurement ID"
                        placeholder="G-XXXXXXXXXX"
                        hint="Your Google Analytics 4 measurement ID"
                        persistent-hint
                        outlined
                        hide-details="auto"
                      ></v-text-field>
                    </v-col>
                  </v-row>
                </div>

                <v-btn
                  color="primary"
                  @click="saveSection('analytics')"
                  :loading="saving.analytics"
                  class="mt-2"
                >
                  <v-icon left>mdi-content-save</v-icon>
                  Save Analytics Settings
                </v-btn>

              </v-form>
            </v-expansion-panel-text>
          </v-expansion-panel>

        </v-expansion-panels>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
/**
 * Admin page for managing system-wide settings.
 * Sections are clustered under four group headers:
 *   - General: general info/instructions, legal documents (privacy policy, terms of service).
 *   - Access & Security: authentication (password/LDAP), user access control (blacklist/whitelist).
 *   - Email & Notifications: email configuration (SMTP, contact, test delivery), email templates,
 *     system notifications (container failure alerts).
 *   - Integrations & Connections: SSH connection methods, analytics.
 * Toggle-type settings (checkboxes, radio buttons) auto-save via watchers;
 * text fields require explicit save button clicks per section.
 */
import axios from 'axios';
import { useMainStore } from '@/store/store'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { privacyPolicyTemplate, termsOfServiceTemplate, fillTemplate } from '/src/helpers/legalTemplates'

export default {
  name: 'PageAdminGeneral',

  setup() {
    const store = useMainStore()
    return { store }
  },

  data: () => ({
    // Currently expanded panel id, shared across all four group containers so
    // that opening a panel in one group automatically collapses any panel open
    // in another group (single-open accordion behavior).
    openPanel: null,
    initialLoadComplete: false, // Flag to prevent auto-save during initial load
    isLoading: false, // Flag to indicate we're currently loading data
    settingsInitialized: {
      blacklistEnabled: false,
      whitelistEnabled: false,
      containerAlertsEnabled: false,
      sendEmail: false,
      loginType: false,
      legalEnabled: false
    }, // Track which settings have been initialized from backend
    legalPreview: {
      privacyPolicy: false,
      termsOfService: false
    },
    legalTemplateDialog: {
      visible: false,
      type: ''
    },
    testEmail: '',
    sendingTest: false,
    testAdUsername: '',
    testAdPassword: '',
    testingAd: false,
    testAdResult: '',
    
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
      emailEnable: { valid: true },  // Add emailEnable form state
      contact: { valid: true },  // Add contact form state
      notifications: { valid: true },
      auth: { valid: true },
      analytics: { valid: true },
      legal: { valid: true },
      connection: { valid: true },
      emailTemplates: { valid: true }
    },

    // Saving states for each section
    saving: {
      general: false,
      access: false,
      email: false,
      emailEnable: false,  // Added emailEnable saving state
      contact: false,  // Added contact saving state
      notifications: false,
      auth: false,
      analytics: false,
      legal: false,
      connection: false,
      emailTemplates: false
    },
    
    // Form validation rules
    rules: {
      required: value => !!value || 'This field is required',
      email: value => {
        if (!value) return true; // Allow empty for optional fields
        const pattern = /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/
        return pattern.test(value) || 'Invalid email format'
      },
      positiveNumber: value => {
        if (!value) return 'This field is required'
        const num = parseInt(value)
        return (num > 0) || 'Must be a positive number'
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
      emailEnable: {
        sendEmail: false
      },
      contact: {
        contactEmail: ''
      },
      notifications: {
        containerAlertsEnabled: false
      },
      auth: {
        loginType: 'password',
        sessionTimeoutMinutes: 1440,
        ldap: {
          url: '',
          usernameFormat: '',
          passwordFormat: '',
          domain: '',
          searchMethod: '',
          accountField: '',
          emailField: '',
          nameField: ''
        }
      },
      analytics: {
        rybbitUrl: '',
        rybbitSiteId: '',
        googleAnalyticsId: ''
      },
      legal: {
        enabled: false,
        organizationName: '',
        contactEmail: '',
        privacyPolicyContent: '',
        termsOfServiceContent: '',
        lastUpdated: ''
      },
      connection: {
        sshMethods: [
          { id: "vscode", name: "VS Code", icon: "mdi-microsoft-visual-studio-code", template: "{username}@{ip}:{port}", helpText: "Open the Remote SSH extension and connect to" },
          { id: "terminal", name: "Terminal", icon: "mdi-console", template: "ssh {username}@{ip} -p {port}", helpText: "Run this command in your terminal" }
        ]
      },
      emailTemplates: {
        enableContainerStarted: true,
        enableContainerError: true,
        enableContainerPaused: true,
        enableContainerResumed: true,
        enableContainerResumeFailed: true,
        subjectContainerStarted: '',
        subjectContainerError: '',
        subjectContainerPaused: '',
        subjectContainerResumed: '',
        subjectContainerResumeFailed: '',
        bodyIntroContainerStarted: '',
        bodyIntroContainerError: '',
        bodyIntroContainerPaused: '',
        bodyIntroContainerResumed: '',
        bodyIntroContainerResumeFailed: '',
        lowPriorityNotice: ''
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

    /** Reset SSH connection methods to defaults after user confirmation. */
    confirmResetSshMethods() {
      if (confirm('Reset SSH connection methods to defaults (VS Code and Terminal)? This will discard your current configuration.')) {
        this.settings.connection.sshMethods = [
          { id: "vscode", name: "VS Code", icon: "mdi-microsoft-visual-studio-code", template: "{username}@{ip}:{port}", helpText: "Open the Remote SSH extension and connect to" },
          { id: "terminal", name: "Terminal", icon: "mdi-console", template: "ssh {username}@{ip} -p {port}", helpText: "Run this command in your terminal" }
        ];
      }
    },

    /** Add a new empty SSH connection method to the list. */
    addSshMethod() {
      const id = 'method-' + Date.now();
      this.settings.connection.sshMethods.push({
        id: id, name: '', icon: 'mdi-application', template: '', helpText: ''
      });
    },

    /** Remove an SSH connection method by index. */
    removeSshMethod(index) {
      if (this.settings.connection.sshMethods.length > 1) {
        this.settings.connection.sshMethods.splice(index, 1);
      }
    },

    /** Move an SSH connection method up or down in the list. */
    moveSshMethod(index, direction) {
      const methods = this.settings.connection.sshMethods;
      const newIndex = index + direction;
      if (newIndex < 0 || newIndex >= methods.length) return;
      const item = methods.splice(index, 1)[0];
      methods.splice(newIndex, 0, item);
    },

    /**
     * Loads all settings sections from the backend and populates local state.
     * Uses settingsInitialized flags and isLoading to prevent watchers from
     * triggering auto-save during the initial hydration.
     */
    async loadSettings() {
      try {
        //console.log('Loading settings from backend...');
        this.isLoading = true; // Set loading flag
        
        let _this = this;
        let currentUser = this.store.user;

        axios({
          method: "get",
          url: this.$appSettings.APIServer.admin.get_general_settings,
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
            
            // Update auth settings
            _this.settings.auth = {
              loginType: data.auth?.loginType || 'password',
              sessionTimeoutMinutes: data.auth?.sessionTimeoutMinutes || 1440,
              ldap: {
                url: data.auth?.ldap?.url || '',
                usernameFormat: data.auth?.ldap?.usernameFormat || '',
                passwordFormat: data.auth?.ldap?.passwordFormat || '',
                domain: data.auth?.ldap?.domain || '',
                searchMethod: data.auth?.ldap?.searchMethod || '',
                accountField: data.auth?.ldap?.accountField || '',
                emailField: data.auth?.ldap?.emailField || '',
                nameField: data.auth?.ldap?.nameField || ''
              }
            };
            
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
            
            // Update email enable setting
            _this.settings.emailEnable = {
              sendEmail: data.emailEnable?.sendEmail || false
            };

            // Update analytics settings
            _this.settings.analytics = {
              rybbitUrl: data.analytics?.rybbitUrl || '',
              rybbitSiteId: data.analytics?.rybbitSiteId || '',
              googleAnalyticsId: data.analytics?.googleAnalyticsId || ''
            };

            // Update legal settings
            _this.settings.legal = {
              enabled: data.legal?.enabled || false,
              organizationName: data.legal?.organizationName || '',
              contactEmail: data.legal?.contactEmail || '',
              privacyPolicyContent: data.legal?.privacyPolicyContent || '',
              termsOfServiceContent: data.legal?.termsOfServiceContent || '',
              lastUpdated: data.legal?.lastUpdated || ''
            };

            // Update connection settings
            if (data.connection?.sshMethods && Array.isArray(data.connection.sshMethods) && data.connection.sshMethods.length > 0) {
              _this.settings.connection.sshMethods = data.connection.sshMethods;
            }

            // Update email template settings
            _this.settings.emailTemplates = {
              enableContainerStarted: data.emailTemplates?.enableContainerStarted !== false,
              enableContainerError: data.emailTemplates?.enableContainerError !== false,
              enableContainerPaused: data.emailTemplates?.enableContainerPaused !== false,
              enableContainerResumed: data.emailTemplates?.enableContainerResumed !== false,
              enableContainerResumeFailed: data.emailTemplates?.enableContainerResumeFailed !== false,
              subjectContainerStarted: data.emailTemplates?.subjectContainerStarted || '',
              subjectContainerError: data.emailTemplates?.subjectContainerError || '',
              subjectContainerPaused: data.emailTemplates?.subjectContainerPaused || '',
              subjectContainerResumed: data.emailTemplates?.subjectContainerResumed || '',
              subjectContainerResumeFailed: data.emailTemplates?.subjectContainerResumeFailed || '',
              bodyIntroContainerStarted: data.emailTemplates?.bodyIntroContainerStarted || '',
              bodyIntroContainerError: data.emailTemplates?.bodyIntroContainerError || '',
              bodyIntroContainerPaused: data.emailTemplates?.bodyIntroContainerPaused || '',
              bodyIntroContainerResumed: data.emailTemplates?.bodyIntroContainerResumed || '',
              bodyIntroContainerResumeFailed: data.emailTemplates?.bodyIntroContainerResumeFailed || '',
              lowPriorityNotice: data.emailTemplates?.lowPriorityNotice || ''
            };

            // Mark settings as initialized after a small delay to ensure watchers don't fire during load
            setTimeout(() => {
              _this.settingsInitialized.blacklistEnabled = true;
              _this.settingsInitialized.whitelistEnabled = true;
              _this.settingsInitialized.containerAlertsEnabled = true;
              _this.settingsInitialized.sendEmail = true;
              _this.settingsInitialized.loginType = true;
              _this.settingsInitialized.legalEnabled = true;
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
            _this.store.showMessage({ 
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
            _this.store.showMessage({ text: error.response.data.detail, color: "red" });
          } else {
            _this.store.showMessage({ 
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
        this.store.showMessage({ 
          text: 'Failed to load settings', 
          color: 'red' 
        });
        // Mark initial load as complete even on error to enable auto-save watchers
        this.isLoading = false;
        this.initialLoadComplete = true;
      }
    },
    
    /**
     * Validates and saves a single settings section to the backend.
     * Reloads app config after saving sections that affect public settings (general, contact).
     * @param {string} sectionName - One of: general, access, email, emailEnable, contact, notifications, auth
     */
    async saveSection(sectionName) {
      try {
        // Validate the form first
        const formRef = `${sectionName}Form`;
        if (this.$refs[formRef] && !this.$refs[formRef].validate()) {
          this.store.showMessage({ 
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
        let currentUser = this.store.user;

        axios({
          method: "post",
          url: this.$appSettings.APIServer.admin.save_general_settings,
          data: {
            section: sectionName,
            settings: settingsData
          },
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(async function (response) {
          if (response.data.status == true) {
            // Show success notification
            _this.store.showMessage({ 
              text: `${_this.getSectionDisplayName(sectionName)} settings saved successfully!`, 
              color: 'green' 
            });
            
            // Reload app config for sections that affect public settings
            if (sectionName === 'general' || sectionName === 'contact' || sectionName === 'legal' || sectionName === 'analytics') {
              try {
                await _this.store.loadAppConfig();
                //console.log('App configuration reloaded after saving', sectionName, 'settings');
              } catch (error) {
                console.error('Failed to reload app config:', error);
                // Don't show error to user as the save was successful
              }
            }
            
          } else {
            console.log(`Failed to save ${sectionName} settings...`);
            _this.store.showMessage({ 
              text: response.data.message || `There was an error saving ${_this.getSectionDisplayName(sectionName)} settings.`, 
              color: "red" 
            });
          }
          _this.saving[sectionName] = false;
        })
        .catch(function (error) {
          console.error(`Failed to save ${sectionName} settings:`, error);
          if (error.response && (error.response.status == 400 || error.response.status == 401)) {
            _this.store.showMessage({ text: error.response.data.detail, color: "red" });
          } else {
            _this.store.showMessage({ 
              text: `Failed to save ${_this.getSectionDisplayName(sectionName)} settings`, 
              color: 'red' 
            });
          }
          _this.saving[sectionName] = false;
        });
        
      } catch (error) {
        console.error(`Failed to save ${sectionName} settings:`, error);
        this.store.showMessage({ 
          text: `Failed to save ${this.getSectionDisplayName(sectionName)} settings`, 
          color: 'red' 
        });
        this.saving[sectionName] = false;
      }
    },
    
    async sendTestEmail() {
      if (!this.isValidEmail(this.testEmail)) {
        this.store.showMessage({ 
          text: 'Please enter a valid email address', 
          color: 'red' 
        });
        return;
      }
      
      try {
        this.sendingTest = true;
        
        console.log(`Sending test email to: ${this.testEmail}`);
        
        let _this = this;
        let currentUser = this.store.user;

        axios({
          method: "post",
          url: this.$appSettings.APIServer.admin.test_email,
          data: {
            email: this.testEmail
          },
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
          if (response.data.status == true) {
            _this.store.showMessage({ 
              text: `Test email sent successfully to ${_this.testEmail}`, 
              color: 'green' 
            });
          } else {
            console.log("Failed to send test email...");
            _this.store.showMessage({ 
              text: response.data.message || 'Failed to send test email', 
              color: "red" 
            });
          }
          _this.sendingTest = false;
        })
        .catch(function (error) {
          console.error('Failed to send test email:', error);
          if (error.response && (error.response.status == 400 || error.response.status == 401)) {
            _this.store.showMessage({ text: error.response.data.detail, color: "red" });
          } else {
            _this.store.showMessage({ 
              text: 'Failed to send test email', 
              color: 'red' 
            });
          }
          _this.sendingTest = false;
        });
        
      } catch (error) {
        console.error('Failed to send test email:', error);
        this.store.showMessage({ 
          text: 'Failed to send test email', 
          color: 'red' 
        });
        this.sendingTest = false;
      }
    },

    async testAdConnection() {
      if (!this.testAdUsername || !this.testAdPassword) {
        this.store.showMessage({
          text: 'Please enter both username and password',
          color: 'red'
        });
        return;
      }

      try {
        this.testingAd = true;
        this.testAdResult = '';

        let _this = this;
        let currentUser = this.store.user;

        axios({
          method: "post",
          url: this.$appSettings.APIServer.admin.test_ad,
          data: {
            username: this.testAdUsername,
            password: this.testAdPassword
          },
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
          if (response.data.status == true) {
            _this.store.showMessage({
              text: 'LDAP connection test successful',
              color: 'green'
            });
            _this.testAdResult = JSON.stringify(response.data.data, null, 2);
          } else {
            _this.store.showMessage({
              text: response.data.message || 'LDAP connection test failed',
              color: "red"
            });
            _this.testAdResult = 'Error: ' + (response.data.message || 'LDAP connection test failed');
          }
          _this.testingAd = false;
        })
        .catch(function (error) {
          console.error('Failed to test AD connection:', error);
          let errorMessage = 'Failed to test AD connection';
          if (error.response && error.response.data) {
            errorMessage = error.response.data.detail || error.response.data.message || errorMessage;
          } else if (error.message) {
            errorMessage = error.message;
          }
          _this.store.showMessage({ text: errorMessage, color: "red" });
          _this.testAdResult = 'Error: ' + errorMessage;
          _this.testingAd = false;
        });

      } catch (error) {
        console.error('Failed to test AD connection:', error);
        this.store.showMessage({
          text: 'Failed to test AD connection',
          color: 'red'
        });
        this.testAdResult = 'Error: ' + error.message;
        this.testingAd = false;
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
        emailEnable: 'Email System',
        contact: 'Contact Information',
        notifications: 'System Notifications',
        auth: 'Authentication',
        analytics: 'Analytics',
        legal: 'Legal Documents',
        connection: 'Connection Methods',
        emailTemplates: 'Email Templates'
      };
      return names[sectionName] || sectionName;
    },

    /**
     * Show confirmation dialog before loading a template, or load directly if the field is empty.
     * @param {string} type - Either 'privacyPolicy' or 'termsOfService'.
     */
    confirmLoadTemplate(type) {
      const hasContent = type === 'privacyPolicy'
        ? this.settings.legal.privacyPolicyContent
        : this.settings.legal.termsOfServiceContent

      if (hasContent) {
        this.legalTemplateDialog.type = type
        this.legalTemplateDialog.visible = true
      } else {
        this.loadTemplate(type)
      }
    },

    /**
     * Load a default template into the privacy policy or terms of service textarea.
     * Replaces {{ORGANIZATION_NAME}} and {{CONTACT_EMAIL}} placeholders with
     * values from the organization info fields.
     * @param {string} type - Either 'privacyPolicy' or 'termsOfService'.
     */
    loadTemplate(type) {
      if (type === 'privacyPolicy') {
        this.settings.legal.privacyPolicyContent = privacyPolicyTemplate
      } else if (type === 'termsOfService') {
        this.settings.legal.termsOfServiceContent = termsOfServiceTemplate
      }
      this.legalTemplateDialog.visible = false
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

  computed: {
    /** @returns {string} Rendered HTML of the privacy policy Markdown content with placeholders filled. */
    renderedPrivacyPolicy() {
      if (!this.settings.legal.privacyPolicyContent) return ''
      const filled = fillTemplate(this.settings.legal.privacyPolicyContent, this.settings.legal.organizationName, this.settings.legal.contactEmail, this.settings.legal.lastUpdated)
      return DOMPurify.sanitize(marked.parse(filled))
    },
    /** @returns {string} Rendered HTML of the terms of service Markdown content with placeholders filled. */
    renderedTermsOfService() {
      if (!this.settings.legal.termsOfServiceContent) return ''
      const filled = fillTemplate(this.settings.legal.termsOfServiceContent, this.settings.legal.organizationName, this.settings.legal.contactEmail, this.settings.legal.lastUpdated)
      return DOMPurify.sanitize(marked.parse(filled))
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
    },

    // Auto-save when email enable checkbox is toggled
    'settings.emailEnable.sendEmail': function(newValue, oldValue) {
      if (this.settingsInitialized.sendEmail && !this.isLoading && oldValue !== undefined && newValue !== oldValue) {
        this.saveSection('emailEnable');
      }
    },

    // Auto-save when login type is changed
    'settings.auth.loginType': function(newValue, oldValue) {
      if (this.settingsInitialized.loginType && !this.isLoading && oldValue !== undefined && newValue !== oldValue) {
        this.saveSection('auth');
      }
    },

    // Auto-save when legal enabled toggle is changed
    'settings.legal.enabled': function(newValue, oldValue) {
      if (this.settingsInitialized.legalEnabled && !this.isLoading && oldValue !== undefined && newValue !== oldValue) {
        this.saveSection('legal');
      }
    },

    // Smooth-scroll the newly opened panel into position right under the
    // 48px sticky top nav. The 300ms delay lets Vuetify's expand/collapse
    // transitions finish so we measure the panel's final resting position
    // (otherwise closing the previously open panel would shift the target).
    openPanel(newValue) {
      if (!newValue) return;
      setTimeout(() => {
        const el = document.getElementById(`panel-${newValue}`);
        if (!el) return;
        const STICKY_NAV_OFFSET = 48 + 16;
        const top = el.getBoundingClientRect().top + window.scrollY - STICKY_NAV_OFFSET;
        window.scrollTo({ top, behavior: 'smooth' });
      }, 300);
    }
  }
}
</script>

<style scoped lang="scss">
// Group headers that label clusters of related expansion panels
.settings-group-header {
  font-size: 14px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: rgba(255, 255, 255, 0.65);
  text-align: left;
  margin: 32px 4px 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);

  &--first {
    margin-top: 8px;
  }
}

// Override Vuetify's expansion panel header styles
:deep(.v-expansion-panel-title) {
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
:deep(.v-expansion-panel-title > div:first-child) {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  flex-grow: 0 !important;
}

:deep(.v-expansion-panel-title .v-icon:first-child) {
  margin-right: 8px !important;
  margin-left: 0 !important;
  flex-shrink: 0 !important;
}

:deep(.v-expansion-panel-title .font-weight-bold) {
  margin: 0 !important;
  white-space: nowrap !important;
}

:deep(.v-expansion-panel-text__wrapper) {
  padding-left: 50px !important;
}

// Keep the expand/collapse icon on the right
:deep(.v-expansion-panel-title__icon) {
  margin-left: auto !important;
  flex-shrink: 0 !important;
}

.font-weight-bold {
  font-weight: 700 !important;
  font-size: 18px !important;
}

.v-subheader {
  font-size: 18px;
  font-weight: 500;
}

.v-expansion-panel-text {
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

.v-expansion-panel-title>:not(.v-expansion-panel-title__icon) {
    flex: 0;
}

// Email chip container styling
.v-chip {
  margin: 2px !important;
}

// Legal document Markdown preview
.legal-preview {
  border: 1px solid rgba(255, 255, 255, 0.15);
  max-height: 500px;
  overflow-y: auto;
  text-align: left;
  line-height: 1.7;

  :deep(h1) { font-size: 1.5rem; margin-top: 1.5rem; margin-bottom: 0.75rem; }
  :deep(h2) { font-size: 1.25rem; margin-top: 1.25rem; margin-bottom: 0.5rem; }
  :deep(h3) { font-size: 1.1rem; margin-top: 1rem; margin-bottom: 0.5rem; }
  :deep(p) { margin-bottom: 0.75rem; }
  :deep(ul), :deep(ol) { margin-bottom: 0.75rem; padding-left: 1.5rem; }
  :deep(li) { margin-bottom: 0.25rem; }
  :deep(table) { border-collapse: collapse; margin-bottom: 1rem; width: 100%; }
  :deep(th), :deep(td) { border: 1px solid rgba(255, 255, 255, 0.15); padding: 8px 12px; text-align: left; }
  :deep(th) { font-weight: 600; }
}
</style>