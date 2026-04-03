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

      <!-- Time (relative, with full time tooltip) -->
      <template v-slot:item.createdAt="{item}">
        <v-tooltip v-if="item.createdAt" location="bottom" :text="parseTime(item.createdAt)">
          <template v-slot:activator="{ props }">
            <span v-bind="props">{{ parseRelativeTime(item.createdAt) }}</span>
          </template>
        </v-tooltip>
        <span v-else>-</span>
      </template>

      <!-- User (clickable to filter) -->
      <template v-slot:item.userEmail="{item}">
        <v-tooltip v-if="item.userEmail" location="bottom" text="Click to filter by this user">
          <template v-slot:activator="{ props }">
            <span v-bind="props" class="filterable" @click="emitFilter('user', item.userEmail)">
              {{ item.userEmail }}
              <span v-if="item.userName" class="text-grey"> ({{ item.userName }})</span>
            </span>
          </template>
        </v-tooltip>
        <span v-else class="text-grey">-</span>
      </template>

      <!-- Resource Type (clickable to filter) -->
      <template v-slot:item.resourceType="{item}">
        <v-tooltip v-if="item.resourceType" location="bottom" text="Click to filter by this resource type">
          <template v-slot:activator="{ props }">
            <span v-bind="props" class="filterable d-inline-flex align-center" style="gap: 6px;" @click="emitFilter('resourceType', item.resourceType)">
              <v-icon size="small">{{ getResourceTypeIcon(item.resourceType) }}</v-icon>
              {{ item.resourceType }}
            </span>
          </template>
        </v-tooltip>
        <span v-else class="text-grey">-</span>
      </template>

      <!-- Action (clickable to filter) -->
      <template v-slot:item.action="{item}">
        <v-tooltip location="bottom" text="Click to filter by this action">
          <template v-slot:activator="{ props }">
            <v-chip v-bind="props" :color="getActionColor(item.action)" size="small" variant="tonal" class="filterable" @click="emitFilter('action', item.action)">
              {{ item.action }}
            </v-chip>
          </template>
        </v-tooltip>
      </template>

      <!-- IP Address (clickable to filter) -->
      <template v-slot:item.ipAddress="{item}">
        <v-tooltip v-if="item.ipAddress" location="bottom" text="Click to filter by this IP">
          <template v-slot:activator="{ props }">
            <span v-bind="props" class="filterable" @click="emitFilter('ipAddress', item.ipAddress)">
              {{ item.ipAddress }}
            </span>
          </template>
        </v-tooltip>
        <span v-else class="text-grey">-</span>
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
    </v-data-table-server>
  </div>
</template>

<script>
/**
 * Server-side paginated data table of audit log entries.
 * Shows timestamp, user, action, resource type, IP, and details.
 * Clickable cells on user, resource type, action, and IP emit a filterBy
 * event so the parent page can apply the filter automatically.
 */
import { DisplayTime, RelativeTime } from '/src/helpers/time.js'
import { getActionColor } from '/src/helpers/auditLog.js'

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
        { title: 'Resource', key: 'resourceType', sortable: true },
        { title: 'Action', key: 'action', sortable: true },
        { title: 'IP', key: 'ipAddress', sortable: false },
        { title: 'Details', key: 'details', sortable: false },
      ],
    }
  }),
  methods: {
    parseTime(timestamp) {
      if (!timestamp) return '-';
      return DisplayTime(timestamp);
    },
    parseRelativeTime(timestamp) {
      if (!timestamp) return '-';
      return RelativeTime(timestamp);
    },
    onOptionsUpdate(options) {
      this.$emit('update:options', options)
    },
    emitFilter(key, value) {
      this.$emit('filterBy', { key, value })
    },
    getActionColor,
    getResourceTypeIcon(resourceType) {
      const icons = {
        reservation: 'mdi-calendar-clock',
        user: 'mdi-account',
        role: 'mdi-shield-account',
        container: 'mdi-cube-outline',
        computer: 'mdi-server',
        settings: 'mdi-cog',
      };
      return icons[resourceType] || 'mdi-help-circle-outline';
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
.filterable {
  cursor: pointer;
  text-decoration: underline;
  text-decoration-style: dotted;
  text-underline-offset: 3px;
  &:hover {
    text-decoration-style: solid;
  }
}

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
