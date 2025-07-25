<template>
  <v-container>
    <v-row class="text-center">
      <v-col cols="12">
        <h4>Admin</h4>
        <h2>All Roles</h2>
      </v-col>
    </v-row>

    <v-row class="text-center">
      <v-col cols="12">
        <v-btn color="green" @click="createNewRole">Create New Role</v-btn>
      </v-col>
    </v-row>

    <v-row v-if="!isFetching">
      <v-col cols="12">
        <div v-if="roles && roles.length > 0" style="margin-top: 50px">
          <AdminRolesTable 
            v-on:emitEditRole="editRole" 
            v-on:emitRemoveRole="removeRole" 
            v-on:emitManageMounts="manageMounts" 
            v-on:emitManageHardwareLimits="manageHardwareLimits"
            v-bind:propItems="roles" />
        </div>
        <p v-else class="dim text-center">No roles.</p>
      </v-col>
    </v-row>
    <v-row v-else>
      <v-col cols="12">
        <Loading class="loading" />
      </v-col>
    </v-row>

    <AdminManageRoleModal 
      v-if="showRoleModal" 
      :propData="selectedItem"
      :key="dialogKey"
      @emitModalClose="closeDialog"
    />

    <!-- Add the mounts modal -->
    <AdminRoleMountsModal 
      v-if="selectedMountsRole"
      :roleId="selectedMountsRole.roleId"
      :roleName="selectedMountsRole.name"
      @emitModalClose="closeMountsDialog">
    </AdminRoleMountsModal>

    <!-- Add the hardware limits modal -->
    <AdminRoleHardwareLimitsModal 
      v-if="selectedHardwareLimitsRole"
      :roleId="selectedHardwareLimitsRole.roleId"
      :roleName="selectedHardwareLimitsRole.name"
      @emitModalClose="closeHardwareLimitsDialog">
    </AdminRoleHardwareLimitsModal>
  </v-container>
</template>

<script>
import Loading from '/src/components/global/Loading.vue';
import AdminRolesTable from '/src/components/admin/AdminRolesTable.vue';
import AdminManageRoleModal from '/src/components/admin/AdminManageRoleModal.vue';
import AdminRoleMountsModal from '/src/components/admin/AdminRoleMountsModal.vue';
import AdminRoleHardwareLimitsModal from '/src/components/admin/AdminRoleHardwareLimitsModal.vue';

// Add axios back
const axios = require('axios').default;

export default {
  name: 'PageAdminRoles',
  components: {
    Loading,
    AdminRolesTable,
    AdminManageRoleModal,
    AdminRoleMountsModal,
    AdminRoleHardwareLimitsModal
  },
  data: () => ({
    intervalFetch: null,
    isFetching: false,
    roles: [],
    selectedItem: undefined,
    selectedMountsRole: null,
    selectedHardwareLimitsRole: null,
    showRoleModal: false,
    dialogKey: new Date().getTime(),
    tableName: "roles",
  }),
  mounted () {
    this.isFetching = true;
    this.fetch();

    // Keep updating data every 30 seconds
    this.intervalFetch = setInterval(() => { this.fetch()}, 30000);
  },
  methods: {
    createNewRole() {
      this.selectedItem = null;
      this.showRoleModal = true;
      this.dialogKey++;
    },
    editRole(roleId) {
      // Find the role data from our roles array
      this.selectedItem = this.roles.find(role => role.roleId === roleId);
      this.showRoleModal = true;
      this.dialogKey++; // Force modal refresh
    },
    async removeRole(roleId) {
      const role = this.roles.find(r => r.roleId === roleId);
      if (role.name === "admin" || role.name === "everyone") {
        this.$store.commit('showMessage', { 
          text: "Cannot remove built-in roles", 
          color: "error" 
        });
        return;
      }

      const confirm = window.confirm("Do you really want to remove this role? This action cannot be undone.");
      if (!confirm) return;

      try {
        const currentUser = this.$store.getters.user;
        const response = await axios({
          method: "post",
          url: this.AppSettings.APIServer.admin.remove_role,
          params: { roleId },
          headers: {"Authorization": `Bearer ${currentUser.loginToken}`}
        });

        if (response.data.status) {
          this.$store.commit('showMessage', { 
            text: "Role removed successfully", 
            color: "success" 
          });
          await this.fetch(); // Make sure to await the fetch
        } else {
          this.$store.commit('showMessage', { 
            text: response.data.message, 
            color: "error" 
          });
        }
      } catch (error) {
        console.error(error);
        this.$store.commit('showMessage', { 
          text: "Error removing role", 
          color: "error" 
        });
      }
    },
    closeDialog() {
      this.showRoleModal = false;
      this.selectedItem = undefined;
      this.fetch(); // Always fetch when closing the modal
    },
    async fetch() {
      try {
        const currentUser = this.$store.getters.user;
        const response = await axios({
          method: "get",
          url: this.AppSettings.APIServer.admin.get_roles,
          headers: {"Authorization": `Bearer ${currentUser.loginToken}`}
        });

        if (response.data.status) {
          this.roles = response.data.data.roles;
        } else {
          this.$store.commit('showMessage', { 
            text: "Failed to fetch roles", 
            color: "error" 
          });
        }
      } catch (error) {
        console.error(error);
        this.$store.commit('showMessage', { 
          text: "Error fetching roles", 
          color: "error" 
        });
      } finally {
        this.isFetching = false;
      }
    },
    manageMounts(role) {
      this.selectedMountsRole = role;
    },
    closeMountsDialog(shouldRefresh) {
      this.selectedMountsRole = null;
      if (shouldRefresh) {
        this.fetch();
      }
    },
    manageHardwareLimits(role) {
      this.selectedHardwareLimitsRole = role;
    },
    closeHardwareLimitsDialog(shouldRefresh) {
      this.selectedHardwareLimitsRole = null;
      if (shouldRefresh) {
        this.fetch();
      }
    }
  },
  beforeDestroy() {
    if (this.intervalFetch) {
      clearInterval(this.intervalFetch);
    }
  },
}
</script>

<style scoped lang="scss">
.loading {
  margin: 60px auto;
}
</style> 