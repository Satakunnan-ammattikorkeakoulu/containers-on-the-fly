<template>
  <v-container>
    <v-row class="text-center">
      <v-col cols="12">
        <h4 class="m-0">Admin</h4>
        <h2 class="m-0">Audit Log</h2>
        <p class="audit-log-description">
          Records of all significant user and admin actions in the system.
          The current retention is <strong>{{ retentionDays > 0 ? retentionDays + ' days' : 'forever' }}</strong>
          <a class="retention-toggle-link" @click="showRetentionEditor = !showRetentionEditor">{{ showRetentionEditor ? '(hide)' : '(change)' }}</a>
        </p>
      </v-col>
    </v-row>

    <!-- Retention Setting (toggled) -->
    <v-row v-if="showRetentionEditor" class="justify-center">
      <v-col cols="12" md="6" class="d-flex flex-column align-center" style="gap: 8px;">
        <div class="d-flex align-center" style="gap: 12px;">
          <v-text-field
            v-model.number="retentionDays"
            label="Retention (days, 0 = forever)"
            type="number"
            density="compact"
            hide-details
            style="min-width: 250px"
          ></v-text-field>
          <v-btn color="primary" size="small" @click="confirmSaveRetention" :loading="savingRetention">Save</v-btn>
        </div>
        <span style="font-size: 14px; opacity: 0.5;">
          Entries older than the retention period are automatically removed when new events are logged.
        </span>
      </v-col>
    </v-row>

    <!-- Retention confirmation dialog -->
    <v-dialog v-model="showRetentionDialog" max-width="460">
      <v-card>
        <v-card-title>Change retention period?</v-card-title>
        <v-card-text>
          <span v-if="retentionDays > 0">
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
          @update:model-value="onResourceTypeChange"
        ></v-autocomplete>
      </v-col>
      <v-col cols="12" md="3">
        <v-autocomplete
          :items="filteredActionItems"
          label="Action"
          v-model="filters.action"
          @update:model-value="onFilterChange"
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
      <v-col cols="12" md="1" class="d-flex align-center justify-center">
        <v-tooltip text="Refresh data" :open-delay="0">
          <template v-slot:activator="{ props }">
            <v-btn icon variant="text" v-bind="props" @click="fetch">
              <v-icon>mdi-refresh</v-icon>
            </v-btn>
          </template>
        </v-tooltip>
      </v-col>
    </v-row>

    <v-row v-if="!initialLoading" style="margin-top: 0px">
      <v-col cols="12">
        <AdminAuditLogTable
          @update:options="onTableOptionsUpdate"
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
      { title: 'All', value: '' },
      { title: 'reservation', value: 'reservation' },
      { title: 'user', value: 'user' },
      { title: 'role', value: 'role' },
      { title: 'container', value: 'container' },
      { title: 'computer', value: 'computer' },
      { title: 'settings', value: 'settings' },
    ],
  }),
  mounted() {
    this.fetch();
  },
  computed: {
    filteredActionItems() {
      if (!this.filters.resourceType) return this.allActionItems;
      return this.allActionItems.filter(a => a.value === '' || a.resourceType === this.filters.resourceType);
    },
  },
  methods: {
    getActionColor,
    onTableOptionsUpdate(options) {
      this.tableOptions.page = options.page;
      this.tableOptions.itemsPerPage = options.itemsPerPage;
      if (options.sortBy && options.sortBy.length > 0) {
        this.tableOptions.sortBy = options.sortBy;
      }
      this.fetch();
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

.retention-toggle-link {
  cursor: pointer;
  color: #2096f3;
  text-decoration: none;
  margin-left: 4px;

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
