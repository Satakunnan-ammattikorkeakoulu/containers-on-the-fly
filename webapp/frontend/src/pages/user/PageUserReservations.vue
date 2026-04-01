<template>
  <v-container>
    <v-row class="text-center section">
      <v-col>
        <v-btn color="success" large @click="createReservation">Reserve Server</v-btn>
        <br>
        <p style="color: grey; font-size: 13px; margin-top: 8px; margin-bottom: 0px;">{{ activeReservationCount }} of {{ maxActiveReservations }} active reservations</p>
        <a @click="toggleCalendarView" style="margin-top: 15px; display: inline-block; font-size: 13px;">
          {{ showCalendar ? 'hide reservation calendar' : 'show reservation calendar' }}
        </a>
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

    <v-row class="text-center" v-if="justReserved">
      <v-col cols="1"></v-col>
      <v-col cols="10">
        <v-alert type="info" :icon="false" closable v-model="justReserved" class="text-center reservation-success-alert">
          <h3 style="margin-bottom: 15px;">Reservation created succesfully</h3>
          <p>Your server has been reserved. You can view the details on how to access the server from this page after the container has been started.</p>
          <p v-if="informByEmail">You will also be emailed the connection details after the container starts.</p>
        </v-alert>
      </v-col>
      <v-col cols="1"></v-col>
    </v-row>

    <!-- Title -->
    <v-row class="text-center">
      <v-col cols="12">
        <h2 class="m-0">Your Reservations</h2>
        <p class="dim m-0">Listing reservations from past 3 months</p>
      </v-col>
    </v-row>

    <!-- Filters -->
    <v-row class="text-center row-filters">
      <v-row>
        <v-col cols="3" style="margin: 0 auto;">
          <v-select
            :items="statusItems"
            label="Status"
            v-model="filters.status"
            item-title="text"
            item-value="value"
            @update:model-value="onFilterChange"
          ></v-select>
        </v-col>
      </v-row>
    </v-row>

    <!-- Data table -->
    <v-row v-if="!initialLoading">
      <v-col cols="12">
        <div style="margin-top: 50px">
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
      UserReservationsModalConnectionDetails,
      CalendarReservations
    },
    data: () => ({
      filters: { status: "All" },
      intervalFetchReservations: null,
      initialLoading: true,
      loading: false,
      reservations: [],
      totalItems: 0,
      totalReservationCount: 0,
      statusCounts: {},
      activeReservationCount: 0,
      justReserved: false,
      informByEmail: false,
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
    }),
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
              _this.totalReservationCount = (_this.statusCounts.reserved || 0) + (_this.statusCounts.started || 0) + (_this.statusCounts.stopped || 0) + (_this.statusCounts.error || 0) + (_this.statusCounts.paused || 0)
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
      extendReservation(reservationId) {
        let extraHours = prompt("How many hours do you want to extend for? (Max 24 hours). Type for example: 12", "");
        if (extraHours == null|| extraHours == "") {
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
      editDescription(reservationId, currentDescription) {
        let newDescription = prompt("Enter a new description (max 50 characters):", currentDescription || "");
        if (newDescription === null) return;

        if (newDescription.length > 50) {
          this.store.showMessage({ text: "Description is too long (max 50 characters).", color: "red" })
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
          { text: `All (${this.totalReservationCount})`, value: 'All' },
          { text: `Reserved (${this.statusCounts.reserved || 0})`, value: 'reserved' },
          { text: `Running (${this.statusCounts.started || 0})`, value: 'started' },
          { text: `Paused (${this.statusCounts.paused || 0})`, value: 'paused' },
          { text: `Stopped (${this.statusCounts.stopped || 0})`, value: 'stopped' },
          { text: `Error (${this.statusCounts.error || 0})`, value: 'error' }
        ];
        return items;
      },
      globalTimezone() {
        return this.store.appTimezone;
      },
      maxActiveReservations() {
        return this.store.userMaxActiveReservations;
      }
    },
    beforeUnmount() {
      clearInterval(this.intervalFetchReservations)
    },
  }
</script>

<style scoped lang="scss">
  .loading {
    margin: 60px auto;
  }

  .row-filters {
    .col-3 {
      padding-top: 30px;
      padding-bottom: 0px;
    }
  }
</style>

<style lang="scss">
  .reservation-success-alert {
    position: relative;

    .v-alert__close {
      position: absolute !important;
      top: 0 !important;
      right: 0 !important;
      margin: 0 !important;
      padding: 0 !important;
      flex: none !important;
      grid-area: unset !important;
    }
  }
</style>
