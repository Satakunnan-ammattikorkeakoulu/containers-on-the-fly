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

    <!-- Filters -->
    <v-row class="text-center row-filters justify-center">
      <v-col cols="12" md="3">
        <v-select
          :items="roleItems"
          label="Role"
          v-model="filters.role"
          item-text="text"
          item-value="value"
          @change="applyFilters"
        ></v-select>
      </v-col>
      <v-col cols="12" md="3">
        <v-text-field
          v-model="filters.email"
          label="Email"
          clearable
          @input="applyFilters"
        ></v-text-field>
      </v-col>
      <v-col cols="12" md="3">
        <v-text-field
          v-model="filters.userId"
          label="User ID"
          clearable
          @input="applyFilters"
        ></v-text-field>
      </v-col>
    </v-row>

    <v-row v-if="!isFetching" style="margin-top: 0px">
      <v-col cols="12">
        <div v-if="filteredUsers && filteredUsers.length > 0">
          <AdminUsersTable v-on:emitEditUser="editUser" v-bind:propItems="filteredUsers" />
        </div>
        <p v-else class="dim text-center">{{ users.length > 0 ? 'No users match the filters.' : 'No users.' }}</p>
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
    filteredUsers: [],
    availableRoles: [],
    selectedItem: undefined,
    dialog: false,
    dialogKey: new Date().getTime(),
    tableName: "users",
    filters: {
      userId: '',
      email: '',
      role: 'All'
    }
  }),
  computed: {
    roleItems() {
      const items = [{text: `All (${this.users.length})`, value: 'All'}];
      if (this.availableRoles) {
        items.push(...this.availableRoles.map(role => ({
          text: `${role.name} (${role.userCount || 0})`,
          value: role.name
        })));
      }
      return items;
    }
  },
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
          _this.availableRoles = response.data.data.availableRoles || [];
          _this.applyFilters();
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
    },
    applyFilters() {
      let filtered = this.users;
      
      // Filter by User ID
      if (this.filters.userId && this.filters.userId.trim() !== '') {
        filtered = filtered.filter(user => 
          user.userId.toString().toLowerCase().includes(this.filters.userId.toLowerCase().trim())
        );
      }
      
      // Filter by Email
      if (this.filters.email && this.filters.email.trim() !== '') {
        filtered = filtered.filter(user => 
          user.email.toLowerCase().includes(this.filters.email.toLowerCase().trim())
        );
      }
      
      // Filter by Role
      if (this.filters.role && this.filters.role !== 'All') {
        filtered = filtered.filter(user => {
          if (Array.isArray(user.roles)) {
            return user.roles.includes(this.filters.role);
          }
          return user.roles === this.filters.role;
        });
      }
      
      this.filteredUsers = filtered;
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

.row-filters {
  margin-top: 50px;
  margin-bottom: 0px;
}
</style>