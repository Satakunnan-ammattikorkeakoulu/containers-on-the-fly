<template>
  <v-dialog v-model="isOpen" persistent max-width="800px">
    <v-card>
      <v-card-title>
        <span class="headline">Reservation Limits - {{ roleName }}</span>
      </v-card-title>
      
      <v-card-text>
        <!-- Description section -->
        <v-alert
          type="info"
          outlined
          class="mb-4"
        >
          <div class="text-body-2">
            <strong>Reservation Limits</strong> allow you to customize reservation duration and count limits for users with this role.
          </div>
          <div class="mt-2 text-caption grey--text">
            Note: Users will inherit the highest limits from all their assigned roles.
          </div>
        </v-alert>

        <v-container>
          <!-- Loading state -->
          <v-row v-if="isFetching">
            <v-col cols="12" class="text-center">
              <Loading />
            </v-col>
          </v-row>

          <!-- Content when loaded -->
          <template v-else>
            <!-- Duration Limits Section -->
            <v-row>
              <v-col cols="12">
                <div class="text-h6 mb-3">
                  <v-icon class="mr-2">mdi-clock-outline</v-icon>
                  Duration Limits
                </div>
              </v-col>
            </v-row>
            
            <v-row>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model.number="reservationLimits.minDuration"
                  type="number"
                  label="Minimum Duration (hours)"
                  :min="1"
                  :max="reservationLimits.maxDuration || 720"
                  outlined
                  dense
                  required
                  :rules="minDurationRules"
                >
                  <template v-slot:append>
                    <v-tooltip bottom>
                      <template v-slot:activator="{ on }">
                        <v-icon v-on="on" small>mdi-information-outline</v-icon>
                      </template>
                      <span>Minimum hours a user can reserve a container</span>
                    </v-tooltip>
                  </template>
                </v-text-field>
              </v-col>
              
              <v-col cols="12" md="6">
                <v-text-field
                  v-model.number="reservationLimits.maxDuration"
                  type="number"
                  label="Maximum Duration (hours)"
                  :min="reservationLimits.minDuration || 1"
                  :max="1440"
                  outlined
                  dense
                  required
                  :rules="maxDurationRules"
                >
                  <template v-slot:append>
                    <v-tooltip bottom>
                      <template v-slot:activator="{ on }">
                        <v-icon v-on="on" small>mdi-information-outline</v-icon>
                      </template>
                      <span>Maximum hours a user can reserve a container (up to 60 days)</span>
                    </v-tooltip>
                  </template>
                </v-text-field>
              </v-col>
            </v-row>

            <!-- Reservation Count Limits Section -->
            <v-row class="mt-4">
              <v-col cols="12">
                <div class="text-h6 mb-3">
                  <v-icon class="mr-2">mdi-counter</v-icon>
                  Reservation Count Limits
                </div>
              </v-col>
            </v-row>
            
            <v-row>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model.number="reservationLimits.maxActiveReservations"
                  type="number"
                  label="Max Active Reservations"
                  :min="0"
                  :max="99"
                  outlined
                  dense
                  required
                  :rules="maxActiveRules"
                >
                  <template v-slot:append>
                    <v-tooltip bottom>
                      <template v-slot:activator="{ on }">
                        <v-icon v-on="on" small>mdi-information-outline</v-icon>
                      </template>
                      <span>Maximum number of active (reserved or started) reservations a user can have</span>
                    </v-tooltip>
                  </template>
                </v-text-field>
              </v-col>
            </v-row>

          </template>
        </v-container>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="blue darken-1" text @click="close">Cancel</v-btn>
        <v-btn 
          color="blue darken-1" 
          text 
          @click="save" 
          :loading="isSubmitting"
          :disabled="!isValid"
        >
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
const axios = require('axios').default;
import Loading from '../global/Loading.vue';

export default {
  name: "AdminRoleReservationLimitsModal",
  components: {
    Loading
  },
  props: {
    roleId: {
      type: Number,
      required: true
    },
    roleName: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      isOpen: true,
      isFetching: true,
      isSubmitting: false,
      reservationLimits: {
        minDuration: null,
        maxDuration: null,
        maxActiveReservations: null
      }
    }
  },
  computed: {
    isValid() {
      // Check if min/max duration relationship is valid
      if (this.reservationLimits.minDuration !== null && this.reservationLimits.maxDuration !== null) {
        if (this.reservationLimits.minDuration > this.reservationLimits.maxDuration) {
          return false;
        }
      }
      return true;
    },
    minDurationRules() {
      return [
        v => !!v || v === 0 || 'This field is required',
        v => (v >= 1 && v <= 720) || 'Must be between 1 and 720 hours',
        v => {
          if (this.reservationLimits.maxDuration !== null && this.reservationLimits.maxDuration !== '') {
            return v <= this.reservationLimits.maxDuration || 'Must be less than or equal to max duration';
          }
          return true;
        }
      ];
    },
    maxDurationRules() {
      return [
        v => !!v || v === 0 || 'This field is required',
        v => (v >= 1 && v <= 1440) || 'Must be between 1 and 1440 hours (60 days)',
        v => {
          if (this.reservationLimits.minDuration !== null && this.reservationLimits.minDuration !== '') {
            return v >= this.reservationLimits.minDuration || 'Must be greater than or equal to min duration';
          }
          return true;
        }
      ];
    },
    maxActiveRules() {
      return [
        v => v !== null && v !== '' && v !== undefined || 'This field is required',
        v => (v >= 0 && v <= 99) || 'Must be between 0 and 99'
      ];
    }
  },
  mounted() {
    this.fetchData();
  },
  methods: {
    async fetchData() {
      this.isFetching = true;
      try {
        const currentUser = this.$store.getters.user;
        
        // Fetch existing role reservation limits from backend
        const response = await axios({
          method: "get",
          url: this.AppSettings.APIServer.admin.get_role_reservation_limits,
          params: { roleId: this.roleId },
          headers: {
            'Authorization': `Bearer ${currentUser.loginToken}`
          }
        });
        
        if (response.data.status === true) {
          const limits = response.data.data.reservationLimits;
          this.reservationLimits = {
            minDuration: limits.minDuration,
            maxDuration: limits.maxDuration,
            maxActiveReservations: limits.maxActiveReservations
          };
        }
      } catch (error) {
        console.error('Error fetching data:', error);
        this.$store.commit('showMessage', { 
          text: "Error loading reservation limits", 
          color: "red" 
        });
      } finally {
        this.isFetching = false;
      }
    },
    async save() {
      if (!this.isValid) return;
      
      this.isSubmitting = true;
      try {
        const currentUser = this.$store.getters.user;
        
        const response = await axios({
          method: "post",
          url: this.AppSettings.APIServer.admin.save_role_reservation_limits,
          data: { 
            roleId: this.roleId,
            reservationLimits: this.reservationLimits
          },
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${currentUser.loginToken}`
          }
        });

        if (response.data.status === true) {
          this.$store.commit('showMessage', { 
            text: "Reservation limits saved successfully", 
            color: "green" 
          });
          this.$emit('emitModalClose', true);
        } else {
          this.$store.commit('showMessage', { 
            text: response.data.message, 
            color: "red" 
          });
        }
      } catch (error) {
        console.error('Error saving reservation limits:', error);
        this.$store.commit('showMessage', { 
          text: "Error saving reservation limits", 
          color: "red" 
        });
      } finally {
        this.isSubmitting = false;
      }
    },
    close() {
      this.$emit('emitModalClose');
    }
  }
}
</script>

<style scoped lang="scss">
.text-caption {
  font-size: 0.75rem !important;
}
</style>