<template>
  <v-dialog v-model="dialogOpen" persistent max-width="900px">
    <v-card>
      <v-card-title class="d-flex align-center">
        <span>Image Build Log</span>
        <v-spacer></v-spacer>
        <v-chip
          v-if="buildStatus === 'building' || buildStatus === 'pending'"
          color="orange"
          text-color="white"
          size="small"
          class="ml-2"
        >
          <v-progress-circular indeterminate size="14" width="2" class="mr-2"></v-progress-circular>
          {{ buildStatus === 'pending' ? 'Queued...' : 'Building...' }}
        </v-chip>
        <v-chip
          v-else-if="buildStatus === 'success'"
          color="green"
          text-color="white"
          size="small"
          class="ml-2"
        >
          Build Successful
        </v-chip>
        <v-chip
          v-else-if="buildStatus === 'failed'"
          color="red"
          text-color="white"
          size="small"
          class="ml-2"
        >
          Build Failed
        </v-chip>
      </v-card-title>

      <v-card-text>
        <div class="build-log-container" ref="logContainer">
          <pre class="build-log">{{ buildLog || 'Waiting for build to start...' }}</pre>
        </div>
      </v-card-text>

      <v-card-actions>
        <v-btn variant="text" @click="editContainer">
          <v-icon size="small" class="mr-1">mdi-pencil-outline</v-icon>
          Edit Container
        </v-btn>
        <v-spacer></v-spacer>
        <v-btn color="primary" variant="text" @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
  /**
   * Dialog that displays Docker image build progress and logs.
   * Polls the backend for build status updates while a build is in progress.
   * Auto-scrolls the log output to show the latest lines.
   *
   * Props:
   *   containerId - Database ID of the container being built.
   *   isOpen - Whether the dialog should be visible.
   *
   * Emits:
   *   emitClose - When the dialog is closed by the user.
   *   emitEditContainer - When the user wants to edit the container.
   */
  import axios from 'axios';
  import { useMainStore } from '@/store/store'

  export default {
    name: "AdminBuildLogDialog",
    setup() {
      const store = useMainStore()
      return { store }
    },
    props: {
      containerId: {
        type: Number,
        required: true,
      },
      isOpen: {
        type: Boolean,
        default: false,
      },
    },
    data() {
      return {
        dialogOpen: this.isOpen,
        buildStatus: null,
        buildLog: '',
        pollInterval: null,
      }
    },
    created() {
      this.fetchBuildStatus();
      this.startPolling();
    },
    beforeUnmount() {
      this.stopPolling();
    },
    methods: {
      fetchBuildStatus() {
        let currentUser = this.store.user;
        let _this = this;

        axios({
          method: "get",
          url: this.$appSettings.APIServer.admin.container_build_status,
          params: { containerId: this.containerId },
          headers: { "Authorization": `Bearer ${currentUser.loginToken}` }
        })
        .then(function (response) {
          if (response.data.status == true) {
            _this.buildStatus = response.data.data.buildStatus;
            _this.buildLog = response.data.data.buildLog;
            _this.scrollToBottom();

            // Stop polling when build is done
            if (_this.buildStatus === 'success' || _this.buildStatus === 'failed') {
              _this.stopPolling();
            }
          }
        })
        .catch(function (error) {
          console.log("Error fetching build status:", error);
        });
      },
      startPolling() {
        this.pollInterval = setInterval(() => {
          this.fetchBuildStatus();
        }, 5000);
      },
      stopPolling() {
        if (this.pollInterval) {
          clearInterval(this.pollInterval);
          this.pollInterval = null;
        }
      },
      scrollToBottom() {
        this.$nextTick(() => {
          let container = this.$refs.logContainer;
          if (container) {
            container.scrollTop = container.scrollHeight;
          }
        });
      },
      close() {
        this.stopPolling();
        this.dialogOpen = false;
        this.$emit('emitClose');
      },
      editContainer() {
        this.stopPolling();
        this.dialogOpen = false;
        this.$emit('emitEditContainer', this.containerId);
      },
    },
    watch: {
      isOpen(newVal) {
        this.dialogOpen = newVal;
        if (newVal) {
          this.fetchBuildStatus();
          this.startPolling();
        } else {
          this.stopPolling();
        }
      },
    },
  }
</script>

<style scoped lang="scss">
  .build-log-container {
    max-height: 500px;
    overflow-y: auto;
    background: #1e1e1e;
    border-radius: 4px;
    padding: 12px;
  }

  .build-log {
    font-family: 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.5;
    color: #d4d4d4;
    white-space: pre-wrap;
    word-break: break-all;
    margin: 0;
  }
</style>
