<template>
  <div class="text-center">
    <v-dialog v-model="isOpen" width="600">
      <v-card class="pa-4">
        <v-card-title class="text-h5 lighten-2 pt-6">
          Connection Details
        </v-card-title>

        <v-card-text v-if="!isLoading && details">

          <!-- Primary non-SSH port (when a non-SSH port is set as primary) -->
          <div v-if="primaryPort">
            <v-card variant="tonal" color="surface-variant" class="pa-4 mb-5 mt-2">
              <div class="text-body-2 text-medium-emphasis mb-3">
                {{ primaryPortTypeConfig.helpText || 'Connect to:' }}
              </div>
              <div class="d-flex align-center justify-space-between connection-string-box pa-3 rounded">
                <a v-if="primaryPortTypeConfig.clickable" :href="primaryPortUrl" target="_blank" rel="noopener noreferrer" class="primary-port-link">
                  <code class="text-body-1">{{ primaryPortUrl }}</code>
                </a>
                <code v-else class="text-body-1">{{ primaryPortUrl }}</code>
                <v-icon size="small" class="copy-icon ml-3" @click="copyToClipboard(primaryPortUrl, primaryPort.serviceName)">mdi-content-copy</v-icon>
              </div>
              <div class="mt-2" style="font-style: italic; opacity: 0.5; font-size: 13px;">
                {{ primaryPort.serviceName }} — {{ primaryPortTypeConfig.name || 'TCP' }}, local port {{ primaryPort.localPort }}
              </div>
            </v-card>
          </div>

          <!-- SSH Connection (shown prominently when SSH is primary, or in collapsible when not) -->
          <div v-if="details.sshPort && isSSHPrimary">

            <!-- Connection method toggle -->
            <div class="text-body-2 text-medium-emphasis mb-2 mt-2">How do you want to connect?</div>
            <div class="d-flex mb-4 flex-wrap" style="gap: 8px;">
              <v-btn
                v-for="(method, i) in sshMethods"
                :key="method.id"
                :variant="selectedMethodIndex === i ? 'flat' : 'outlined'"
                :color="selectedMethodIndex === i ? 'primary' : undefined"
                density="compact"
                class="flex-grow-1"
                @click="selectedMethodIndex = i"
              >
                <v-icon start size="small">{{ method.icon }}</v-icon>
                {{ method.name }}
              </v-btn>
            </div>

            <!-- Connection string card -->
            <v-card variant="tonal" color="surface-variant" class="pa-4 mb-5">
              <div class="text-body-2 text-medium-emphasis mb-3">
                {{ activeMethod.helpText }}
              </div>
              <div class="d-flex align-center justify-space-between connection-string-box pa-3 rounded">
                <code class="text-body-1">{{ renderedConnectionString }}</code>
                <v-icon
                  size="small"
                  class="copy-icon ml-3"
                  @click="copyToClipboard(renderedConnectionString, activeMethod.name + ' connection string')"
                >mdi-content-copy</v-icon>
              </div>

              <v-divider class="my-4"></v-divider>

              <!-- Password -->
              <div class="text-body-2 text-medium-emphasis mb-3">
                <v-icon size="small" class="mr-1">mdi-key-variant</v-icon>
                When prompted, enter this password
              </div>
              <div class="d-flex align-center justify-space-between connection-string-box pa-3 rounded">
                <code class="text-body-1">{{ details.sshPassword }}</code>
                <v-icon size="small" class="copy-icon ml-3" @click="copyToClipboard(details.sshPassword, 'SSH password')">mdi-content-copy</v-icon>
              </div>

              <v-alert v-if="details.hasSshPublicKey" type="info" variant="tonal" density="compact" class="mt-4">
                Your SSH public key has been deployed to this container. You can also connect without a password.
              </v-alert>
              <p v-else class="text-medium-emphasis" style="margin-top: 12px; font-size: 13px;">
                <v-icon size="x-small" class="mr-1">mdi-information-outline</v-icon>
                <v-tooltip location="bottom" max-width="300">
                  <template v-slot:activator="{ props }">
                    <span v-bind="props" class="text-caption link-hint">Enable passwordless SSH login?</span>
                  </template>
                  <span>You can add public SSH key in your user profile to connect to containers without entering a password. The key will be automatically deployed to all future reservations.</span>
                </v-tooltip>
              </p>
            </v-card>
          </div>

          <!-- Collapsible sections -->
          <v-expansion-panels variant="accordion" class="mt-4">

            <!-- SSH (when not primary but exists) -->
            <v-expansion-panel v-if="details.sshPort && !isSSHPrimary">
              <v-expansion-panel-title>
                <div class="d-flex align-center">
                  <v-icon class="mr-2" size="small">mdi-console</v-icon>
                  <span class="text-subtitle-1 font-weight-medium">SSH Connection</span>
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div class="d-flex mb-4 flex-wrap" style="gap: 8px;">
                  <v-btn
                    v-for="(method, i) in sshMethods"
                    :key="method.id"
                    :variant="selectedMethodIndex === i ? 'flat' : 'outlined'"
                    :color="selectedMethodIndex === i ? 'primary' : undefined"
                    density="compact"
                    class="flex-grow-1"
                    @click="selectedMethodIndex = i"
                  >
                    <v-icon start size="small">{{ method.icon }}</v-icon>
                    {{ method.name }}
                  </v-btn>
                </div>
                <div class="text-body-2 text-medium-emphasis mb-2">{{ activeMethod.helpText }}</div>
                <div class="d-flex align-center justify-space-between connection-string-box pa-3 rounded mb-3">
                  <code class="text-body-1">{{ renderedConnectionString }}</code>
                  <v-icon size="small" class="copy-icon ml-3" @click="copyToClipboard(renderedConnectionString, activeMethod.name)">mdi-content-copy</v-icon>
                </div>
                <div class="text-body-2 text-medium-emphasis mb-2">
                  <v-icon size="small" class="mr-1">mdi-key-variant</v-icon> Password
                </div>
                <div class="d-flex align-center justify-space-between connection-string-box pa-3 rounded">
                  <code class="text-body-1">{{ details.sshPassword }}</code>
                  <v-icon size="small" class="copy-icon ml-3" @click="copyToClipboard(details.sshPassword, 'SSH password')">mdi-content-copy</v-icon>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Other Services -->
            <v-expansion-panel v-if="hasOtherPorts">
              <v-expansion-panel-title>
                <div class="d-flex align-center">
                  <v-icon class="mr-2" size="small">mdi-lan</v-icon>
                  <span class="text-subtitle-1 font-weight-medium">Other Services</span>
                  <v-chip size="x-small" color="primary" class="ml-2">{{ nonPrimaryOtherPorts.length }}</v-chip>
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div v-for="port in nonPrimaryOtherPorts" :key="port.serviceName" class="mb-3">
                  <v-text-field
                    :model-value="renderPortUrl(port)"
                    :label="`${port.serviceName} (local port ${port.localPort})`"
                    :prepend-inner-icon="getPortTypeConfig(port).icon || 'mdi-lan'"
                    readonly
                    variant="outlined"
                    density="compact"
                  >
                    <template v-slot:append-inner>
                      <v-icon size="small" class="copy-icon" @click="copyToClipboard(renderPortUrl(port), port.serviceName)">mdi-content-copy</v-icon>
                    </template>
                  </v-text-field>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Container Details -->
            <v-expansion-panel v-if="details.containerName">
              <v-expansion-panel-title>
                <div class="d-flex align-center">
                  <v-icon class="mr-2" size="small">mdi-cube-outline</v-icon>
                  <span class="text-subtitle-1 font-weight-medium">Container Details</span>
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-text-field
                  :model-value="details.containerName"
                  label="Name"
                  prepend-inner-icon="mdi-label-outline"
                  readonly
                  variant="outlined"
                  density="compact"
                  class="mb-2 mt-2"
                ></v-text-field>

                <v-text-field
                  :model-value="details.containerImage"
                  label="Image"
                  prepend-inner-icon="mdi-docker"
                  readonly
                  variant="outlined"
                  density="compact"
                  class="mb-2"
                ></v-text-field>

                <v-textarea
                  v-if="details.containerDescription"
                  :model-value="details.containerDescription"
                  label="Description"
                  prepend-inner-icon="mdi-text"
                  readonly
                  variant="outlined"
                  density="compact"
                  rows="2"
                  auto-grow
                  class="mb-2"
                ></v-textarea>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Server Information -->
            <v-expansion-panel>
              <v-expansion-panel-title>
                <div class="d-flex align-center">
                  <v-icon class="mr-2" size="small">mdi-server</v-icon>
                  <span class="text-subtitle-1 font-weight-medium">Server Information</span>
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-text-field
                  :model-value="details.ip"
                  label="Server Address"
                  prepend-inner-icon="mdi-server"
                  readonly
                  variant="outlined"
                  density="compact"
                  class="mb-2 mt-2"
                >
                  <template v-slot:append-inner>
                    <v-icon size="small" class="copy-icon" @click="copyToClipboard(details.ip, 'IP address')">mdi-content-copy</v-icon>
                  </template>
                </v-text-field>

                <v-text-field
                  v-if="formattedEndDate"
                  :model-value="formattedEndDate"
                  label="Reservation Ends"
                  prepend-inner-icon="mdi-clock-outline"
                  readonly
                  variant="outlined"
                  density="compact"
                  class="mb-2"
                ></v-text-field>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- General Instructions -->
            <v-expansion-panel v-if="hasInstructions">
              <v-expansion-panel-title>
                <div class="d-flex align-center">
                  <v-icon class="mr-2" size="small">mdi-information-outline</v-icon>
                  <span class="text-subtitle-1 font-weight-medium">Instructions</span>
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-textarea
                  :model-value="details.instructions"
                  readonly
                  variant="outlined"
                  density="compact"
                  rows="3"
                  auto-grow
                  class="mt-2"
                ></v-textarea>
              </v-expansion-panel-text>
            </v-expansion-panel>

          </v-expansion-panels>

        </v-card-text>

        <!-- Fallback for legacy response without structured data -->
        <v-card-text v-else-if="!isLoading && !details">
          <div v-html="connectionText"></div>
        </v-card-text>

        <Loading style="margin: 60px 0px;" v-if="isLoading"></Loading>

        <v-divider></v-divider>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" variant="text" @click="isOpen = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
  /**
   * Modal dialog showing connection details for a running reservation.
   * Fetches SSH credentials, port mappings, container info, and server IP on mount,
   * then presents them with dynamic SSH method toggle and type-aware port rendering.
   */
  import Loading from '/src/components/global/Loading.vue';
  import axios from 'axios';
  import { useMainStore } from '@/store/store'
  import { DisplayTime } from '/src/helpers/time.js'

  const FALLBACK_SSH_METHODS = [
    { id: "vscode", name: "VS Code", icon: "mdi-microsoft-visual-studio-code",
      template: "{username}@{ip}:{port}", helpText: "Open the Remote SSH extension and connect to" },
    { id: "terminal", name: "Terminal", icon: "mdi-console",
      template: "ssh {username}@{ip} -p {port}", helpText: "Run this command in your terminal" }
  ]

  /** Port type rendering config for non-SSH ports. */
  const PORT_TYPE_CONFIGS = {
    HTTP:  { name: "HTTP", icon: "mdi-web", helpText: "Open in your browser", urlTemplate: "http://{ip}:{port}", clickable: true },
    HTTPS: { name: "HTTPS", icon: "mdi-lock", helpText: "Open in your browser", urlTemplate: "https://{ip}:{port}", clickable: true },
    VNC:   { name: "VNC", icon: "mdi-monitor", helpText: "Connect with a VNC viewer", urlTemplate: "vnc://{ip}:{port}", clickable: false },
  }
  const DEFAULT_PORT_CONFIG = { name: "TCP", icon: "mdi-lan", helpText: "Connect to", urlTemplate: "{ip}:{port}", clickable: false }

  export default {
    components: {
      Loading
    },
    name: 'UserReservationsModalConnectionDetails',
    setup() {
      const store = useMainStore()
      return { store }
    },
    props: {
      reservationId: {
        type: Number,
        required: false
      }
    },
    data: () => ({
      isOpen: true,
      details: null,
      connectionText: "",
      isLoading: true,
      selectedMethodIndex: 0,
    }),
    computed: {
      containerUsername() {
        return (this.details && this.details.username) || 'user'
      },
      /** SSH methods from backend or fallback. */
      sshMethods() {
        if (this.details?.sshMethods && this.details.sshMethods.length > 0) {
          return this.details.sshMethods
        }
        return FALLBACK_SSH_METHODS
      },
      /** Currently selected SSH method. */
      activeMethod() {
        return this.sshMethods[this.selectedMethodIndex] || this.sshMethods[0]
      },
      /** Rendered connection string with variables replaced. */
      renderedConnectionString() {
        if (!this.activeMethod || !this.details?.sshPort) return ''
        return this.activeMethod.template
          .replace('{username}', this.containerUsername)
          .replace('{ip}', this.details.ip)
          .replace('{port}', this.details.sshPort)
      },
      /** The non-SSH port set as primary, or null if SSH is primary. */
      primaryPort() {
        if (!this.details?.primaryConnectionPortId) return null
        return this.details.otherPorts?.find(
          p => p.containerPortId === this.details.primaryConnectionPortId
        ) || null
      },
      /** Whether SSH is the primary connection method. */
      isSSHPrimary() {
        return !this.primaryPort
      },
      /** Port type config for the primary non-SSH port. */
      primaryPortTypeConfig() {
        if (!this.primaryPort) return DEFAULT_PORT_CONFIG
        return this.getPortTypeConfig(this.primaryPort)
      },
      /** Rendered URL for the primary non-SSH port. */
      primaryPortUrl() {
        if (!this.primaryPort) return ''
        return this.renderPortUrl(this.primaryPort)
      },
      /** Other ports excluding the primary (for the collapsible section). */
      nonPrimaryOtherPorts() {
        if (!this.details?.otherPorts) return []
        if (!this.primaryPort) return this.details.otherPorts
        return this.details.otherPorts.filter(
          p => p.containerPortId !== this.details.primaryConnectionPortId
        )
      },
      hasOtherPorts() {
        return this.nonPrimaryOtherPorts.length > 0
      },
      formattedEndDate() {
        if (!this.details || !this.details.endDate) return null
        return DisplayTime(this.details.endDate)
      },
      hasInstructions() {
        return this.details && this.details.instructions && this.details.instructions.trim().length > 0
      }
    },
    methods: {
      copyToClipboard(text, label) {
        navigator.clipboard.writeText(text).then(() => {
          this.store.showMessage({ text: `${label} copied to clipboard`, color: "green" })
        }).catch(() => {
          this.store.showMessage({ text: "Failed to copy to clipboard", color: "red" })
        })
      },
      /** Get port type rendering config for a non-SSH port. */
      getPortTypeConfig(port) {
        return PORT_TYPE_CONFIGS[port.portType] || DEFAULT_PORT_CONFIG
      },
      /** Render the connection URL for a non-SSH port. */
      renderPortUrl(port) {
        const config = this.getPortTypeConfig(port)
        return config.urlTemplate
          .replace('{ip}', this.details.ip)
          .replace('{port}', port.outsidePort)
      }
    },
    mounted () {
      let currentUser = this.store.user

      axios({
          method: "get",
          url: this.$appSettings.APIServer.reservation.get_own_reservation_details,
          params: { "reservationId": this.reservationId },
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then((response) => {
          this.details = response.data.data.connectionDetails || null
          this.connectionText = response.data.data.connectionText || ""
          this.isLoading = false
        })
        .catch((error) => {
          console.log(error)
          this.isLoading = false
        });
    },
    watch: {
      isOpen: function(newVal) {
        if (newVal === false) {
          this.$emit("emitModalClose");
        }
      },
    }
  }
</script>

<style scoped lang="scss">
  .copy-icon {
    cursor: pointer;
    opacity: 0.6;
    &:hover {
      opacity: 1;
    }
  }
  .connection-string-box {
    background: rgba(var(--v-theme-on-surface), 0.05);
    border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
    font-family: monospace;
  }
  // Wraps the <code> primary-port URL inside .connection-string-box.
  // Uses inherit color so the link blends with the surrounding code styling
  // instead of taking on the global blue link color.
  .primary-port-link {
    color: inherit;
    text-decoration: none;
    &:hover {
      color: inherit;
      text-decoration: underline;
    }
  }
</style>
