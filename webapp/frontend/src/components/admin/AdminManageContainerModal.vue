<template>
  <v-form ref="form">
    <v-dialog v-model="isOpen" persistent max-width="900px">
      <v-card>
        <v-card-text v-if="item">
          <v-container>
            <v-row>
              <v-col cols="12" style="margin-bottom: 15px;">
                <h2 class="title" v-if="isCreatingNew">Create new Container</h2>
                <h2 class="title" v-else>Edit Container</h2>
              </v-col>

              <!-- PUBLIC? -->
              <v-col cols="12">
                <v-checkbox type="text" v-model="data.public" label="Public"></v-checkbox>
              </v-col>
              <!-- NAME -->
              <v-col cols="12">
                <v-text-field type="text" id="name" :rules="[rules.required]" v-model="data.name" label="Name*"></v-text-field>
                <p class="help-text">Visible in the reservation container dropdown listing.</p>
              </v-col>
              <!-- IMAGE NAME -->
              <v-col cols="12">
                <v-text-field type="text" :rules="[rules.required]" v-model="data.imageName" label="Image name*"></v-text-field>
                <p class="help-text">Name of the Docker image. Case sensitive. The image should be available in the system running the backend docker script.</p>
              </v-col>
              <!-- DESCRIPTION -->
              <v-col cols="12">
                <v-textarea v-model="data.description" label="Description"></v-textarea>
                <p class="help-text">Visible in the reservation page after selecting the container.</p>
              </v-col>
              <!-- PORTS -->
              <v-col cols="12">
                <h2 style="margin-top: 40px; margin-bottom: 10px;">Ports</h2>
                <p style="margin-bottom: 20px;">Local ports of the container that will be bound to random outside ports.</p>
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
            </v-row>
          </v-container>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="red" variant="text" @click="closeDialog">Cancel</v-btn>
          <v-btn color="blue" variant="text" @click="submit"><span v-if="isCreatingNew">Add container</span><span v-else>Save Container</span></v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-form>
</template>

<script>
  import axios from 'axios';
  import { useMainStore } from '@/store/store'
  //import Loading from '/src/components/global/Loading.vue';

  export default {
    name: "AdminManageContainerModal",
    setup() {
      const store = useMainStore()
      return { store }
    },
    props: {
      propData: [ Number, String ], // Contains the ID of the container to edit, or "new" if creating new
    },
    data() {
      return {
        item: this.propData, // Contains the ID of the container to edit, or "new" if creating new
        data: { ports: [] }, // Contains the data of the container, for ex: { containerId: 2, public: true, name: "Ubuntu 20.04", ports: [ { id: 1, serviceName: "SSH", port: 22 } ] ...... }
        isCreatingNew: false, // Set to true if creating new container
        isOpen: true, // Set to true to open the modal
        isFetching: true, // Set to true when fetching data from server
        isSubmitting: false, // Set to true when submitting data to server
        modalKey: new Date().toString(), // Used to force re-rendering of the modal
        removedPorts: [], // IDs of ports that were removed
        dataName: "container",
        rules: {
          required: value => !!value || "Required",
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
      addPort() {
        this.data.ports.push({ serviceName: "", port: "" });
      },
      removePort(index) {
        // Mark the port for removal if it also contained containerPortId, thus it was already in the database
        if (this.data.ports[index].containerPortId) {
          this.removedPorts.push(this.data.ports[index].containerPortId);
        }
        this.data.ports.splice(index, 1);
      },
      closeDialog() {
        this.isOpen = false;
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
          url: this.$appSettings.APIServer.admin.get_container,
          params: { containerId: this.item },
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

  .help-text {
    margin-top: -7px;
  }

</style>