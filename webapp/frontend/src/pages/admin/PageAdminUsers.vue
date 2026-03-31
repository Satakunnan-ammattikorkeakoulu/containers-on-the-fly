<template>
  <v-container>
    <v-row class="text-center">
      <v-col cols="12">
        <h4 class="m-0">Admin</h4>
        <h2 class="m-0">All Users</h2>
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
          item-title="text"
          item-value="value"
          @update:model-value="onFilterChange"
        ></v-select>
      </v-col>
      <v-col cols="12" md="3">
        <v-text-field
          v-model="filters.email"
          label="Email"
          clearable
          @update:model-value="onTextFilterChange"
        ></v-text-field>
      </v-col>
      <v-col cols="12" md="3">
        <v-text-field
          v-model="filters.userId"
          label="User ID"
          clearable
          @update:model-value="onTextFilterChange"
        ></v-text-field>
      </v-col>
    </v-row>

    <v-row v-if="!initialLoading" style="margin-top: 0px">
      <v-col cols="12">
        <AdminUsersTable
          v-on:emitEditUser="editUser"
          @update:options="onTableOptionsUpdate"
          :propItems="users"
          :totalItems="totalItems"
          :loading="loading"
          :page="tableOptions.page"
          :itemsPerPage="tableOptions.itemsPerPage"
          :sortBy="tableOptions.sortBy"
        />
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
/**
 * Admin page for managing user accounts.
 * Lists all users with server-side pagination, sorting, and filtering
 * by role, email, and user ID. Supports creating and editing users via modal.
 */
import axios from 'axios';
import Loading from '/src/components/global/Loading.vue';
import AdminUsersTable from '/src/components/admin/AdminUsersTable.vue';
import AdminManageUserModal from '/src/components/admin/AdminManageUserModal.vue';
import { useMainStore } from '@/store/store'

export default {
  name: 'PageAdminUsers',

  setup() {
    const store = useMainStore()
    return { store }
  },

  components: {
    Loading,
    AdminUsersTable,
    AdminManageUserModal
  },
  data: () => ({
    intervalFetch: null,
    initialLoading: true,
    loading: false,
    users: [],
    totalItems: 0,
    availableRoles: [],
    selectedItem: undefined,
    dialog: false,
    dialogKey: new Date().getTime(),
    filters: {
      userId: '',
      email: '',
      role: 'All'
    },
    tableOptions: {
      page: 1,
      itemsPerPage: 10,
      sortBy: [{key: 'userId', order: 'desc'}],
    },
    debounceTimer: null,
  }),
  computed: {
    /** Builds role filter dropdown items with user counts per role. */
    roleItems() {
      const items = [{text: `All`, value: 'All'}];
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
    /** Handles pagination/sort changes from the data table. */
    onTableOptionsUpdate(options) {
      this.tableOptions.page = options.page;
      this.tableOptions.itemsPerPage = options.itemsPerPage;
      if (options.sortBy && options.sortBy.length > 0) {
        this.tableOptions.sortBy = options.sortBy;
      }
      this.fetch();
    },
    /** Handles dropdown filter changes (immediate). */
    onFilterChange() {
      this.tableOptions.page = 1;
      this.fetch();
    },
    /** Handles text filter changes with 300ms debounce. */
    onTextFilterChange() {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = setTimeout(() => {
        this.tableOptions.page = 1;
        this.fetch();
      }, 300);
    },
    fetch() {
      let _this = this;
      let currentUser = this.store.user;
      _this.loading = true;

      axios({
        method: "post",
        url: this.$appSettings.APIServer.admin.get_users,
        data: {
          page: _this.tableOptions.page,
          itemsPerPage: _this.tableOptions.itemsPerPage,
          sortBy: _this.tableOptions.sortBy,
          filters: {
            role: _this.filters.role === 'All' ? '' : (_this.filters.role || ''),
            email: _this.filters.email || '',
            userId: _this.filters.userId || '',
          }
        },
        headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
      })
      .then(function (response) {
        if (response.data.status == true) {
          _this.users = response.data.data.users;
          _this.totalItems = response.data.data.totalItems;
          _this.availableRoles = response.data.data.availableRoles || [];
        } else {
          console.log("Failed getting users...");
          _this.store.showMessage({ text: "There was an error getting users.", color: "red" });
        }
        _this.loading = false;
        _this.initialLoading = false;
      })
      .catch(function (error) {
        if (error.response && (error.response.status == 400 || error.response.status == 401)) {
          _this.store.showMessage({ text: error.response.data.detail, color: "red" });
        }
        else {
          console.log(error);
          _this.store.showMessage({ text: "Unknown error while trying to get users.", color: "red" });
        }
        _this.loading = false;
        _this.initialLoading = false;
      });
    },
  },
  beforeUnmount() {
    clearInterval(this.intervalFetch);
    clearTimeout(this.debounceTimer);
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
