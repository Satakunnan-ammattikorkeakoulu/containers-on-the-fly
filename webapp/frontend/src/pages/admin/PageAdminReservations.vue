<template>
  <v-container>

    <v-row class="text-center">
      <v-col cols="12">
        <h4 class="m-0">Admin</h4>
        <h2 class="m-0">All Reservations</h2>
        <p class="dim m-0 mb-40">Listing reservations from past 3 months</p>
      </v-col>
    </v-row>

    <!-- Statistics Cards -->
    <div v-if="!initialLoading" id="stats-row">
      <!-- Status Statistics -->
      <v-row class="mb-4 justify-center">
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
              <div class="text-h6 font-weight-bold text--primary" style="color: #4CAF50 !important;">{{ stats.started }}</div>
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

      <!-- Time-based Statistics -->
      <v-row class="mb-6 justify-center">
        <v-col cols="12" sm="6" md="2">
          <v-card variant="outlined">
            <v-card-text class="text-center">
              <v-icon size="24" color="primary" class="mb-2">mdi-calendar-today</v-icon>
              <div class="text-h6 font-weight-bold text-primary">{{ stats.today }}</div>
              <div class="text-subtitle-2">Today</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="2">
          <v-card variant="outlined">
            <v-card-text class="text-center">
              <v-icon size="24" color="primary" class="mb-2">mdi-calendar-week</v-icon>
              <div class="text-h6 font-weight-bold text-primary">{{ stats.lastWeek }}</div>
              <div class="text-subtitle-2">Week</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="2">
          <v-card variant="outlined">
            <v-card-text class="text-center">
              <v-icon size="24" color="primary" class="mb-2">mdi-calendar-month</v-icon>
              <div class="text-h6 font-weight-bold text-primary">{{ stats.lastMonth }}</div>
              <div class="text-subtitle-2">Month</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="2">
          <v-card variant="outlined">
            <v-card-text class="text-center">
              <v-icon size="24" color="primary" class="mb-2">mdi-calendar-range</v-icon>
              <div class="text-h6 font-weight-bold text-primary">{{ stats.lastThreeMonths }}</div>
              <div class="text-subtitle-2">3 Months</div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </div>

    <!-- Filters -->
    <v-row class="text-center row-filters justify-center" v-if="!initialLoading">
      <v-col cols="12" md="3">
        <v-select
          :items="statusItems"
          label="Status"
          v-model="filters.status"
          item-title="text"
          item-value="value"
          @update:model-value="onFilterChange"
        ></v-select>
      </v-col>
      <v-col cols="12" md="2">
        <v-text-field
          v-model="filters.reservationId"
          label="Reservation ID"
          clearable
          @update:model-value="onTextFilterChange"
        ></v-text-field>
      </v-col>
    </v-row>

    <v-row v-if="!initialLoading" style="margin-top: 0px">
        <v-col cols="12" style="padding-top: 0px">
          <AdminReservationTable
            @emitCancelReservation="cancelReservation"
            @emitChangeEndDate="changeEndDate"
            @emitRestartContainer="restartContainer"
            @emitShowReservationDetails="showReservationDetails"
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
      intervalFetchReservations: null,
      initialLoading: true,
      loading: false,
      reservations: [],
      totalItems: 0,
      justReserved: false,
      informByEmail: false,
      modalConnectionDetailsVisible: false,
      modalConnectionDetailsReservationId: null,
      filters: {
        status: "All",
        reservationId: ''
      },
      statusCounts: {},
      stats: {
        total: 0,
        started: 0,
        stopped: 0,
        error: 0,
        today: 0,
        lastWeek: 0,
        lastMonth: 0,
        lastThreeMonths: 0
      },
      tableOptions: {
        page: 1,
        itemsPerPage: 10,
        sortBy: [{key: 'reservationId', order: 'desc'}],
      },
      debounceTimer: null,
    }),
    computed: {
      statusItems() {
        const items = [
          { text: `All (${this.statusCounts.reserved + this.statusCounts.started + this.statusCounts.stopped + this.statusCounts.error || 0})`, value: 'All' },
          { text: `reserved (${this.statusCounts.reserved || 0})`, value: 'reserved' },
          { text: `started (${this.statusCounts.started || 0})`, value: 'started' },
          { text: `stopped (${this.statusCounts.stopped || 0})`, value: 'stopped' },
          { text: `error (${this.statusCounts.error || 0})`, value: 'error' }
        ];
        return items;
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
      /** Handles pagination/sort changes from the data table. */
      onTableOptionsUpdate(options) {
        this.tableOptions.page = options.page;
        this.tableOptions.itemsPerPage = options.itemsPerPage;
        if (options.sortBy && options.sortBy.length > 0) {
          this.tableOptions.sortBy = options.sortBy;
        }
        this.fetchReservations();
      },
      /** Handles dropdown filter changes (immediate). */
      onFilterChange() {
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
              reservationId: _this.filters.reservationId || '',
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
      changeEndDate(reservationId, currentEndDate) {
        let newEndDate = prompt("Enter new end date", currentEndDate);
        if (newEndDate == null || newEndDate == currentEndDate || newEndDate == "") {
          this.store.showMessage({ text: "Not changing end date.", color: "blue" })
          return;
        }
        this.store.showMessage({ text: "Changing end date.", color: "green" })

        let params = {
          "reservationId": reservationId,
          "endDate": newEndDate
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
      cancelReservation(reservationId) {
        let result = window.confirm("Do you really want to cancel this reservation?")
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
      restartContainer(reservationId) {
        let result = window.confirm("Do you really want to restart the docker container?")
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

  #stats-row .row.mb-4, #stats-row .row.mb-6 {
    margin-bottom: 0px !important;
    margin-top: 0px !important;
  }
</style>
