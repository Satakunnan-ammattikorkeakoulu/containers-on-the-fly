<template>
  <div class="text-center">
    <v-dialog v-model="isOpen" width="500">
      <v-card>
        <v-card-title class="text-h5 lighten-2">
          Connecting to Container
        </v-card-title>

        <v-card-text v-html="text" v-if="!isLoading">
        </v-card-text>

        <Loading style="margin: 60px 0px;" v-if="isLoading"></Loading>

        <v-divider></v-divider>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" text @click="isOpen = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
  import Loading from '/src/components/global/Loading.vue';
  const axios = require('axios').default;

  export default {
    components: {
      Loading
    },
    name: 'UserReservationsModalConnectionDetails',
    props: {
      reservationId: {
        type: Number,
        required: false
      }
    },
    data: () => ({
      isOpen: true,
      text: "",
      isLoading: true,
    }),
    mounted () {
      let _this = this
      let currentUser = this.$store.getters.user

      this.text = ""
      if (this.reservationId != null) {
        //console.log("Mounted and got res id: " + this.reservationId)
      }
      axios({
          method: "get",
          url: this.AppSettings.APIServer.reservation.get_own_reservation_details,
          params: { "reservationId": this.reservationId },
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
          //console.log(response)´
          _this.text = response.data.data.connectionText
          _this.isLoading = false
        })
        .catch(function (error) {
          console.log(error)
          _this.isLoading = false
        });
    },
    watch: {
      isOpen: function(newVal) {
        if (newVal === false) {
          this.$emit("emitModalClose");
        }
      },
      reservationId: function() {
        /*if (newVal !== this.reservationId) {
          console.log("Reservation ID changed to: " + newVal)
        }*/
      },
    }
  }
</script>

<style scoped lang="scss">
</style>