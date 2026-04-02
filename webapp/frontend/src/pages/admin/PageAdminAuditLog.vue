<template>
  <v-container>
    <v-row class="text-center">
      <v-col cols="12">
        <h4 class="m-0">Admin</h4>
        <h2 class="m-0">Audit Log</h2>
      </v-col>
    </v-row>

    <!-- Retention Setting -->
    <v-row class="justify-center" style="margin-top: 20px">
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

    <!-- Filters -->
    <v-row class="text-center row-filters justify-center">
      <v-col cols="12" md="2">
        <v-select
          :items="resourceTypeItems"
          label="Resource Type"
          v-model="filters.resourceType"
          @update:model-value="onFilterChange"
        ></v-select>
      </v-col>
      <v-col cols="12" md="2">
        <v-select
          :items="actionItems"
          label="Action"
          v-model="filters.action"
          @update:model-value="onFilterChange"
        ></v-select>
      </v-col>
      <v-col cols="12" md="3">
        <v-text-field
          v-model="filters.user"
          label="User (email / name)"
          clearable
          @update:model-value="onTextFilterChange"
        ></v-text-field>
      </v-col>
      <v-col cols="12" md="2">
        <v-text-field
          v-model="filters.dateFrom"
          label="Date From"
          type="date"
          @update:model-value="onFilterChange"
        ></v-text-field>
      </v-col>
      <v-col cols="12" md="2">
        <v-text-field
          v-model="filters.dateTo"
          label="Date To"
          type="date"
          @update:model-value="onFilterChange"
        ></v-text-field>
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
    logs: [],
    totalItems: 0,
    retentionDays: 180,
    filters: {
      action: '',
      resourceType: '',
      user: '',
      dateFrom: '',
      dateTo: '',
    },
    tableOptions: {
      page: 1,
      itemsPerPage: 10,
      sortBy: [{key: 'createdAt', order: 'desc'}],
    },
    debounceTimer: null,
    actionItems: [
      '', 'LOGIN', 'LOGIN_FAILED',
      'RESERVATION_CREATE', 'RESERVATION_CANCEL', 'RESERVATION_EXTEND',
      'RESERVATION_RESTART', 'RESERVATION_UPDATE_DESCRIPTION', 'RESERVATION_ADMIN_EDIT',
      'USER_CREATE', 'USER_UPDATE',
      'ROLE_CREATE', 'ROLE_UPDATE', 'ROLE_DELETE',
      'ROLE_MOUNTS_UPDATE', 'ROLE_HARDWARE_LIMITS_UPDATE', 'ROLE_RESERVATION_LIMITS_UPDATE',
      'CONTAINER_CREATE', 'CONTAINER_UPDATE', 'CONTAINER_DELETE', 'CONTAINER_REBUILD',
      'COMPUTER_CREATE', 'COMPUTER_UPDATE', 'COMPUTER_DELETE',
      'SETTINGS_UPDATE',
    ],
    resourceTypeItems: ['', 'reservation', 'user', 'role', 'container', 'computer', 'settings'],
  }),
  mounted() {
    this.fetch();
  },
  methods: {
    onTableOptionsUpdate(options) {
      this.tableOptions.page = options.page;
      this.tableOptions.itemsPerPage = options.itemsPerPage;
      if (options.sortBy && options.sortBy.length > 0) {
        this.tableOptions.sortBy = options.sortBy;
      }
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

.row-filters {
  margin-top: 30px;
  margin-bottom: 0px;
}
</style>
