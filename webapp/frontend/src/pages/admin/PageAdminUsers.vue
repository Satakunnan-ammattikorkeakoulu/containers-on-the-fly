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
        <br>
        <a v-if="!showFilters" class="show-filters-link" style="margin-top: 12px; margin-bottom: 24px; display: inline-block;" @click="showFilters = true">Show Filters</a>
      </v-col>
    </v-row>

    <!-- Filters row 1 -->
    <v-row v-if="showFilters" class="text-center row-filters justify-center">
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
          v-model="filters.name"
          label="Name"
          clearable
          @update:model-value="onTextFilterChange"
        ></v-text-field>
      </v-col>
    </v-row>

    <!-- Filters row 2 -->
    <v-row v-if="showFilters" class="text-center row-filters-second justify-center">
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
          v-on:emitAnonymizeUser="anonymizeUser"
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

    <!-- Remove User Confirmation Dialog -->
    <v-dialog v-model="anonymizeDialog.show" max-width="550px">
      <v-card class="pa-4">
        <v-card-title>Remove User</v-card-title>
        <v-card-text>
          <p class="mb-3">Are you sure you want to remove <strong>{{ anonymizeDialog.email }}</strong>{{ anonymizeDialog.name ? ` (${anonymizeDialog.name})` : '' }}?</p>

          <v-alert v-if="anonymizeDialog.isAdmin" type="error" variant="tonal" density="compact" class="mb-3">
            This user has the <strong>admin</strong> role. Proceed with caution.
          </v-alert>

          <v-alert v-if="anonymizeDialog.activeReservations > 0" type="warning" variant="tonal" density="compact" class="mb-3">
            There {{ anonymizeDialog.activeReservations === 1 ? 'is' : 'are' }} <strong>{{ anonymizeDialog.activeReservations }}</strong> active reservation{{ anonymizeDialog.activeReservations !== 1 ? 's' : '' }} for this user.
            Active reservations will continue until they end, but descriptions will be cleared.
          </v-alert>

          <p class="mb-2">
            The user will be soft-deleted from the system. An anonymized record of the user will be kept
            so that existing reservations and other references remain intact, but all personal data will
            be permanently removed. The user will no longer appear in the user listing and will not be
            able to log in.
          </p>

          <p class="mb-2">The following data will be cleared:</p>
          <ul class="mb-3" style="padding-left: 20px;">
            <li>Email, name, password, and SSH keys</li>
            <li>Reservation descriptions</li>
            <li>Audit log IP addresses and details</li>
            <li>Role assignments</li>
          </ul>

          <p class="mb-3"><strong>Note:</strong> Files stored in the user's mounts (if any) are <strong>not</strong> automatically removed and must be deleted manually.</p>

          <p class="text-muted mb-6">This action cannot be undone.</p>

          <v-text-field
            v-model="anonymizeDialog.confirmEmail"
            :label="`Type '${anonymizeDialog.email}' to confirm`"
            density="compact"
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="anonymizeDialog.show = false">Cancel</v-btn>
          <v-btn color="red" variant="text" @click="confirmAnonymizeUser" :disabled="anonymizeDialog.confirmEmail !== anonymizeDialog.email">Remove</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
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
    showFilters: false,
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
      name: '',
      email: '',
      role: 'All'
    },
    tableOptions: {
      page: 1,
      itemsPerPage: 10,
      sortBy: [{key: 'userId', order: 'desc'}],
    },
    debounceTimer: null,
    anonymizeDialog: {
      show: false,
      userId: null,
      email: '',
      name: '',
      activeReservations: 0,
      auditLogEntries: 0,
      isAdmin: false,
      confirmEmail: '',
    },
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
    /** Fetch anonymization info and show the confirmation dialog. */
    anonymizeUser({ userId, email }) {
      let _this = this;
      let currentUser = this.store.user;
      axios({
        method: "get",
        url: this.$appSettings.APIServer.admin.user_anonymize_info,
        params: { userId },
        headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
      })
      .then(function (response) {
        if (response.data.status == true) {
          const info = response.data.data;
          _this.anonymizeDialog = {
            show: true,
            userId: userId,
            email: info.email,
            name: info.name,
            activeReservations: info.activeReservations,
            auditLogEntries: info.auditLogEntries,
            isAdmin: info.isAdmin,
            confirmEmail: '',
          };
        } else {
          _this.store.showMessage({ text: response.data.message, color: "red" });
        }
      })
      .catch(function (error) {
        console.log(error);
        _this.store.showMessage({ text: "Error fetching anonymization info.", color: "red" });
      });
    },
    /** Confirm and execute user anonymization. */
    confirmAnonymizeUser() {
      let _this = this;
      let currentUser = this.store.user;
      axios({
        method: "post",
        url: this.$appSettings.APIServer.admin.anonymize_user,
        params: { userId: _this.anonymizeDialog.userId },
        headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
      })
      .then(function (response) {
        if (response.data.status == true) {
          _this.store.showMessage({ text: "User removed and data anonymized successfully.", color: "green" });
          _this.anonymizeDialog.show = false;
          _this.fetch();
        } else {
          _this.store.showMessage({ text: response.data.message, color: "red" });
        }
      })
      .catch(function (error) {
        console.log(error);
        _this.store.showMessage({ text: "Error anonymizing user.", color: "red" });
      });
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
            name: _this.filters.name || '',
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

.show-filters-link {
  font-size: 14px;
  cursor: pointer;
  color: #42A5F5;
  text-decoration: none;
  &:hover {
    text-decoration: underline;
  }
}

.row-filters {
  margin-top: 30px;
  margin-bottom: 0px;
}

.row-filters-second {
  margin-top: 0px;
  margin-bottom: 0px;
}
</style>
