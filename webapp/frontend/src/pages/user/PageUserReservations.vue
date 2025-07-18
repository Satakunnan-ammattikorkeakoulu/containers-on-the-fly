<template>
  <v-container>
    <v-row class="text-center section">
      <v-col>
        <v-btn color="success" large @click="createReservation">Reserve Server</v-btn>
        <br>
        <p style="color: grey; font-size: 13px; margin-top: 8px; margin-bottom: 0px;">or</p>
        <a @click="toggleCalendarView" style="margin-top: 8px; display: inline-block; font-size: 13px;">
          {{ showCalendar ? 'hide reservation calendar' : 'show reservation calendar' }}
        </a>
      </v-col>
    </v-row>

    <!-- Reservation Calendar -->
    <v-row v-if="showCalendar" class="section">
      <v-col cols="12">
        <h3 style="margin-bottom: 20px;">Reservation Calendar</h3>
        <div style="text-align: right; margin-bottom: 10px;">
          <p style="margin-bottom: 0px;"><small>All times are in timezone <strong>{{globalTimezone}}</strong></small></p>
          <p><small><a @click="fetchAllReservations">Refresh reservations</a></small></p>
        </div>
        <CalendarReservations 
          v-if="allReservations" 
          :propReservations="allReservations" 
          :readOnly="true"
          @slotSelected="handleSlotSelected" 
        />
        <Loading v-if="fetchingAllReservations" />
      </v-col>
    </v-row>

    <v-row class="text-center" v-if="justReserved">
      <v-col cols="1"></v-col>
      <v-col cols="10">
        <v-alert type="info" :icon="false" dismissible>
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
        <h2>Your Reservations</h2>
        <p class="dim">Listing reservations from past 3 months</p>
      </v-col>
    </v-row>

    <!-- Filters -->
    <v-row class="text-center row-filters">
      <v-row>
        <v-col cols="3" style="margin: 0 auto;">
          <v-select
            :items="['All', 'reserved', 'started', 'stopped', 'error']"
            label="Status"
            v-model="filters.status"
            item-text="text"
            item-value="value"
            return-object
            @change="setFilters"
          ></v-select>
        </v-col>
      </v-row>
    </v-row>

    <!-- Data table -->
    <v-row v-if="!isFetchingReservations">
      <v-col cols="12">
        <v-slide-x-transition mode="out-in">
          <div v-if="reservations && reservations.length > 0" style="margin-top: 50px">
            <UserReservationTable @emitCancelReservation="cancelReservation" @emitExtendReservation="extendReservation" @emitRestartContainer="restartContainer" @emitShowReservationDetails="showReservationDetails" v-bind:propReservations="reservations" />
          </div>
          <p v-else class="dim text-center">No reservations found.</p>
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
  import UserReservationTable from '/src/components/user/UserReservationTable.vue';
  import UserReservationsModalConnectionDetails from '/src/components/user/UserReservationsModalConnectionDetails.vue';
  import CalendarReservations from '/src/components/user/CalendarReservations.vue';
  import AppSettings from '/src/AppSettings.js';
  
  export default {
    name: 'PageUserReservations',

    components: {
      Loading,
      UserReservationTable,
      UserReservationsModalConnectionDetails,
      CalendarReservations
    },
    data: () => ({
      filters: { status: { text: "All", value: "All" } },
      intervalFetchReservations: null,
      isFetchingReservations: true,
      reservations: [],
      justReserved: false,
      informByEmail: false,
      modalConnectionDetailsVisible: false,
      modalConnectionDetailsReservationId: null,
      showCalendar: false,
      allReservations: [],
      fetchingAllReservations: false,
      AppSettings: AppSettings
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

      this.isFetchingReservations = true
      this.fetchReservations()
      // Keep updating reservations every 15 seconds
      this.intervalFetchReservations = setInterval(() => { this.fetchReservations()}, 15000)
    },
    methods: {
      setFilters() {
        this.fetchReservations()
      },
      closeModalConnectionDetails() {
        this.modalConnectionDetailsVisible = false
      },
      createReservation() {
        let hasActiveReservations = false
        this.reservations.forEach((res) => {
          if (res.status == "started" || res.status == "reserved") hasActiveReservations = true
        })

        let currentUser = this.$store.getters.user

        if (!hasActiveReservations || currentUser.role == "admin")
          this.$router.push("/user/reserve")
        else
          this.$store.commit('showMessage', { text: "You can only have one reserved or started reservation at a time. Cancel the current reservation if you need a new.", color: "red" })
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
          url: this.AppSettings.APIServer.reservation.get_own_reservations,
          data: { filters: filters },
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
          //console.log(response)
            // Success
            if (response.data.status == true) {
              _this.reservations = response.data.data.reservations
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
      extendReservation(reservationId) {
        let extraHours = prompt("How many hours do you want to extend for? (Max 24 hours). Type for example: 12", "");
        if (extraHours == null|| extraHours == "") {
          return;
        }

        if (isNaN(extraHours)) {
          this.$store.commit('showMessage', { text: "Please type in a number.", color: "red" })
          return;
        }
        if (parseInt(extraHours) > 24 || parseInt(extraHours) < 0) {
          this.$store.commit('showMessage', { text: "Please type in a number between 0 and 24.", color: "red" })
          return;
        }

        let params = {
          "reservationId": reservationId,
          "duration": parseInt(extraHours)
        }

        let _this = this
        let currentUser = this.$store.getters.user

        axios({
          method: "post",
          url: this.AppSettings.APIServer.reservation.extend_reservation,
          params: params,
          headers: {
            "Authorization" : `Bearer ${currentUser.loginToken}`
          }
        })
        .then(function (response) {
          //console.log(response)
            // Success
            if (response.data.status == true) {
              _this.$store.commit('showMessage', { text: "Reservation was extended succesfully.", color: "green" })
              _this.fetchReservations()
            }
            // Fail
            else {
              let msg = response && response.data && response.data.message ? response.data.message : "There was an error extending."
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
      toggleCalendarView() {
        this.showCalendar = !this.showCalendar;
        if (this.showCalendar) {
          this.fetchAllReservations();
        }
      },
      fetchAllReservations() {
        let _this = this;
        _this.fetchingAllReservations = true;
        let currentUser = this.$store.getters.user;

        axios({
          method: "get",
          url: this.AppSettings.APIServer.reservation.get_current_reservations,
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
          //console.log(response)
            // Success
            if (response.data.status == true) {
              _this.allReservations = response.data.data.reservations;
            }
            // Fail
            else {
              console.log("Failed getting current reservations...")
              _this.$store.commit('showMessage', { text: "There was an error getting current reservations.", color: "red" })
            }
            _this.fetchingAllReservations = false;
        })
        .catch(function (error) {
            // Error
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.$store.commit('showMessage', { text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.$store.commit('showMessage', { text: "Unknown error while trying to get current reservations.", color: "red" })
            }
            _this.fetchingAllReservations = false;
        });
      },
       handleSlotSelected() {
         // Check if user already has active reservations
         let hasActiveReservations = false;
         this.reservations.forEach((res) => {
           if (res.status == "started" || res.status == "reserved") hasActiveReservations = true;
         });

         let currentUser = this.$store.getters.user;

         if (!hasActiveReservations || currentUser.role == "admin") {
           // Navigate to reservation page and let it handle the selected time
           this.$router.push("/user/reserve");
         } else {
           this.$store.commit('showMessage', { text: "You can only have one reserved or started reservation at a time. Cancel the current reservation if you need a new.", color: "red" });
         }
       }
    },
    computed: {
      globalTimezone() {
        return Intl.DateTimeFormat().resolvedOptions().timeZone;
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
    .col-3 {
      padding-top: 30px;
      padding-bottom: 0px;
    }
  }
</style>