<template>
  <v-container>

    <v-row class="text-center">
      <v-col cols="12">
        <h4>Admin</h4>
        <h2>All Reservations</h2>
        <p class="dim">Listing reservations from past 3 months</p>
      </v-col>
    </v-row>

    <!-- Statistics Cards -->
    <div v-if="!isFetchingReservations" id="stats-row">
      <!-- Status Statistics -->
      <v-row class="mb-4 justify-center">
        <v-col cols="12" sm="6" md="2">
          <v-card outlined>
            <v-card-text class="text-center">
              <v-icon size="24" color="blue-grey" class="mb-2">mdi-chart-bar</v-icon>
              <div class="text-h6 font-weight-bold">{{ stats.total }}</div>
              <div class="text-subtitle-2">Total</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="2">
          <v-card outlined>
            <v-card-text class="text-center">
              <v-icon size="24" color="green" class="mb-2">mdi-play-circle</v-icon>
              <div class="text-h6 font-weight-bold text--primary" style="color: #4CAF50 !important;">{{ stats.started }}</div>
              <div class="text-subtitle-2">Running</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="2">
          <v-card outlined>
            <v-card-text class="text-center">
              <v-icon size="24" color="orange" class="mb-2">mdi-stop-circle</v-icon>
              <div class="text-h6 font-weight-bold" style="color: #FF9800 !important;">{{ stats.stopped }}</div>
              <div class="text-subtitle-2">Stopped</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="2">
          <v-card outlined>
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
          <v-card outlined>
            <v-card-text class="text-center">
              <v-icon size="24" color="primary" class="mb-2">mdi-calendar-today</v-icon>
              <div class="text-h6 font-weight-bold text-primary">{{ stats.today }}</div>
              <div class="text-subtitle-2">Today</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="2">
          <v-card outlined>
            <v-card-text class="text-center">
              <v-icon size="24" color="primary" class="mb-2">mdi-calendar-week</v-icon>
              <div class="text-h6 font-weight-bold text-primary">{{ stats.lastWeek }}</div>
              <div class="text-subtitle-2">Week</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="2">
          <v-card outlined>
            <v-card-text class="text-center">
              <v-icon size="24" color="primary" class="mb-2">mdi-calendar-month</v-icon>
              <div class="text-h6 font-weight-bold text-primary">{{ stats.lastMonth }}</div>
              <div class="text-subtitle-2">Month</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="2">
          <v-card outlined>
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
    <v-row class="text-center row-filters justify-center" v-if="!isFetchingReservations">
      <v-col cols="12" md="3">
        <v-select
          :items="statusItems"
          label="Status"
          v-model="filters.status"
          item-text="text"
          item-value="value"
          return-object
          @change="applyFilters"
        ></v-select>
      </v-col>
      <v-col cols="12" md="2">
        <v-text-field
          v-model="filters.reservationId"
          label="Reservation ID"
          clearable
          @input="applyFilters"
        ></v-text-field>
      </v-col>
    </v-row>

    <v-row v-if="!isFetchingReservations" style="margin-top: 0px">
        <v-col cols="12" style="padding-top: 0px">
          <v-slide-x-transition mode="out-in">
            <div v-if="filteredReservations && filteredReservations.length > 0">
              <AdminReservationTable @emitCancelReservation="cancelReservation" @emitChangeEndDate="changeEndDate" @emitRestartContainer="restartContainer" @emitShowReservationDetails="showReservationDetails" v-bind:propReservations="filteredReservations" />
            </div>
          
            <p v-else class="dim text-center">{{ reservations.length > 0 ? 'No reservations match the filters.' : 'No reservations found.' }}</p>
          </v-slide-x-transition>
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
  const axios = require('axios').default;
  import Loading from '/src/components/global/Loading.vue';
  import AdminReservationTable from '/src/components/admin/AdminReservationTable.vue';
  import UserReservationsModalConnectionDetails from '/src/components/user/UserReservationsModalConnectionDetails.vue';
  
  export default {
    name: 'PageUserReservations',

    components: {
      Loading,
      AdminReservationTable,
      UserReservationsModalConnectionDetails
    },
    data: () => ({
      intervalFetchReservations: null,
      isFetchingReservations: true,
      reservations: [],
      justReserved: false,
      informByEmail: false,
      modalConnectionDetailsVisible: false,
      modalConnectionDetailsReservationId: null,
      filters: { 
        status: { text: "All", value: "All" },
        reservationId: ''
      },
      filteredReservations: [],
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
      }
    }),
    computed: {
      statusItems() {
        const items = [
          { text: `All (${this.reservations.length})`, value: 'All' },
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

      this.isFetchingReservations = true
      this.fetchReservations()
      // Keep updating reservations every 15 seconds
      this.intervalFetchReservations = setInterval(() => { this.fetchReservations()}, 15000)
    },
    methods: {
      applyFilters() {
        let filtered = this.reservations;
        
        // Filter by Status
        if (this.filters.status && this.filters.status.value !== 'All') {
          filtered = filtered.filter(reservation => 
            reservation.status === this.filters.status.value
          );
        }
        
        // Filter by Reservation ID
        if (this.filters.reservationId && this.filters.reservationId.trim() !== '') {
          filtered = filtered.filter(reservation => 
            reservation.reservationId.toString().toLowerCase().includes(this.filters.reservationId.toLowerCase().trim())
          );
        }
        
        this.filteredReservations = filtered;
        this.updateStats();
      },
      setFilters() {
        this.fetchReservations()
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
          if ((res.status == "started" || res.status == "reserved") && res.userEmail === this.$store.getters.user.email) {
            activeReservationCount++
          }
        })

        // Get user's reservation limits from store
        const maxActiveReservations = this.$store.getters.userMaxActiveReservations

        // Check against the user's actual limit
        if (activeReservationCount >= maxActiveReservations) {
          this.$store.commit('showMessage', { 
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
        let currentUser = this.$store.getters.user
        
        let filters = {}
        Object.keys(_this.filters).forEach(function(key) {
          if (_this.filters[key] == "All" || typeof _this.filters[key] !== 'string') filters[key] = ""
          else filters[key] = _this.filters[key]
        });

        axios({
          method: "post",
          url: this.AppSettings.APIServer.admin.get_reservations,
          data: { filters: filters },
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
          //console.log(response)
            // Success
            if (response.data.status == true) {
              _this.reservations = response.data.data.reservations
              _this.statusCounts = response.data.data.statusCounts || {}
              _this.applyFilters()
            }
            // Fail
            else {
              console.log("Failed getting own reservations...")
              _this.$store.commit('showMessage', { text: "There was an error getting own reservations.", color: "red" })
            }
            _this.isFetchingReservations = false
        })
        .catch(function (error) {
            // Error
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.$store.commit('showMessage', { text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.$store.commit('showMessage', { text: "Unknown error while trying to get reservations.", color: "red" })
            }
            _this.isFetchingReservations = false
        });
      },
      changeEndDate(reservationId, currentEndDate) {
        let newEndDate = prompt("Enter new end date", currentEndDate);
        if (newEndDate == null || newEndDate == currentEndDate || newEndDate == "") {
          this.$store.commit('showMessage', { text: "Not changing end date.", color: "blue" })
          return;
        }
        this.$store.commit('showMessage', { text: "Changing end date.", color: "green" })

        let params = {
          "reservationId": reservationId,
          "endDate": newEndDate
        }

        let _this = this
        let currentUser = this.$store.getters.user

        axios({
          method: "post",
          url: this.AppSettings.APIServer.admin.edit_reservation,
          params: params,
          headers: {
            "Authorization" : `Bearer ${currentUser.loginToken}`
          }
        })
        .then(function (response) {
          //console.log(response)
            // Success
            if (response.data.status == true) {
              _this.$store.commit('showMessage', { text: "Reservation edited.", color: "green" })
              _this.fetchReservations()
            }
            // Fail
            else {
              console.log("Failed editing reservation...")
              console.log(response)
              let msg = response && response.data && response.data.message ? response.data.message : "There was an error editing the reservation."
              _this.$store.commit('showMessage', { text: msg, color: "red" })
            }
        })
        .catch(function (error) {
            // Error
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.$store.commit('showMessage', { text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.$store.commit('showMessage', { text: "Unknown error.", color: "red" })
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
        let currentUser = this.$store.getters.user

        axios({
          method: "post",
          url: this.AppSettings.APIServer.reservation.cancel_reservation,
          params: params,
          headers: {
            "Authorization" : `Bearer ${currentUser.loginToken}`
          }
        })
        .then(function (response) {
          //console.log(response)
            // Success
            if (response.data.status == true) {
              _this.$store.commit('showMessage', { text: "Reservation cancelled.", color: "green" })
              _this.fetchReservations()
            }
            // Fail
            else {
              console.log("Failed removing reservation...")
              console.log(response)
              let msg = response && response.data && response.data.message ? response.data.message : "There was an error getting the hardware specs."
              _this.$store.commit('showMessage', { text: msg, color: "red" })
            }
            _this.cancellingReservation = false
        })
        .catch(function (error) {
            // Error
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.$store.commit('showMessage', { text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.$store.commit('showMessage', { text: "Unknown error.", color: "red" })
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
        let currentUser = this.$store.getters.user

        axios({
          method: "post",
          url: this.AppSettings.APIServer.reservation.restart_container,
          params: params,
          headers: {
            "Authorization" : `Bearer ${currentUser.loginToken}`
          }
        })
        .then(function (response) {
          //console.log(response)
            // Success
            if (response.data.status == true) {
              _this.$store.commit('showMessage', { text: "Container restarted succesfully.", color: "green" })
              _this.fetchReservations()
            }
            // Fail
            else {
              console.log("Failed restarting container...")
              console.log(response)
              let msg = response && response.data && response.data.message ? response.data.message : "There was an error getting the hardware specs."
              _this.$store.commit('showMessage', { text: msg, color: "red" })
            }
            _this.restartingContainer = false
        })
        .catch(function (error) {
            // Error
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.$store.commit('showMessage', { text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.$store.commit('showMessage', { text: "Unknown error.", color: "red" })
            }
            _this.restartingContainer = false
        });
      },
      showReservationDetails(reservationId) {
        this.modalConnectionDetailsVisible = true
        this.modalConnectionDetailsReservationId = reservationId
      },
      updateStats() {
        const now = new Date()
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
        const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
        const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
        const threeMonthsAgo = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000)
        
        // Always use all reservations for statistics
        this.stats.total = this.reservations.length
        this.stats.started = this.reservations.filter(r => r.status === 'started').length
        this.stats.stopped = this.reservations.filter(r => r.status === 'stopped').length
        this.stats.error = this.reservations.filter(r => r.status === 'error').length
        
        this.stats.today = this.reservations.filter(r => {
          const startDate = new Date(r.startDate)
          return startDate >= today
        }).length

        this.stats.lastWeek = this.reservations.filter(r => {
          const startDate = new Date(r.startDate)
          return startDate >= weekAgo
        }).length

        this.stats.lastMonth = this.reservations.filter(r => {
          const startDate = new Date(r.startDate)
          return startDate >= monthAgo
        }).length

        this.stats.lastThreeMonths = this.reservations.filter(r => {
          const startDate = new Date(r.startDate)
          return startDate >= threeMonthsAgo
        }).length
      }
    },
    beforeDestroy() {
      clearInterval(this.intervalFetchReservations)
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