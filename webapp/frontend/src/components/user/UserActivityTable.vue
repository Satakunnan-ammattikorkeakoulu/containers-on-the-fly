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

      <!-- Time (relative, with full time in tooltip) -->
      <template v-slot:item.createdAt="{item}">
        <v-tooltip v-if="item.createdAt" location="bottom" :text="parseTime(item.createdAt)">
          <template v-slot:activator="{ props }">
            <span v-bind="props" class="link-hint">{{ parseRelativeTime(item.createdAt) }}</span>
          </template>
        </v-tooltip>
        <span v-else>-</span>
      </template>

      <!-- Action (human-readable label derived from action + details) -->
      <template v-slot:item.action="{item}">
        <v-chip
          v-if="isNew(item)"
          color="info"
          size="x-small"
          variant="flat"
          class="new-chip"
        >NEW</v-chip>
        <v-chip :color="getActionColor(item.action, item.details)" size="small" variant="tonal">
          {{ formatActionLabel(item.action, item.details) }}
        </v-chip>
      </template>

      <!-- Reservation (with hover tooltip showing resources) -->
      <template v-slot:item.resourceId="{item}">
        <template v-if="item.resourceId">
          <v-tooltip v-if="getSummary(item.resourceId)" location="bottom">
            <template v-slot:activator="{ props }">
              <span v-bind="props" class="link-hint">#{{ item.resourceId }}</span>
            </template>
            <div class="reservation-summary-tooltip">
              <div><strong>Server:</strong> {{ getSummary(item.resourceId).computerName || '-' }}</div>
              <div><strong>Resources:</strong> {{ formatResources(getSummary(item.resourceId).hardwareSpecs) }}</div>
              <div><strong>SHM Size:</strong> {{ getSummary(item.resourceId).shmSizePercent != null ? getSummary(item.resourceId).shmSizePercent : 50 }}% of RAM</div>
              <div v-if="getSummary(item.resourceId).ramDiskSizePercent && getSummary(item.resourceId).ramDiskSizePercent > 0">
                <strong>RAM Disk:</strong> {{ getSummary(item.resourceId).ramDiskSizePercent }}% of RAM
              </div>
              <div v-if="getSummary(item.resourceId).isLowPriority" style="color: #ff9800; font-weight: 500;">Low-Priority</div>
              <div v-if="getSummary(item.resourceId).imageName"><strong>Container:</strong> {{ getSummary(item.resourceId).imageName }}</div>
              <div v-if="getSummary(item.resourceId).ports && getSummary(item.resourceId).ports.length > 0">
                <strong>Ports:</strong>
                <div v-for="(port, idx) in getSummary(item.resourceId).ports" :key="idx">
                  {{ port.localPort }} → {{ port.outsidePort }} ({{ port.serviceName }})
                </div>
              </div>
            </div>
          </v-tooltip>
          <span v-else>#{{ item.resourceId }}</span>
        </template>
        <span v-else class="text-grey">-</span>
      </template>

      <!-- Details (raw whitelisted JSON) -->
      <template v-slot:item.details="{item}">
        <span v-if="hasDetails(item.details)" class="details-json">
          {{ formatDetailsJson(item.details) }}
        </span>
        <span v-else class="text-grey">-</span>
      </template>
    </v-data-table-server>
  </div>
</template>

<script>
/**
 * Server-side paginated data table of the user's own reservation activity.
 * Shows time, a human-readable action label, and the reservation ID.
 * Consumes rows returned by /api/reservation/get_own_activity.
 */
import { DisplayTime, RelativeTime } from '/src/helpers/time.js'
import { getActionColor, formatActionLabel } from '/src/helpers/auditLog.js'

export default {
  name: 'UserActivityTable',
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
    propReservationSummaries: {
      type: Object,
      default: () => ({}),
    },
    propLastSeenAt: {
      type: String,
      default: null,
    },
    propNotableActions: {
      type: Array,
      default: () => [],
    },
  },
  data: () => ({
    table: {
      headers: [
        { title: 'Time', key: 'createdAt' },
        { title: 'Action', key: 'action', sortable: true },
        { title: 'Reservation', key: 'resourceId', sortable: false },
        { title: 'Details', key: 'details', sortable: false },
      ],
    }
  }),
  methods: {
    getActionColor,
    formatActionLabel,
    parseTime(timestamp) {
      try {
        if (!timestamp) return '-';
        return DisplayTime(timestamp);
      } catch {
        return '-';
      }
    },
    parseRelativeTime(timestamp) {
      try {
        if (!timestamp) return '-';
        return RelativeTime(timestamp);
      } catch {
        return '-';
      }
    },
    onOptionsUpdate(options) {
      this.$emit('update:options', options)
    },
    hasDetails(details) {
      return !!details && typeof details === 'object' && Object.keys(details).length > 0;
    },
    /** Look up a reservation summary, tolerating missing entries. */
    getSummary(reservationId) {
      try {
        if (!reservationId) return null;
        const key = String(reservationId);
        const summaries = this.propReservationSummaries || {};
        return summaries[key] || null;
      } catch {
        return null;
      }
    },
    /**
     * Decide whether a row should render a "NEW" chip. A row is new when
     * (a) its createdAt is strictly later than the snapshot the frontend
     * captured at activity-view open time, AND (b) its action is in the
     * notable-actions allowlist (so user-initiated routine events like
     * create/extend/restart never render NEW even if they are recent).
     *
     * Falls back to false on any parse failure, missing snapshot, missing
     * allowlist, or unrecognized action.
     */
    isNew(item) {
      try {
        if (!item || !item.createdAt || !this.propLastSeenAt) return false;
        if (!Array.isArray(this.propNotableActions) || this.propNotableActions.length === 0) return false;
        if (!this.propNotableActions.includes(item.action)) return false;
        const rowTs = Date.parse(item.createdAt);
        const seenTs = Date.parse(this.propLastSeenAt);
        if (!Number.isFinite(rowTs) || !Number.isFinite(seenTs)) return false;
        return rowTs > seenTs;
      } catch {
        return false;
      }
    },
    /** Render hardware specs list into "4 GB, 8 CPUs" style text. */
    formatResources(specs) {
      try {
        if (!Array.isArray(specs) || specs.length === 0) return '-';
        return specs
          .filter(s => s && Number.isFinite(Number(s.amount)) && Number(s.amount) > 0)
          .map(s => `${s.amount} ${s.format || ''}`.trim())
          .join(', ') || '-';
      } catch {
        return '-';
      }
    },
    /** Render the details dict as compact single-line JSON with safe fallback. */
    formatDetailsJson(details) {
      try {
        if (!this.hasDetails(details)) return '-';
        return JSON.stringify(details);
      } catch {
        return '-';
      }
    },
  },
}
</script>

<style scoped lang="scss">
.details-json {
  font-family: monospace;
  font-size: 12px;
  opacity: 0.75;
  word-break: break-all;
}

.reservation-summary-tooltip {
  max-width: 300px;
}

.new-chip {
  margin-right: 6px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
</style>
