<template>
  <v-container>
    <v-row class="text-center section">
      <v-col>
        <v-btn color="success" large @click="createReservation">Reserve Server</v-btn>
      </v-col>
    </v-row>

    <v-row class="text-center" v-if="justReserved" ref="reservationSuccessAlert">
      <v-col cols="1"></v-col>
      <v-col cols="10">
        <v-alert type="info" :icon="false" closable v-model="justReserved" class="text-center reservation-success-alert">
          <h3 style="margin-bottom: 15px;">Reservation created succesfully</h3>
          <p>Your server has been reserved. You can view the details on how to access the server from this page after the container has been started.</p>
          <p v-if="store.emailEnabled">You will also be emailed the connection details after the container starts.</p>
        </v-alert>
      </v-col>
      <v-col cols="1"></v-col>
    </v-row>

    <!-- Title -->
    <v-row class="text-center">
      <v-col cols="12">
        <h2 class="m-0">{{ viewMode === 'activity' ? 'Your Activity' : 'Your Reservations' }}</h2>
        <p v-if="viewMode === 'reservations'" class="dim m-0" style="font-size: 13px;">{{ activeReservationCount }} of {{ maxActiveReservations }} active reservations</p>
        <div class="header-links">
          <template v-if="viewMode === 'reservations'">
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <a v-bind="props" @click="showFilters = !showFilters"><v-icon size="x-small" class="mr-1">mdi-filter-outline</v-icon>Filters</a>
              </template>
              <span>Show or hide filters</span>
            </v-tooltip>
            <span class="header-link-separator">·</span>
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <a v-bind="props" @click="showActivityView"><v-icon size="x-small" class="mr-1">mdi-history</v-icon>Activity</a>
              </template>
              <span>View reservation activity log</span>
            </v-tooltip>
            <v-badge
              v-if="unreadActivityCount > 0"
              :content="unreadActivityBadgeText"
              color="info"
              inline
              class="activity-badge"
            ></v-badge>
            <span class="header-link-separator">·</span>
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <a v-bind="props" @click="toggleCalendarView"><v-icon size="x-small" class="mr-1">mdi-calendar</v-icon>Reservation Calendar</a>
              </template>
              <span>{{ showCalendar ? 'Hide' : 'Show' }} reservation calendar</span>
            </v-tooltip>
            <span class="header-link-separator">·</span>
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <a v-bind="props" @click="fetchReservations"><v-icon size="x-small" class="mr-1">mdi-refresh</v-icon>Refresh</a>
              </template>
              <span>Auto-refreshes every 15s. Click to refresh now.</span>
            </v-tooltip>
          </template>
          <template v-else>
            <a @click="showReservationsView"><v-icon size="x-small" class="mr-1">mdi-arrow-left</v-icon>Back to Reservations</a>
            <span class="header-link-separator">·</span>
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <a v-bind="props" @click="fetchActivity"><v-icon size="x-small" class="mr-1">mdi-refresh</v-icon>Refresh</a>
              </template>
              <span>Auto-refreshes every 30s. Click to refresh now.</span>
            </v-tooltip>
          </template>
        </div>
      </v-col>
    </v-row>

    <!-- Reservation Calendar -->
    <v-row v-if="showCalendar" class="section">
      <v-col cols="12">
        <h3 style="margin-bottom: 10px;">Reservation Calendar</h3>
        <p style="margin-bottom: 20px; color: #666; font-size: 14px;">All times are in timezone <strong>{{globalTimezone}}</strong></p>
        <CalendarReservations
          v-if="showCalendar"
          :propReservations="allReservations || []"
          :readOnly="true"
          @slotSelected="handleSlotSelected"
          @reservationsRefreshed="handleReservationsRefreshed"
          @requestRefresh="fetchAllReservations"
          ref="calendarComponent"
        />
        <Loading v-if="fetchingAllReservations" />
      </v-col>
    </v-row>

    <!-- Activity retention info -->
    <v-row v-if="viewMode === 'activity'" class="justify-center" style="margin-top: 8px; margin-bottom: 0;">
      <v-col cols="12" md="9" class="text-center">
        <span class="filter-summary-text">
          Showing events for your reservations.<template v-if="retentionDescription"> {{ retentionDescription }}</template>
        </span>
      </v-col>
    </v-row>

    <!-- Filters -->
    <v-row v-if="viewMode === 'reservations' && showFilters" class="text-center row-filters justify-center">
      <v-col cols="12" md="3">
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

    <!-- Filter summary -->
    <v-row v-if="viewMode === 'reservations' && !initialLoading && showFilters" class="justify-center" style="margin-top: -8px; margin-bottom: 24px;">
      <v-col cols="12" md="9" class="text-center">
        <span class="filter-summary-text">Showing <strong>{{ reservations.length }}</strong> of <strong>{{ totalItems }}</strong> items for <strong v-if="dateRangeDays !== null">{{ dateRangeDays }} {{ dateRangeDays === 1 ? 'day' : 'days' }}</strong><strong v-else>all time</strong>.</span>
        <a v-if="hasActiveFilters" class="filter-summary-action" @click="resetFilters">Reset Filters</a>
      </v-col>
    </v-row>

    <!-- Reservations data table -->
    <v-row v-if="viewMode === 'reservations' && !initialLoading">
      <v-col cols="12">
        <div style="margin-top: 10px">
          <UserReservationTable
            @emitCancelReservation="cancelReservation"
            @emitExtendReservation="extendReservation"
            @emitRestartContainer="restartContainer"
            @emitShowReservationDetails="showReservationDetails"
            @emitEditDescription="editDescription"
            @update:options="onTableOptionsUpdate"
            :propReservations="reservations"
            :totalItems="totalItems"
            :loading="loading"
            :page="tableOptions.page"
            :itemsPerPage="tableOptions.itemsPerPage"
            :sortBy="tableOptions.sortBy"
          />
        </div>
      </v-col>
    </v-row>
    <v-row v-else-if="viewMode === 'reservations'">
      <v-col cols="12">
        <Loading class="loading" />
      </v-col>
    </v-row>

    <!-- Activity data table -->
    <v-row v-if="viewMode === 'activity' && !activityInitialLoading">
      <v-col cols="12">
        <div style="margin-top: 10px">
          <UserActivityTable
            @update:options="onActivityTableOptionsUpdate"
            :propItems="activity"
            :propReservationSummaries="activityReservationSummaries"
            :propLastSeenAt="activitySeenSnapshot"
            :propNotableActions="activityNotableActions"
            :totalItems="activityTotalItems"
            :loading="activityLoading"
            :page="activityTableOptions.page"
            :itemsPerPage="activityTableOptions.itemsPerPage"
            :sortBy="activityTableOptions.sortBy"
          />
        </div>
      </v-col>
    </v-row>
    <v-row v-else-if="viewMode === 'activity'">
      <v-col cols="12">
        <Loading class="loading" />
      </v-col>
    </v-row>
    <UserReservationsModalConnectionDetails :reservationId="modalConnectionDetailsReservationId" v-on:emitModalClose="closeModalConnectionDetails" v-if="modalConnectionDetailsVisible && modalConnectionDetailsReservationId != null"></UserReservationsModalConnectionDetails>
  </v-container>
</template>

<script>
  /**
   * User-facing reservations dashboard.
   * Displays the user's own reservations (past 3 months) with server-side
   * pagination, sorting, and status filtering. Provides actions to cancel,
   * extend, restart, edit description, and view connection details. Includes
   * an optional calendar view of all current reservations.
   * Enforces per-user active reservation limits using server-provided counts.
   * Data auto-refreshes every 15 seconds.
   */
  import axios from 'axios';
  import Loading from '/src/components/global/Loading.vue';
  import UserReservationTable from '/src/components/user/UserReservationTable.vue';
  import UserActivityTable from '/src/components/user/UserActivityTable.vue';
  import UserReservationsModalConnectionDetails from '/src/components/user/UserReservationsModalConnectionDetails.vue';
  import CalendarReservations from '/src/components/user/CalendarReservations.vue';
  import { useMainStore } from '@/store/store'

  export default {
    name: 'PageUserReservations',

    setup() {
      const store = useMainStore()
      return { store }
    },

    components: {
      Loading,
      UserReservationTable,
      UserActivityTable,
      UserReservationsModalConnectionDetails,
      CalendarReservations
    },
    data: () => ({
      viewMode: 'reservations',
      showFilters: false,
      filters: {
        status: "All",
        dateFrom: '',
        dateTo: '',
      },
      intervalFetchReservations: null,
      intervalFetchActivity: null,
      initialLoading: true,
      loading: false,
      reservations: [],
      totalItems: 0,
      totalReservationCount: 0,
      statusCounts: {},
      activeReservationCount: 0,
      justReserved: false,
      modalConnectionDetailsVisible: false,
      modalConnectionDetailsReservationId: null,
      showCalendar: false,
      allReservations: null,
      fetchingAllReservations: false,
      tableOptions: {
        page: 1,
        itemsPerPage: 10,
        sortBy: [{key: 'reservationId', order: 'desc'}],
      },
      activity: [],
      activityTotalItems: 0,
      activityInitialLoading: true,
      activityLoading: false,
      activityRetentionDays: null,
      activityReservationSummaries: {},
      activityNotableActions: [],
      unreadActivityCount: 0,
      unreadActivityCapped: false,
      activitySeenSnapshot: null,
      activityMarkedSeenForThisOpen: false,
      activityTableOptions: {
        page: 1,
        itemsPerPage: 10,
        sortBy: [{key: 'createdAt', order: 'desc'}],
      },
    }),
    mounted () {
      if (localStorage.getItem("justReserved") === "true") {
        this.justReserved = true;
        localStorage.removeItem("justReserved");
        // Scroll to the success alert after it renders
        this.$nextTick(() => {
          if (this.$refs.reservationSuccessAlert) {
            const el = this.$refs.reservationSuccessAlert.$el || this.$refs.reservationSuccessAlert
            el.scrollIntoView({ behavior: 'smooth', block: 'center' })
          }
        })
        // Refetch after 6 seconds so the new reservation's status has time to update
        setTimeout(() => this.fetchReservations(), 5000);
      }
      this.fetchReservations()
      // Keep updating reservations every 15 seconds
      this.intervalFetchReservations = setInterval(() => { this.fetchReservations()}, 15000)
    },
    methods: {
      getStatusColor(status) {
        if (status == "reserved") return "primary"
        else if (status == "started") return "green"
        else if (status == "stopped") return "grey"
        else if (status == "error") return "red"
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
      /** Switch to the activity view, mark seen once, and start polling. */
      showActivityView() {
        this.viewMode = 'activity';
        this.activityMarkedSeenForThisOpen = false;
        this.fetchActivity();
        this.markActivitySeen();
        clearInterval(this.intervalFetchActivity);
        this.intervalFetchActivity = setInterval(() => { this.fetchActivity() }, 30000);
      },
      /** Switch back to the reservations view and stop activity polling. */
      showReservationsView() {
        this.viewMode = 'reservations';
        clearInterval(this.intervalFetchActivity);
        this.intervalFetchActivity = null;
        // Refresh reservations immediately so the badge clears (unread count
        // is reported from the reservations endpoint).
        this.fetchReservations();
      },
      /**
       * POST mark_activity_seen exactly once per activity-view open.
       * Captures the previous activityLastSeenAt as the snapshot used to
       * highlight "NEW" rows for the rest of this session in the view.
       */
      markActivitySeen() {
        if (this.activityMarkedSeenForThisOpen) return;
        this.activityMarkedSeenForThisOpen = true;
        let _this = this;
        let currentUser = this.store.user;
        axios({
          method: "post",
          url: this.$appSettings.APIServer.reservation.mark_activity_seen,
          headers: {"Authorization": `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
            if (response.data && response.data.status === true && response.data.data) {
              _this.activitySeenSnapshot = response.data.data.previousLastSeenAt || null;
            }
            // Optimistically clear the badge in this view; the next
            // reservations poll will confirm.
            _this.unreadActivityCount = 0;
            _this.unreadActivityCapped = false;
        })
        .catch(function (error) {
            console.log("Failed to mark activity as seen", error);
            // Allow a retry on the next view open.
            _this.activityMarkedSeenForThisOpen = false;
        });
      },
      /** Handles pagination/sort changes from the activity table. */
      onActivityTableOptionsUpdate(options) {
        this.activityTableOptions.page = options.page;
        this.activityTableOptions.itemsPerPage = options.itemsPerPage;
        if (options.sortBy && options.sortBy.length > 0) {
          this.activityTableOptions.sortBy = options.sortBy;
        }
        this.fetchActivity();
      },
      fetchActivity() {
        let _this = this
        let currentUser = this.store.user
        _this.activityLoading = true;

        axios({
          method: "post",
          url: this.$appSettings.APIServer.reservation.get_own_activity,
          data: {
            page: _this.activityTableOptions.page,
            itemsPerPage: _this.activityTableOptions.itemsPerPage,
            sortBy: _this.activityTableOptions.sortBy,
            filters: {},
          },
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
            if (response.data.status == true) {
              _this.activity = response.data.data.logs
              _this.activityTotalItems = response.data.data.totalItems
              if (response.data.data.retentionDays !== undefined) {
                _this.activityRetentionDays = response.data.data.retentionDays
              }
              _this.activityReservationSummaries = response.data.data.reservationSummaries || {}
              _this.activityNotableActions = Array.isArray(response.data.data.notableActions) ? response.data.data.notableActions : []
            }
            else {
              console.log("Failed getting activity...")
              _this.store.showMessage({ text: "There was an error getting your activity.", color: "red" })
            }
            _this.activityLoading = false
            _this.activityInitialLoading = false
        })
        .catch(function (error) {
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.store.showMessage({ text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.store.showMessage({ text: "Unknown error while trying to get activity.", color: "red" })
            }
            _this.activityLoading = false
            _this.activityInitialLoading = false
        });
      },
      /** Handles dropdown filter changes (immediate). */
      onFilterChange() {
        this.tableOptions.page = 1;
        this.fetchReservations();
      },
      /** Reset all filters to defaults. */
      resetFilters() {
        this.filters.status = 'All';
        this.filters.dateFrom = '';
        this.filters.dateTo = '';
        this.tableOptions.page = 1;
        this.fetchReservations();
      },
      closeModalConnectionDetails() {
        this.modalConnectionDetailsVisible = false
      },
      createReservation() {
        // Check against the user's actual limit
        if (this.activeReservationCount >= this.maxActiveReservations) {
          this.store.showMessage({
            text: `You have reached your maximum of ${this.maxActiveReservations} active reservation${this.maxActiveReservations === 1 ? '' : 's'}. Please wait for an existing reservation to complete before creating a new one.`,
            color: "red"
          })
          return
        }

        // User has not reached their limit, allow navigation
        this.$router.push("/user/reserve")
      },
      fetchReservations() {
        let _this = this
        let currentUser = this.store.user
        _this.loading = true;

        axios({
          method: "post",
          url: this.$appSettings.APIServer.reservation.get_own_reservations,
          data: {
            page: _this.tableOptions.page,
            itemsPerPage: _this.tableOptions.itemsPerPage,
            sortBy: _this.tableOptions.sortBy,
            filters: {
              status: _this.filters.status === 'All' ? '' : (_this.filters.status || ''),
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
              _this.activeReservationCount = response.data.data.activeReservationCount || 0
              // Always update status counts and total from server
              _this.statusCounts = response.data.data.statusCounts || {}
              _this.totalReservationCount = (_this.statusCounts.reserved || 0) + (_this.statusCounts.started || 0) + (_this.statusCounts.stopping || 0) + (_this.statusCounts.stopped || 0) + (_this.statusCounts.error || 0) + (_this.statusCounts.paused || 0)
              _this.unreadActivityCount = response.data.data.unreadActivityCount || 0
              _this.unreadActivityCapped = !!response.data.data.unreadActivityCapped
            }
            else {
              console.log("Failed getting own reservations...")
              _this.store.showMessage({ text: "There was an error getting own reservations.", color: "red" })
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
      async extendReservation(reservationId) {
        let extraHours = await this.store.showPromptDialog({
          title: 'Extend Reservation',
          message: 'How many hours do you want to extend for? (Max 24 hours)',
          inputLabel: 'Hours',
          inputType: 'number',
          defaultValue: '1',
          min: 1,
          max: 24,
        })
        if (extraHours == null || extraHours == "") {
          return;
        }

        if (isNaN(extraHours)) {
          this.store.showMessage({ text: "Please type in a number.", color: "red" })
          return;
        }
        if (parseInt(extraHours) > 24 || parseInt(extraHours) < 0) {
          this.store.showMessage({ text: "Please type in a number between 0 and 24.", color: "red" })
          return;
        }

        let params = {
          "reservationId": reservationId,
          "duration": parseInt(extraHours)
        }

        let _this = this
        let currentUser = this.store.user

        axios({
          method: "post",
          url: this.$appSettings.APIServer.reservation.extend_reservation,
          params: params,
          headers: {
            "Authorization" : `Bearer ${currentUser.loginToken}`
          }
        })
        .then(function (response) {
            if (response.data.status == true) {
              _this.store.showMessage({ text: "Reservation was extended succesfully.", color: "green" })
              _this.fetchReservations()
            }
            else {
              let msg = response && response.data && response.data.message ? response.data.message : "There was an error extending."
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
      async editDescription(reservationId, currentDescription) {
        let newDescription = await this.store.showPromptDialog({
          title: 'Edit Reservation Description',
          message: 'Enter a new description (max 40 characters):',
          inputLabel: 'Description',
          defaultValue: currentDescription || '',
          maxlength: 40,
          counter: true,
        })
        if (newDescription === null) return;

        if (newDescription.length > 40) {
          this.store.showMessage({ text: "Description is too long (max 40 characters).", color: "red" })
          return;
        }

        let params = {
          "reservationId": reservationId,
          "description": newDescription
        }

        let _this = this
        let currentUser = this.store.user

        axios({
          method: "post",
          url: this.$appSettings.APIServer.reservation.update_reservation_description,
          params: params,
          headers: {
            "Authorization" : `Bearer ${currentUser.loginToken}`
          }
        })
        .then(function (response) {
            if (response.data.status == true) {
              _this.store.showMessage({ text: "Description updated.", color: "green" })
              _this.fetchReservations()
            }
            else {
              let msg = response && response.data && response.data.message ? response.data.message : "There was an error updating the description."
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
      showReservationDetails(reservationId) {
        this.modalConnectionDetailsVisible = true
        this.modalConnectionDetailsReservationId = reservationId
      },
      toggleCalendarView() {
        this.showCalendar = !this.showCalendar;
        if (this.showCalendar) {
          // Use nextTick to ensure calendar component is mounted before fetching
          this.$nextTick(() => {
            this.fetchAllReservations();
          });
        }
      },
      /** Fetches all current/upcoming reservations for the calendar overlay view. */
      fetchAllReservations() {
        let _this = this;
        _this.fetchingAllReservations = true;
        let currentUser = this.store.user;

        axios({
          method: "get",
          url: this.$appSettings.APIServer.reservation.get_current_reservations,
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
            if (response.data.status == true) {
              _this.allReservations = response.data.data.reservations || [];
            }
            else {
              console.log("Failed getting current reservations...")
              _this.store.showMessage({ text: "There was an error getting current reservations.", color: "red" })
            }
            _this.fetchingAllReservations = false;
        })
        .catch(function (error) {
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.store.showMessage({ text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.store.showMessage({ text: "Unknown error while trying to get current reservations.", color: "red" })
            }
            _this.fetchingAllReservations = false;
        });
      },
       handleSlotSelected() {
         // Check against the user's actual limit
         if (this.activeReservationCount >= this.maxActiveReservations) {
           this.store.showMessage({
             text: `You have reached your maximum of ${this.maxActiveReservations} active reservation${this.maxActiveReservations === 1 ? '' : 's'}. Please wait for an existing reservation to complete before creating a new one.`,
             color: "red"
           })
           return
         }

         // User has not reached their limit, allow navigation
         this.$router.push("/user/reserve");
       },
       async refreshCalendarReservations() {
         if (this.$refs.calendarComponent) {
           await this.$refs.calendarComponent.refreshCalendarData();
         }
       },
       handleReservationsRefreshed(reservations) {
         this.allReservations = reservations;
       },
    },
    computed: {
      statusItems() {
        const items = [
          { title: `All (${this.totalReservationCount})`, value: 'All' },
          { title: `Reserved (${this.statusCounts.reserved || 0})`, value: 'reserved' },
          { title: `Running (${this.statusCounts.started || 0})`, value: 'started' },
          { title: `Paused (${this.statusCounts.paused || 0})`, value: 'paused' },
          { title: `Error (${this.statusCounts.error || 0})`, value: 'error' },
          { title: `Stopped (${this.statusCounts.stopped || 0})`, value: 'stopped' }
        ];
        return items;
      },
      globalTimezone() {
        return this.store.appTimezone;
      },
      maxActiveReservations() {
        return this.store.userMaxActiveReservations;
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
          this.filters.dateFrom || this.filters.dateTo
        );
      },
      retentionDescription() {
        const days = this.activityRetentionDays;
        if (days === -1) return 'Activity logging is currently disabled.';
        if (days && days > 0) return `Activity is kept for ${days} ${days === 1 ? 'day' : 'days'}.`;
        return '';
      },
      unreadActivityBadgeText() {
        if (this.unreadActivityCapped) return '99+';
        return String(this.unreadActivityCount);
      },
    },
    beforeUnmount() {
      clearInterval(this.intervalFetchReservations)
      clearInterval(this.intervalFetchActivity)
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

  .activity-badge {
    margin-left: 4px;
  }
</style>

<style lang="scss">
  .reservation-success-alert {
    position: relative;

    .v-alert__close {
      position: absolute !important;
      top: 10px !important;
      right: 10px !important;
      margin: 0 !important;
      padding: 0 !important;
      flex: none !important;
      grid-area: unset !important;
    }
  }
</style>
