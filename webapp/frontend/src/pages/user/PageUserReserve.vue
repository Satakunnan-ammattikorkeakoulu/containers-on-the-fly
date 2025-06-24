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
            <h1 style="margin-bottom: 10px;">Reserve Server</h1>
            <p>When do you want to start the reservation?</p>
            
            <v-btn large @click="reserveNow" style="margin-bottom: 20px; margin-top: 30px;" color="green">Reserve Now</v-btn>
            <p class="dim" style="font-weight: 17px;">OR</p>
            <p class="dim">To reserve into future, click on the time in the calendar.</p>
          </v-col>
        </v-row>
        <v-row>
          <v-col class="section">
            <div style="text-align: right">
              <p style="margin-bottom: 0px;"><small>All times are in timezone <strong>{{globalTimezone}}</strong></small></p>
              <p><small><a @click="fetchReservations">Refresh reservations</a></small></p>
            </div>
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
            <p style="color: gray;">Minimum duration is <b>{{ minimumDuration }}</b> hours.</p>
            <v-row>
              <v-col cols="6">
                <v-select v-model="reserveDurationDays" :items="reservableDays" item-text="text" item-value="value" label="Days"></v-select>
              </v-col>
              <v-col cols="6">
                <v-select v-model="reserveDurationHours" :items="reservableHours" item-text="text" item-value="value" label="Hours"></v-select>
              </v-col>
            </v-row>
          </v-col>
        </v-row>

        <v-btn text @click="prevStep()" style="margin-right: 7px">Back</v-btn>

        <v-btn color="primary" @click="fetchAvailableHardware" :disabled="!reserveDurationDays && !reserveDurationHours && !fetchingComputers">Continue</v-btn>
        <Loading v-if="fetchingComputers" />
      </v-stepper-content>

      <!-- STEP 3: HARDWARE -->
      <v-stepper-content step="3">
        <v-btn @click="prevStep()">&larr; Back</v-btn>
        <br>
        <br>

        <!-- Select container -->
        <v-row v-if="reserveDate != null && reserveDurationDays !== null && reserveDurationHours !== null && !fetchingComputers && allComputers">
          <v-col cols="12">
            <h2>Select Container</h2>
            <v-row>
              <v-col cols="6" style="margin: 0 auto">
                <v-select v-model="container" :items="containers" item-text="text" item-value="value" label="Container"></v-select>
              </v-col>
            </v-row>
          </v-col>
        </v-row>

        <v-row v-if="container">
          <v-col cols="6" style="margin: 0 auto;">
            <!-- Readonly v-textarea, text should come from function getContainerDescription() -->
            <v-textarea :readonly="true" :value="getContainerDescription" :style="{ userSelect: 'none' }" label="Container Description"></v-textarea>
          </v-col>
        </v-row>

        <!-- Select computer, hardware specs & submit -->
        <v-row v-if="reserveDate != null && reserveDurationDays !== null && reserveDurationHours !== null && !fetchingComputers && allComputers && container" class="section">      
          <v-col cols="12">
            <h2 style="margin-top: 30px;">Select Computer</h2>
            <v-row>
              <v-col cols="6" style="margin: 0 auto">
                <v-select v-model="computer" v-on:change="computerChanged" :items="computers" item-text="text" item-value="value" label="Computer"></v-select>
              </v-col>
            </v-row>
          </v-col>

          <v-row v-if="computer && hardwareData">
            <v-col cols="12">
              <h2>Select Hardware</h2>

              <v-col cols="12">
                <h3>GPUs</h3>
                <v-col cols="6" style="margin: 0 auto">
                  <v-select v-model="selectedgpus" :items="hardwareDataOnlyGPUs()" attach chips label="GPUs" v-on:input="gpuLimit" :menu-props="{ auto: true }" multiple></v-select>
                </v-col>
              </v-col>

              <v-row v-for="spec in hardwareDataNoGPUs()" :key="spec.name" class="spec-row">
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

          <!-- Admin extra task: reserve for another user -->
          <v-col cols="12" v-if="isAdmin() && computer && hardwareData" style="margin-top: 30px;">
              <h2>Reserve for another user</h2>
              <v-row>
                <v-col cols="3" style="margin: 0 auto">
                  <p><span style="color: gray; font-size: 15px;">Admin only!</span> Write email address of another user, or leave empty to reserve for yourself.</p>
                  <v-text-field v-model="adminReserveUserEmail" v-if="isAdmin" label="" placeholder="Email"></v-text-field>
                </v-col>
              </v-row>
          </v-col>

        </v-row>

        <!-- Notification of depleted resources -->
        <v-row v-if="refreshTip">
          <v-col cols="6" style="margin: 0 auto;">
            <v-alert class="refresh-tip" color="info" title="Information">
              <v-btn style="margin-bottom: 10px;" @click="refreshHardware">Refresh Hardware Data</v-btn>
              <p>If there were not enough resources for reservation, then click the button above to refresh the hardware data.</p>
            </v-alert>
          </v-col>
        </v-row>

        <!-- Create reservation button -->
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
  import AppSettings from '/src/AppSettings.js'

  async function checkHardwareAvailability(date, duration, loginToken) {
    let returnData = null;
    let dateParsed = dayjs(date).tz("GMT+0").toISOString()
    await axios({
      method: "get",
      url: AppSettings.APIServer.reservation.get_available_hardware,
      params: { "date": dateParsed, "duration": duration },
      headers: {"Authorization" : `Bearer ${loginToken}`}
    })
    .then(function (response) {
      //console.log(response)
        // Success
        if (response.data.status == true) {
          returnData = null
        }
        else {
          returnData = response.data.message
          //return response.data.message
        }
    })
    .catch(function (error) {
        console.log(error)
        returnData = "An error occurred while checking hardware availability. Please try again later."
        //return "An error occurred while checking hardware availability. Please try again later."
    });
    return returnData
  }

  export default {
    name: 'PageUserReserve',
    components: {
      CalendarReservations,
      Loading
    },
    data: () => ({
      reserveDate: null,
      step: 1,
      reserveType: "",
      pickedDate: (new Date(Date.now() - (new Date()).getTimezoneOffset() * 60000)).toISOString().substr(0, 10),
      pickedHour: {},
      reservableHours: [],
      adminReserveUserEmail: null,
      hours: [],
      refreshTip: false, // True if there were not enough resources for reservation, shows a tip to refresh hardware data
      reserveDurationDays: null,
      reserveDurationHours: null,
      fetchingReservations: false, // True if we are fetching all current and upcoming reservations
      allReservations: null, // Contains all current reservations
      fetchingComputers: false, // True if we are fetching computers and their hardware data from the server
      allComputers: null, // Contains all computers from server and their hardware data
      allContainers: null, // Contains all containers from server and their hardware data
      computer: null, // Model for the currently selected computer dropdown
      computers: null, // Contains a list of all computer items for the computer dropdown
      container: null, // Model for the currently selected container dropdown
      containers: null, // Contains a list of all container items for the container dropdown
      selectedgpus: [], // Contains a list of all selected gpus
      hardwareData: null, // Contains hardware data for the currently selected computer
      selectedHardwareSpecs: {}, // Selected hardware specs for the current computer
      isSubmittingReservation: false, // Set to true when user is submitting the reservation
      minimumDurationDays: 0, // TODO: Grab from server settings
      maximumDurationDays: 4,  // TODO: Grab from server settings      
      minimumDurationHours: 0, // TODO: Grab from server settings
      maximumDurationHours: 24,  // TODO: Grab from server settings
      minimumDuration: 5, // TODO: Grab from server settings
    }),
    mounted() {
      let d = new Date()

      let hours = []
      for (let i = this.minimumDurationHours; i <= this.maximumDurationHours; i++) {
        hours.push( { "text": i + " hours", "value": i } )
      }
      this.reservableHours = hours
      //this.duration = { "text": "8 hours", "value": 8 }

      // If is admin, set days to 60
      if (this.isAdmin) {
        this.maximumDurationDays = 60
      }

      let days = []
      for (let i = this.minimumDurationDays; i <= this.maximumDurationDays; i++) {
        days.push( { "text": i + " days", "value": i } )
      }
      this.reservableDays = days

      let dayHours = []
      for (let i = 0; i < 24; i++) {
        let current = i < 10 ? "0" + i : i
        dayHours.push( { "text": i + ":00", "value": current } )
      }
      this.hours = dayHours
      this.pickedHour = d.getHours() < 10 ? "0"+d.getHours() : d.getHours.toString()

      this.fetchReservations()
    },
    methods: {
      /**
       * Refreshes the hardware data.
       */
      refreshHardware() {
        this.fetchAvailableHardware();
        this.refreshTip = false;
      },
      /**
       * Checks if user is admin.
       * @returns {Boolean} True if user is admin, false if not
       */
      isAdmin() {
        let currentUser = this.$store.getters.user
        if (!currentUser) return false

        if (currentUser.role == "admin") return true
        return false
      },
      /**
       * Limits the amount of selected GPUs to the maximum amount allowed.
       */
      gpuLimit() {
        let max = 1;
        this.hardwareData.forEach((spec) => {
          if (spec.type === "gpus") max = spec.maximumAmountForUser
        })

        if (this.selectedgpus.length > max) {
          this.$store.commit('showMessage', { text: `Maximum of ${max} GPUs can be selected.`, color: "red" })
          this.selectedgpus.pop()
        }
      },
      /**
       * Returns a list of all hardware specs except GPUs in the hardware data.
       * @returns {Array} Array of all hardware specs except GPUs
      */
      hardwareDataNoGPUs() {
        let data = []
        this.hardwareData.forEach((spec) => {
          if (spec.type != "gpu" && spec.type !== "gpus") data.push(spec)
        })
        return data
      },
      /**
       * Returns a list of all GPUs in the hardware data.
       * @returns {Array} Array of all GPUs
      */
      hardwareDataOnlyGPUs() {
        let data = []
        this.hardwareData.forEach((spec) => {
          if (spec.type == "gpu") {
            // Only add GPUs that are reservable
            if (spec.maximumAmountForUser > 0) {
              let obj = { text: `${spec.internalId}: ${spec.format}`, value: spec.hardwareSpecId }
              data.push(obj)
            }
          }
        })
        return data
      },
      /**
       * Goes to the next step in the reservation process.
       */
      nextStep() {
        if (this.step == 3) return

        let duration = this.reserveDurationDays * 24 + this.reserveDurationHours
        if (this.step == 2 && duration < this.minimumDuration) {
          return this.$store.commit('showMessage', { text: "Minimum duration is "+this.minimumDuration+" hours.", color: "red" })
        }

        this.step = this.step + 1
      },
      /**
       * Goes to the previous step in the reservation process.
       */
      prevStep() {
        if (this.step == 1) return
        this.step = this.step - 1

        // If going back to step 2 (select reservation duration), reset all selected containers, computers and hardware specs
        if (this.step == 2) {
          this.container = null
          this.computer = null
        }
      },
      /**
       * Called when the user clicks the "Reserve now" button.
       * Checks if there is enough hardware resources from current time + minimumHours
       */
       reserveNow() {
        checkHardwareAvailability(dayjs().toISOString(), this.minimumDurationHours, this.$store.getters.user.loginToken).then(res => {
          if (res !== null) {
            return this.$store.commit('showMessage', { text: res, color: "red" })
          }
          this.reserveDate = dayjs().toISOString()
          this.reserveType = "now"
          this.reserveDurationDays = 0
          this.reserveDurationHours = 0
          this.nextStep()
        })
      },
      /**
       * Called when a time slot is selected on the calendar.
       * Checks if there is enough hardware resources in the selected time + minimumHours
       * @param {Date} time The selected time slot
       */
      slotSelected(time) {
        checkHardwareAvailability(time, this.minimumDurationHours, this.$store.getters.user.loginToken).then(res => {
          if (res !== null) {
            return this.$store.commit('showMessage', { text: res, color: "red" })
          }
          this.reserveDate = time.toISOString()
          this.reserveDurationDays = 0
          this.reserveDurationHours = 0
          this.nextStep()
        })
      },
      /**
       * Called when the computer dropdown is changed.
       * Sets the hardware data for the selected computer.
       */
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

        // Set default values for selected GPUs
        this.selectedgpus = []
      },
      /**
       * Toggles the reservation calendar.
       */
      toggleReservationCalendar() {
        this.showReservationCalendar = !this.showReservationCalendar
      },
      /**
       * Fetches all current and upcoming reservations from the server.
       */
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
      /**
       * Fetches all available hardware from the server.
       */
      fetchAvailableHardware() {
        this.fetchingComputers = true
        let _this = this
        this.computer = null
        let currentUser = this.$store.getters.user

        let duration = this.reserveDurationDays * 24 + this.reserveDurationHours

        axios({
          method: "get",
          url: this.AppSettings.APIServer.reservation.get_available_hardware,
          params: { "date": dayjs(this.reserveDate).tz("GMT+0").toISOString(), duration: duration },
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
                if (container.removed == true) return
                if (!_this.isAdmin() && container.public == false) return
                let name = container.name
                if (container.public == false) name = name + " (private)"

                containers.push({ "value": container.containerId, "text": name })
              });
              _this.containers = containers
              _this.nextStep()
            }
            // Fail
            else {
              //console.log("Failed getting hardware data...")
              _this.$store.commit('showMessage', { text: response.data.message, color: "red" })
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
      /**
       * Submits the reservation to the server.
       */
      submitReservation() {
        this.isSubmittingReservation = true
        let _this = this
        let currentUser = this.$store.getters.user
        let computerId = this.computer
        /*console.log("selected computerId: ", this.computer)
        console.log("selected containerId: ", this.container)
        console.log("Selected hardware specs", {...this.selectedHardwareSpecs})
        console.log("Duration:", this.reserveDuration)*/
        
        // Add GPUs to reservation
        this.selectedgpus.forEach((gpu) => {
          this.selectedHardwareSpecs[gpu] = 1
        })
        
        //console.log({...this.selectedHardwareSpecs})
        //console.log({...this.selectedgpus})

        let duration = this.reserveDurationDays * 24 + this.reserveDurationHours

        let params = {
          "date": dayjs(this.reserveDate).tz("GMT+0").toISOString(),
          "computerId": computerId,
          "duration": duration,
          "containerId": this.container,
          "hardwareSpecs": JSON.stringify(this.selectedHardwareSpecs),
          "adminReserveUserEmail": this.adminReserveUserEmail ? this.adminReserveUserEmail : ""
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
              localStorage.setItem("justReserved", true)
              localStorage.setItem("justReservedInformEmail", response.data.data.informByEmail)
              _this.$router.push("/user/reservations")
              _this.$store.commit('showMessage', { text: "Reservation created succesfully!", color: "green" })
              _this.refreshTip = false;
            }
            // Fail
            else {
              let msg = response && response.data && response.data.message ? response.data.message + " Please select less resources or go back and select another time." : "There was an error getting the hardware specs."
              _this.$store.commit('showMessage', { text: msg, color: "red" })
              _this.refreshTip = true;
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
            _this.refreshTip = true;
        });
      },
    },
    computed: {
      getContainerDescription() {
        if (this.container) {
          let container = this.allContainers.find(x => x.containerId == this.container)
          if (container) return container.description
          else return ""
        }
        else return ""
      },
      parsedTime() {
        return dayjs(this.reserveDate).format("DD.MM.YYYY HH:mm")
      },
      globalTimezone() {
        return AppSettings.General.timezone
      },
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