<template>
  <div class="text-center">
    <v-dialog v-model="isOpen" width="600">
      <v-card>
        <v-card-title class="text-h5 lighten-2 pt-6">
          Connection Details
        </v-card-title>

        <v-card-text v-if="!isLoading && details">

          <!-- SSH Connection -->
          <div v-if="details.sshPort">
            <div class="d-flex align-center mb-5 mt-2">
              <v-icon class="mr-2" size="small">mdi-console</v-icon>
              <span class="text-subtitle-1 font-weight-medium">SSH Connection</span>
            </div>

            <v-text-field
              :model-value="vscodeConnectionString"
              label="VS Code (Remote SSH)"
              prepend-inner-icon="mdi-microsoft-visual-studio-code"
              readonly
              variant="outlined"
              density="compact"
              class="mb-2"
            >
              <template v-slot:append-inner>
                <v-icon size="small" class="copy-icon" @click="copyToClipboard(vscodeConnectionString, 'VS Code connection string')">mdi-content-copy</v-icon>
              </template>
            </v-text-field>

            <v-text-field
              :model-value="sshCommand"
              label="Terminal Command"
              prepend-inner-icon="mdi-console"
              readonly
              variant="outlined"
              density="compact"
              class="mb-2"
            >
              <template v-slot:append-inner>
                <v-icon size="small" class="copy-icon" @click="copyToClipboard(sshCommand, 'SSH command')">mdi-content-copy</v-icon>
              </template>
            </v-text-field>

            <v-text-field
              :model-value="details.sshPassword"
              label="SSH Password"
              prepend-inner-icon="mdi-key-variant"
              readonly
              variant="outlined"
              density="compact"
              class="mb-2"
            >
              <template v-slot:append-inner>
                <v-icon size="small" class="copy-icon" @click="copyToClipboard(details.sshPassword, 'SSH password')">mdi-content-copy</v-icon>
              </template>
            </v-text-field>
          </div>

          <!-- Other Services -->
          <div v-if="hasOtherPorts">
            <div class="d-flex align-center mb-5">
              <v-icon class="mr-2" size="small">mdi-lan</v-icon>
              <span class="text-subtitle-1 font-weight-medium">Other Services</span>
            </div>

            <v-text-field
              v-for="port in details.otherPorts"
              :key="port.serviceName"
              :model-value="`${details.ip}:${port.outsidePort}`"
              :label="`${port.serviceName} (local port ${port.localPort})`"
              prepend-inner-icon="mdi-open-in-new"
              readonly
              variant="outlined"
              density="compact"
              class="mb-2"
            >
              <template v-slot:append-inner>
                <v-icon size="small" class="copy-icon" @click="copyToClipboard(`${details.ip}:${port.outsidePort}`, port.serviceName)">mdi-content-copy</v-icon>
              </template>
            </v-text-field>
          </div>

          <!-- Collapsible sections -->
          <v-expansion-panels variant="accordion" class="mt-4">

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
                  label="IP Address"
                  prepend-inner-icon="mdi-ip-network"
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
   * then presents them in copyable text fields with collapsible sections for
   * container details, server information, and instructions.
   */
  import Loading from '/src/components/global/Loading.vue';
  import axios from 'axios';
  import { useMainStore } from '@/store/store'
  import { DisplayTime } from '/src/helpers/time.js'

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
    }),
    computed: {
      containerUsername() {
        return (this.details && this.details.username) || 'user'
      },
      vscodeConnectionString() {
        if (!this.details || !this.details.sshPort) return null
        return `${this.containerUsername}@${this.details.ip}:${this.details.sshPort}`
      },
      sshCommand() {
        if (!this.details || !this.details.sshPort) return null
        return `ssh ${this.containerUsername}@${this.details.ip} -p ${this.details.sshPort}`
      },
      formattedEndDate() {
        if (!this.details || !this.details.endDate) return null
        return DisplayTime(this.details.endDate)
      },
      hasOtherPorts() {
        return this.details && this.details.otherPorts && this.details.otherPorts.length > 0
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
</style>
