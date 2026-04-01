<template>
  <v-form ref="form">
    <v-dialog v-model="isOpen" persistent max-width="900px">
      <v-card>
        <v-card-text v-if="item">
          <v-container>
            <v-row>
              <v-col cols="12" style="margin-bottom: 15px;">
                <h1 class="text-h4" style="margin-bottom: 0px; margin-top: 5px;" v-if="isCreatingNew">Create new Container</h1>
                <h1 class="text-h4" v-else>Edit Container</h1>
                <p class="text-body-2 mt-2 text-muted">
                  <span v-if="isCreatingNew">Create a new container image that users can reserve.</span>
                  <span v-else>Edit the container image configuration.</span>
                  You can either build the image automatically using the built-in Image Builder,
                  or use a pre-built image that you manage and push to the Docker registry yourself.
                </p>
              </v-col>

              <!-- BASIC INFORMATION -->
              <v-col cols="12">
                <h2 style="margin-top: 20px; margin-bottom: 0px;">Basic Information</h2>
              </v-col>

              <v-col cols="12">
                <!-- PUBLIC? -->
                <v-switch
                  v-model="data.public"
                  :label="data.public ? 'Public' : 'Private'"
                  color="primary"
                  hint="Public containers are available to all users. Private containers are only visible to admins when creating a reservation."
                  class="mb-10"
                ></v-switch>

                <!-- NAME -->
                <v-text-field type="text" id="name" :rules="[rules.required]" v-model="data.name" label="Name*" hint="Visible in the reservation container dropdown listing." class="mb-10"></v-text-field>

                <!-- IMAGE NAME -->
                <v-text-field type="text" :rules="[rules.required, rules.imageName]" v-model="data.imageName" label="Image name*" hint="Only lowercase letters, digits, dots, hyphens, underscores, and forward slashes. Used as the image tag in the registry." class="mb-10"></v-text-field>

                <!-- DESCRIPTION -->
                <v-textarea v-model="data.description" label="Description" hint="Visible in the reservation page after selecting the container." class="mb-10"></v-textarea>
              </v-col>

              <!-- CONTAINER CARD PREVIEW -->
              <v-col cols="12" v-if="data.name">
                <p class="text-body-2 mb-3 text-muted">Preview — how this container appears on the reservation page:</p>
                <v-card
                  style="min-height: 200px; max-width: 320px;"
                  variant="outlined"
                >
                  <v-card-text style="height: 100%;">
                    <div class="d-flex flex-column h-100" style="padding: 10px;">
                      <div class="text-center mb-3">
                        <v-icon size="32" class="mb-2" color="primary">mdi-docker</v-icon>
                        <div class="font-weight-medium text-h6">
                          {{ data.name || 'Container Name' }}
                        </div>
                        <div
                          class="text-body-2 mt-1"
                          style="color: rgba(255,255,255,0.7); font-size: 12px; font-family: monospace;"
                        >
                          {{ data.imageName || 'image-name' }}
                        </div>
                        <div
                          v-if="!data.public"
                          class="text-body-2 mt-1"
                          style="color: rgba(255,165,0,0.9); font-size: 11px; font-weight: 500;"
                        >
                          Private
                        </div>
                      </div>
                      <div class="flex-grow-1 text-center">
                        <div
                          class="text-body-2"
                          style="color: rgba(255,255,255,0.8); font-size: 13px; line-height: 1.3;"
                        >
                          {{ data.description || 'No description available' }}
                        </div>
                      </div>
                    </div>
                  </v-card-text>
                </v-card>
              </v-col>

              <!-- PORTS -->
              <v-col cols="12">
                <h2 style="margin-top: 20px; margin-bottom: 3px;">Ports</h2>
                <p class="text-muted" style="margin-bottom: 20px; margin-top: 0px;">Local ports of the container that will be bound to random outside ports.</p>
                <!-- Built-in SSH port (always present, read-only) -->
                <v-row>
                  <v-col cols="12">
                    <v-row>
                      <v-col cols="12" md="4">
                        <v-text-field model-value="SSH" label="Service name" readonly variant="outlined" bg-color="grey-darken-3"></v-text-field>
                      </v-col>
                      <v-col cols="12" md="4">
                        <v-text-field model-value="22" label="Port" readonly variant="outlined" bg-color="grey-darken-3"></v-text-field>
                      </v-col>
                      <v-col cols="12" md="4" class="d-flex align-center">
                        <v-chip color="info" size="small">Always included</v-chip>
                      </v-col>
                    </v-row>
                    <p class="text-caption text-medium-emphasis" style="margin-top: -8px;">SSH is the primary way users connect to their reserved container. It is always included automatically.</p>
                  </v-col>
                </v-row>
                <v-row>
                  <!-- Loop through all ports and add them here one by one -->
                  <v-col cols="12" v-for="(port, index) in data.ports" :key="index">
                    <v-row>
                      <v-col cols="12" md="4">
                        <v-text-field type="text" v-model="port.serviceName" :rules="[rules.required]" label="Service name"></v-text-field>
                      </v-col>
                      <v-col cols="12" md="4">
                        <v-text-field type="text" v-model="port.port" :rules="[rules.required]" label="Port"></v-text-field>
                      </v-col>
                      <v-col cols="12" md="4">
                        <v-btn color="red" variant="text" @click="removePort(index)">Remove</v-btn>
                      </v-col>
                    </v-row>
                  </v-col>
                </v-row>
                <v-btn color="primary" style="margin-top: 20px;" @click="addPort">Add port</v-btn>
              </v-col>

              <!-- IMAGE MANAGEMENT MODE -->
              <v-col cols="12">
                <h2 style="margin-top: 40px; margin-bottom: 3px;">Image Management</h2>
                <p class="text-body text-muted" style="margin-bottom: 20px; margin-top: 0px;">
                  Choose how this container image is managed.
                </p>

                <v-radio-group v-model="data.managedExternally" inline class="mb-6">
                  <v-radio :value="false" label="Build with Image Builder (recommended)"></v-radio>
                  <v-radio :value="true" label="Use pre-built image (managed externally)"></v-radio>
                </v-radio-group>

                <!-- EXTERNALLY MANAGED INFO -->
                <v-alert
                  v-if="isExternallyManaged"
                  type="info"
                  variant="tonal"
                  density="compact"
                  class="mb-4"
                >
                  This image is managed outside the system. Push the image to the Docker registry manually.
                  Refer to the project README for instructions on building and pushing images externally.
                </v-alert>
              </v-col>

              <!-- IMAGE BUILDER SECTION (only shown when NOT externally managed) -->
              <v-col cols="12" v-if="!isExternallyManaged">
                <h2 style="margin-top: 10px; margin-bottom: 3px;">Image Builder</h2>
                <p class="text-muted" style="margin-bottom: 30px; margin-top: 0px;">
                  Define the Dockerfile to build this image automatically.
                </p>

                <!-- Build Status -->
                <div v-if="!isCreatingNew && data.buildStatus" class="mb-4 d-flex align-center">
                  <span class="mr-2">Build Status:</span>
                  <v-chip
                    :color="buildStatusColor"
                    text-color="white"
                    size="small"
                  >
                    <v-progress-circular
                      v-if="data.buildStatus === 'building' || data.buildStatus === 'pending'"
                      indeterminate size="14" width="2" class="mr-1"
                    ></v-progress-circular>
                    {{ buildStatusLabel }}
                  </v-chip>
                  <v-btn
                    v-if="data.buildLog"
                    variant="text"
                    size="small"
                    color="primary"
                    class="ml-2"
                    @click="showBuildLogDialog = true"
                  >
                    View Build Log
                  </v-btn>
                </div>

                <!-- Container Username -->
                <v-text-field
                  v-model="data.containerUsername"
                  label="Container Username*"
                  :rules="[rules.required, rules.username]"
                  class="mb-10"
                  hint=" "
                >
                  <template v-slot:message>
                    <span>Linux username inside the container that users will SSH into. Default is: user.
                      <a class="reset-link" @click.stop.prevent="resetUsernameToDefault">Reset</a>
                    </span>
                  </template>
                </v-text-field>

                <!-- Base Image -->
                <v-text-field
                  v-model="data.baseImage"
                  label="Base Image*"
                  placeholder="ubuntu:22.04"
                  :rules="[rules.required]"
                  class="mb-10"
                  hint=" "
                >
                  <template v-slot:message>
                    <span>Docker image for the FROM line (e.g. ubuntu:22.04, ubuntu:24.04, nvidia/cuda:11.8.0-devel-ubuntu22.04). Pulled from Docker Hub or other registries.
                      <a class="reset-link" @click.stop.prevent="resetBaseImageToDefault">Reset</a>
                    </span>
                  </template>
                </v-text-field>

                <!-- Dockerfile Body -->
                <v-textarea
                  v-model="data.dockerfileCommands"
                  label="Dockerfile Body*"
                  placeholder="Dockerfile instructions between FROM and CMD"
                  rows="15"
                  :rules="[rules.required]"
                  class="dockerfile-textarea mb-10"
                  hint=" "
                >
                  <template v-slot:message>
                    <span>Full Dockerfile instructions between FROM and CMD. Edit freely to customize packages, user setup, SSH config, etc.
                      <a v-if="data.dockerfileCommands" class="reset-link" @click.stop.prevent="resetDockerfileToDefaults">Reset</a>
                    </span>
                  </template>
                </v-textarea>

                <!-- CMD -->
                <v-text-field
                  v-model="data.containerCmd"
                  label="CMD (start command)*"
                  :rules="[rules.required]"
                  class="dockerfile-textarea mb-10"
                  hint=" "
                >
                  <template v-slot:message>
                    <span>The container start command (last Dockerfile line). Default starts SSH daemon.
                      <a class="reset-link" @click.stop.prevent="resetCmdToDefaults">Reset</a>
                    </span>
                  </template>
                </v-text-field>
              </v-col>

              <!-- RUNTIME POST-START COMMANDS (only shown when NOT externally managed) -->
              <v-col cols="12" v-if="!isExternallyManaged">
                <v-expansion-panels class="mt-2">
                  <v-expansion-panel>
                    <v-expansion-panel-title>
                      <v-icon class="mr-2" size="small">mdi-console</v-icon>
                      Runtime Post-Start Commands
                    </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <p class="text-body-2 mb-4 text-muted">
                        These commands run as root inside the container after every start.
                        Template variables <code>{username}</code>, <code>{password}</code>, and <code>{ssh_key}</code> are replaced with actual values at runtime.
                      </p>

                      <!-- Password Command -->
                      <v-text-field
                        v-model="data.passwordCommand"
                        label="Password Command"
                        class="dockerfile-textarea mb-10"
                        hint=" "
                      >
                        <template v-slot:message>
                          <span>Executed to set the SSH password. Variables: {username}, {password}.
                            <a class="reset-link" @click.stop.prevent="resetPasswordCommandToDefaults">Reset</a>
                          </span>
                        </template>
                      </v-text-field>

                      <!-- SSH Key Deploy Commands -->
                      <v-textarea
                        v-model="data.sshKeyDeployCommands"
                        label="SSH Key Deploy Commands"
                        rows="5"
                        class="dockerfile-textarea mb-4"
                        hint=" "
                      >
                        <template v-slot:message>
                          <span>Executed if user has an SSH public key. Variables: {username}, {ssh_key}.
                            <a class="reset-link" @click.stop.prevent="resetSshKeyCommandsToDefaults">Reset</a>
                          </span>
                        </template>
                      </v-textarea>
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                </v-expansion-panels>
              </v-col>

            </v-row>
          </v-container>
        </v-card-text>

        <v-card-actions class="mx-6 mb-6 mt-2" style="align-items: center; flex-wrap: wrap; gap: 8px;">
          <!-- SAVE INFO -->
          <v-alert
            v-if="hasRequiredFields"
            :type="saveInfoType"
            variant="tonal"
            density="compact"
            style="flex: 1 1 0; min-width: 0;"
          >
            {{ saveInfoMessage }}
          </v-alert>
          <v-btn color="red" variant="text" @click="closeDialog">Cancel</v-btn>
          <v-btn color="blue" variant="text" @click="submit" :loading="isSubmitting">
            <span v-if="isCreatingNew">Add container</span><span v-else>Save Container</span>
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Build Log Dialog -->
    <AdminBuildLogDialog
      v-if="showBuildLogDialog && data.containerId"
      :containerId="data.containerId"
      :isOpen="showBuildLogDialog"
      @emitClose="onBuildLogClose"
      @emitEditContainer="onBuildLogEditContainer"
    />
  </v-form>
</template>

<script>
  /**
   * Modal dialog for creating or editing a container image definition.
   * Supports two modes: Image Builder (managed internally) and pre-built (managed externally).
   *
   * Image Builder mode allows admins to configure the Dockerfile body, CMD, container username,
   * and runtime post-start commands. Pre-built mode hides these fields and expects the admin
   * to manage the image outside the system.
   *
   * Props:
   *   propData - The container ID to edit, or "new" to create a new container.
   *
   * Emits:
   *   emitModalClose - When the modal is closed (after save or cancel).
   */
  import axios from 'axios';
  import { useMainStore } from '@/store/store'
  import AdminBuildLogDialog from '/src/components/admin/AdminBuildLogDialog.vue';

  export default {
    name: "AdminManageContainerModal",
    components: {
      AdminBuildLogDialog,
    },
    setup() {
      const store = useMainStore()
      return { store }
    },
    props: {
      propData: [ Number, String ],
    },
    data() {
      return {
        item: this.propData,
        data: {
          ports: [],
          managedExternally: false,
          baseImage: 'ubuntu:22.04',
          dockerfileCommands: '',
          containerCmd: '',
          buildStatus: null,
          buildLog: '',
          containerUsername: 'user',
          passwordCommand: '',
          sshKeyDeployCommands: '',
        },
        defaults: null,
        originalImageFields: null,
        isCreatingNew: false,
        isOpen: true,
        isFetching: true,
        isSubmitting: false,
        modalKey: new Date().toString(),
        removedPorts: [],
        dataName: "container",
        showBuildLogDialog: false,
        rules: {
          required: value => !!value || "Required",
          imageName: value => {
            if (!value || value.trim() === '') return true;
            if (!/^[a-z0-9][a-z0-9._/\-]{0,127}$/.test(value)) return 'Only lowercase letters, digits, dots, hyphens, underscores, and forward slashes.';
            return true;
          },
          username: value => {
            if (!value || value.trim() === '') return true;
            if (!/^[a-z_][a-z0-9_-]{0,31}$/.test(value)) return 'Must be 1-32 lowercase letters, digits, hyphens, or underscores.';
            if (['root', 'daemon', 'bin', 'sys', 'nobody', 'www-data', 'mail', 'sshd'].includes(value)) return 'This username is reserved.';
            return true;
          },
          number: value => !isNaN(parseFloat(value)),
        }
      }
    },
    computed: {
      isExternallyManaged() {
        // null = legacy container, treat as externally managed
        return this.data.managedExternally === true || this.data.managedExternally === null;
      },
      /** Whether saving will trigger an image rebuild. */
      willRebuild() {
        if (this.isExternallyManaged) return false;
        if (!this.data.dockerfileCommands || !this.data.dockerfileCommands.trim()) return false;
        if (this.isCreatingNew) return true;
        if (!this.originalImageFields) return false;
        return (
          this.data.dockerfileCommands !== this.originalImageFields.dockerfileCommands ||
          this.data.baseImage !== this.originalImageFields.baseImage ||
          this.data.containerUsername !== this.originalImageFields.containerUsername ||
          this.data.containerCmd !== this.originalImageFields.containerCmd
        );
      },
      /** Context-sensitive save info message. */
      /** Whether all required basic fields are filled. */
      hasRequiredFields() {
        return this.data.name && this.data.name.trim() && this.data.imageName && this.data.imageName.trim();
      },
      saveInfoMessage() {
        let imageName = this.data.imageName || 'your-image';
        if (this.isExternallyManaged) {
          if (this.isCreatingNew) {
            return `The container will be registered but no image will be built. You need to manually build and push the image "${imageName}" to the Docker registry before users can reserve it.`;
          }
          return `No image will be built. The image "${imageName}" is managed externally — make sure it is available in the Docker registry.`;
        }
        if (this.isCreatingNew) {
          return `The image "${imageName}" will be built and pushed to the Docker registry automatically. After saving, the build log will open so you can follow the progress. Once built, the image will be available on the container server (visible via "docker images" command).`;
        }
        if (this.willRebuild) {
          return `Image builder settings were changed. The image "${imageName}" will be rebuilt and pushed to the Docker registry. The build log will open after saving.`;
        }
        return `No image rebuild needed — the image builder settings were not changed. Only container configuration will be updated.`;
      },
      saveInfoType() {
        if (this.isExternallyManaged) return 'warning';
        if (this.isCreatingNew || this.willRebuild) return 'info';
        return 'success';
      },
      buildStatusColor() {
        const colors = { pending: 'yellow', building: 'orange', success: 'green', failed: 'red' };
        return colors[this.data.buildStatus] || 'grey';
      },
      buildStatusLabel() {
        const labels = { pending: 'Build Queued', building: 'Building...', success: 'Built', failed: 'Build Failed' };
        return labels[this.data.buildStatus] || this.data.buildStatus;
      },
    },
    created() {
      if (this.item === "new") {
        this.isCreatingNew = true;
        this.isFetching = false;
        this.data.managedExternally = false;
        this.fetchDefaults();
      }
      else {
        this.isFetching = true;
        this.fetchData();
      }
    },
    mounted() {
    },
    methods: {
      addPort() {
        this.data.ports.push({ serviceName: "", port: "" });
      },
      /** Removes a port entry and tracks its ID for backend deletion if it was already persisted. */
      removePort(index) {
        if (this.data.ports[index].containerPortId) {
          this.removedPorts.push(this.data.ports[index].containerPortId);
        }
        this.data.ports.splice(index, 1);
      },
      closeDialog() {
        this.isOpen = false;
      },
      /** Fetch default values from backend for new container creation. */
      fetchDefaults(username) {
        let _this = this;
        let currentUser = this.store.user;
        let params = {};
        if (username) params.username = username;

        axios({
          method: "get",
          url: this.$appSettings.APIServer.admin.container_defaults,
          params: params,
          headers: { "Authorization": `Bearer ${currentUser.loginToken}` }
        })
        .then(function (response) {
          if (response.data.status == true) {
            _this.defaults = response.data.data;
            // Pre-fill if creating new and fields are empty
            if (_this.isCreatingNew) {
              if (!_this.data.dockerfileCommands) _this.data.dockerfileCommands = _this.defaults.dockerfileBody;
              if (!_this.data.containerCmd) _this.data.containerCmd = _this.defaults.containerCmd;
              if (!_this.data.passwordCommand) _this.data.passwordCommand = _this.defaults.passwordCommand;
              if (!_this.data.sshKeyDeployCommands) _this.data.sshKeyDeployCommands = _this.defaults.sshKeyDeployCommands;
            }
          }
        })
        .catch(function (error) {
          console.log("Error fetching container defaults:", error);
        });
      },
      /** Reset the Dockerfile body to defaults for the current username. */
      resetDockerfileToDefaults() {
        let _this = this;
        let currentUser = this.store.user;
        let username = this.data.containerUsername || 'user';

        axios({
          method: "get",
          url: this.$appSettings.APIServer.admin.container_defaults,
          params: { username: username },
          headers: { "Authorization": `Bearer ${currentUser.loginToken}` }
        })
        .then(function (response) {
          if (response.data.status == true) {
            _this.data.dockerfileCommands = response.data.data.dockerfileBody;
            _this.data.containerCmd = response.data.data.containerCmd;
          }
        });
      },
      /** Reset username to default value. */
      resetUsernameToDefault() {
        this.data.containerUsername = 'user';
      },
      /** Reset base image to default value. */
      resetBaseImageToDefault() {
        this.data.baseImage = 'ubuntu:22.04';
      },
      /** Reset CMD to default value. */
      resetCmdToDefaults() {
        if (this.defaults) {
          this.data.containerCmd = this.defaults.containerCmd;
        }
      },
      /** Reset password command to default value. */
      resetPasswordCommandToDefaults() {
        if (this.defaults) {
          this.data.passwordCommand = this.defaults.passwordCommand;
        }
      },
      /** Reset SSH key deploy commands to default value. */
      resetSshKeyCommandsToDefaults() {
        if (this.defaults) {
          this.data.sshKeyDeployCommands = this.defaults.sshKeyDeployCommands;
        }
      },
      submit() {
        if (!this.$refs.form.validate()) return;
        this.isSubmitting = true;
        let containerId = this.item == "new" ? -1 : this.item;
        let data = this.data;
        data.removedPorts = this.removedPorts;

        let _this = this
        let currentUser = this.store.user

        axios({
          method: "post",
          url: this.$appSettings.APIServer.admin.save_container,
          data: { containerId: containerId, data: data },
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
            // Success
            if (response.data.status == true) {
              let savedId = response.data.data ? response.data.data.containerId : null;
              if (_this.willRebuild && savedId) {
                _this.store.showMessage({ text: "Container saved. Image build queued.", color: "green" })
                _this.data.containerId = savedId;
                _this.showBuildLogDialog = true;
                _this.isOpen = false;
                _this.isSubmitting = false;
                return;
              } else {
                _this.store.showMessage({ text: "Container saved.", color: "green" })
              }
              _this.closeDialog();
              _this.isSubmitting = false
            }
            // Fail
            else {
              console.log("Failed saving "+_this.dataName+" information...")
              _this.store.showMessage({ text: response.data.message || "There was an error saving "+_this.dataName+" information.", color: "red" })
            }
            _this.isSubmitting = false
        })
        .catch(function (error) {
            // Error
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.store.showMessage({ text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.store.showMessage({ text: "Unknown error while trying to save "+_this.dataName+" information.", color: "red" })
            }
            _this.isSubmitting = false
        });
      },
      fetchData() {
        let _this = this
        let currentUser = this.store.user

        axios({
          method: "get",
          url: this.$appSettings.APIServer.admin.get_container,
          params: { containerId: this.item },
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
            // Success
            if (response.data.status == true) {
              _this.data = response.data.data.data
              // Ensure defaults for fields
              if (!_this.data.baseImage) _this.data.baseImage = 'ubuntu:22.04'
              if (!_this.data.containerUsername) _this.data.containerUsername = 'user'
              if (!_this.data.ports) _this.data.ports = []
              // Legacy containers (managedExternally is null) — treat as externally managed
              if (_this.data.managedExternally === null || _this.data.managedExternally === undefined) {
                _this.data.managedExternally = true;
              }
              // Store original image-related fields for rebuild detection
              _this.originalImageFields = {
                dockerfileCommands: _this.data.dockerfileCommands,
                baseImage: _this.data.baseImage,
                containerUsername: _this.data.containerUsername,
                containerCmd: _this.data.containerCmd,
              };
              // Fetch defaults for reset buttons (only if using Image Builder)
              if (!_this.data.managedExternally) {
                _this.fetchDefaults(_this.data.containerUsername);
              }
            }
            // Fail
            else {
              console.log("Failed getting "+_this.dataName+"...")
              _this.store.showMessage({ text: "There was an error getting "+_this.dataName+".", color: "red" })
            }
            _this.isFetching = false
        })
        .catch(function (error) {
            // Error
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.store.showMessage({ text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.store.showMessage({ text: "Unknown error while trying to get "+_this.dataName+".", color: "red" })
            }
            _this.isFetching = false
        });

        this.isFetching = false
      },
      onBuildLogClose() {
        this.showBuildLogDialog = false;
        this.$emit("emitModalClose");
      },
      onBuildLogEditContainer(containerId) {
        this.showBuildLogDialog = false;
        this.item = containerId;
        this.isCreatingNew = false;
        this.isOpen = true;
        this.fetchData();
      },
    },
    watch: {
      isOpen: function(newVal) {
        if (newVal === false) {
          this.$emit("emitModalClose");
        }
      },
      /** When switching from external to Image Builder, fetch defaults to pre-fill empty fields. */
      'data.managedExternally': function(newVal) {
        if (newVal === false && !this.defaults) {
          this.fetchDefaults(this.data.containerUsername);
        }
      },
    }
  }
</script>

<style scoped lang="scss">
  .title {
    margin-top: 40px;
  }

  .dockerfile-textarea :deep(textarea),
  .dockerfile-textarea :deep(input) {
    font-family: monospace;
    font-size: 15px;
  }

  .reset-link {
    color: #fb8c00;
    cursor: pointer;
    text-decoration: none;
    margin-left: 4px;
    &:hover {
      text-decoration: underline;
    }
  }
</style>
