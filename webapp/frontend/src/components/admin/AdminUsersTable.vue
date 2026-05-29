<template>
  <div>
    <v-data-table-server
      :headers="table.headers"
      :items="propItems"
      :items-length="totalItems"
      :loading="loading"
      :sort-by="sortBy"
      :items-per-page="itemsPerPage"
      :items-per-page-options="[10, 25, 50]"
      :page="page"
      @update:options="onOptionsUpdate"
      class="elevation-1">

      <!-- Actions -->
      <template v-slot:item.actions="{item}">
        <v-menu>
          <template v-slot:activator="{ props }">
            <a v-bind="props">
              Actions <v-icon size="small">mdi-chevron-down</v-icon>
            </a>
          </template>
          <v-list density="compact">
            <v-list-item @click="emitEditUser(item.userId)">
              <template v-slot:prepend><v-icon size="small">mdi-pencil-outline</v-icon></template>
              <v-list-item-title>Edit User</v-list-item-title>
            </v-list-item>
            <v-list-item @click="emitAnonymizeUser(item.userId, item.email)">
              <template v-slot:prepend><v-icon size="small" color="red">mdi-account-remove</v-icon></template>
              <v-list-item-title>Remove User (Anonymize)</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </template>

      <!-- Created -->
      <template v-slot:item.createdAt="{item}">
        <v-tooltip v-if="item.createdAt" location="bottom" :text="parseTime(item.createdAt)">
          <template v-slot:activator="{ props }">
            <span v-bind="props">{{ parseRelativeTime(item.createdAt) }}</span>
          </template>
        </v-tooltip>
        <span v-else>-</span>
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

      <!-- User ID with online indicator -->
      <template v-slot:item.userId="{item}">
        <v-tooltip :text="isOnline(item) ? 'Online' : 'Offline'" location="bottom">
          <template v-slot:activator="{ props }">
            <v-icon v-bind="props" :color="isOnline(item) ? 'green' : 'grey'" size="x-small" style="vertical-align: middle; margin-right: 4px;">mdi-circle</v-icon>
          </template>
        </v-tooltip>
        {{ item.userId }}
      </template>

      <!-- Last Seen -->
      <template v-slot:item.lastSeenAt="{item}">
        <v-tooltip v-if="item.lastSeenAt" location="bottom" :text="parseTime(item.lastSeenAt)">
          <template v-slot:activator="{ props }">
            <span v-bind="props">{{ parseRelativeTime(item.lastSeenAt) }}</span>
          </template>
        </v-tooltip>
        <span v-else>Never</span>
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
import { DisplayTime, RelativeTime } from '/src/helpers/time.js'

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
    propOnlineThresholdMinutes: {
      type: Number,
      default: 2,
    },
  },
  data: () => ({
    table: {
      headers: [
        { title: 'User ID', key: 'userId' },
        { title: 'Name', key: 'name' },
        { title: 'Email', key: 'email' },
        { title: 'Roles', key: 'roles', sortable: false },
        { title: 'Password Set', key: 'hasPassword' },
        { title: 'Created', key: 'createdAt' },
        { title: 'Last Seen', key: 'lastSeenAt' },
        { title: '', key: 'actions', sortable: false },
      ],
    }
  }),
  methods: {
    emitEditUser(userId) {
      this.$emit('emitEditUser', userId)
    },
    emitAnonymizeUser(userId, email) {
      this.$emit('emitAnonymizeUser', { userId, email })
    },
    parseTime(timestamp) {
      if (!timestamp) return '-';
      return DisplayTime(timestamp);
    },
    parseRelativeTime(timestamp) {
      if (!timestamp) return '-'
      return RelativeTime(timestamp)
    },
    onOptionsUpdate(options) {
      this.$emit('update:options', options)
    },
    isOnline(item) {
      if (!item.lastSeenAt) return false
      const ts = item.lastSeenAt.endsWith('Z') || item.lastSeenAt.includes('+') ? item.lastSeenAt : item.lastSeenAt + 'Z'
      return (Date.now() - new Date(ts).getTime()) < this.propOnlineThresholdMinutes * 60 * 1000
    },
  },
}
</script>

