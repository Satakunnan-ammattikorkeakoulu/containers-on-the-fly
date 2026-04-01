<template>
  <v-container class="text-center">

  <v-stepper v-model="step">
    <v-stepper-header>
      <v-stepper-item :complete="step > 1" :value="1" title="Time"></v-stepper-item>
      <v-divider></v-divider>
      <v-stepper-item :complete="step > 2" :value="2" title="Duration"></v-stepper-item>
      <v-divider></v-divider>
      <v-stepper-item :value="3" title="Hardware"></v-stepper-item>
    </v-stepper-header>

    <v-stepper-window>
      <!-- STEP 1: CALENDAR -->
      <v-stepper-window-item :value="1">
        <v-row>
          <v-col>
            <h1 style="margin-bottom: 10px;">Reserve Server</h1>
            <p>When do you want to start the reservation?</p>
            
            <!-- Reservation Page Instructions -->
            <v-col cols="12" v-if="reservationPageInstructions && reservationPageInstructions.trim()" class="mb-4">
              <v-alert 
                type="info" 
                outlined
                class="mx-auto text-left"
                style="max-width: 800px;"
              >
                <div v-html="reservationPageInstructions.replace(/\n/g, '<br>')"></div>
              </v-alert>
            </v-col>
            
            <v-btn large @click="reserveNow" style="margin-bottom: 20px; margin-top: 30px;" color="green">Reserve Now</v-btn>
            <p class="dim" style="font-weight: 17px;">OR</p>
            <p class="dim">To reserve into future, click on the time in the calendar.</p>
          </v-col>
        </v-row>
        <v-row>
          <v-col class="section">
            <div style="text-align: left">
              <p style="margin-bottom: 10px;"><small>All times are in timezone <strong>{{globalTimezone}}</strong></small></p>
            </div>
            <div style="text-align: center;">
              <CalendarReservations 
                v-if="allReservations" 
                :propReservations="allReservations" 
                :readOnly="false" 
                @slotSelected="slotSelected" 
                @reservationsRefreshed="handleReservationsRefreshed"
                ref="calendarComponent"
              />
            </div>
          </v-col>
        </v-row>
      </v-stepper-window-item>

      <!-- STEP 2: DURATION -->
      <v-stepper-window-item :value="2">
        <v-row v-if="reserveDate != null" class="section">
          <v-col cols="12" style="margin: 0 auto">
            <h2>Reservation Time</h2>
            <p>{{parsedTime}}</p>
          </v-col>
          <v-col cols="12" sm="6" md="4" lg="3" style="margin: 0 auto; min-width: 320px">
            <h2>Reservation duration</h2>
            <p style="color: gray;">Minimum duration is <b>{{ minimumDuration }}</b> hours.</p>
            <v-row>
              <v-col cols="6">
                <v-select v-model="reserveDurationDays" :items="reservableDays" item-title="text" item-value="value" label="Days"></v-select>
              </v-col>
              <v-col cols="6">
                <v-select v-model="reserveDurationHours" :items="reservableHours" item-title="text" item-value="value" label="Hours"></v-select>
              </v-col>
            </v-row>
          </v-col>
        </v-row>

        <v-btn variant="text" @click="prevStep()" style="margin-right: 7px">Back</v-btn>

        <v-btn color="primary" @click="fetchAvailableHardware" :disabled="!reserveDurationDays && !reserveDurationHours && !fetchingComputers">Continue</v-btn>
        <Loading v-if="fetchingComputers" />
      </v-stepper-window-item>

      <!-- STEP 3: HARDWARE -->
      <v-stepper-window-item :value="3">
        <v-btn @click="prevStep()">&larr; Back</v-btn>
        <br>
        <br>

        <!-- Select container -->
        <v-row v-if="reserveDate != null && reserveDurationDays !== null && reserveDurationHours !== null && !fetchingComputers && allComputers">
          <v-col cols="12">
            <h2>Select Container</h2>
            <v-row justify="center">
              <v-col cols="10">
                <v-row style="justify-content: center !important;">
                  <v-col 
                    v-for="containerItem in containers" 
                    :key="containerItem.value" 
                    cols="12" 
                    sm="6" 
                    md="4"
                  >
                    <v-card 
                      :class="{ 'selected-card': container === containerItem.value }"
                      @click="selectContainer(containerItem.value)"
                      hover
                      style="cursor: pointer; min-height: 260px;"
                      :outlined="container !== containerItem.value"
                      :color="container === containerItem.value ? 'primary' : ''"
                    >
                      <v-card-body class="pa-4" style="height: 100%;">
                        <div class="d-flex flex-column h-100" style="padding: 15px;">
                          <div class="text-center mb-3">
                            <v-icon 
                              size="32" 
                              class="mb-2"
                              :color="container === containerItem.value ? 'white' : 'primary'"
                            >
                              mdi-docker
                            </v-icon>
                            <div 
                              class="font-weight-medium text-h6"
                              :style="{ color: container === containerItem.value ? 'white' : '' }"
                            >
                              {{ containerItem.text }}
                            </div>
                            <div 
                              class="text-body-2 mt-1"
                              :style="{ 
                                color: container === containerItem.value ? 'rgba(255,255,255,0.9)' : 'rgba(255,255,255,0.7)',
                                fontSize: '12px',
                                fontFamily: 'monospace'
                              }"
                            >
                              {{ getContainerImageById(containerItem.value) || 'No image specified' }}
                            </div>
                            <div 
                              v-if="!getContainerPublicById(containerItem.value) && isAdmin()"
                              class="text-body-2 mt-1"
                              :style="{ 
                                color: container === containerItem.value ? 'rgba(255,255,255,0.9)' : 'rgba(255,165,0,0.9)',
                                fontSize: '11px',
                                fontWeight: '500'
                              }"
                            >
                              Private
                            </div>
                          </div>
                          <div class="flex-grow-1">
                            <div 
                              class="text-body-2"
                              :style="{ 
                                color: container === containerItem.value ? 'white' : 'rgba(255,255,255,0.8)',
                                fontSize: '13px',
                                lineHeight: '1.3'
                              }"
                            >
                              {{ getContainerDescriptionById(containerItem.value) || 'No description available' }}
                            </div>
                          </div>
                        </div>
                      </v-card-body>
                    </v-card>
                  </v-col>
                </v-row>
              </v-col>
            </v-row>
          </v-col>
        </v-row>


        <!-- Select computer, hardware specs & submit -->
        <v-row v-if="reserveDate != null && reserveDurationDays !== null && reserveDurationHours !== null && !fetchingComputers && allComputers && container" class="section">      
          <v-col cols="12">
            <h2 id="select-computer-section">Select Computer</h2>
            <v-row justify="center">
              <v-col cols="10">
                <v-row style="justify-content: center !important;">
                  <v-col 
                    v-for="computerItem in computers" 
                    :key="computerItem.value" 
                    cols="12" 
                    sm="6" 
                    md="4"
                  >
                    <v-card 
                      :class="{ 'selected-card': computer === computerItem.value }"
                      @click="computer = computerItem.value; computerChanged()"
                      hover
                      style="cursor: pointer; min-height: 260px;"
                      :outlined="computer !== computerItem.value"
                      :color="computer === computerItem.value ? 'primary' : ''"
                    >
                      <v-card-body class="pa-4" style="height: 100%;">
                        <div class="d-flex flex-column h-100" style="padding: 15px;">
                          <div class="text-center mb-3">
                            <v-icon 
                              size="32" 
                              class="mb-2"
                              :color="computer === computerItem.value ? 'white' : 'primary'"
                            >
                              mdi-server
                            </v-icon>
                            <div 
                              class="font-weight-medium text-h6"
                              :style="{ color: computer === computerItem.value ? 'white' : '' }"
                            >
                              {{ computerItem.text }}
                            </div>
                          </div>
                          <div class="flex-grow-1">
                            <div 
                              class="text-body-2 font-weight-medium mb-2"
                              :style="{ 
                                color: computer === computerItem.value ? 'white' : 'rgba(255,255,255,0.8)',
                                fontSize: '12px'
                              }"
                            >
                              Available Hardware
                            </div>
                            <div 
                              v-for="spec in getComputerHardwareList(computerItem.value)" 
                              :key="spec.id"
                              class="text-body-2"
                              :style="{ 
                                color: computer === computerItem.value ? 'white' : 'rgba(255,255,255,0.8)',
                                fontSize: '11px',
                                lineHeight: '1.4'
                              }"
                            >
                              • {{ spec.text }}
                            </div>
                          </div>
                        </div>
                      </v-card-body>
                    </v-card>
                  </v-col>
                </v-row>
              </v-col>
            </v-row>
          </v-col>

          <v-row v-if="computer && hardwareData">
            <v-col cols="12">
              <h2 id="select-hardware-section" style="margin-top: 15px;">Select Hardware</h2>

              <v-col cols="12">
                <h3 class="text-center">
                  <v-icon class="mr-1" size="small">mdi-expansion-card</v-icon>
                  GPUs
                </h3>
                <p class="text-center text-medium-emphasis" style="font-size: 13px; margin-bottom: 5px;">
                  {{ hardwareDataOnlyGPUs().length }} available — select up to {{ getMaxGpus() }}
                </p>
                <div style="margin-bottom: 30px; margin-top: 15px;" v-if="hardwareDataOnlyGPUs().length === 0" class="text-center text-medium-emphasis">
                  No GPUs Available
                </div>
                <v-row v-else justify="center" style="margin-top: 15px; margin-bottom: 20px;">
                  <v-col
                    v-for="gpu in hardwareDataOnlyGPUs()"
                    :key="gpu.value"
                    cols="4"
                    sm="3"
                    md="2"
                  >
                    <v-card
                      :class="{ 'selected-card': selectedgpus.includes(gpu.value) }"
                      @click="toggleGpu(gpu.value)"
                      hover
                      style="cursor: pointer; min-height: 90px;"
                      :outlined="!selectedgpus.includes(gpu.value)"
                    >
                      <v-card-text style="height: 100%;">
                        <div class="d-flex flex-column align-center justify-center h-100 text-center" style="padding: 10px;">
                          <v-icon
                            size="28"
                            class="mb-2"
                            :color="selectedgpus.includes(gpu.value) ? 'primary' : 'grey'"
                          >mdi-expansion-card</v-icon>
                          <div class="font-weight-medium" style="font-size: 14px;">{{ gpu.text.split(': ').slice(1).join(': ') || gpu.text }}</div>
                          <div class="text-medium-emphasis" style="font-size: 12px;">GPU {{ gpu.text.split(':')[0] }}</div>
                        </div>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>
              </v-col>

              <v-row v-for="spec in hardwareDataNoGPUs()" :key="spec.hardwareSpecId" justify="center">
                <v-col cols="12" md="6" style="padding: 0 60px;">
                  <h3 class="text-center">
                    <v-icon v-if="spec.type.toLowerCase() === 'cpus'" class="mr-1" size="small">mdi-cpu-64-bit</v-icon>
                    <v-icon v-else-if="spec.type.toLowerCase() === 'ram'" class="mr-1" size="small">mdi-memory</v-icon>
                    {{ formatSpecType(spec.type) }}
                  </h3>
                  <p class="text-center text-medium-emphasis" style="font-size: 13px; margin-bottom: 15px;">
                    <span v-if="spec.type.toLowerCase() === 'cpus'">Number of CPU cores to dedicate</span>
                    <span v-else-if="spec.type.toLowerCase() === 'ram'">Amount of RAM to allocate</span>
                    <span v-else>Amount to allocate</span>
                  </p>
                  <v-slider
                    :min="spec.minimumAmount"
                    show-ticks="always"
                    v-model="selectedHardwareSpecs[spec.hardwareSpecId]"
                    :max="spec.maximumAmountForUser"
                    thumb-label="always"
                    :step="1"
                    color="primary"
                    track-color="grey-darken-2"
                  >
                    <template v-slot:thumb-label="{ modelValue }">
                      <span style="font-size: 15px;">{{ (modelValue ?? 0) }} / {{ spec.maximumAmountForUser }} {{ spec.format }}</span>
                    </template>
                  </v-slider>
                </v-col>
              </v-row>
            </v-col>
          </v-row>

          <!-- Advanced Settings -->
          <v-col cols="12" v-if="computer && hardwareData" style="margin-top: 30px;">
            <div class="text-center">
              <h3 style="margin-bottom: 8px;">Advanced Settings</h3>
              <a style="cursor: pointer; color: #2196f3; font-size: 14px;" @click="showAdvancedSettings = !showAdvancedSettings">
                {{ showAdvancedSettings ? 'Hide Advanced Settings' : 'Show Advanced Settings' }}
              </a>
            </div>

            <div v-if="showAdvancedSettings" style="margin-top: 25px;">
              <!-- Admin reserve + Description side by side -->
              <v-row style="margin-bottom: 20px;">
                <v-col cols="12" :md="isAdmin() ? 6 : 6" :style="isAdmin() ? 'padding: 0 40px;' : 'margin: 0 auto; padding: 0 40px;'" v-if="isAdmin()">
                  <h3 class="text-center">Reserve for another user</h3>
                  <p class="text-center"><span style="color: gray; font-size: 15px;">Admin only!</span> Write email address of another user, or leave empty to reserve for yourself.</p>
                  <v-text-field v-model="adminReserveUserEmail" label="" placeholder="Email"></v-text-field>
                </v-col>
                <v-col cols="12" :md="isAdmin() ? 6 : 6" :style="isAdmin() ? 'padding: 0 40px;' : 'margin: 0 auto; padding: 0 40px;'">
                  <h3 class="text-center">Reservation Description</h3>
                  <p class="text-center" style="color: gray; font-size: 15px;">Optional description for your reservation. (max 50 characters)</p>
                  <v-text-field
                    v-model="reservationDescription"
                    label="Description (optional)"
                    placeholder="Enter description..."
                    counter="50"
                    :rules="[rules.maxLength50]"
                    maxlength="50">
                  </v-text-field>
                </v-col>
              </v-row>

              <!-- Low-Priority Reservation -->
              <v-row style="margin-bottom: 20px;">
                <v-col cols="12" md="6" style="margin: 0 auto; padding: 0 40px;">
                  <h3 class="text-center">Low-Priority Reservation</h3>
                  <p class="text-center" style="color: gray; font-size: 15px;">
                    Low-priority reservations may be paused when resources are needed by other users,
                    and automatically resumed when resources become available. Save your work to mounted volumes.
                  </p>
                  <div class="d-flex justify-center">
                    <v-switch
                      v-model="isLowPriority"
                      color="warning"
                      label="Make reservation low-priority"
                    ></v-switch>
                  </div>
                </v-col>
              </v-row>

              <!-- SHM + RAM Disk side by side -->
              <v-row>
                <v-col cols="12" md="6" style="padding: 0 60px;">
                  <h3 class="text-center">Shared Memory (SHM) Size</h3>
                  <p style="color: gray; font-size: 15px;">Shared memory for inter-process communication. Required for applications like PyTorch, databases, and parallel computing. Default: 50%</p>
                  <v-slider
                    v-model="shmSizePercent"
                    :min="10"
                    :max="90"
                    show-ticks="always"
                    thumb-label="always"
                    :step="5">
                    <template v-slot:thumb-label="{ modelValue }">
                      <span style="font-size: 15px;">{{ modelValue }}%</span>
                    </template>
                  </v-slider>
                  <p style="text-align: center; margin-top: 10px;">
                    SHM Size: {{ shmSizePercent }}% of allocated memory
                    <span v-if="selectedHardwareSpecs && getMemorySpecId()">
                      (≈ {{ calculateShmSizeGB() }} GB)
                    </span>
                  </p>
                </v-col>

                <v-col cols="12" md="6" style="padding: 0 60px;">
                  <h3 class="text-center">RAM Disk Size</h3>
                  <p style="color: gray; font-size: 15px;">Mounts a high-speed RAM-based folder to your home directory. Ideal for caching, temp files, and I/O intensive operations. Default: 0%</p>
                  <v-slider
                    v-model="ramDiskSizePercent"
                    :min="0"
                    :max="60"
                    show-ticks="always"
                    thumb-label="always"
                    :step="5">
                    <template v-slot:thumb-label="{ modelValue }">
                      <span style="font-size: 15px;">{{ modelValue }}%</span>
                    </template>
                  </v-slider>
                  <p style="text-align: center; margin-top: 10px;">
                    RAM Disk Size: {{ ramDiskSizePercent }}% of allocated memory
                    <span v-if="selectedHardwareSpecs && getMemorySpecId()">
                      (≈ {{ calculateRamDiskSizeGB() }} GB)
                    </span>
                  </p>
                </v-col>
              </v-row>
            </div>
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
        <v-row v-if="computer && hardwareData" style="margin-top: 40px;">
          <v-col cols="12">
            <v-btn color="primary" @click="submitReservation" :disabled="isSubmittingReservation">Create Reservation</v-btn>
          </v-col>
        </v-row>

        <Loading v-if="isSubmittingReservation" />
      </v-stepper-window-item>

    </v-stepper-window>
  </v-stepper>



  </v-container>
</template>

<script>
  import axios from 'axios';
  import dayjs from "dayjs";
  import utc from 'dayjs/plugin/utc'
  import timezone from 'dayjs/plugin/timezone'
  import customParseFormat from 'dayjs/plugin/customParseFormat'
  import CalendarReservations from '/src/components/user/CalendarReservations.vue';
  import Loading from '/src/components/global/Loading.vue';
  import AppSettings from '/src/AppSettings.js'
  import { useMainStore } from '@/store/store'

  dayjs.extend(utc)
  dayjs.extend(timezone)
  dayjs.extend(customParseFormat)

  /**
   * Pre-flight check that verifies hardware resources are available for the given date and duration.
   * @param {string} date - ISO date string for the reservation start
   * @param {number} duration - Duration in hours
   * @param {string} loginToken - Auth token
   * @returns {Promise<string|null>} Error message string, or null if resources are available
   */
  async function checkHardwareAvailability(date, duration, loginToken) {
    let returnData = null;
    let dateParsed = dayjs(date).utc().toISOString()
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

  /**
   * Multi-step reservation wizard for creating new container reservations.
   * Step 1: Select start time via calendar or "Reserve Now" button.
   * Step 2: Choose reservation duration (days/hours) within role-based limits.
   * Step 3: Select container image, target server, hardware resources (GPUs, CPUs,
   *         memory, storage), and advanced settings (SHM size, RAM disk, description,
   *         admin-only reserve-for-another-user).
   * Validates hardware availability at each step before proceeding.
   */
  export default {
    name: 'PageUserReserve',

    setup() {
      const store = useMainStore()
      return { store }
    },

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
      reservableDays: [],
      adminReserveUserEmail: null,
      reservationDescription: "", // Description for the reservation
      hours: [],
      refreshTip: false, // True if there were not enough resources for reservation, shows a tip to refresh hardware data
      reserveDurationDays: null,
      reserveDurationHours: null,
      initializingDefaults: false, // Flag to prevent watchers from interfering during initialization
      isLowPriority: false, // Low-priority reservations can be paused when resources are needed
      shmSizePercent: 50, // Default SHM size to 50% of memory
      ramDiskSizePercent: 0, // Default RAM disk size to 0% of memory
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
      showAdvancedSettings: false,
      isSubmittingReservation: false, // Set to true when user is submitting the reservation
      rules: {
        maxLength50: value => !value || value.length <= 50 || "Description must be 50 characters or less"
      }
    }),
    mounted() {
      let d = new Date()

      // Initialize duration defaults if store config is already loaded
      if (this.store.configLoaded) {
        this.initializeDurationDefaults()
      }
      // Otherwise, the watcher will handle initialization when config loads

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
       * Handles container selection and auto-scroll to computer selection.
       * @param {number} containerValue - The selected container ID
       */
      selectContainer(containerValue) {
        this.container = containerValue;
        
        // Auto-scroll to the "Select Computer" section after a short delay
        // to allow Vue to render the computer selection section
        try {
          this.$nextTick(() => {
            setTimeout(() => {
              const element = document.getElementById('select-computer-section');
              if (element) {
                element.scrollIntoView({ 
                  behavior: 'smooth', 
                  block: 'start' 
                });
              }
            }, 100);
          });
        } catch (error) {
          // Silently handle any scrolling errors
          console.debug('Auto-scroll error:', error);
        }
      },
      /**
       * Checks if user is admin.
       * @returns {Boolean} True if user is admin, false if not
       */
      isAdmin() {
        let currentUser = this.store.user
        if (!currentUser) return false

        if (currentUser.role == "admin") return true
        if (currentUser.roles && currentUser.roles.includes("admin")) return true
        return false
      },
      /**
       * Limits the amount of selected GPUs to the maximum amount allowed.
       */
      /** Get the maximum number of GPUs the user can select. */
      getMaxGpus() {
        if (this.isAdmin()) return this.hardwareDataOnlyGPUs().length;
        let max = 1;
        this.hardwareData.forEach((spec) => {
          if (spec.type === "gpus" && spec.maximumAmountForUser) {
            max = spec.maximumAmountForUser;
          }
        });
        return max;
      },
      /** Toggle GPU selection by clicking its card. */
      toggleGpu(gpuValue) {
        let index = this.selectedgpus.indexOf(gpuValue);
        if (index > -1) {
          this.selectedgpus.splice(index, 1);
        } else {
          this.selectedgpus.push(gpuValue);
        }
        this.gpuLimit();
      },
      gpuLimit() {
        // Allow admins to select unlimited GPUs
        if (this.isAdmin()) {
          return
        }

        let max = 1; // Default fallback
        
        // Look for the "gpus" summary spec which contains the computer-specific maximum
        let gpusSummarySpec = null
        
        this.hardwareData.forEach((spec) => {
          if (spec.type === "gpus") {
            gpusSummarySpec = spec
          }
        })

        // Use the computer-specific GPU limit from the "gpus" summary spec
        if (gpusSummarySpec) {
          max = gpusSummarySpec.maximumAmountForUser
        }

        if (this.selectedgpus.length > max) {
          this.store.showMessage({ text: `Maximum of ${max} GPUs can be selected.`, color: "red" })
          // Remove the last selected GPU to stay within the limit
          this.selectedgpus.splice(-1, 1)
        }
      },
      /**
       * Returns a list of all hardware specs except GPUs in the hardware data.
       * @returns {Array} Array of all hardware specs except GPUs
      */
      /** Format hardware spec type for display (e.g. "cpus" → "CPUs", "ram" → "RAM"). */
      formatSpecType(type) {
        const labels = { 'cpus': 'CPUs', 'ram': 'RAM', 'cpu': 'CPU' };
        return labels[type.toLowerCase()] || type;
      },
      hardwareDataNoGPUs() {
        let data = []
        this.hardwareData.forEach((spec) => {
          if (spec.type !== "gpus" && spec.type !== "gpu") data.push(spec)
        })
        return data.sort((a, b) => a.type.localeCompare(b.type))
      },
      /**
       * Returns a list of all GPUs in the hardware data.
       * @returns {Array} Array of all GPUs
      */
      hardwareDataOnlyGPUs() {
        let data = []
        this.hardwareData.forEach((spec) => {
          if (spec.type === "gpu") {
            // Only add individual GPUs that are reservable (not the summary "gpus" type)
            if (spec.maximumAmountForUser > 0) {
              let obj = { text: `${spec.internalId}: ${spec.format}`, value: spec.hardwareSpecId }
              data.push(obj)
            }
          }
        })
        return data.sort((a, b) => a.text.localeCompare(b.text))
      },
      /**
       * Goes to the next step in the reservation process.
       */
      nextStep() {
        if (this.step == 3) return

        let duration = this.reserveDurationDays * 24 + this.reserveDurationHours
        if (this.step == 2 && duration < this.minimumDuration) {
          return this.store.showMessage({ text: "Minimum duration is "+this.minimumDuration+" hours.", color: "red" })
        }
        // Skip maximum duration check for admins
        if (this.step == 2 && duration > this.maximumDuration) {
          return this.store.showMessage({ text: "Maximum duration is "+this.maximumDuration+" hours.", color: "red" })
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
          // Initialize duration defaults when step 2 becomes active
          this.initializeDurationDefaultsIfNeeded()
      
          this.container = null
          this.computer = null
        }
      },
      /**
       * Called when the user clicks the "Reserve now" button.
       * Checks if there is enough hardware resources from current time + minimumHours
       */
       reserveNow() {
        checkHardwareAvailability(dayjs().toISOString(), this.minimumDuration, this.store.user.loginToken).then(res => {
          if (res !== null) {
            return this.store.showMessage({ text: res, color: "red" })
          }
          this.reserveDate = dayjs().toISOString()
          this.reserveType = "now"
          this.reserveDurationDays = this.minimumDurationDays
          this.reserveDurationHours = this.minimumDurationHours
          this.nextStep()
        })
      },
      /**
       * Called when a time slot is selected on the calendar.
       * Checks if there is enough hardware resources in the selected time + minimumHours
       * @param {Date} time The selected time slot
       */
      slotSelected(time) {
        checkHardwareAvailability(time, this.minimumDuration, this.store.user.loginToken).then(res => {
          if (res !== null) {
            return this.store.showMessage({ text: res, color: "red" })
          }
          this.reserveDate = dayjs(time).toISOString()
          this.reserveDurationDays = this.minimumDurationDays
          this.reserveDurationHours = this.minimumDurationHours
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

        // Auto-scroll to the "Select Hardware" section
        try {
          this.$nextTick(() => {
            setTimeout(() => {
              const element = document.getElementById('select-hardware-section');
              if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }
            }, 100);
          });
        } catch (error) {
          console.debug('Auto-scroll error:', error);
        }
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
        let currentUser = this.store.user

        axios({
          method: "get",
          url: this.$appSettings.APIServer.reservation.get_current_reservations,
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
          //console.log(response)
            // Success
            if (response.data.status == true) {
              _this.allReservations = response.data.data.reservations
            }
            // Fail
            else {
              console.log("Failed getting reservations...")
              //_this.store.showMessage({ text: "There was an error getting the reservations.", color: "red" })
            }
            _this.fetchingReservations = false
        })
        .catch(function (error) {
            // Error
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              //_this.store.showMessage({ text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              //_this.store.showMessage({ text: "Unknown error.", color: "red" })
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
        let currentUser = this.store.user

        let duration = this.reserveDurationDays * 24 + this.reserveDurationHours

        axios({
          method: "get",
          url: this.$appSettings.APIServer.reservation.get_available_hardware,
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
                containers.push({ 
                  "value": container.containerId, 
                  "text": container.name,
                  "isPublic": container.public 
                })
              });
              
              // Sort containers: public first (alphabetically), then private (alphabetically)
              containers.sort((a, b) => {
                if (a.isPublic === b.isPublic) {
                  // Same visibility, sort by name
                  return a.text.localeCompare(b.text)
                }
                // Different visibility, public containers first
                return b.isPublic - a.isPublic
              })
              
              _this.containers = containers
              _this.nextStep()
            }
            // Fail
            else {
              //console.log("Failed getting hardware data...")
              _this.store.showMessage({ text: response.data.message, color: "red" })
            }
            _this.fetchingComputers = false
        })
        .catch(function (error) {
            // Error
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.store.showMessage({ text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.store.showMessage({ text: "Unknown error.", color: "red" })
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
        let currentUser = this.store.user
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
          "adminReserveUserEmail": this.adminReserveUserEmail ? this.adminReserveUserEmail : "",
          "description": this.reservationDescription && this.reservationDescription.trim() ? this.reservationDescription.trim() : "",
          "shmSizePercent": this.shmSizePercent,
          "ramDiskSizePercent": this.ramDiskSizePercent,
          "isLowPriority": this.isLowPriority
        }

        axios({
          method: "post",
          url: this.$appSettings.APIServer.reservation.create_reservation,
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
              _this.store.showMessage({ text: "Reservation created succesfully!", color: "green" })
              _this.refreshTip = false;
            }
            // Fail
            else {
              let msg = response && response.data && response.data.message ? response.data.message + " Please select less resources or go back and select another time." : "There was an error getting the hardware specs."
              _this.store.showMessage({ text: msg, color: "red" })
              _this.refreshTip = true;
            }
            _this.isSubmittingReservation = false
        })
        .catch(function (error) {
            // Error
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.store.showMessage({ text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.store.showMessage({ text: "Unknown error.", color: "red" })
            }
            _this.isSubmittingReservation = false
            _this.refreshTip = true;
        });
      },
      /**
       * Updates the hours dropdown based on selected days to respect min/max duration limits
       * @param {number} selectedDays The currently selected number of days
       */
      updateHoursDropdown(selectedDays) {
        let hours = []
        let minHours = 0
        let maxHours = 23
        
        // If at minimum days, start from minimum hours
        if (selectedDays === this.minimumDurationDays) {
          minHours = this.minimumDurationHours
        }
        
        // If at maximum days, limit to maximum hours
        if (selectedDays === this.maximumDurationDays) {
          maxHours = this.maximumDurationHours
        }
        
        // Special case: if we're at max days and max hours is 0, only allow 0 hours
        if (selectedDays === this.maximumDurationDays && this.maximumDurationHours === 0) {
          maxHours = 0
        }
        
        for (let i = minHours; i <= maxHours; i++) {
          hours.push( { "text": i + " hours", "value": i } )
        }
        
        this.reservableHours = hours
        
        // Reset hour selection if current value is not in the new range or is null
        if (this.reserveDurationHours === null || this.reserveDurationHours < minHours || this.reserveDurationHours > maxHours) {
          this.reserveDurationHours = minHours
        }
      },
      /**
       * Initialize duration defaults when store data is available
       */
      initializeDurationDefaults() {
        this.initializingDefaults = true
        
        // Generate days dropdown from minimum to maximum
        let maxDays = this.maximumDurationDays
        let minDays = this.minimumDurationDays
        
        let days = []
        for (let i = minDays; i <= maxDays; i++) {
          let text = i === 1 ? i + " day" : i + " days"
          days.push( { "text": text, "value": i } )
        }
        this.reservableDays = days

        // Generate initial hours dropdown first
        this.updateHoursDropdown(minDays)
        
        // Then set initial default values to minimum allowed (this will trigger the watcher)
        this.reserveDurationDays = minDays
        this.reserveDurationHours = this.minimumDurationHours
        
        // Use nextTick to ensure watchers complete before clearing the flag
        this.$nextTick(() => {
          this.initializingDefaults = false
        })
      },
      /**
       * Initialize duration defaults only if they haven't been set yet and config is loaded
       */
      initializeDurationDefaultsIfNeeded() {
        if (!this.store.configLoaded) {
          return
        }
        
        // Only set defaults if no values are currently selected
        if (this.reserveDurationDays === null || this.reserveDurationHours === null) {
          this.initializeDurationDefaults()
        }
      },
      /**
       * Gets the container description for a specific container ID
       * @param {number} containerId The container ID to get the description for
       * @returns {string} The container description
       */
      getContainerDescriptionById(containerId) {
        if (this.allContainers) {
          let container = this.allContainers.find(x => x.containerId == containerId)
          if (container) return container.description
        }
        return ""
      },
      /**
       * Gets the container image name for a specific container ID
       * @param {number} containerId The container ID to get the image name for
       * @returns {string} The container image name
       */
      getContainerImageById(containerId) {
        if (this.allContainers) {
          let container = this.allContainers.find(x => x.containerId == containerId)
          if (container) return container.imageName
        }
        return ""
      },
      /**
       * Gets the container public status for a specific container ID
       * @param {number} containerId The container ID to get the public status for
       * @returns {boolean} Whether the container is public
       */
      getContainerPublicById(containerId) {
        if (this.allContainers) {
          let container = this.allContainers.find(x => x.containerId == containerId)
          if (container) return container.public
        }
        return true // Default to public if not found
      },
      /**
       * Gets the hardware specs for a specific computer ID
       * @param {number} computerId The computer ID to get the hardware specs for
       * @returns {Array} The hardware specs array
       */
      getComputerHardwareById(computerId) {
        if (this.allComputers) {
          let computer = this.allComputers.find(x => x.computerId == computerId)
          if (computer) return computer.hardwareSpecs
        }
        return []
      },
      /**
       * Formats hardware specs for display in computer cards
       * @param {number} computerId The computer ID to get the formatted specs for
       * @returns {string} Formatted hardware specs string
       */
      getFormattedHardwareSpecs(computerId) {
        let specs = this.getComputerHardwareById(computerId)
        if (!specs || specs.length === 0) return "No hardware specs available"
        
        let formattedSpecs = []
        
        // Group specs by type
        let gpuSpecs = specs.filter(spec => spec.type === "gpu")
        let otherSpecs = specs.filter(spec => spec.type !== "gpus" && spec.type !== "gpu").sort((a, b) => a.type.localeCompare(b.type))
        
        // Add GPU info
        if (gpuSpecs.length > 0) {
          // Count actual GPUs (number of GPU specs), not total reservable slots
          let gpuCount = gpuSpecs.filter(spec => spec.maximumAmountForUser > 0).length
          if (gpuCount > 0) {
            formattedSpecs.push(`${gpuCount} GPU${gpuCount > 1 ? 's' : ''}`)
          }
        }
        
        // Add other specs (limit to first 2-3 most important ones)
        let prioritySpecs = otherSpecs.slice(0, 2)
        prioritySpecs.forEach(spec => {
          if (spec.maximumAmountForUser > 0) {
            // Clean up the display format
            let displayName = spec.type
            if (spec.type === "cpus") displayName = "CPUs"
            else if (spec.type === "memory") displayName = "RAM"
            else if (spec.type === "storage") displayName = "Storage"
            else displayName = spec.type.charAt(0).toUpperCase() + spec.type.slice(1)
            
            formattedSpecs.push(`${spec.maximumAmountForUser} ${spec.format} ${displayName}`)
          }
        })
        
        return formattedSpecs.length > 0 ? formattedSpecs.join(" • ") : "No resources available"
      },
      /**
       * Gets a list of hardware specs formatted for display in computer cards
       * @param {number} computerId The computer ID to get the hardware list for
       * @returns {Array} Array of formatted hardware spec objects
       */
      getComputerHardwareList(computerId) {
        let specs = this.getComputerHardwareById(computerId)
        if (!specs || specs.length === 0) return [{ id: 'none', text: 'No hardware specs available' }]
        
        let hardwareList = []
        
        // Group specs by type - GPUs first, then others alphabetically (matching hardware selection order)
        let gpuSpecs = specs.filter(spec => spec.type === "gpu")
        let otherSpecs = specs.filter(spec => spec.type !== "gpus" && spec.type !== "gpu")
        
        // Always add GPUs first (matching the order in hardware selection)
        let gpuCount = gpuSpecs.filter(spec => spec.maximumAmountForUser > 0).length
        hardwareList.push({ 
          id: 'gpu', 
          text: `${gpuCount} GPU${gpuCount !== 1 ? 's' : ''}`
        })
        
        // Add other specs sorted alphabetically (matching hardwareDataNoGPUs method)
        let sortedOtherSpecs = [...otherSpecs].sort((a, b) => a.type.localeCompare(b.type))
        
        sortedOtherSpecs.forEach(spec => {
          let displayName = spec.type
          let text = ""
          
          if (spec.type === "cpus") {
            displayName = "CPUs"
            text = `${spec.maximumAmountForUser} ${displayName}`
          } else if (spec.type === "memory") {
            displayName = "RAM"
            text = `${spec.maximumAmountForUser} ${spec.format} ${displayName}`
          } else if (spec.type === "storage") {
            displayName = "Storage"
            text = `${spec.maximumAmountForUser} ${spec.format} ${displayName}`
          } else {
            displayName = spec.type.charAt(0).toUpperCase() + spec.type.slice(1)
            text = `${spec.maximumAmountForUser} ${spec.format} ${displayName}`
          }
          
          hardwareList.push({ 
            id: spec.hardwareSpecId || spec.type, 
            text: text
          })
        })
        
        return hardwareList.length > 0 ? hardwareList : [{ id: 'none', text: 'No resources available' }]
      },
      async refreshCalendarReservations() {
        if (this.$refs.calendarComponent) {
          await this.$refs.calendarComponent.refreshCalendarData();
        }
      },
      handleReservationsRefreshed(reservations) {
        this.allReservations = reservations;
      },
      /**
       * Gets the memory spec ID from the selected hardware specs
       * @returns {string|null} The memory spec ID or null if not found
       */
      getMemorySpecId() {
        if (!this.hardwareData) return null;
        const memorySpec = this.hardwareData.find(spec => spec.type === "memory");
        return memorySpec ? memorySpec.hardwareSpecId : null;
      },
      /**
       * Calculates the actual SHM size in GB based on the percentage and selected memory
       * @returns {string} The calculated SHM size in GB
       */
      calculateShmSizeGB() {
        const memorySpecId = this.getMemorySpecId();
        if (!memorySpecId || !this.selectedHardwareSpecs[memorySpecId]) return "0";
        
        const memoryGB = this.selectedHardwareSpecs[memorySpecId];
        const shmGB = (memoryGB * this.shmSizePercent / 100).toFixed(1);
        return shmGB;
      },
      /**
       * Calculates the actual RAM disk size in GB based on the percentage and selected memory
       * @returns {string} The calculated RAM disk size in GB
       */
      calculateRamDiskSizeGB() {
        const memorySpecId = this.getMemorySpecId();
        if (!memorySpecId || !this.selectedHardwareSpecs[memorySpecId]) return "0";
        
        const memoryGB = this.selectedHardwareSpecs[memorySpecId];
        const ramDiskGB = (memoryGB * this.ramDiskSizePercent / 100).toFixed(1);
        return ramDiskGB;
      }
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
        return this.store.appTimezone
      },
      minimumDuration() {
        // Get minimum duration from user's role-based limits in store
        return this.store.userMinDuration || 1
      },
      maximumDuration() {
        // Get maximum duration from user's role-based limits in store
        return this.store.userMaxDuration || 48
      },
      minimumDurationDays() {
        return Math.floor(this.minimumDuration / 24)
      },
      maximumDurationDays() {
        return Math.floor(this.maximumDuration / 24)
      },
      minimumDurationHours() {
        return this.minimumDuration % 24
      },
      maximumDurationHours() {
        return this.maximumDuration % 24
      },
      reservationPageInstructions() {
        return this.store.reservationPageInstructions
      }
    },
    watch: {
      /**
       * Watch for changes in selected days and update hours dropdown accordingly
       */
      reserveDurationDays(newDays) {
        // Don't interfere if we're currently initializing defaults
        if (this.initializingDefaults) {
          return
        }
        
        if (newDays !== null && newDays !== undefined) {
          this.updateHoursDropdown(newDays)
        }
      },
      /**
       * Watch for when app config is loaded from store
       */
      'store.configLoaded'(isLoaded) {
        if (isLoaded && this.reservableDays.length === 0) {
          this.initializeDurationDefaults()
        }
      },
      /**
       * Watch for step changes to initialize defaults when step 2 becomes active
       */
      step(newStep) {
        if (newStep === 2) {
          this.initializeDurationDefaultsIfNeeded()
        }
      },
    }
  }
</script>

<style scoped lang="scss">
  h2 {
    margin-bottom: 10px;
  }
  
  .spec-row {
    margin-bottom: 10px;
  }

  .section {
    margin: 30px 0px;
  }

  .color-violet {
    color: #6d4c7d;
  }

  .dim {
    opacity: 0.8;
  }

  .color-green {
    color: green;
  }

  .refresh-tip {
    margin-top: 30px;
  }

  .selected-card {
    border: 2px solid #2196f3 !important;
    box-shadow: 0 0 12px rgba(33, 150, 243, 0.3) !important;
    transform: translateY(-2px);
    transition: all 0.3s ease;
  }

  .v-card:hover {
    transform: translateY(-1px);
    transition: all 0.3s ease;
  }

  .selected-card:hover {
    transform: translateY(-3px);
  }

  .v-expansion-panel::before {
    box-shadow: none !important;
  }
</style>