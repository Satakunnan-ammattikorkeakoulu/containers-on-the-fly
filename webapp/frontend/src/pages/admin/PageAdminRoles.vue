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
        <v-btn color="green" @click="addRole">Create New Role</v-btn>
      </v-col>
    </v-row>

    <v-row v-if="!isFetching">
      <v-col cols="12">
        <div v-if="roles && roles.length > 0" style="margin-top: 50px">
          <AdminRolesTable v-on:emitEditRole="editRole" v-on:emitRemoveRole="removeRole" v-bind:propItems="roles" />
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
      @click.stop="dialog = true" 
      v-if="selectedItem" 
      v-on:emitModalClose="closeDialog" 
      :propData="selectedItem" 
      :key="dialogKey">
    </AdminManageRoleModal>
  </v-container>
</template>

<script>
import Loading from '/src/components/global/Loading.vue';
import AdminRolesTable from '/src/components/admin/AdminRolesTable.vue';
import AdminManageRoleModal from '/src/components/admin/AdminManageRoleModal.vue';

export default {
  name: 'PageAdminRoles',
  components: {
    Loading,
    AdminRolesTable,
    AdminManageRoleModal
  },
  data: () => ({
    intervalFetch: null,
    isFetching: false,
    roles: [],
    selectedItem: undefined,
    dialog: false,
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
    addRole() {
      this.selectedItem = "new";
      this.dialogKey = new Date().getTime();
      this.dialog = true;
    },
    editRole(roleId) {
      this.dialogKey = new Date().getTime();
      this.selectedItem = roleId;
      this.dialog = true;
    },
    removeRole(roleId) {
      // Don't allow removing built-in roles (everyone and admin)
      if (roleId === 0 || roleId === 1) {
        this.$store.commit('showMessage', { text: "Cannot remove built-in roles.", color: "error" });
        return;
      }
      let result = window.confirm("Do you really want to remove this role? This action cannot be undone.");
      if (!result) return;
      // TODO: Add backend call to remove role
    },
    closeDialog() {
      this.dialog = false;
      this.selectedItem = undefined;
      this.fetch();
    },
    fetch() {
      // TODO: Add backend call to fetch roles
      // For now, using mock data with built-in roles
      this.roles = [
        {
          roleId: 0,
          name: "Everyone",
          createdAt: new Date().toISOString()
        },
        {
          roleId: 1,
          name: "Admin",
          createdAt: new Date().toISOString()
        }
      ];
      this.isFetching = false;
    }
  },
  beforeDestroy() {
    clearInterval(this.intervalFetch);
  },
}
</script>

<style scoped lang="scss">
.loading {
  margin: 60px auto;
}
</style> 