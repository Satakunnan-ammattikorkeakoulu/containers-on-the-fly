<template>
  <v-container class="text-center">

  <v-stepper v-model="step">
    <v-stepper-header>
      <v-stepper-step :complete="step > 1" step="1"><b>Time</b></v-stepper-step>
      <v-divider></v-divider>
      <v-stepper-step :complete="step > 2" step="2"><b>Duration</b></v-stepper-step>
      <v-divider></v-divider>
      <v-stepper-step step="3"><b>Hardware</b></v-stepper-step>
    </v-stepper-header>

    <v-stepper-items>
      <!-- STEP 1: CALENDAR -->
      <v-stepper-content step="1">
        <v-row>
          <v-col>
            <h1>Reserve Server</h1>
            <p class="dim">Click on a time on the calendar or <b><a @click="reserveNow">click here</a></b> to make a reservation right now.</p>
          </v-col>
        </v-row>
        <v-row>
          <v-col class="section">
            <CalendarReservations v-if="allReservations" :propReservations="allReservations" @slotSelected="slotSelected" />
          </v-col>
        </v-row>
      </v-stepper-content>

      <!-- STEP 2: DURATION -->
      <v-stepper-content step="2">
        <v-row v-if="reserveDate != null" class="section">
          <v-col cols="12" style="margin: 0 auto">
            <h2>Reservation Time</h2>
            <p>{{parsedTime}}</p>
          </v-col>
          <v-col cols="3" style="margin: 0 auto">
            <h2>Reservation duration</h2>
            <v-select v-model="reserveDuration" :items="reservableHours" item-text="text" item-value="value" label="Duration"></v-select>
          </v-col>
        </v-row>

        <v-btn text @click="prevStep()" style="margin-right: 7px">Back</v-btn>

        <v-btn color="primary" @click="fetchAvailableHardware" :disabled="!reserveDuration && !fetchingComputers">Continue</v-btn>
        <Loading v-if="fetchingComputers" />
      </v-stepper-content>

      <!-- STEP 3: HARDWARE -->
      <v-stepper-content step="3">
        <v-btn @click="prevStep()">&larr; Back</v-btn>
        <br>
        <br>

        <!-- Select container -->
        <v-row v-if="reserveDate != null && reserveDuration !== null && !fetchingComputers && allComputers">
          <v-col cols="12">
            <h2>Select Container</h2>
            <v-row>
              <v-col cols="3" style="margin: 0 auto">
                <v-select v-model="container" :items="containers" item-text="text" item-value="value" label="Container"></v-select>
              </v-col>
            </v-row>
          </v-col>
        </v-row>

        <!-- Select computer, hardware specs & submit -->
        <v-row v-if="reserveDate != null && reserveDuration !== null && !fetchingComputers && allComputers && container" class="section">      
          <v-col cols="12">
            <h2>Select Computer</h2>
            <v-row>
              <v-col cols="3" style="margin: 0 auto">
                <v-select v-model="computer" v-on:change="computerChanged" :items="computers" item-text="text" item-value="value" label="Computer"></v-select>
              </v-col>
            </v-row>
          </v-col>

          <v-row v-if="computer && hardwareData">
            <v-col cols="12">
              <h2>Select Hardware</h2>
              <v-row v-for="spec in hardwareData" :key="spec.name" class="spec-row">
                <v-col cols="12">
                  <h3>{{ spec.type }}</h3>
                </v-col>
                <v-col cols="6" style="margin: 0 auto">
                  <v-slider :min="spec.minimumAmount" :thumb-size="60" ticks="always" v-model="selectedHardwareSpecs[spec.hardwareSpecId]" :max="spec.maximumAmountForUser" thumb-label="always">
                    <template v-slot:thumb-label="{ value }">
                      {{ value + " " + spec.format }}
                    </template>
                  </v-slider>
                </v-col>
              </v-row>
            </v-col>
          </v-row>
        </v-row>

        <v-row v-if="computer && hardwareData">
          <v-col cols="12">
            <v-btn color="primary" @click="submitReservation" :disabled="isSubmittingReservation">Create Reservation</v-btn>
          </v-col>
        </v-row>

        <Loading v-if="isSubmittingReservation" />
      </v-stepper-content>

    </v-stepper-items>
  </v-stepper>



  </v-container>
</template>

<script>
  import CalendarReservations from '/src/components/user/CalendarReservations.vue';
  import Loading from '/src/components/global/Loading.vue';

  const axios = require('axios').default;
  import dayjs from "dayjs";
  var utc = require('dayjs/plugin/utc')
  var timezone = require('dayjs/plugin/timezone')
  var customParseFormat = require('dayjs/plugin/customParseFormat')
  dayjs.extend(utc)
  dayjs.extend(timezone)
  dayjs.extend(customParseFormat)

  export default {
    name: 'PageUserReserve',
    components: {
      CalendarReservations,
      Loading,
    },
    data: () => ({
      reserveDate: null,
      step: 1,
      reserveType: "",
      pickedDate: (new Date(Date.now() - (new Date()).getTimezoneOffset() * 60000)).toISOString().substr(0, 10),
      pickedHour: {},
      reservableHours: [],
      hours: [],
      reserveDuration: null,
      fetchingReservations: false, // True if we are fetching all current and upcoming reservations
      allReservations: null, // Contains all current reservations
      fetchingComputers: false, // True if we are fetching computers and their hardware data from the server
      allComputers: null, // Contains all computers from server and their hardware data
      allContainers: null, // Contains all containers from server and their hardware data
      computer: null, // Model for the currently selected computer dropdown
      computers: null, // Contains a list of all computer items for the computer dropdown
      container: null, // Model for the currently selected container dropdown
      containers: null, // Contains a list of all container items for the container dropdown
      hardwareData: null, // Contains hardware data for the currently selected computer
      selectedHardwareSpecs: {}, // Selected hardware specs for the current computer
      isSubmittingReservation: false, // Set to true when user is submitting the reservation
    }),
    mounted() {
      let d = new Date()

      let hours = []
      for (let i = 5; i < 72; i++) {
        hours.push( { "text": i + " hours", "value": i } )
      }
      this.reservableHours = hours
      //this.duration = { "text": "8 hours", "value": 8 }

      let dayHours = []
      for (let i = 0; i < 24; i++) {
        let current = i < 10 ? "0" + i : i
        dayHours.push( { "text": i + ":00", "value": current } )
      }
      this.hours = dayHours
      this.pickedHour = d.getHours() < 10 ? "0"+d.getHours() : d.getHours.toString()

      // TODO: Repeat every 15 seconds
      this.fetchReservations()
    },
    methods: {
      nextStep() {
        if (this.step == 3) return
        this.step = this.step + 1
      },
      prevStep() {
        if (this.step == 1) return
        this.step = this.step - 1
      },
      slotSelected(time) {
        this.reserveDate = time.toISOString()
        this.nextStep()
      },
      computerChanged() {
        let currentComputerId = this.computer
        let data = null
        this.allComputers.forEach((comp) => {
          if (comp.computerId == currentComputerId) data = comp.hardwareSpecs
        })
        this.hardwareData = data
        
        // Set default values for hardware specs
        let selectedHardwareSpecs = {}
        this.hardwareData.forEach((spec) => {
          selectedHardwareSpecs[spec.hardwareSpecId] = spec.defaultAmountForUser
        })
        this.selectedHardwareSpecs = selectedHardwareSpecs
      },
      toggleReservationCalendar() {
        this.showReservationCalendar = !this.showReservationCalendar
      },
      reserveNow() {
        this.reserveDate = dayjs().toISOString()
        this.reserveType = "now"
        this.reserveDuration = null
        this.nextStep()
      },
      reserveLater() {
        this.reserveDate = null
        this.reserveType = "pickdate"
        this.reserveDuration = null
      },
      reserveSelectedTime() {
        if (!this.pickedDate) return this.$store.commit('showMessage', { text: "Please select day.", color: "red" })
        if (!this.pickedHour) return this.$store.commit('showMessage', { text: "Please select hour.", color: "red" })
        let d = dayjs(this.pickedDate + " " + this.pickedHour, "YYYY-MM-DD HH")
        this.reserveDate = d.toISOString()
      },
      fetchReservations() {
        this.fetchingReservations = true
        let _this = this
        let currentUser = this.$store.getters.user

        axios({
          method: "get",
          url: this.AppSettings.APIServer.reservation.get_current_reservations,
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
          //console.log(response)
            // Success
            if (response.data.status == true) {
              _this.allReservations = response.data.data.reservations
              //console.log(_this.allReservations)
              _this.fetchingReservations = false
            }
            // Fail
            else {
              console.log("Failed getting reservations...")
              //_this.$store.commit('showMessage', { text: "There was an error getting the reservations.", color: "red" })
            }
            _this.fetchingReservations = false
        })
        .catch(function (error) {
            // Error
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              //_this.$store.commit('showMessage', { text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              //_this.$store.commit('showMessage', { text: "Unknown error.", color: "red" })
            }
            _this.fetchingReservations = false
        });
      },
      fetchAvailableHardware() {
        this.fetchingComputers = true
        let _this = this
        this.computer = null
        let currentUser = this.$store.getters.user

        axios({
          method: "get",
          url: this.AppSettings.APIServer.reservation.get_available_hardware,
          params: { "date": dayjs(this.reserveDate).tz("GMT+0").toISOString() },
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
          //console.log(response)
            // Success
            if (response.data.status == true) {
              _this.allComputers = response.data.data.computers
              _this.allContainers = response.data.data.containers
              let computers = []
              _this.allComputers.forEach((computer) => {
                computers.push({ "value": computer.computerId, "text": computer.name })
              });
              _this.computers = computers
              
              let containers = []
              _this.allContainers.forEach((container) => {
                containers.push({ "value": container.containerId, "text": container.name })
              });
              _this.containers = containers
              _this.nextStep()
            }
            // Fail
            else {
              console.log("Failed getting hardware data...")
              _this.$store.commit('showMessage', { text: "There was an error getting the hardware specs.", color: "red" })
            }
            _this.fetchingComputers = false
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
            _this.fetchingComputers = false
        });
      },
      submitReservation() {
        this.isSubmittingReservation = true
        let _this = this
        let currentUser = this.$store.getters.user
        let computerId = this.computer
        /*console.log("selected computerId: ", this.computer)
        console.log("selected containerId: ", this.container)
        console.log("Selected hardware specs", {...this.selectedHardwareSpecs})
        console.log("Duration:", this.reserveDuration)*/
        let params = {
          "date": dayjs(this.reserveDate).tz("GMT+0").toISOString(),
          "computerId": computerId,
          "duration": this.reserveDuration,
          "containerId": this.container,
          "hardwareSpecs": {...this.selectedHardwareSpecs}
        }

        axios({
          method: "post",
          url: this.AppSettings.APIServer.reservation.create_reservation,
          params: params,
          headers: {
            "Authorization" : `Bearer ${currentUser.loginToken}`,
            "Content-Type": "multipart/form-data"
            }
        })
        .then(function (response) {
          //console.log(response)
            // Success
            if (response.data.status == true) {
              _this.$router.push("/user/reservations")
              _this.$store.commit('showMessage', { text: "Reservation created succesfully!", color: "green" })
            }
            // Fail
            else {
              console.log("Failed getting hardware data...")
              console.log(response)
              let msg = response && response.data && response.data.message ? response.data.message : "There was an error getting the hardware specs."
              _this.$store.commit('showMessage', { text: msg, color: "red" })
            }
            _this.isSubmittingReservation = false
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
            _this.isSubmittingReservation = false
        });
      },
    },
    computed: {
      parsedTime() {
        return dayjs(this.reserveDate).format("DD.MM.YYYY HH:mm")
      }
    },
  }
</script>

<style scoped lang="scss">
  h2 {
    margin-bottom: 10px;
  }
  
  .spec-row {
    margin-bottom: 10px;
  }
</style>