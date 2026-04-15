<template>
  <v-form ref="form">
    <v-dialog v-model="isOpen" persistent max-width="1100px">
      <v-card>
        <v-card-text v-if="item">
          <v-container>
            <v-row>
              <v-col cols="12" style="margin-bottom: 15px;">
                <h2 class="title" v-if="isCreatingNew">Create new Computer</h2>
                <h2 class="title" v-else>Edit Computer</h2>
              </v-col>

              <!-- PUBLIC? -->
              <v-col cols="12">
                <v-switch v-model="data.public" :label="data.public ? 'Public' : 'Not Public'" :color="data.public ? 'success' : 'error'" :base-color="data.public ? '' : 'error'" hide-details></v-switch>
                <p class="help-text" style="margin-top: 8px;">When public, all users can see and reserve from this computer. When not public, only administrators can use it for testing.</p>
              </v-col>
              <!-- NAME -->
              <v-col cols="12">
                <v-text-field type="text" id="name" :rules="[rules.required, rules.computerName]" v-model="data.name" label="Name*"></v-text-field>
                <p class="help-text">Visible in the reservation dropdown. Must exactly match the DOCKER_SERVER_NAME setting in the container server's <code>user_config/settings</code> file. Only letters, numbers, dots, underscores, and hyphens allowed.</p>
              </v-col>
              <!-- IP -->
              <v-col cols="12">
                <v-text-field type="text" :rules="[rules.required]" v-model="data.ip" label="IP address / Address*"></v-text-field>
                <p class="help-text">IP address / address of the computer. This will be used to instruct users to access the server using this address. For example: aiserver1.samk.fi</p>
              </v-col>
              <!-- vCPUs -->
              <v-col cols="12">
                <h2 style="margin-bottom: 20px; margin-top: 40px;">vCPUs</h2>
                <p class="help-text">Configure vCPU limits for this server. Integer values, e.g. 3. Hover the field icons for details.</p>
                <v-row>
                  <v-col cols="12" md="4">
                    <v-text-field type="text" :rules="[rules.requiredNumber]" v-model="data.hardware.cpu.maximumAmount" label="Total on server*">
                      <template v-slot:append-inner>
                        <v-tooltip location="bottom">
                          <template v-slot:activator="{ props }">
                            <v-icon v-bind="props" size="small">mdi-information-outline</v-icon>
                          </template>
                          <span>The total vCPUs physically available on this server. Hard ceiling — no user or role can exceed it.</span>
                        </v-tooltip>
                      </template>
                    </v-text-field>
                  </v-col>
                  <v-col cols="12" md="4">
                    <v-text-field type="text" :rules="[rules.requiredNumber]" v-model="data.hardware.cpu.minimumAmount" label="Minimum per reservation*">
                      <template v-slot:append-inner>
                        <v-tooltip location="bottom">
                          <template v-slot:activator="{ props }">
                            <v-icon v-bind="props" size="small">mdi-information-outline</v-icon>
                          </template>
                          <span>The smallest number of vCPUs a user can request in one reservation. Prevents wasteful tiny slices.</span>
                        </v-tooltip>
                      </template>
                    </v-text-field>
                  </v-col>
                  <v-col cols="12" md="4">
                    <v-text-field type="text" :rules="[rules.requiredNumber]" v-model="data.hardware.cpu.defaultAmountForUser" label="Default for user*">
                      <template v-slot:append-inner>
                        <v-tooltip location="bottom">
                          <template v-slot:activator="{ props }">
                            <v-icon v-bind="props" size="small">mdi-information-outline</v-icon>
                          </template>
                          <span>The vCPU amount pre-selected on the reserve page when a user opens it. A reasonable starting point for most reservations.</span>
                        </v-tooltip>
                      </template>
                    </v-text-field>
                  </v-col>
                </v-row>
                <v-row class="mt-n3">
                  <v-col cols="12" md="6">
                    <v-text-field type="text" :rules="[rules.requiredNumber]" v-model="data.hardware.cpu.maximumAmountForUser" label="Maximum per user (normal)*">
                      <template v-slot:append-inner>
                        <v-tooltip location="bottom">
                          <template v-slot:activator="{ props }">
                            <v-icon v-bind="props" size="small">mdi-information-outline</v-icon>
                          </template>
                          <span>The largest number of vCPUs one user can request in a single normal reservation. Role-level overrides can raise this further.</span>
                        </v-tooltip>
                      </template>
                    </v-text-field>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-text-field type="text" :rules="[rules.requiredNumber]" v-model="data.hardware.cpu.maximumAmountForUserLowPriority" label="Maximum per user (low-priority)*">
                      <template v-slot:append-inner>
                        <v-tooltip location="bottom">
                          <template v-slot:activator="{ props }">
                            <v-icon v-bind="props" size="small">mdi-information-outline</v-icon>
                          </template>
                          <span>The largest number of vCPUs one user can request in a single low-priority reservation. Usually set higher than the normal cap since low-priority reservations may be paused when resources are needed by others.</span>
                        </v-tooltip>
                      </template>
                    </v-text-field>
                  </v-col>
                </v-row>
              </v-col>
              <!-- RAM -->
              <v-col cols="12">
                <h2 style="margin-bottom: 20px; margin-top: 40px;">Ram Memory</h2>
                <p class="help-text">Configure RAM limits (in GB) for this server. Integer values, e.g. 256. Hover the field icons for details.</p>
                <v-row>
                  <v-col cols="12" md="4">
                    <v-text-field type="text" :rules="[rules.requiredNumber]" v-model="data.hardware.ram.maximumAmount" label="Total on server*">
                      <template v-slot:append-inner>
                        <v-tooltip location="bottom">
                          <template v-slot:activator="{ props }">
                            <v-icon v-bind="props" size="small">mdi-information-outline</v-icon>
                          </template>
                          <span>The total RAM (in GB) physically available on this server. Hard ceiling — no user or role can exceed it.</span>
                        </v-tooltip>
                      </template>
                    </v-text-field>
                  </v-col>
                  <v-col cols="12" md="4">
                    <v-text-field type="text" :rules="[rules.requiredNumber]" v-model="data.hardware.ram.minimumAmount" label="Minimum per reservation*">
                      <template v-slot:append-inner>
                        <v-tooltip location="bottom">
                          <template v-slot:activator="{ props }">
                            <v-icon v-bind="props" size="small">mdi-information-outline</v-icon>
                          </template>
                          <span>The smallest amount of RAM (in GB) a user can request in one reservation. Prevents wasteful tiny slices.</span>
                        </v-tooltip>
                      </template>
                    </v-text-field>
                  </v-col>
                  <v-col cols="12" md="4">
                    <v-text-field type="text" :rules="[rules.requiredNumber]" v-model="data.hardware.ram.defaultAmountForUser" label="Default for user*">
                      <template v-slot:append-inner>
                        <v-tooltip location="bottom">
                          <template v-slot:activator="{ props }">
                            <v-icon v-bind="props" size="small">mdi-information-outline</v-icon>
                          </template>
                          <span>The RAM amount (in GB) pre-selected on the reserve page when a user opens it. A reasonable starting point for most reservations.</span>
                        </v-tooltip>
                      </template>
                    </v-text-field>
                  </v-col>
                </v-row>
                <v-row class="mt-n3">
                  <v-col cols="12" md="6">
                    <v-text-field type="text" :rules="[rules.requiredNumber]" v-model="data.hardware.ram.maximumAmountForUser" label="Maximum per user (normal)*">
                      <template v-slot:append-inner>
                        <v-tooltip location="bottom">
                          <template v-slot:activator="{ props }">
                            <v-icon v-bind="props" size="small">mdi-information-outline</v-icon>
                          </template>
                          <span>The largest amount of RAM (in GB) one user can request in a single normal reservation. Role-level overrides can raise this further.</span>
                        </v-tooltip>
                      </template>
                    </v-text-field>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-text-field type="text" :rules="[rules.requiredNumber]" v-model="data.hardware.ram.maximumAmountForUserLowPriority" label="Maximum per user (low-priority)*">
                      <template v-slot:append-inner>
                        <v-tooltip location="bottom">
                          <template v-slot:activator="{ props }">
                            <v-icon v-bind="props" size="small">mdi-information-outline</v-icon>
                          </template>
                          <span>The largest amount of RAM (in GB) one user can request in a single low-priority reservation. Usually set higher than the normal cap since low-priority reservations may be paused when resources are needed by others.</span>
                        </v-tooltip>
                      </template>
                    </v-text-field>
                  </v-col>
                </v-row>
              </v-col>
              <!-- GPU Max -->
              <v-col cols="12">
                <h2 style="margin-bottom: 20px; margin-top: 40px;">GPU</h2>
                <p class="help-text">Configure per-user GPU caps for this server. Integer values, e.g. 2. Hover the field icons for details.</p>
                <v-row>
                  <v-col cols="12" md="6">
                    <v-text-field type="text" :rules="[rules.requiredNumber]" v-model="data.hardware.gpu.maximumAmountForUser" label="Maximum per user (normal)*">
                      <template v-slot:append-inner>
                        <v-tooltip location="bottom">
                          <template v-slot:activator="{ props }">
                            <v-icon v-bind="props" size="small">mdi-information-outline</v-icon>
                          </template>
                          <span>The largest number of GPUs one user can request in a single normal reservation.</span>
                        </v-tooltip>
                      </template>
                    </v-text-field>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-text-field type="text" :rules="[rules.requiredNumber]" v-model="data.hardware.gpu.maximumAmountForUserLowPriority" label="Maximum per user (low-priority)*">
                      <template v-slot:append-inner>
                        <v-tooltip location="bottom">
                          <template v-slot:activator="{ props }">
                            <v-icon v-bind="props" size="small">mdi-information-outline</v-icon>
                          </template>
                          <span>The largest number of GPUs one user can request in a single low-priority reservation. Usually set higher than the normal cap since low-priority reservations may be paused when the GPUs are needed.</span>
                        </v-tooltip>
                      </template>
                    </v-text-field>
                  </v-col>
                </v-row>
              </v-col>
              <!-- GPUs -->
              <v-col cols="12">
                <h2 style="margin-top: 40px; margin-bottom: 10px;">GPUs</h2>
                <p class="help-text">Write the Nvidia / Cuda ID for each GPU (can be located using the nvidia-smi command) and name for each GPU. The name could also include the GPU ram amount, like: Nvidia RTX A5000 24GB</p>
                <p style="margin-bottom: 20px;"></p>
                <v-row>
                  <!-- Loop through all gpus and add them here one by one -->
                  <v-col cols="12" v-for="(gpu, index) in data.hardware.gpus" :key="index">
                    <v-row>
                      <v-col cols="12" md="4">
                        <v-text-field type="text" v-model="gpu.internalId" :rules="[rules.required]" label="Cuda ID"></v-text-field>
                      </v-col>
                      <v-col cols="12" md="4">
                        <v-text-field type="text" v-model="gpu.format" :rules="[rules.required]" label="Name"></v-text-field>
                      </v-col>
                      <v-col cols="12" md="4">
                        <v-btn color="red" variant="text" @click="removeGPU(index)">Remove</v-btn>
                      </v-col>
                    </v-row>
                  </v-col>
                </v-row>
                <v-btn color="primary" style="margin-top: 20px;" @click="addGPU">Add GPU</v-btn>

              </v-col>
            </v-row>
          </v-container>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="red" variant="text" @click="closeDialog">Cancel</v-btn>
          <v-btn color="blue" variant="text" @click="submit"><span v-if="isCreatingNew">Add Computer</span><span v-else>Save Computer</span></v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-form>
</template>

<script>
  /**
   * Modal dialog for creating or editing a container server (computer).
   * Allows admins to configure the server's name, IP address, public visibility,
   * and hardware specs (vCPUs, RAM, GPU count, and individual GPU entries with CUDA IDs).
   *
   * Props:
   *   propData - The computer ID to edit, or "new" to create a new computer.
   *
   * Emits:
   *   emitModalClose - When the modal is closed (after save or cancel).
   */
  import axios from 'axios';
  import { useMainStore } from '@/store/store'
  //import Loading from '/src/components/global/Loading.vue';

  export default {
    name: "AdminManageComputerModal",
    setup() {
      const store = useMainStore()
      return { store }
    },
    props: {
      propData: [ Number, String ], // Contains the ID of the computer to edit, or "new" if creating new
    },
    data() {
      return {
        item: this.propData, // Contains the ID of the computer to edit, or "new" if creating new
        data: { hardware: { cpu: {}, gpus: [], gpu: {}, ram: {} } }, // Contains the data of the computer
        isCreatingNew: false, // Set to true if creating new computer
        isOpen: true, // Set to true to open the modal
        isFetching: true, // Set to true when fetching data from server
        isSubmitting: false, // Set to true when submitting data to server
        modalKey: new Date().toString(), // Used to force re-rendering of the modal
        removedGPUs: [], // IDs of GPUs that were removed
        dataName: "computer",
        rules: {
          required: value => !!value || "Required",
          computerName: value => !value || /^[a-zA-Z0-9._-]+$/.test(value) || "Only letters, numbers, dots, underscores, and hyphens allowed.",
          requiredNumber: value => value !== '' && value !== null && value !== undefined || "Required",
          newPassword: value => {
            if (!value || value == "" || value.trim() == "") return "Password cannot be empty.";
            if (value.length < 5) return "Password has to be over 4 characters long.";
            return true;
          },
          number: value => !isNaN(parseFloat(value)),
          email: value => {
            const pattern = /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/
            return pattern.test(value) || 'Type in working email address.'
          },
        }
      }
    },
    computed: {
    },
    created() {
      if (this.item === "new") {
        this.isCreatingNew = true;
        this.isFetching = false;
        //this.item = Object.assign({}, this.item, { services: [], members: [], hasOpeningHours: false, hasSpecialPrices: false, branding: {} });
      }
      else {
        this.isFetching = true;
        this.fetchData();
      }
    },
    mounted() {
    },
    methods: {
      addGPU() {
        this.data.hardware.gpus.push({ format: "", internalId: "" });
      },
      /** Removes a GPU entry and tracks its ID for backend deletion if it was already persisted. */
      removeGPU(index) {
        if (this.data.hardware.gpus[index].hardwareSpecId) {
          this.removedGPUs.push(this.data.hardware.gpus[index].hardwareSpecId);
        }
        this.data.hardware.gpus.splice(index, 1);
      },
      closeDialog() {
        this.isOpen = false;
      },
      submit() {
        if (!this.$refs.form.validate()) return;
        this.isSubmitting = true;
        let computerId = this.item == "new" ? -1 : this.item;
        let data = this.data;
        data.removedGPUs = this.removedGPUs;

        let _this = this
        let currentUser = this.store.user

        axios({
          method: "post",
          url: this.$appSettings.APIServer.admin.save_computer,
          data: { computerId: computerId, data: data },
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
          //console.log(response)
            // Success
            if (response.data.status == true) {
              _this.closeDialog();
              _this.isSubmitting = false
            }
            // Fail
            else {
              console.log("Failed saving "+_this.dataName+" information...")
              _this.store.showMessage({ text: "There was an error saving "+_this.dataName+" information.", color: "red" })
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
          url: this.$appSettings.APIServer.admin.get_computer,
          params: { computerId: this.item },
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
          //console.log(response)
            // Success
            if (response.data.status == true) {
              _this.data = response.data.data.data
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
      }
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
  .title {
    margin-top: 40px;
  }


</style>