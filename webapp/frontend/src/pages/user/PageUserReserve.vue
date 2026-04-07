<template>
  <v-container class="text-center reserve-page">

    <h1 style="margin-bottom: 10px;">Reserve Server</h1>

    <!-- Reservation Page Instructions -->
    <v-row v-if="reservationPageInstructions && reservationPageInstructions.trim()">
      <v-col cols="12" class="mb-4">
        <v-alert
          type="info"
          outlined
          class="mx-auto text-left"
          style="max-width: 800px;"
        >
          <div v-html="reservationPageInstructions.replace(/\n/g, '<br>')"></div>
        </v-alert>
      </v-col>
    </v-row>

    <v-expansion-panels v-model="activePanel" class="mb-6">

      <!-- PANEL 0: DURATION -->
      <v-expansion-panel>
        <v-expansion-panel-title>
          <div class="d-flex align-center panel-title-content">
            <v-avatar size="28" color="primary" class="mr-3 flex-shrink-0">
              <span class="text-white text-body-2 font-weight-bold">1</span>
            </v-avatar>
            <v-icon class="mr-2">mdi-timer-outline</v-icon>
            <span class="font-weight-bold">Duration</span>
            <v-chip
              v-if="completedSections.duration && activePanel !== 0"
              color="success" variant="tonal" size="small" class="ml-3"
            >
              <v-icon start size="x-small">mdi-check</v-icon>
              {{ durationSummary }}
            </v-chip>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-alert
            v-if="hardwareFetched"
            type="info" variant="tonal" density="compact" class="mb-4 mx-auto text-left" style="max-width: 500px;"
          >
            Changing the duration will require re-checking hardware availability.
          </v-alert>
          <v-row justify="center">
            <v-col cols="12" sm="6" md="4" lg="3" style="min-width: 320px">
              <h2>Reservation Duration</h2>
              <p class="panel-description">Select how long you need the server. Minimum is <b>{{ formatDuration(minimumDuration) }}</b>, maximum is <b>{{ formatDuration(maximumDuration) }}</b>.</p>
              <v-row>
                <v-col cols="6">
                  <v-select v-model="reserveDurationDays" :items="reservableDays" item-title="text" item-value="value" label="Days"></v-select>
                </v-col>
                <v-col cols="6">
                  <v-select v-model="reserveDurationHours" :items="reservableHours" item-title="text" item-value="value" label="Hours"></v-select>
                </v-col>
              </v-row>
              <v-btn color="primary" @click="confirmDuration" :disabled="reserveDurationDays === null && reserveDurationHours === null" class="mt-2">
                Continue
              </v-btn>
            </v-col>
          </v-row>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <!-- PANEL 1: START TIME -->
      <v-expansion-panel :disabled="!completedSections.duration">
        <v-expansion-panel-title>
          <div class="d-flex align-center panel-title-content">
            <v-avatar size="28" :color="completedSections.duration ? 'primary' : 'grey-darken-1'" class="mr-3 flex-shrink-0">
              <span class="text-white text-body-2 font-weight-bold">2</span>
            </v-avatar>
            <v-icon class="mr-2">mdi-calendar-clock</v-icon>
            <span class="font-weight-bold">Start Time</span>
            <v-chip
              v-if="completedSections.time && activePanel !== 1"
              color="success" variant="tonal" size="small" class="ml-3"
            >
              <v-icon start size="x-small">mdi-check</v-icon>
              {{ parsedTimeSummary }}
            </v-chip>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-row>
            <v-col>
              <h2>Start Time</h2>
              <p class="panel-description">Start immediately or pick a time from the calendar below. Use the <strong>Availability</strong> toggle to check server resources.</p>
              <v-btn large @click="reserveNow" color="green" :loading="fetchingComputers && reserveType === 'now'" :disabled="fetchingComputers" class="mt-4">
                Start Immediately
              </v-btn>
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
          <Loading v-if="fetchingComputers && reserveType !== 'now'" />
          <v-alert v-if="hardwareFetchError" type="error" variant="tonal" class="mt-3 mx-auto" style="max-width: 600px;">
            {{ hardwareFetchError }}
          </v-alert>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <!-- PANEL 2: CONTAINER -->
      <v-expansion-panel :disabled="!hardwareFetched">
        <v-expansion-panel-title>
          <div class="d-flex align-center panel-title-content">
            <v-avatar size="28" :color="hardwareFetched ? 'primary' : 'grey-darken-1'" class="mr-3 flex-shrink-0">
              <span class="text-white text-body-2 font-weight-bold">3</span>
            </v-avatar>
            <v-icon class="mr-2">mdi-docker</v-icon>
            <span class="font-weight-bold">Container</span>
            <v-chip
              v-if="completedSections.container && activePanel !== 2"
              color="success" variant="tonal" size="small" class="ml-3"
            >
              <v-icon start size="x-small">mdi-check</v-icon>
              {{ containerSummary }}
            </v-chip>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <h2>Container Image</h2>
          <p class="panel-description">Select the operating system and software environment for your reservation.</p>
          <v-row justify="center" v-if="containers && containers.length">
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
        </v-expansion-panel-text>
      </v-expansion-panel>

      <!-- PANEL 3: SERVER & HARDWARE -->
      <v-expansion-panel :disabled="!completedSections.container">
        <v-expansion-panel-title>
          <div class="d-flex align-center panel-title-content">
            <v-avatar size="28" :color="completedSections.container ? 'primary' : 'grey-darken-1'" class="mr-3 flex-shrink-0">
              <span class="text-white text-body-2 font-weight-bold">4</span>
            </v-avatar>
            <v-icon class="mr-2">mdi-server</v-icon>
            <span class="font-weight-bold">Server & Hardware</span>
            <v-chip
              v-if="completedSections.hardware && activePanel !== 3"
              color="success" variant="tonal" size="small" class="ml-3"
            >
              <v-icon start size="x-small">mdi-check</v-icon>
              {{ hardwareSummary }}
            </v-chip>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <!-- Select computer -->
          <h2 id="select-computer-section">Select Server</h2>
          <p class="panel-description">Choose which server to run your container on. Hardware shown is what's available for your selected time slot.</p>
          <v-row justify="center" v-if="computers && computers.length">
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
                            class="font-weight-medium mb-2"
                            :style="{
                              color: computer === computerItem.value ? 'white' : 'rgba(255,255,255,0.8)',
                              fontSize: '14px'
                            }"
                          >
                            Available Hardware
                          </div>
                          <div
                            v-for="spec in getComputerHardwareList(computerItem.value)"
                            :key="spec.id"
                            :style="{
                              color: computer === computerItem.value ? 'white' : 'rgba(255,255,255,0.8)',
                              fontSize: '14px',
                              lineHeight: '1.6'
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

          <!-- Hardware selection (shown after computer is selected) -->
          <div v-if="computer && hardwareData">
            <h2 id="select-hardware-section" style="margin-top: 15px;">Configure Hardware</h2>

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
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <!-- PANEL 4: ADVANCED SETTINGS -->
      <v-expansion-panel :disabled="!completedSections.hardware">
        <v-expansion-panel-title>
          <div class="d-flex align-center panel-title-content">
            <v-avatar size="28" :color="completedSections.hardware ? 'primary' : 'grey-darken-1'" class="mr-3 flex-shrink-0">
              <span class="text-white text-body-2 font-weight-bold">5</span>
            </v-avatar>
            <v-icon class="mr-2">mdi-cog-outline</v-icon>
            <span class="font-weight-bold">Advanced Settings</span>
            <v-chip color="grey" variant="tonal" size="small" class="ml-3">
              {{ advancedSettingsSummary || 'Optional' }}
            </v-chip>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
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

          <!-- Start/Stop Script Paths -->
          <v-row style="margin-top: 20px;">
            <v-col cols="12" md="6" style="padding: 0 60px;">
              <h3 class="text-center">Start Script Path</h3>
              <p style="color: gray; font-size: 15px;">Absolute path to a script inside the container to run on start. Pre-filled from your profile.</p>
              <v-text-field
                v-model="reservationStartScriptPath"
                label="Start Script (optional)"
                placeholder=""
                :rules="[rules.scriptPath]"
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="6" style="padding: 0 60px;">
              <h3 class="text-center">Stop Script Path</h3>
              <p style="color: gray; font-size: 15px;">Absolute path to a script inside the container to run before stop. Pre-filled from your profile.</p>
              <v-text-field
                v-model="reservationStopScriptPath"
                label="Stop Script (optional)"
                placeholder=""
                :rules="[rules.scriptPath]"
              ></v-text-field>
            </v-col>
          </v-row>
        </v-expansion-panel-text>
      </v-expansion-panel>

    </v-expansion-panels>

    <!-- Create Reservation Section -->
    <v-row>
      <v-col cols="12">
        <!-- Notification of depleted resources -->
        <v-row v-if="refreshTip" justify="center">
          <v-col cols="12" sm="8" md="6">
            <v-alert class="refresh-tip" color="info" title="Information">
              <v-btn style="margin-bottom: 10px;" @click="refreshHardware">Refresh Hardware Data</v-btn>
              <p>If there were not enough resources for reservation, click the button above to refresh the hardware data.</p>
            </v-alert>
          </v-col>
        </v-row>

        <v-btn
          color="primary"
          size="large"
          @click="submitReservation"
          :disabled="!canCreateReservation || isSubmittingReservation"
        >
          Create Reservation
        </v-btn>
        <Loading v-if="isSubmittingReservation" />
        <p v-if="!canCreateReservation && !isSubmittingReservation" class="text-medium-emphasis mt-2" style="font-size: 14px;">
          {{ reservationIncompleteMessage }}
        </p>
      </v-col>
    </v-row>

  </v-container>
</template>

<script>
  import axios from 'axios';
  import dayjs from "dayjs";
  import utc from 'dayjs/plugin/utc'
  import timezone from 'dayjs/plugin/timezone'
  import customParseFormat from 'dayjs/plugin/customParseFormat'
  import relativeTime from 'dayjs/plugin/relativeTime'
  import CalendarReservations from '/src/components/user/CalendarReservations.vue';
  import Loading from '/src/components/global/Loading.vue';

  import { useMainStore } from '@/store/store'

  dayjs.extend(utc)
  dayjs.extend(timezone)
  dayjs.extend(customParseFormat)
  dayjs.extend(relativeTime)

  /**
   * Accordion-based reservation wizard for creating new container reservations.
   * Panel 1: Choose reservation duration (days/hours) within role-based limits.
   * Panel 2: Select start time via calendar or "Start Immediately" button.
   *          Triggers hardware availability check using the actual selected duration.
   * Panel 3: Select container image.
   * Panel 4: Select target server and hardware resources (GPUs, CPUs, memory, storage).
   * Panel 5: Advanced settings (SHM size, RAM disk, description, low-priority,
   *          admin-only reserve-for-another-user, start/stop scripts).
   * Collapsed panels show a summary of selections. Panels lock until prerequisites are met.
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
      activePanel: 0,
      completedSections: {
        duration: false,
        time: false,
        container: false,
        hardware: false,
      },
      hardwareFetched: false,
      hardwareFetchError: null,
      confirmedDuration: null, // Last confirmed total duration in hours
      reserveDate: null,
      reserveType: "",
      reservableHours: [],
      reservableDays: [],
      adminReserveUserEmail: null,
      reservationDescription: "",
      refreshTip: false,
      reserveDurationDays: null,
      reserveDurationHours: null,
      initializingDefaults: false,
      isLowPriority: false,
      shmSizePercent: 50,
      ramDiskSizePercent: 0,
      fetchingReservations: false,
      allReservations: null,
      fetchingComputers: false,
      allComputers: null,
      allContainers: null,
      computer: null,
      computers: null,
      container: null,
      containers: null,
      selectedgpus: [],
      hardwareData: null,
      selectedHardwareSpecs: {},
      reservationStartScriptPath: '',
      reservationStopScriptPath: '',
      timeTick: Date.now(),
      timeTickInterval: null,
      isSubmittingReservation: false,
      rules: {
        maxLength50: value => !value || value.length <= 50 || "Description must be 50 characters or less",
        scriptPath: v => !v || !v.trim() || v.trim().startsWith('/') || 'Must be an absolute path (starting with /)'
      }
    }),
    mounted() {
      // Initialize duration defaults if store config is already loaded
      if (this.store.configLoaded) {
        this.initializeDurationDefaults()
      }
      // Otherwise, the watcher will handle initialization when config loads

      this.fetchReservations()
      // Pre-fill script paths from user profile (synced via store)
      this.reservationStartScriptPath = this.store.user.startScriptPath || ''
      this.reservationStopScriptPath = this.store.user.stopScriptPath || ''
      // Update relative time display every 60 seconds
      this.timeTickInterval = setInterval(() => { this.timeTick = Date.now() }, 60000)
    },
    beforeUnmount() {
      if (this.timeTickInterval) {
        clearInterval(this.timeTickInterval)
      }
    },
    methods: {
      /**
       * Validates the selected duration and advances to the Time panel.
       * If the duration changed from a previously confirmed value, invalidates downstream data.
       */
      confirmDuration() {
        let duration = this.reserveDurationDays * 24 + this.reserveDurationHours
        if (duration < this.minimumDuration) {
          return this.store.showMessage({ text: "Minimum duration is " + this.minimumDuration + " hours.", color: "red" })
        }
        if (duration > this.maximumDuration) {
          return this.store.showMessage({ text: "Maximum duration is " + this.maximumDuration + " hours.", color: "red" })
        }

        // If duration changed from previously confirmed value, invalidate downstream
        if (this.hardwareFetched && this.confirmedDuration !== null && this.confirmedDuration !== duration) {
          this.invalidateFromDuration()
        }

        this.confirmedDuration = duration
        this.completedSections.duration = true
        this.advanceToPanel(1)
      },
      /**
       * Opens the specified expansion panel after the current tick completes.
       * @param {number} index - The panel index to open (0-based)
       */
      advanceToPanel(index) {
        this.$nextTick(() => {
          this.activePanel = index
        })
      },
      /**
       * Clears all hardware-dependent state when duration or time changes.
       * Called when the user confirms a changed duration or re-selects a time.
       */
      invalidateFromDuration() {
        this.hardwareFetched = false
        this.hardwareFetchError = null
        this.completedSections.time = false
        this.completedSections.container = false
        this.completedSections.hardware = false
        this.allComputers = null
        this.allContainers = null
        this.computers = null
        this.containers = null
        this.container = null
        this.computer = null
        this.hardwareData = null
        this.selectedHardwareSpecs = {}
        this.selectedgpus = []
      },
      /**
       * Refreshes the hardware data for the current date and duration.
       */
      refreshHardware() {
        if (this.reserveDate && this.completedSections.duration) {
          this.fetchAvailableHardware()
        }
        this.refreshTip = false
      },
      /**
       * Handles container selection and advances to the Server & Hardware panel.
       * @param {number} containerValue - The selected container ID
       */
      selectContainer(containerValue) {
        this.container = containerValue
        this.completedSections.container = true
        this.advanceToPanel(3)
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
      /**
       * Limits the amount of selected GPUs to the maximum amount allowed.
       */
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
       * Formats a duration in hours as a human-readable string with days and hours.
       * @param {number} totalHours - Duration in hours
       * @returns {string} Formatted string, e.g. "1 hour", "2 days", "60 days"
       */
      formatDuration(totalHours) {
        const days = Math.floor(totalHours / 24)
        const hours = totalHours % 24
        let parts = []
        if (days > 0) parts.push(`${days} day${days !== 1 ? 's' : ''}`)
        if (hours > 0) parts.push(`${hours} hour${hours !== 1 ? 's' : ''}`)
        return parts.join(' and ') || '0 hours'
      },
      /** Format hardware spec type for display (e.g. "cpus" -> "CPUs", "ram" -> "RAM"). */
      formatSpecType(type) {
        const labels = { 'cpus': 'CPUs', 'ram': 'RAM', 'cpu': 'CPU' };
        return labels[type.toLowerCase()] || type;
      },
      /**
       * Returns a list of all hardware specs except GPUs in the hardware data.
       * @returns {Array} Array of all hardware specs except GPUs
       */
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
       * Called when the user clicks "Start Immediately".
       * Sets the reservation date to now and fetches available hardware.
       */
      reserveNow() {
        if (this.fetchingComputers) return
        this.reserveDate = dayjs().toISOString()
        this.reserveType = "now"
        this.fetchAvailableHardware()
      },
      /**
       * Called when a time slot is selected on the calendar.
       * Sets the reservation date and fetches available hardware.
       * @param {Date} time The selected time slot
       */
      slotSelected(time) {
        if (this.fetchingComputers) return
        this.reserveDate = dayjs(time).toISOString()
        this.reserveType = "calendar"
        this.fetchAvailableHardware()
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

        this.completedSections.hardware = true

        // Auto-scroll to the "Configure Hardware" section
        try {
          this.$nextTick(() => {
            setTimeout(() => {
              const element = document.getElementById('select-hardware-section');
              if (element) {
                const navbarHeight = document.querySelector('.navbar')?.offsetHeight || 48
                const rect = element.getBoundingClientRect()
                window.scrollTo({
                  top: window.scrollY + rect.top - navbarHeight - 10,
                  behavior: 'smooth'
                })
              }
            }, 100);
          });
        } catch (error) {
          console.debug('Auto-scroll error:', error);
        }
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
            // Success
            if (response.data.status == true) {
              _this.allReservations = response.data.data.reservations
            }
            else {
              console.log("Failed getting reservations...")
            }
            _this.fetchingReservations = false
        })
        .catch(function (error) {
            // Error
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              // Silently handle auth errors on reservation fetch
            }
            else {
              console.log(error)
            }
            _this.fetchingReservations = false
        });
      },
      /**
       * Fetches all available hardware from the server for the selected date and duration.
       * On success, populates computers/containers and advances to the Container panel.
       */
      fetchAvailableHardware() {
        this.fetchingComputers = true
        this.hardwareFetchError = null
        // Clear downstream selections
        this.container = null
        this.computer = null
        this.hardwareData = null
        this.selectedHardwareSpecs = {}
        this.selectedgpus = []
        this.completedSections.container = false
        this.completedSections.hardware = false

        let _this = this
        let currentUser = this.store.user
        let duration = this.reserveDurationDays * 24 + this.reserveDurationHours

        axios({
          method: "get",
          url: this.$appSettings.APIServer.reservation.get_available_hardware,
          params: { "date": dayjs(this.reserveDate).tz("GMT+0").toISOString(), duration: duration },
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
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
                  return a.text.localeCompare(b.text)
                }
                return b.isPublic - a.isPublic
              })

              _this.containers = containers
              _this.hardwareFetched = true
              _this.completedSections.time = true
              _this.advanceToPanel(2) // Advance to Container panel
            }
            // Fail
            else {
              _this.hardwareFetchError = response.data.message
              _this.store.showMessage({ text: response.data.message, color: "red" })
            }
            _this.fetchingComputers = false
        })
        .catch(function (error) {
            // Error
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.hardwareFetchError = error.response.data.detail
              _this.store.showMessage({ text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.hardwareFetchError = "Unknown error."
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

        // Add GPUs to reservation
        this.selectedgpus.forEach((gpu) => {
          this.selectedHardwareSpecs[gpu] = 1
        })

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
          "isLowPriority": this.isLowPriority,
          "startScriptPath": this.reservationStartScriptPath && this.reservationStartScriptPath.trim() ? this.reservationStartScriptPath.trim() : "",
          "stopScriptPath": this.reservationStopScriptPath && this.reservationStopScriptPath.trim() ? this.reservationStopScriptPath.trim() : ""
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
            // Success
            if (response.data.status == true) {
              localStorage.setItem("justReserved", true)
              _this.$router.push("/user/reservations")
              _this.store.showMessage({ text: "Reservation created succesfully!", color: "green" })
              _this.refreshTip = false;
            }
            // Fail
            else {
              let msg = response && response.data && response.data.message ? response.data.message + " Try selecting fewer resources or a different time." : "There was an error creating the reservation."
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
          let gpuCount = gpuSpecs.filter(spec => spec.maximumAmountForUser > 0).length
          if (gpuCount > 0) {
            formattedSpecs.push(`${gpuCount} GPU${gpuCount > 1 ? 's' : ''}`)
          }
        }

        // Add other specs (limit to first 2-3 most important ones)
        let prioritySpecs = otherSpecs.slice(0, 2)
        prioritySpecs.forEach(spec => {
          if (spec.maximumAmountForUser > 0) {
            let displayName
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

        // Group specs by type - GPUs first, then others alphabetically
        let gpuSpecs = specs.filter(spec => spec.type === "gpu")
        let otherSpecs = specs.filter(spec => spec.type !== "gpus" && spec.type !== "gpu")

        // Always add GPUs first
        let gpuCount = gpuSpecs.filter(spec => spec.maximumAmountForUser > 0).length
        hardwareList.push({
          id: 'gpu',
          text: `${gpuCount} GPU${gpuCount !== 1 ? 's' : ''}`
        })

        // Add other specs sorted alphabetically
        let sortedOtherSpecs = [...otherSpecs].sort((a, b) => a.type.localeCompare(b.type))

        sortedOtherSpecs.forEach(spec => {
          let displayName
          let text

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
      /**
       * Refreshes the calendar reservations data.
       */
      async refreshCalendarReservations() {
        if (this.$refs.calendarComponent) {
          await this.$refs.calendarComponent.refreshCalendarData();
        }
      },
      /**
       * Handles refreshed reservations from the calendar component.
       * @param {Array} reservations Updated reservations array
       */
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
      /** Summary text for the Duration panel when collapsed. */
      durationSummary() {
        if (this.reserveDurationDays === null && this.reserveDurationHours === null) return ''
        let parts = []
        if (this.reserveDurationDays > 0) parts.push(`${this.reserveDurationDays} day${this.reserveDurationDays !== 1 ? 's' : ''}`)
        if (this.reserveDurationHours > 0) parts.push(`${this.reserveDurationHours} hour${this.reserveDurationHours !== 1 ? 's' : ''}`)
        return parts.join(', ') || `${this.minimumDuration} hours`
      },
      /** Summary text for the Start Time panel when collapsed. Shows relative time + full date. */
      parsedTimeSummary() {
        if (!this.reserveDate) return ''
        if (this.reserveType === 'now') return 'Immediately'
        // Reference timeTick to force recomputation every 60 seconds
        void this.timeTick
        const relative = dayjs(this.reserveDate).fromNow()
        const full = dayjs(this.reserveDate).format("DD.MM.YYYY HH:mm")
        return `Starts ${relative} (${full})`
      },
      /** Summary text for the Container panel when collapsed. */
      containerSummary() {
        if (!this.container || !this.allContainers) return ''
        let c = this.allContainers.find(x => x.containerId == this.container)
        return c ? c.name : ''
      },
      /** Summary text for the Server & Hardware panel when collapsed. */
      hardwareSummary() {
        if (!this.computer || !this.hardwareData) return ''
        let compName = ''
        if (this.computers) {
          let comp = this.computers.find(x => x.value === this.computer)
          if (comp) compName = comp.text
        }
        let parts = []
        if (this.selectedgpus.length > 0) {
          parts.push(`${this.selectedgpus.length} GPU${this.selectedgpus.length !== 1 ? 's' : ''}`)
        }
        this.hardwareDataNoGPUs().forEach(spec => {
          let val = this.selectedHardwareSpecs[spec.hardwareSpecId]
          if (val !== undefined && val !== null) {
            parts.push(`${val} ${spec.format} ${this.formatSpecType(spec.type)}`)
          }
        })
        let hwPart = parts.join(', ')
        return compName + (hwPart ? ' \u2022 ' + hwPart : '')
      },
      /** Summary text for the Advanced Settings panel when collapsed. */
      advancedSettingsSummary() {
        let parts = []
        if (this.isLowPriority) parts.push('Low-priority')
        if (this.reservationDescription && this.reservationDescription.trim()) parts.push(`"${this.reservationDescription.trim()}"`)
        if (this.shmSizePercent !== 50) parts.push(`SHM ${this.shmSizePercent}%`)
        if (this.ramDiskSizePercent > 0) parts.push(`RAM Disk ${this.ramDiskSizePercent}%`)
        if (this.adminReserveUserEmail && this.adminReserveUserEmail.trim()) parts.push(`For: ${this.adminReserveUserEmail.trim()}`)
        return parts.length > 0 ? parts.join(', ') : ''
      },
      /** Whether all required fields are filled to create a reservation. */
      canCreateReservation() {
        return this.completedSections.duration
          && this.completedSections.time
          && this.hardwareFetched
          && this.container !== null
          && this.computer !== null
          && Object.keys(this.selectedHardwareSpecs).length > 0
      },
      /** Message explaining what the user still needs to complete. */
      reservationIncompleteMessage() {
        if (!this.completedSections.duration) return 'Select a duration to begin.'
        if (!this.completedSections.time || !this.hardwareFetched) return 'Choose a start time and check availability.'
        if (!this.container) return 'Select a container image.'
        if (!this.computer) return 'Select a server and configure hardware.'
        return ''
      },
      globalTimezone() {
        return this.store.appTimezone
      },
      minimumDuration() {
        return this.store.userMinDuration || 1
      },
      maximumDuration() {
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
       * Scroll newly opened panel into view
       */
      activePanel(newPanel) {
        if (newPanel !== undefined && newPanel !== null) {
          // Wait for the expansion panel open/close animation to fully complete
          setTimeout(() => {
            const panels = this.$el.querySelectorAll('.v-expansion-panel')
            if (panels[newPanel]) {
              // Account for the fixed navbar height (68px) plus a small margin
              const navbarHeight = document.querySelector('.navbar')?.offsetHeight || 68
              const rect = panels[newPanel].getBoundingClientRect()
              window.scrollTo({
                top: window.scrollY + rect.top - navbarHeight + 10,
                behavior: 'smooth'
              })
            }
          }, 400)
        }
      }
    }
  }
</script>

<style scoped lang="scss">
  h2 {
    margin-bottom: 7px;
  }

  .panel-description {
    margin-top: 0px;
    margin-bottom: 30px;
    color: gray;
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

  /* Expansion panel title styling */
  :deep(.v-expansion-panel-title) {
    padding: 18px 24px !important;
    font-size: 16px !important;
    display: flex !important;
    align-items: center !important;
  }

  :deep(.v-expansion-panel-text__wrapper) {
    padding: 16px 24px 24px !important;
  }

  :deep(.v-expansion-panel--disabled) {
    opacity: 0.5;
  }

  .panel-title-content {
    flex: 1;
    text-align: left;
  }
</style>
