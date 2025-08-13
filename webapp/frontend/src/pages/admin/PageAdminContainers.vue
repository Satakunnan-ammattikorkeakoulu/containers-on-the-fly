<template>
  <v-container>

    <v-row class="text-center">
      <v-col cols="12">
        <h4>Admin</h4>
        <h2>All Containers (Images)</h2>
      </v-col>
    </v-row>

    <v-row class="text-center">
      <v-col cols="12">
        <v-btn color="green" @click="addContainer">Create New Container</v-btn>
      </v-col>
    </v-row>

    <v-row v-if="!isFetching">
      <v-col cols="12">
        <div v-if="data && data.length > 0" style="margin-top: 50px">
          <AdminContainersTable v-on:emitEditContainer="editContainer" v-on:emitRemoveContainer="removeContainer" v-bind:propItems="data" />
        </div>
        <p v-else class="dim text-center">No containers.</p>
      </v-col>
    </v-row>
    <v-row v-else>
      <v-col cols="12">
        <Loading class="loading" />
      </v-col>
    </v-row>
    <AdminManageContainerModal @click.stop="dialog = true" v-if="selectedItem" v-on:emitModalClose="closeDialog" :propData="selectedItem" :key="dialogKey"></AdminManageContainerModal>
  </v-container>
</template>

<script>
  const axios = require('axios').default;
  import Loading from '/src/components/global/Loading.vue';
  import AdminContainersTable from '/src/components/admin/AdminContainersTable.vue';
  import AdminManageContainerModal from '/src/components/admin/AdminManageContainerModal.vue';
  
  export default {
    name: 'PageAdminContainers',

    components: {
    Loading,
    AdminContainersTable,
    AdminManageContainerModal
},
    data: () => ({
      intervalFetch: null,
      isFetching: false,
      data: [],
      isCreatingNew: false,
      selectedItem: undefined,
      dialog: false,
      dialogKey: new Date().getTime(),
      tableName: "containers",
    }),
    mounted () {
      this.isFetching = true
      this.fetch()

      // Keep updating data every 30 seconds
      this.intervalFetch = setInterval(() => { this.fetch()}, 30000)
    },
    methods: {
      addContainer() {
        this.selectedItem = "new";
        this.dialogKey = new Date().getTime();
        this.dialog = true;
      },
      editContainer(containerId) {
        this.dialogKey = new Date().getTime();
        this.selectedItem = containerId;
        this.dialog = true;
      },
      removeContainer(containerId) {
        let result = window.confirm("Do you really want to remove the container? It will be marked as removed in the database and as not public anymore.")
        if (!result) return
        let params = {
          "containerId": containerId,
        }

        let _this = this
        let currentUser = this.$store.getters.user

        axios({
          method: "post",
          url: this.AppSettings.APIServer.admin.remove_container,
          params: params,
          headers: {
            "Authorization" : `Bearer ${currentUser.loginToken}`
          }
        })
        .then(function (response) {
          //console.log(response)
            // Success
            if (response.data.status == true) {
              _this.$store.commit('showMessage', { text: "Container removed.", color: "green" })
              _this.fetch()
            }
            // Fail
            else {
              console.log("Failed removing container...")
              console.log(response)
              let msg = response && response.data && response.data.message ? response.data.message : "There was an error removing the container."
              _this.$store.commit('showMessage', { text: msg, color: "red" })
            }
        })
        .catch(function (error) {
            // Error
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.$store.commit('showMessage', { text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.$store.commit('showMessage', { text: "Unknown error.", color: "red" })
            }
        });
      },
      closeDialog() {
        this.dialog = false;
        this.fetch();
      },
      fetch() {
        let _this = this
        let currentUser = this.$store.getters.user

        axios({
          method: "get",
          url: this.AppSettings.APIServer.admin.get_containers,
          //params: { }
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
          //console.log(response)
            // Success
            if (response.data.status == true) {
              _this.data = response.data.data[_this.tableName]
            }
            // Fail
            else {
              console.log("Failed getting "+_this.tableName+"...")
              _this.$store.commit('showMessage', { text: "There was an error getting "+_this.tableName+".", color: "red" })
            }
            _this.isFetching = false
        })
        .catch(function (error) {
            // Error
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.$store.commit('showMessage', { text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.$store.commit('showMessage', { text: "Unknown error while trying to get "+_this.tableName+".", color: "red" })
            }
            _this.isFetching = false
        });

        this.isFetching = false
      },
    },
    beforeDestroy() {
      clearInterval(this.intervalFetch)
    },
  }
</script>

<style scoped lang="scss">
  .loading {
    margin: 60px auto;
  }
</style>