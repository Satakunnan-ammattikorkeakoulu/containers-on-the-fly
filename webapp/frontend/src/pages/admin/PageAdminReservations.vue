<template>
  <v-container>

    <v-row class="text-center">
      <v-col cols="12">
        <h4 class="m-0">Admin</h4>
        <h2 class="m-0">All Reservations</h2>
        <p class="dim m-0 mb-40">Listing reservations for all users</p>
      </v-col>
    </v-row>

    <!-- Action links -->
    <v-row v-if="!initialLoading" class="text-center justify-center" style="margin-top: 0px; margin-bottom: 16px;">
      <v-col cols="12">
        <div class="header-links">
          <v-tooltip location="bottom">
            <template v-slot:activator="{ props }">
              <a v-bind="props" @click="showFilters = !showFilters"><v-icon size="x-small" class="mr-1">mdi-filter-outline</v-icon>Filters</a>
            </template>
            <span>Show or hide filters</span>
          </v-tooltip>
          <span class="header-link-separator">·</span>
          <v-menu location="bottom center" :close-on-content-click="true">
            <template v-slot:activator="{ props: menuProps }">
              <v-tooltip location="bottom">
                <template v-slot:activator="{ props: tooltipProps }">
                  <a v-bind="{ ...menuProps, ...tooltipProps }"><v-icon size="x-small" class="mr-1">mdi-calendar-range</v-icon>Time Range</a>
                </template>
                <span>Filter by preset time range</span>
              </v-tooltip>
            </template>
            <v-list density="compact">
              <v-list-item v-for="preset in quickPresets" :key="preset.label" @click="applyPreset(preset.days)">
                <v-list-item-title>{{ preset.label }}</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
          <span class="header-link-separator">·</span>
          <v-tooltip location="bottom">
            <template v-slot:activator="{ props }">
              <a v-bind="props" @click="showStatistics = !showStatistics"><v-icon size="x-small" class="mr-1">mdi-chart-bar</v-icon>Statistics</a>
            </template>
            <span>Show or hide statistics</span>
          </v-tooltip>
          <span class="header-link-separator">·</span>
          <v-tooltip location="bottom" max-width="250">
            <template v-slot:activator="{ props }">
              <a v-bind="props" @click="fetchReservations"><v-icon size="x-small" class="mr-1">mdi-refresh</v-icon>Refresh</a>
            </template>
            <span>Auto-refreshes every 15s. Click to refresh now.</span>
          </v-tooltip>
        </div>
      </v-col>
    </v-row>

    <!-- Filters row 1 -->
    <v-row class="text-center row-filters justify-center" v-if="!initialLoading && showFilters">
      <v-col cols="12" md="2">
        <v-select
          :items="statusItems"
          label="Status"
          v-model="filters.status"
          @update:model-value="onFilterChange"
        >
          <template v-slot:item="{ item, props }">
            <v-list-item v-bind="props">
              <template v-slot:title>
                <v-chip v-if="item.value && item.value !== 'All'" :color="getStatusColor(item.value)" size="small" variant="tonal">{{ item.title }}</v-chip>
                <span v-else>{{ item.title }}</span>
              </template>
            </v-list-item>
          </template>
          <template v-slot:selection="{ item }">
            <v-chip v-if="item.value && item.value !== 'All'" :color="getStatusColor(item.value)" size="small" variant="tonal">{{ item.title }}</v-chip>
            <span v-else>{{ item.title }}</span>
          </template>
        </v-select>
      </v-col>
      <v-col cols="12" md="2">
        <v-select
          :items="computerItems"
          label="Computer"
          v-model="filters.computerId"
          item-title="text"
          item-value="value"
          :clearable="!!filters.computerId"
          @update:model-value="onDropdownClear('computerId')"
        ></v-select>
      </v-col>
      <v-col cols="12" md="2">
        <v-select
          :items="containerItems"
          label="Container"
          v-model="filters.containerId"
          item-title="text"
          item-value="value"
          :clearable="!!filters.containerId"
          @update:model-value="onDropdownClear('containerId')"
        ></v-select>
      </v-col>
      <v-col cols="12" md="3">
        <v-text-field
          v-model="filters.user"
          label="User (email or name)"
          clearable
          @update:model-value="onTextFilterChange"
        ></v-text-field>
      </v-col>
    </v-row>

    <!-- Filters row 2: date range -->
    <v-row class="text-center row-filters-second justify-center" v-if="!initialLoading && showFilters">
      <v-col cols="12" md="2">
        <v-text-field
          v-model="filters.reservationId"
          label="Reservation ID"
          clearable
          @update:model-value="onTextFilterChange"
        ></v-text-field>
      </v-col>
      <v-col cols="12" md="3">
        <v-text-field
          v-model="filters.dateFrom"
          label="Reservation Date From"
          type="date"
          clearable
          @update:model-value="onFilterChange"
        ></v-text-field>
      </v-col>
      <v-col cols="12" md="3">
        <v-text-field
          v-model="filters.dateTo"
          label="Reservation Date To"
          type="date"
          clearable
          @update:model-value="onFilterChange"
        ></v-text-field>
      </v-col>
    </v-row>

    <!-- Statistics Cards -->
    <v-row v-if="!initialLoading && showStatistics" class="mb-4 justify-center">
      <v-col cols="12" sm="6" md="2">
        <v-card variant="outlined">
          <v-card-text class="text-center">
            <v-icon size="24" color="blue-grey" class="mb-2">mdi-chart-bar</v-icon>
            <div class="text-h6 font-weight-bold">{{ stats.total }}</div>
            <div class="text-subtitle-2">Total</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="2">
        <v-card variant="outlined">
          <v-card-text class="text-center">
            <v-icon size="24" color="green" class="mb-2">mdi-play-circle</v-icon>
            <div class="text-h6 font-weight-bold" style="color: #4CAF50 !important;">{{ stats.started }}</div>
            <div class="text-subtitle-2">Running</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="2">
        <v-card variant="outlined">
          <v-card-text class="text-center">
            <v-icon size="24" color="orange" class="mb-2">mdi-stop-circle</v-icon>
            <div class="text-h6 font-weight-bold" style="color: #FF9800 !important;">{{ stats.stopped }}</div>
            <div class="text-subtitle-2">Stopped</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="2">
        <v-card variant="outlined">
          <v-card-text class="text-center">
            <v-icon size="24" color="red" class="mb-2">mdi-alert-circle</v-icon>
            <div class="text-h6 font-weight-bold" style="color: #F44336 !important;">{{ stats.error }}</div>
            <div class="text-subtitle-2">Errored</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Filter summary (always visible) -->
    <v-row v-if="!initialLoading" class="justify-center" style="margin-top: 8px; margin-bottom: 24px;">
      <v-col cols="12" md="9" class="text-center">
        <span class="filter-summary-text">Showing <strong>{{ reservations.length }}</strong> of <strong>{{ totalItems }}</strong> items for <strong v-if="dateRangeDays !== null">{{ dateRangeDays }} {{ dateRangeDays === 1 ? 'day' : 'days' }}</strong><strong v-else>all time</strong>.</span>
        <a v-if="hasActiveFilters" class="filter-summary-action" @click="resetFilters">Reset Filters</a>
      </v-col>
    </v-row>

    <v-row v-if="!initialLoading" style="margin-top: 0px">
        <v-col cols="12" style="padding-top: 0px">
          <AdminReservationTable
            @emitCancelReservation="cancelReservation"
            @emitChangeEndDate="changeEndDate"
            @emitRestartContainer="restartContainer"
            @emitShowReservationDetails="showReservationDetails"
            @filterByUser="onFilterByUser"
            @update:options="onTableOptionsUpdate"
            :propReservations="reservations"
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

    <UserReservationsModalConnectionDetails :reservationId="modalConnectionDetailsReservationId" v-on:emitModalClose="closeModalConnectionDetails" v-if="modalConnectionDetailsVisible && modalConnectionDetailsReservationId != null"></UserReservationsModalConnectionDetails>

  </v-container>
</template>

<script>
  /**
   * Admin page for viewing and managing all reservations system-wide.
   * Displays reservation statistics (by status and time period), supports
   * server-side filtering by status and reservation ID, and provides actions
   * to cancel, change end dates, restart containers, and view connection details.
   * Data auto-refreshes every 15 seconds.
   */
  import axios from 'axios';
  import Loading from '/src/components/global/Loading.vue';
  import AdminReservationTable from '/src/components/admin/AdminReservationTable.vue';
  import UserReservationsModalConnectionDetails from '/src/components/user/UserReservationsModalConnectionDetails.vue';
  import { useMainStore } from '@/store/store'

  export default {
    name: 'PageUserReservations',

    setup() {
      const store = useMainStore()
      return { store }
    },

    components: {
      Loading,
      AdminReservationTable,
      UserReservationsModalConnectionDetails
    },
    data: () => ({
      showFilters: false,
      showStatistics: true,
      intervalFetchReservations: null,
      initialLoading: true,
      loading: false,
      reservations: [],
      totalItems: 0,
      justReserved: false,
      informByEmail: false,
      modalConnectionDetailsVisible: false,
      modalConnectionDetailsReservationId: null,
      availableComputers: [],
      availableContainers: [],
      filters: {
        status: "All",
        user: '',
        reservationId: '',
        computerId: '',
        containerId: '',
        dateFrom: '',
        dateTo: '',
      },
      statusCounts: {},
      stats: {
        total: 0,
        started: 0,
        stopped: 0,
        error: 0
      },
      tableOptions: {
        page: 1,
        itemsPerPage: 10,
        sortBy: [{key: 'reservationId', order: 'desc'}],
      },
      debounceTimer: null,
      quickPresets: [
        { label: 'All time', days: null },
        { label: 'Today', days: 0 },
        { label: 'Yesterday', days: 1 },
        { label: 'Last 3 days', days: 3 },
        { label: 'Last week', days: 7 },
        { label: 'Last 2 weeks', days: 14 },
        { label: 'Last month', days: 30 },
        { label: 'Last 3 months', days: 90 },
        { label: 'Last year', days: 365 },
      ],
    }),
    computed: {
      statusItems() {
        const items = [
          { title: `All (${(this.statusCounts.reserved || 0) + (this.statusCounts.started || 0) + (this.statusCounts.stopping || 0) + (this.statusCounts.stopped || 0) + (this.statusCounts.error || 0) + (this.statusCounts.paused || 0)})`, value: 'All' },
          { title: `Reserved (${this.statusCounts.reserved || 0})`, value: 'reserved' },
          { title: `Running (${this.statusCounts.started || 0})`, value: 'started' },
          { title: `Paused (${this.statusCounts.paused || 0})`, value: 'paused' },
          { title: `Error (${this.statusCounts.error || 0})`, value: 'error' },
          { title: `Stopped (${this.statusCounts.stopped || 0})`, value: 'stopped' }
        ];
        return items;
      },
      computerItems() {
        const items = [{ text: 'All', value: '' }];
        items.push(...this.availableComputers.map(c => ({ text: c.name, value: c.id })));
        return items;
      },
      containerItems() {
        const items = [{ text: 'All', value: '' }];
        items.push(...this.availableContainers.map(c => ({ text: c.name, value: c.id })));
        return items;
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
        return !!(
          (this.filters.status && this.filters.status !== 'All') ||
          this.filters.user || this.filters.reservationId ||
          this.filters.computerId || this.filters.containerId ||
          this.filters.dateFrom || this.filters.dateTo
        );
      }
    },
    mounted () {
      if (localStorage.getItem("justReserved") === "true") {
        this.justReserved = true;
        localStorage.removeItem("justReserved");
      }
      if (localStorage.getItem("justReservedInformEmail") === "true") {
        this.informByEmail = true;
        localStorage.removeItem("justReservedInformEmail");
      }

      this.fetchReservations()
      // Keep updating reservations every 15 seconds
      this.intervalFetchReservations = setInterval(() => { this.fetchReservations()}, 15000)
    },
    methods: {
      getStatusColor(status) {
        if (status == "reserved") return "primary"
        else if (status == "started") return "green"
        else if (status == "stopped") return "red"
        else if (status == "error") return "orange"
        else if (status == "paused") return "warning"
      },
      /** Handles pagination/sort changes from the data table. */
      onTableOptionsUpdate(options) {
        this.tableOptions.page = options.page;
        this.tableOptions.itemsPerPage = options.itemsPerPage;
        if (options.sortBy && options.sortBy.length > 0) {
          this.tableOptions.sortBy = options.sortBy;
        }
        this.fetchReservations();
      },
      onFilterByUser(email) {
        this.filters.user = email;
        this.tableOptions.page = 1;
        this.fetchReservations();
      },
      /** Handles dropdown filter changes (immediate). */
      onFilterChange() {
        this.tableOptions.page = 1;
        this.fetchReservations();
      },
      /** Handles clearable dropdown filters — resets null to empty string. */
      onDropdownClear(filterKey) {
        if (this.filters[filterKey] === null || this.filters[filterKey] === undefined) {
          this.filters[filterKey] = '';
        }
        this.onFilterChange();
      },
      applyPreset(days) {
        if (days === null) {
          this.filters.dateFrom = '';
          this.filters.dateTo = '';
          this.tableOptions.page = 1;
          this.fetchReservations();
          return;
        }
        const today = new Date();
        const from = new Date(today);
        if (days === 0) {
          this.filters.dateFrom = today.toISOString().split('T')[0];
          this.filters.dateTo = today.toISOString().split('T')[0];
        } else if (days === 1) {
          from.setDate(from.getDate() - 1);
          this.filters.dateFrom = from.toISOString().split('T')[0];
          this.filters.dateTo = from.toISOString().split('T')[0];
        } else {
          from.setDate(from.getDate() - (days - 1));
          this.filters.dateFrom = from.toISOString().split('T')[0];
          this.filters.dateTo = today.toISOString().split('T')[0];
        }
        this.tableOptions.page = 1;
        this.fetchReservations();
      },
      /** Reset all filters to defaults. */
      resetFilters() {
        this.filters.status = 'All';
        this.filters.user = '';
        this.filters.reservationId = '';
        this.filters.computerId = '';
        this.filters.containerId = '';
        this.filters.dateFrom = '';
        this.filters.dateTo = '';
        this.tableOptions.page = 1;
        this.fetchReservations();
      },
      /** Handles text filter changes with 300ms debounce. */
      onTextFilterChange() {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
          this.tableOptions.page = 1;
          this.fetchReservations();
        }, 300);
      },
      closeModalConnectionDetails() {
        this.modalConnectionDetailsVisible = false
      },
      createReservation() {
        // For admins, their limits are typically very high (99 active reservations)
        // But we still check to be consistent

        // Count active reservations for the admin user
        let activeReservationCount = 0
        this.reservations.forEach((res) => {
          // Only count admin's own reservations
          if ((res.status == "started" || res.status == "reserved") && res.userEmail === this.store.user.email) {
            activeReservationCount++
          }
        })

        // Get user's reservation limits from store
        const maxActiveReservations = this.store.userMaxActiveReservations

        // Check against the user's actual limit
        if (activeReservationCount >= maxActiveReservations) {
          this.store.showMessage({
            text: `You have reached your maximum of ${maxActiveReservations} active reservations.`,
            color: "red"
          })
          return
        }

        // Admin has not reached their limit, allow navigation
        this.$router.push("/user/reserve")
      },
      fetchReservations() {
        let _this = this
        let currentUser = this.store.user
        _this.loading = true;

        axios({
          method: "post",
          url: this.$appSettings.APIServer.admin.get_reservations,
          data: {
            page: _this.tableOptions.page,
            itemsPerPage: _this.tableOptions.itemsPerPage,
            sortBy: _this.tableOptions.sortBy,
            filters: {
              status: _this.filters.status === 'All' ? '' : (_this.filters.status || ''),
              user: _this.filters.user || '',
              reservationId: _this.filters.reservationId || '',
              computerId: _this.filters.computerId || '',
              containerId: _this.filters.containerId || '',
              dateFrom: _this.filters.dateFrom || '',
              dateTo: _this.filters.dateTo || '',
            }
          },
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
            if (response.data.status == true) {
              _this.reservations = response.data.data.reservations
              _this.totalItems = response.data.data.totalItems
              _this.statusCounts = response.data.data.statusCounts || {}
              _this.stats = response.data.data.stats || _this.stats
              _this.availableComputers = response.data.data.availableComputers || []
              _this.availableContainers = response.data.data.availableContainers || []
            }
            else {
              console.log("Failed getting reservations...")
              _this.store.showMessage({ text: "There was an error getting reservations.", color: "red" })
            }
            _this.loading = false
            _this.initialLoading = false
        })
        .catch(function (error) {
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.store.showMessage({ text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.store.showMessage({ text: "Unknown error while trying to get reservations.", color: "red" })
            }
            _this.loading = false
            _this.initialLoading = false
        });
      },
      async changeEndDate(reservationId, currentEndDate) {
        // Format current end date for datetime-local input (YYYY-MM-DDTHH:MM)
        let defaultValue = ''
        if (currentEndDate) {
          const utcStr = currentEndDate.endsWith('Z') ? currentEndDate : currentEndDate + 'Z'
          const d = new Date(utcStr)
          if (!isNaN(d.getTime())) {
            const pad = (n) => String(n).padStart(2, '0')
            defaultValue = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
          }
        }
        let newEndDate = await this.store.showPromptDialog({
          title: 'Adjust End Date',
          message: 'Select new end date and time:',
          inputLabel: 'End Date',
          inputType: 'datetime-local',
          defaultValue: defaultValue,
        })
        if (newEndDate == null || newEndDate == "" || newEndDate == defaultValue) {
          return;
        }
        this.store.showMessage({ text: "Changing end date.", color: "green" })

        // Convert local datetime to ISO string with timezone offset so the backend interprets it correctly
        const selectedDate = new Date(newEndDate)
        const endDateISO = selectedDate.toISOString()

        let params = {
          "reservationId": reservationId,
          "endDate": endDateISO
        }

        let _this = this
        let currentUser = this.store.user

        axios({
          method: "post",
          url: this.$appSettings.APIServer.admin.edit_reservation,
          params: params,
          headers: {
            "Authorization" : `Bearer ${currentUser.loginToken}`
          }
        })
        .then(function (response) {
            if (response.data.status == true) {
              _this.store.showMessage({ text: "Reservation edited.", color: "green" })
              _this.fetchReservations()
            }
            else {
              console.log("Failed editing reservation...")
              console.log(response)
              let msg = response && response.data && response.data.message ? response.data.message : "There was an error editing the reservation."
              _this.store.showMessage({ text: msg, color: "red" })
            }
        })
        .catch(function (error) {
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.store.showMessage({ text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.store.showMessage({ text: "Unknown error.", color: "red" })
            }
        });
      },
      async cancelReservation(reservationId) {
        let result = await this.store.showConfirmDialog({
          title: 'Cancel Reservation',
          message: 'Do you really want to cancel this reservation?',
          confirmText: 'Cancel Reservation',
          confirmColor: 'red',
        })
        if (!result) return
        let params = {
          "reservationId": reservationId,
        }

        let _this = this
        _this.cancellingReservation = true
        let currentUser = this.store.user

        axios({
          method: "post",
          url: this.$appSettings.APIServer.reservation.cancel_reservation,
          params: params,
          headers: {
            "Authorization" : `Bearer ${currentUser.loginToken}`
          }
        })
        .then(function (response) {
            if (response.data.status == true) {
              _this.store.showMessage({ text: "Reservation cancelled.", color: "green" })
              _this.fetchReservations()
              setTimeout(() => _this.fetchReservations(), 5000)
            }
            else {
              console.log("Failed removing reservation...")
              console.log(response)
              let msg = response && response.data && response.data.message ? response.data.message : "There was an error getting the hardware specs."
              _this.store.showMessage({ text: msg, color: "red" })
            }
            _this.cancellingReservation = false
        })
        .catch(function (error) {
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.store.showMessage({ text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.store.showMessage({ text: "Unknown error.", color: "red" })
            }
            _this.cancellingReservation = false
        });
      },
      async restartContainer(reservationId) {
        let result = await this.store.showConfirmDialog({
          title: 'Restart Container',
          message: 'Do you really want to restart the docker container?',
          confirmText: 'Restart',
          confirmColor: 'orange',
        })
        if (!result) return
        let params = {
          "reservationId": reservationId,
        }

        let _this = this
        _this.restartingContainer = true
        let currentUser = this.store.user

        axios({
          method: "post",
          url: this.$appSettings.APIServer.reservation.restart_container,
          params: params,
          headers: {
            "Authorization" : `Bearer ${currentUser.loginToken}`
          }
        })
        .then(function (response) {
            if (response.data.status == true) {
              _this.store.showMessage({ text: "Container restarted succesfully.", color: "green" })
              _this.fetchReservations()
              setTimeout(() => _this.fetchReservations(), 5000)
            }
            else {
              console.log("Failed restarting container...")
              console.log(response)
              let msg = response && response.data && response.data.message ? response.data.message : "There was an error getting the hardware specs."
              _this.store.showMessage({ text: msg, color: "red" })
            }
            _this.restartingContainer = false
        })
        .catch(function (error) {
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.store.showMessage({ text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.store.showMessage({ text: "Unknown error.", color: "red" })
            }
            _this.restartingContainer = false
        });
      },
      showReservationDetails(reservationId) {
        this.modalConnectionDetailsVisible = true
        this.modalConnectionDetailsReservationId = reservationId
      },
    },
    beforeUnmount() {
      clearInterval(this.intervalFetchReservations)
      clearTimeout(this.debounceTimer)
    },
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

  .header-links {
    font-size: 15px;
    margin-top: 6px;
  }

  .header-link-separator {
    margin: 0 8px;
    opacity: 0.4;
  }
</style>
