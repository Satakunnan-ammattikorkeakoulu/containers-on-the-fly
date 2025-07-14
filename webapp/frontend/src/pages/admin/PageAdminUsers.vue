<template>
  <v-container>
    <v-row class="text-center">
      <v-col cols="12">
        <h4>Admin</h4>
        <h2>All Users</h2>
      </v-col>
    </v-row>

    <v-row class="text-center">
      <v-col cols="12">
        <v-btn color="green" @click="addUser">Create New User</v-btn>
      </v-col>
    </v-row>

    <v-row v-if="!isFetching">
      <v-col cols="12">
        <div v-if="users && users.length > 0" style="margin-top: 50px">
          <AdminUsersTable v-on:emitEditUser="editUser" v-bind:propItems="users" />
        </div>
        <p v-else class="dim text-center">No users.</p>
      </v-col>
    </v-row>
    <v-row v-else>
      <v-col cols="12">
        <Loading class="loading" />
      </v-col>
    </v-row>

    <AdminManageUserModal 
      @click.stop="dialog = true" 
      v-if="selectedItem" 
      v-on:emitModalClose="closeDialog" 
      :propData="selectedItem" 
      :key="dialogKey">
    </AdminManageUserModal>
  </v-container>
</template>

<script>
const axios = require('axios').default;
import Loading from '/src/components/global/Loading.vue';
import AdminUsersTable from '/src/components/admin/AdminUsersTable.vue';
import AdminManageUserModal from '/src/components/admin/AdminManageUserModal.vue';

export default {
  name: 'PageAdminUsers',
  components: {
    Loading,
    AdminUsersTable,
    AdminManageUserModal
  },
  data: () => ({
    intervalFetch: null,
    isFetching: false,
    users: [],  // Changed from data to users
    selectedItem: undefined,
    dialog: false,
    dialogKey: new Date().getTime(),
    tableName: "users",
  }),
  mounted () {
    this.isFetching = true;
    this.fetch();

    // Keep updating data every 30 seconds
    this.intervalFetch = setInterval(() => { this.fetch()}, 30000);
  },
  methods: {
    addUser() {
      this.selectedItem = "new";
      this.dialogKey = new Date().getTime();
      this.dialog = true;
    },
    editUser(userId) {
      this.dialogKey = new Date().getTime();
      this.selectedItem = userId;
      this.dialog = true;
    },
    closeDialog() {
      this.dialog = false;
      this.selectedItem = undefined;
      this.fetch();
    },
    fetch() {
      let _this = this;
      let currentUser = this.$store.getters.user;

      axios({
        method: "get",
        url: this.AppSettings.APIServer.admin.get_users,
        headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
      })
      .then(function (response) {
        if (response.data.status == true) {
          _this.users = response.data.data[_this.tableName];  // Changed from data to users
        } else {
          console.log("Failed getting "+_this.tableName+"...");
          _this.$store.commit('showMessage', { text: "There was an error getting "+_this.tableName+".", color: "red" });
        }
        _this.isFetching = false;
      })
      .catch(function (error) {
        // Error
        if (error.response && (error.response.status == 400 || error.response.status == 401)) {
          _this.$store.commit('showMessage', { text: error.response.data.detail, color: "red" });
        }
        else {
          console.log(error);
          _this.$store.commit('showMessage', { text: "Unknown error while trying to get "+_this.tableName+".", color: "red" });
        }
        _this.isFetching = false;
      });
    }
  },
  beforeDestroy() {
    clearInterval(this.intervalFetch);
  }
}
</script>

<style scoped lang="scss">
.loading {
  margin: 60px auto;
}
</style>