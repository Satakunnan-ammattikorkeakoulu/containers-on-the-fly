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

      <!-- Time -->
      <template v-slot:item.createdAt="{item}">
        {{ item.createdAt ? parseTime(item.createdAt) : '-' }}
      </template>

      <!-- User -->
      <template v-slot:item.userEmail="{item}">
        <span v-if="item.userEmail">
          {{ item.userEmail }}
          <span v-if="item.userName" class="text-grey"> ({{ item.userName }})</span>
        </span>
        <span v-else class="text-grey">-</span>
      </template>

      <!-- Action -->
      <template v-slot:item.action="{item}">
        <v-chip :color="getActionColor(item.action)" size="small" variant="tonal">
          {{ item.action }}
        </v-chip>
      </template>

      <!-- Resource Type -->
      <template v-slot:item.resourceType="{item}">
        {{ item.resourceType || '-' }}
      </template>

      <!-- Resource ID -->
      <template v-slot:item.resourceId="{item}">
        {{ item.resourceId != null ? item.resourceId : '-' }}
      </template>

      <!-- Details -->
      <template v-slot:item.details="{item}">
        <v-tooltip v-if="item.details" location="bottom">
          <template v-slot:activator="{ props }">
            <span v-bind="props" class="details-text">{{ formatDetailsShort(item.details) }}</span>
          </template>
          <pre class="details-tooltip">{{ formatDetailsFull(item.details) }}</pre>
        </v-tooltip>
        <span v-else class="text-grey">-</span>
      </template>

      <!-- IP Address -->
      <template v-slot:item.ipAddress="{item}">
        {{ item.ipAddress || '-' }}
      </template>
    </v-data-table-server>
  </div>
</template>

<script>
/**
 * Server-side paginated data table of audit log entries.
 * Shows timestamp, user, action, resource type/ID, details, and IP address.
 * Emits pagination/sort changes to the parent via @update:options.
 */
import { DisplayTime } from '/src/helpers/time.js'

export default {
  name: 'AdminAuditLogTable',
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
      default: () => [{key: 'createdAt', order: 'desc'}],
    },
  },
  data: () => ({
    table: {
      headers: [
        { title: 'Time', key: 'createdAt' },
        { title: 'User', key: 'userEmail', sortable: true },
        { title: 'Action', key: 'action', sortable: true },
        { title: 'Resource', key: 'resourceType', sortable: true },
        { title: 'Resource ID', key: 'resourceId', sortable: false },
        { title: 'Details', key: 'details', sortable: false },
        { title: 'IP', key: 'ipAddress', sortable: false },
      ],
    }
  }),
  methods: {
    parseTime(timestamp) {
      if (!timestamp) return '-';
      return DisplayTime(timestamp);
    },
    onOptionsUpdate(options) {
      this.$emit('update:options', options)
    },
    getActionColor(action) {
      if (!action) return 'grey';
      if (action.startsWith('LOGIN_FAILED')) return 'red';
      if (action.startsWith('LOGIN')) return 'blue';
      if (action.startsWith('RESERVATION')) return 'green';
      if (action.startsWith('USER')) return 'orange';
      if (action.startsWith('ROLE')) return 'purple';
      if (action.startsWith('CONTAINER')) return 'teal';
      if (action.startsWith('COMPUTER')) return 'indigo';
      if (action.startsWith('SETTINGS')) return 'grey';
      return 'grey';
    },
    formatDetailsShort(details) {
      if (!details) return '-';
      if (typeof details === 'string') return details.substring(0, 50);
      const keys = Object.keys(details);
      if (keys.length === 0) return '-';
      const parts = keys.slice(0, 2).map(k => `${k}: ${details[k]}`);
      const text = parts.join(', ');
      return text.length > 50 ? text.substring(0, 47) + '...' : text;
    },
    formatDetailsFull(details) {
      if (!details) return '-';
      if (typeof details === 'string') return details;
      return JSON.stringify(details, null, 2);
    },
  },
}
</script>

<style scoped lang="scss">
.details-text {
  cursor: help;
  max-width: 200px;
  display: inline-block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.details-tooltip {
  max-width: 400px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
}
</style>
