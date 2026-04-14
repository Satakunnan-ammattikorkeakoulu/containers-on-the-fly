<template>
  <v-container>
    <v-row class="text-center">
      <v-col cols="12">
        <h4 class="m-0">Admin</h4>
        <h2 class="m-0">Audit Log</h2>
        <p class="audit-log-description">
          Records of all significant user and admin actions in the system.
          The current retention is <strong>{{ retentionDays === -1 ? 'disabled' : (retentionDays > 0 ? retentionDays + ' days' : 'forever') }}</strong>
          <a style="margin-left: 4px;" @click="showRetentionEditor = !showRetentionEditor">{{ showRetentionEditor ? '(hide)' : '(change)' }}</a>
        </p>
      </v-col>
    </v-row>

    <!-- Retention Setting (toggled) -->
    <v-row v-if="showRetentionEditor" class="justify-center">
      <v-col cols="12" md="6" class="d-flex flex-column align-center" style="gap: 8px;">
        <div class="d-flex align-center" style="gap: 12px;">
          <v-text-field
            v-model.number="retentionDays"
            label="Retention (days, 0 = forever, -1 = disabled)"
            type="number"
            density="compact"
            hide-details
            style="min-width: 350px"
          ></v-text-field>
          <v-btn color="primary" size="small" @click="confirmSaveRetention" :loading="savingRetention">Save</v-btn>
        </div>
        <span style="font-size: 14px; opacity: 0.5;">
          Entries older than the retention period are automatically removed when new events are logged. Set to -1 to disable audit logging entirely.
        </span>
      </v-col>
    </v-row>

    <!-- Retention confirmation dialog -->
    <v-dialog v-model="showRetentionDialog" max-width="460">
      <v-card>
        <v-card-title>Change retention period?</v-card-title>
        <v-card-text>
          <span v-if="retentionDays === -1">
            Audit logging will be <strong>disabled</strong>. All existing audit log entries will be permanently deleted and no new events will be recorded.
            This cannot be undone.
          </span>
          <span v-else-if="retentionDays > 0">
            Audit log entries older than <strong>{{ retentionDays }} days</strong> will be automatically deleted.
            This cannot be undone.
          </span>
          <span v-else>
            Audit log entries will be kept <strong>forever</strong>. The table may grow large over time.
          </span>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="showRetentionDialog = false">Cancel</v-btn>
          <v-btn color="primary" variant="flat" @click="saveRetention">Confirm</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Filters row 1 -->
    <v-row class="text-center row-filters justify-center">
      <v-col cols="12" md="3">
        <v-autocomplete
          :items="resourceTypeItems"
          label="Resource Type"
          v-model="filters.resourceType"
          :clearable="!!filters.resourceType"
          @update:model-value="onResourceTypeClear"
        ></v-autocomplete>
      </v-col>
      <v-col cols="12" md="3">
        <v-autocomplete
          :items="filteredActionItems"
          label="Action"
          v-model="filters.action"
          :clearable="!!filters.action"
          @update:model-value="onActionClear"
        >
          <template v-slot:item="{ item, props }">
            <v-list-item v-bind="props">
              <template v-slot:title>
                <v-chip v-if="item.value" :color="getActionColor(item.value)" size="small" variant="tonal">{{ item.value }}</v-chip>
                <span v-else class="text-grey">All</span>
              </template>
            </v-list-item>
          </template>
        </v-autocomplete>
      </v-col>
      <v-col cols="12" md="3">
        <v-text-field
          v-model="filters.user"
          label="User (email / name)"
          clearable
          @update:model-value="onTextFilterChange"
        ></v-text-field>
      </v-col>
    </v-row>
    <!-- Filters row 2 -->
    <v-row class="text-center row-filters-second justify-center">
      <v-col cols="12" md="3">
        <v-text-field
          v-model="filters.ip"
          label="IP Address"
          clearable
          @update:model-value="onTextFilterChange"
        ></v-text-field>
      </v-col>
      <v-col cols="12" md="3">
        <v-text-field
          v-model="filters.dateFrom"
          label="Date From (start of day)"
          type="date"
          @update:model-value="onFilterChange"
        ></v-text-field>
      </v-col>
      <v-col cols="12" md="3">
        <v-text-field
          v-model="filters.dateTo"
          label="Date To (end of day)"
          type="date"
          @update:model-value="onFilterChange"
        ></v-text-field>
      </v-col>
    </v-row>

    <!-- Filter summary -->
    <v-row v-if="!initialLoading" class="justify-center" style="margin-top: -8px; margin-bottom: 24px;">
      <v-col cols="12" md="9" class="text-center">
        <span class="filter-summary-text">Showing <strong>{{ logs.length }}</strong> of <strong>{{ totalItems }}</strong> items for <strong v-if="dateRangeDays !== null">{{ dateRangeDays }} {{ dateRangeDays === 1 ? 'day' : 'days' }}</strong><strong v-else>all time</strong>.</span>
        <v-menu location="bottom center" :close-on-content-click="true">
          <template v-slot:activator="{ props }">
            <a class="filter-summary-action" v-bind="props">Time Range</a>
          </template>
          <v-list density="compact">
            <v-list-item v-for="preset in quickPresets" :key="preset.label" @click="applyPreset(preset.days)">
              <v-list-item-title>{{ preset.label }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
        <a v-if="hasActiveFilters" class="filter-summary-action" @click="resetFilters">Reset Filters</a>
        <a class="filter-summary-action" @click="fetch">Refresh Data</a>
      </v-col>
    </v-row>

    <v-row v-if="!initialLoading" style="margin-top: 0px">
      <v-col cols="12">
        <AdminAuditLogTable
          @update:options="onTableOptionsUpdate"
          @filterBy="onCellFilterClick"
          :propItems="logs"
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
  </v-container>
</template>

<script>
/**
 * Admin page for viewing the audit log.
 * Server-side paginated table of all recorded actions with filtering
 * by action type, resource type, user, and date range.
 * Includes a retention setting control.
 */
import axios from 'axios';
import Loading from '/src/components/global/Loading.vue';
import AdminAuditLogTable from '/src/components/admin/AdminAuditLogTable.vue';
import { getActionColor } from '/src/helpers/auditLog.js';
import { useMainStore } from '@/store/store'

export default {
  name: 'PageAdminAuditLog',

  setup() {
    const store = useMainStore()
    return { store }
  },

  components: {
    Loading,
    AdminAuditLogTable,
  },
  data: () => ({
    intervalFetch: null,
    initialLoading: true,
    loading: false,
    savingRetention: false,
    showRetentionDialog: false,
    showRetentionEditor: false,
    logs: [],
    totalItems: 0,
    retentionDays: 180,
    filters: {
      action: '',
      resourceType: '',
      user: '',
      ip: '',
      dateFrom: '',
      dateTo: '',
    },
    tableOptions: {
      page: 1,
      itemsPerPage: 10,
      sortBy: [{key: 'createdAt', order: 'desc'}],
    },
    debounceTimer: null,
    quickPresets: [
      { label: 'Today', days: 0 },
      { label: 'Yesterday', days: 1 },
      { label: 'Last 3 days', days: 3 },
      { label: 'Last week', days: 7 },
      { label: 'Last 2 weeks', days: 14 },
      { label: 'Last month', days: 30 },
      { label: 'Last year', days: 365 },
    ],
    allActionItems: [
      { title: 'All', value: '', resourceType: '' },
      { title: 'LOGIN', value: 'LOGIN', resourceType: 'user' },
      { title: 'LOGIN_FAILED', value: 'LOGIN_FAILED', resourceType: 'user' },
      { title: 'RESERVATION_CREATE', value: 'RESERVATION_CREATE', resourceType: 'reservation' },
      { title: 'RESERVATION_CANCEL', value: 'RESERVATION_CANCEL', resourceType: 'reservation' },
      { title: 'RESERVATION_EXTEND', value: 'RESERVATION_EXTEND', resourceType: 'reservation' },
      { title: 'RESERVATION_RESTART', value: 'RESERVATION_RESTART', resourceType: 'reservation' },
      { title: 'RESERVATION_UPDATE_DESCRIPTION', value: 'RESERVATION_UPDATE_DESCRIPTION', resourceType: 'reservation' },
      { title: 'RESERVATION_ADMIN_EDIT', value: 'RESERVATION_ADMIN_EDIT', resourceType: 'reservation' },
      { title: 'RESERVATION_STARTED', value: 'RESERVATION_STARTED', resourceType: 'reservation' },
      { title: 'RESERVATION_RESUMED', value: 'RESERVATION_RESUMED', resourceType: 'reservation' },
      { title: 'RESERVATION_PAUSED', value: 'RESERVATION_PAUSED', resourceType: 'reservation' },
      { title: 'RESERVATION_AUTO_STOPPED', value: 'RESERVATION_AUTO_STOPPED', resourceType: 'reservation' },
      { title: 'RESERVATION_ERROR', value: 'RESERVATION_ERROR', resourceType: 'reservation' },
      { title: 'USER_CREATE', value: 'USER_CREATE', resourceType: 'user' },
      { title: 'USER_UPDATE', value: 'USER_UPDATE', resourceType: 'user' },
      { title: 'ROLE_CREATE', value: 'ROLE_CREATE', resourceType: 'role' },
      { title: 'ROLE_UPDATE', value: 'ROLE_UPDATE', resourceType: 'role' },
      { title: 'ROLE_DELETE', value: 'ROLE_DELETE', resourceType: 'role' },
      { title: 'ROLE_MOUNTS_UPDATE', value: 'ROLE_MOUNTS_UPDATE', resourceType: 'role' },
      { title: 'ROLE_HARDWARE_LIMITS_UPDATE', value: 'ROLE_HARDWARE_LIMITS_UPDATE', resourceType: 'role' },
      { title: 'ROLE_RESERVATION_LIMITS_UPDATE', value: 'ROLE_RESERVATION_LIMITS_UPDATE', resourceType: 'role' },
      { title: 'CONTAINER_CREATE', value: 'CONTAINER_CREATE', resourceType: 'container' },
      { title: 'CONTAINER_UPDATE', value: 'CONTAINER_UPDATE', resourceType: 'container' },
      { title: 'CONTAINER_DELETE', value: 'CONTAINER_DELETE', resourceType: 'container' },
      { title: 'CONTAINER_REBUILD', value: 'CONTAINER_REBUILD', resourceType: 'container' },
      { title: 'COMPUTER_CREATE', value: 'COMPUTER_CREATE', resourceType: 'computer' },
      { title: 'COMPUTER_UPDATE', value: 'COMPUTER_UPDATE', resourceType: 'computer' },
      { title: 'COMPUTER_DELETE', value: 'COMPUTER_DELETE', resourceType: 'computer' },
      { title: 'SETTINGS_UPDATE', value: 'SETTINGS_UPDATE', resourceType: 'settings' },
    ],
    resourceTypeItems: [
      { title: 'All', value: '', props: { prependIcon: 'mdi-filter-off' } },
      { title: 'Reservation', value: 'reservation', props: { prependIcon: 'mdi-calendar-clock' } },
      { title: 'User', value: 'user', props: { prependIcon: 'mdi-account' } },
      { title: 'Role', value: 'role', props: { prependIcon: 'mdi-shield-account' } },
      { title: 'Container', value: 'container', props: { prependIcon: 'mdi-cube-outline' } },
      { title: 'Computer', value: 'computer', props: { prependIcon: 'mdi-server' } },
      { title: 'Settings', value: 'settings', props: { prependIcon: 'mdi-cog' } },
    ],
  }),
  mounted() {
    this.fetch();
    this.intervalFetch = setInterval(() => { this.fetch() }, 30000);
  },
  computed: {
    filteredActionItems() {
      if (!this.filters.resourceType) return this.allActionItems;
      return this.allActionItems.filter(a => a.value === '' || a.resourceType === this.filters.resourceType);
    },
    dateRangeDays() {
      if (!this.filters.dateFrom || !this.filters.dateTo) return null;
      const from = new Date(this.filters.dateFrom);
      const to = new Date(this.filters.dateTo);
      const diffMs = to - from;
      if (diffMs < 0) return null;
      return Math.round(diffMs / (1000 * 60 * 60 * 24)) + 1;
    },
    hasActiveFilters() {
      return !!(this.filters.action || this.filters.resourceType || this.filters.user || this.filters.ip || this.filters.dateFrom || this.filters.dateTo);
    },
  },
  methods: {
    getActionColor,
    applyPreset(days) {
      const today = new Date();
      const from = new Date(today);
      if (days === 0) {
        // Today only
        this.filters.dateFrom = today.toISOString().split('T')[0];
        this.filters.dateTo = today.toISOString().split('T')[0];
      } else if (days === 1) {
        // Yesterday only
        from.setDate(from.getDate() - 1);
        this.filters.dateFrom = from.toISOString().split('T')[0];
        this.filters.dateTo = from.toISOString().split('T')[0];
      } else {
        from.setDate(from.getDate() - (days - 1));
        this.filters.dateFrom = from.toISOString().split('T')[0];
        this.filters.dateTo = today.toISOString().split('T')[0];
      }
      this.tableOptions.page = 1;
      this.fetch();
    },
    resetFilters() {
      this.filters.action = '';
      this.filters.resourceType = '';
      this.filters.user = '';
      this.filters.ip = '';
      this.filters.dateFrom = '';
      this.filters.dateTo = '';
      this.tableOptions.page = 1;
      this.fetch();
    },
    onTableOptionsUpdate(options) {
      this.tableOptions.page = options.page;
      this.tableOptions.itemsPerPage = options.itemsPerPage;
      if (options.sortBy && options.sortBy.length > 0) {
        this.tableOptions.sortBy = options.sortBy;
      }
      this.fetch();
    },
    onResourceTypeClear(val) {
      if (val === null || val === undefined) this.filters.resourceType = '';
      this.onResourceTypeChange();
    },
    onActionClear(val) {
      if (val === null || val === undefined) this.filters.action = '';
      this.onFilterChange();
    },
    onResourceTypeChange() {
      // Clear action filter if it doesn't match the new resource type
      if (this.filters.action) {
        const match = this.allActionItems.find(a => a.value === this.filters.action);
        if (match && match.resourceType && match.resourceType !== this.filters.resourceType) {
          this.filters.action = '';
        }
      }
      this.tableOptions.page = 1;
      this.fetch();
    },
    onCellFilterClick({ key, value }) {
      if (key === 'resourceType') {
        this.filters.resourceType = value;
        this.onResourceTypeChange();
      } else if (key === 'action') {
        this.filters.action = value;
      } else if (key === 'user') {
        this.filters.user = value;
      } else if (key === 'ipAddress') {
        this.filters.ip = value;
      }
      this.tableOptions.page = 1;
      this.fetch();
    },
    onFilterChange() {
      this.tableOptions.page = 1;
      this.fetch();
    },
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
        url: this.$appSettings.APIServer.admin.get_audit_logs,
        data: {
          page: _this.tableOptions.page,
          itemsPerPage: _this.tableOptions.itemsPerPage,
          sortBy: _this.tableOptions.sortBy,
          filters: {
            action: _this.filters.action || '',
            resourceType: _this.filters.resourceType || '',
            user: _this.filters.user || '',
            ip: _this.filters.ip || '',
            dateFrom: _this.filters.dateFrom || '',
            dateTo: _this.filters.dateTo || '',
          }
        },
        headers: {"Authorization": `Bearer ${currentUser.loginToken}`}
      })
      .then(function (response) {
        if (response.data.status == true) {
          _this.logs = response.data.data.logs;
          _this.totalItems = response.data.data.totalItems;
          if (response.data.data.retentionDays !== undefined) {
            _this.retentionDays = response.data.data.retentionDays;
          }
        } else {
          _this.store.showMessage({ text: "Error fetching audit logs.", color: "red" });
        }
        _this.loading = false;
        _this.initialLoading = false;
      })
      .catch(function (error) {
        if (error.response && (error.response.status == 400 || error.response.status == 401)) {
          _this.store.showMessage({ text: error.response.data.detail, color: "red" });
        } else {
          console.log(error);
          _this.store.showMessage({ text: "Unknown error fetching audit logs.", color: "red" });
        }
        _this.loading = false;
        _this.initialLoading = false;
      });
    },
    confirmSaveRetention() {
      this.showRetentionDialog = true;
    },
    saveRetention() {
      this.showRetentionDialog = false;
      let _this = this;
      let currentUser = this.store.user;
      _this.savingRetention = true;

      axios({
        method: "post",
        url: this.$appSettings.APIServer.admin.save_general_settings,
        data: {
          section: "auditLog",
          settings: { retentionDays: _this.retentionDays }
        },
        headers: {"Authorization": `Bearer ${currentUser.loginToken}`}
      })
      .then(function (response) {
        if (response.data.status == true) {
          _this.store.showMessage({ text: "Retention setting saved.", color: "green" });
        } else {
          _this.store.showMessage({ text: response.data.message || "Error saving retention.", color: "red" });
        }
        _this.savingRetention = false;
      })
      .catch(function () {
        _this.store.showMessage({ text: "Error saving retention setting.", color: "red" });
        _this.savingRetention = false;
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

.audit-log-description {
  margin-top: 8px;
  font-size: 14px;
  opacity: 0.7;
}

.row-filters {
  margin-top: 30px;
  margin-bottom: 0px;
}

.row-filters-second {
  margin-top: 0px;
  margin-bottom: 0px;
}

.filter-summary-text {
  font-size: 14px;
  opacity: 0.5;
}

.filter-summary-action {
  font-size: 14px;
  margin-left: 8px;
}
</style>
