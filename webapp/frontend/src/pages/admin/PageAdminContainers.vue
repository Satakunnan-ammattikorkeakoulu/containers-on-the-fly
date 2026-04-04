<template>
  <v-container>

    <v-row class="text-center">
      <v-col cols="12">
        <h4 class="m-0">Admin</h4>
        <h2 class="m-0">All Containers (Images)</h2>
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
          <v-row justify="center" class="mb-4">
            <v-col cols="12" sm="4" md="3">
              <v-select
                v-model="visibilityFilter"
                :items="visibilityOptions"
                item-title="text"
                item-value="value"
                label="Visibility"
                hide-details
              ></v-select>
            </v-col>
          </v-row>
          <AdminContainersTable
            v-on:emitEditContainer="editContainer"
            v-on:emitRemoveContainer="removeContainer"
            v-on:emitRebuildContainer="rebuildContainer"
            v-on:emitViewBuildLog="viewBuildLog"
            v-bind:propItems="filteredData"
          />
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

    <!-- Remove Container Confirmation Dialog -->
    <v-dialog v-model="removeDialog.show" max-width="550px">
      <v-card class="pa-4">
        <v-card-title>Remove Container</v-card-title>
        <v-card-text>
          <p class="mb-3">Are you sure you want to remove <strong>{{ removeDialog.imageName }}</strong>?</p>

          <v-alert v-if="removeDialog.activeReservations > 0" type="warning" variant="tonal" density="compact" class="mb-3">
            There {{ removeDialog.activeReservations === 1 ? 'is' : 'are' }} <strong>{{ removeDialog.activeReservations }}</strong> active reservation{{ removeDialog.activeReservations !== 1 ? 's' : '' }} currently using this container.
            The container will be hidden from new reservations, but existing reservations will continue until they end.
          </v-alert>
          <v-alert v-else type="success" variant="tonal" density="compact" class="mb-3">
            No active reservations are using this container. It is safe to remove.
          </v-alert>

          <p v-if="!removeDialog.managedExternally" class="mb-2">
            The Docker image <strong>{{ removeDialog.imageName }}</strong> will be removed from the container server automatically.
          </p>
          <p v-else class="mb-2">
            This is an externally managed image. The Docker image will <strong>not</strong> be removed — you need to clean it up manually if desired.
          </p>

          <p class="text-muted">The container will be marked as removed in the database and will no longer be visible to users.</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="removeDialog.show = false">Cancel</v-btn>
          <v-btn color="red" variant="text" @click="confirmRemoveContainer">Remove</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Build Log Dialog for rebuild from table -->
    <AdminBuildLogDialog
      v-if="rebuildContainerId !== null"
      :containerId="rebuildContainerId"
      :isOpen="rebuildContainerId !== null"
      @emitClose="onRebuildLogClose"
      @emitEditContainer="onBuildLogEditContainer"
    />
  </v-container>
</template>

<script>
  /**
   * Admin page for managing container images.
   * Lists all registered Docker container images with CRUD operations
   * via a modal dialog. Data auto-refreshes every 30 seconds.
   */
  import axios from 'axios';
  import Loading from '/src/components/global/Loading.vue';
  import AdminContainersTable from '/src/components/admin/AdminContainersTable.vue';
  import AdminManageContainerModal from '/src/components/admin/AdminManageContainerModal.vue';
  import AdminBuildLogDialog from '/src/components/admin/AdminBuildLogDialog.vue';
  import { useMainStore } from '@/store/store'

  export default {
    name: 'PageAdminContainers',

    setup() {
      const store = useMainStore()
      return { store }
    },

    components: {
    Loading,
    AdminContainersTable,
    AdminManageContainerModal,
    AdminBuildLogDialog
},
    data: () => ({
      intervalFetch: null,
      isFetching: false,
      data: [],
      visibilityFilter: 'all',
      isCreatingNew: false,
      selectedItem: undefined,
      dialog: false,
      dialogKey: new Date().getTime(),
      tableName: "containers",
      rebuildContainerId: null,
      removeDialog: {
        show: false,
        containerId: null,
        imageName: '',
        activeReservations: 0,
        managedExternally: true,
      },
    }),
    computed: {
      visibilityOptions() {
        return [
          { text: `All (${this.data.length})`, value: 'all' },
          { text: `Public (${this.publicCount})`, value: 'public' },
          { text: `Private (${this.privateCount})`, value: 'private' },
        ];
      },
      filteredData() {
        if (this.visibilityFilter === 'public') return this.data.filter(c => c.public);
        if (this.visibilityFilter === 'private') return this.data.filter(c => !c.public);
        return this.data;
      },
      publicCount() {
        return this.data.filter(c => c.public).length;
      },
      privateCount() {
        return this.data.filter(c => !c.public).length;
      },
    },
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
      /** Fetch removal info and show the confirmation dialog. */
      removeContainer(containerId) {
        let _this = this;
        let currentUser = this.store.user;

        axios({
          method: "get",
          url: this.$appSettings.APIServer.admin.container_remove_info,
          params: { containerId: containerId },
          headers: { "Authorization": `Bearer ${currentUser.loginToken}` }
        })
        .then(function (response) {
          if (response.data.status == true) {
            _this.removeDialog.containerId = containerId;
            _this.removeDialog.imageName = response.data.data.imageName;
            _this.removeDialog.activeReservations = response.data.data.activeReservations;
            _this.removeDialog.managedExternally = response.data.data.managedExternally;
            _this.removeDialog.show = true;
          } else {
            _this.store.showMessage({ text: response.data.message || "Error fetching container info.", color: "red" })
          }
        })
        .catch(function (error) {
          console.log(error);
          _this.store.showMessage({ text: "Error fetching container info.", color: "red" })
        });
      },
      /** Confirm and execute the container removal. */
      confirmRemoveContainer() {
        let _this = this;
        let currentUser = this.store.user;

        axios({
          method: "post",
          url: this.$appSettings.APIServer.admin.remove_container,
          params: { containerId: this.removeDialog.containerId },
          headers: { "Authorization": `Bearer ${currentUser.loginToken}` }
        })
        .then(function (response) {
          if (response.data.status == true) {
            _this.store.showMessage({ text: "Container removed.", color: "green" })
            _this.fetch()
          } else {
            _this.store.showMessage({ text: response.data.message || "Error removing container.", color: "red" })
          }
          _this.removeDialog.show = false;
        })
        .catch(function (error) {
          if (error.response && (error.response.status == 400 || error.response.status == 401)) {
            _this.store.showMessage({ text: error.response.data.detail, color: "red" })
          } else {
            console.log(error)
            _this.store.showMessage({ text: "Unknown error.", color: "red" })
          }
          _this.removeDialog.show = false;
        });
      },
      /** Trigger a rebuild of a container's Docker image. */
      async rebuildContainer(containerId) {
        let result = await this.store.showConfirmDialog({
          title: 'Rebuild Docker Image',
          message: 'Rebuild the Docker image for this container? This will replace the existing image in the registry.',
          confirmText: 'Rebuild',
          confirmColor: 'orange',
        })
        if (!result) return

        let _this = this
        let currentUser = this.store.user

        axios({
          method: "post",
          url: this.$appSettings.APIServer.admin.rebuild_container_image,
          params: { containerId: containerId },
          headers: { "Authorization": `Bearer ${currentUser.loginToken}` }
        })
        .then(function (response) {
          if (response.data.status == true) {
            _this.store.showMessage({ text: response.data.message, color: "green" })
            _this.rebuildContainerId = containerId;
            _this.fetch()
          } else {
            _this.store.showMessage({ text: response.data.message || "Failed to queue rebuild.", color: "red" })
          }
        })
        .catch(function (error) {
          if (error.response && (error.response.status == 400 || error.response.status == 401)) {
            _this.store.showMessage({ text: error.response.data.detail, color: "red" })
          } else {
            console.log(error)
            _this.store.showMessage({ text: "Unknown error while trying to rebuild image.", color: "red" })
          }
        });
      },
      /** Open the build log dialog for a container (without triggering a rebuild). */
      viewBuildLog(containerId) {
        this.rebuildContainerId = containerId;
      },
      onRebuildLogClose() {
        this.rebuildContainerId = null;
        this.fetch();
      },
      /** Handle edit container request from build log dialog. */
      onBuildLogEditContainer(containerId) {
        this.rebuildContainerId = null;
        this.editContainer(containerId);
      },
      closeDialog() {
        this.dialog = false;
        this.fetch();
      },
      fetch() {
        let _this = this
        let currentUser = this.store.user

        axios({
          method: "get",
          url: this.$appSettings.APIServer.admin.get_containers,
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
            // Success
            if (response.data.status == true) {
              _this.data = response.data.data[_this.tableName]
            }
            // Fail
            else {
              console.log("Failed getting "+_this.tableName+"...")
              _this.store.showMessage({ text: "There was an error getting "+_this.tableName+".", color: "red" })
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
              _this.store.showMessage({ text: "Unknown error while trying to get "+_this.tableName+".", color: "red" })
            }
            _this.isFetching = false
        });

        this.isFetching = false
      },
    },
    beforeUnmount() {
      clearInterval(this.intervalFetch)
    },
  }
</script>

<style scoped lang="scss">
  .loading {
    margin: 60px auto;
  }
</style>
