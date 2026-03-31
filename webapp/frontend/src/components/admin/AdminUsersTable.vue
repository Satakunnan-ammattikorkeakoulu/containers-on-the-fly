<template>
  <div>
    <v-data-table-server
      :headers="table.headers"
      :items="propItems"
      :items-length="totalItems"
      :loading="loading"
      :sort-by="sortBy"
      :items-per-page="itemsPerPage"
      :page="page"
      @update:options="onOptionsUpdate"
      class="elevation-1">

      <!-- Actions -->
      <template v-slot:item.actions="{item}">
        <v-menu>
          <template v-slot:activator="{ props }">
            <a class="actions-link" v-bind="props">
              Actions <v-icon size="small">mdi-chevron-down</v-icon>
            </a>
          </template>
          <v-list density="compact">
            <v-list-item @click="emitEditUser(item.userId)">
              <template v-slot:prepend><v-icon size="small">mdi-pencil-outline</v-icon></template>
              <v-list-item-title>Edit User</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </template>

      <!-- Created At -->
      <template v-slot:item.createdAt="{item}">
        {{ item.createdAt ? parseTime(item.createdAt) : '-' }}
      </template>

      <!-- Roles -->
      <template v-slot:item.roles="{item}">
        {{ Array.isArray(item.roles) ? item.roles.join(', ') : item.roles }}
      </template>

      <!-- Password Set -->
      <template v-slot:item.hasPassword="{item}">
        <v-icon v-if="item.hasPassword" color="green">mdi-check</v-icon>
        <v-icon v-else color="red">mdi-close</v-icon>
      </template>
    </v-data-table-server>
  </div>
</template>

<script>
/**
 * Server-side paginated data table of all users in the system.
 * Shows user ID, email, assigned roles, password status, and creation date.
 * Emits pagination/sort changes to the parent via @update:options.
 * Used in PageAdminUsers.
 */
import { DisplayTime } from '/src/helpers/time.js'

export default {
  name: 'AdminUsersTable',
  props: {
    propItems: {
      type: Array,
      required: true,
    },
    totalItems: {
      type: Number,
      default: 0,
    },
    loading: {
      type: Boolean,
      default: false,
    },
    page: {
      type: Number,
      default: 1,
    },
    itemsPerPage: {
      type: Number,
      default: 10,
    },
    sortBy: {
      type: Array,
      default: () => [{key: 'userId', order: 'desc'}],
    },
  },
  data: () => ({
    table: {
      headers: [
        { title: 'User ID', key: 'userId' },
        { title: 'Email', key: 'email' },
        { title: 'Roles', key: 'roles', sortable: false },
        { title: 'Password Set', key: 'hasPassword' },
        { title: 'Created At', key: 'createdAt' },
        { title: '', key: 'actions', sortable: false },
      ],
    }
  }),
  methods: {
    emitEditUser(userId) {
      this.$emit('emitEditUser', userId)
    },
    parseTime(timestamp) {
      if (!timestamp) return '-';
      return DisplayTime(timestamp);
    },
    onOptionsUpdate(options) {
      this.$emit('update:options', options)
    },
  },
}
</script>

<style scoped lang="scss">
.actions-link {
  color: #2196f3;
  cursor: pointer;
  text-decoration: none;
  white-space: nowrap;
  &:hover {
    text-decoration: underline;
  }
}
</style>
