<template>
  <v-container>
    <v-row class="text-center section">
      <v-col>
        <v-btn color="success" large @click="createReservation">Reserve Server</v-btn>
      </v-col>
    </v-row>

    <v-row class="text-center">
      <v-col cols="12">
        <h2>Your Reservations</h2>
        <p class="dim">Listing reservations from past 3 months</p>
      </v-col>
    </v-row>

    <v-row v-if="!isFetchingReservations">
      <v-col cols="12">
        <div v-if="reservations && reservations.length > 0" style="margin-top: 50px">
          <UserReservationTable @emitCancelReservation="cancelReservation" v-bind:propReservations="reservations" />
        </div>
        <p v-else class="dim text-center">No servers reserved yet.</p>
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
  const axios = require('axios').default;
  import Loading from '/src/components/global/Loading.vue';
  import UserReservationTable from '/src/components/user/UserReservationTable.vue';
  
  export default {
    name: 'PageUserReservations',

    components: {
      Loading,
      UserReservationTable,
    },
    data: () => ({
      intervalFetchReservations: null,
      isFetchingReservations: false,
      reservations: [],
    }),
    mounted () {
      this.isFetchingReservations = true
      this.fetchReservations()
      // Keep updating reservations every 15 seconds
      this.intervalFetchReservations = setInterval(() => { this.fetchReservations()}, 15000)
    },
    methods: {
      createReservation() {
        let hasActiveReservations = false
        this.reservations.forEach((res) => {
          if (res.status == "started" || res.status == "reserved") hasActiveReservations = true
        })

        let currentUser = this.$store.getters.user

        if (!hasActiveReservations || currentUser.role == "admin")
          this.$router.push("/user/reserve")
        else
          this.$store.commit('showMessage', { text: "You can only have one reserved or started reservation at a time. Cancel the current if you need new.", color: "red" })
      },
      fetchReservations() {
        let _this = this
        let currentUser = this.$store.getters.user
        
        axios({
          method: "get",
          url: this.AppSettings.APIServer.reservation.get_own_reservations,
          //params: { }
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

        this.isFetchingReservations = false
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
</style>