<template>
  <v-dialog v-model="isOpen" persistent max-width="1200px">
    <v-card>
      <v-card-title>
        <span class="headline">Hardware Limits - {{ roleName }}</span>
      </v-card-title>
      
      <v-card-text>
        <!-- Description section -->
        <v-alert
          type="info"
          outlined
          class="mb-4"
        >
          <div class="text-body-2">
            <strong>Hardware Limits</strong> allow you to override the default hardware allocation limits for users with this role.
            Leave fields empty to use the computer's default limits.
          </div>
          <div class="mt-2 text-caption grey--text">
            Note: These limits override the computer's default user limits but cannot exceed the system maximum.
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
            <!-- Computers and their hardware limits -->
            <v-expansion-panels v-model="expandedComputers" multiple>
              <v-expansion-panel
                v-for="computer in computers"
                :key="computer.computerId"
              >
                <v-expansion-panel-header>
                  <div>
                    <v-icon small class="mr-2">mdi-server</v-icon>
                    {{ computer.name }}
                    <v-chip
                      v-if="hasCustomLimits(computer.computerId)"
                      x-small
                      color="primary"
                      class="ml-2"
                    >
                      Customized
                    </v-chip>
                  </div>
                </v-expansion-panel-header>
                <v-expansion-panel-content>
                  <v-row
                    v-for="spec in getFilteredHardwareSpecs(computer)"
                    :key="spec.hardwareSpecId"
                    class="mb-4"
                  >
                    <v-col cols="12">
                      <div class="hardware-spec-section">
                        <div class="hardware-spec-header">
                          <v-icon small class="mr-1">{{ getHardwareIcon(spec.type) }}</v-icon>
                          <span class="font-weight-medium">{{ spec.displayName || spec.type.toUpperCase() }}</span>
                        </div>
                        <div class="hardware-spec-info text-caption grey--text">
                          Current user max: {{ spec.maximumAmountForUser }} | System max: {{ getSystemMaximum(computer, spec) }}
                        </div>
                        <div class="d-flex align-center mt-2">
                          <v-text-field
                            v-model.number="hardwareLimits[computer.computerId][spec.hardwareSpecId].maximum"
                            type="number"
                            label="Override Max"
                            :placeholder="spec.maximumAmountForUser.toString()"
                            :min="0"
                            :max="getSystemMaximum(computer, spec)"
                            dense
                            outlined
                            hide-details
                            class="flex-grow-1 mr-2"
                            style="max-width: 300px;"
                            @input="handleInputChange(computer.computerId, spec.hardwareSpecId, $event)"
                          >
                            <template v-slot:append>
                              <v-tooltip bottom>
                                <template v-slot:activator="{ on }">
                                  <v-icon v-on="on" small>mdi-information-outline</v-icon>
                                </template>
                                <span>Maximum amount users with this role can reserve (0-{{ getSystemMaximum(computer, spec) }})</span>
                              </v-tooltip>
                            </template>
                          </v-text-field>
                          <v-btn
                            icon
                            small
                            @click="resetHardwareLimit(computer.computerId, spec.hardwareSpecId)"
                            :disabled="!hasCustomLimit(computer.computerId, spec.hardwareSpecId)"
                          >
                            <v-icon small>mdi-restore</v-icon>
                          </v-btn>
                        </div>
                      </div>
                    </v-col>
                  </v-row>
                </v-expansion-panel-content>
              </v-expansion-panel>
            </v-expansion-panels>
          </template>
        </v-container>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="blue darken-1" text @click="close">Cancel</v-btn>
        <v-btn color="blue darken-1" text @click="save" :loading="isSubmitting">Save</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
const axios = require('axios').default;
import Loading from '../global/Loading.vue';

export default {
  name: "AdminRoleHardwareLimitsModal",
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
      computers: [],
      hardwareLimits: {},
      expandedComputers: []
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
        
        // Fetch available computers
        const response = await axios({
          method: "get",
          url: this.AppSettings.APIServer.admin.get_computers,
          headers: {
            'Authorization': `Bearer ${currentUser.loginToken}`
          }
        });

        if (response.data.status === true) {
          this.computers = response.data.data.computers;
          
          // Initialize hardware limits structure
          this.computers.forEach(computer => {
            this.hardwareLimits[computer.computerId] = {};
            computer.hardwareSpecs.forEach(spec => {
              this.hardwareLimits[computer.computerId][spec.hardwareSpecId] = {
                maximum: null
              };
            });
          });
          
          // Fetch existing role hardware limits from backend
          const limitsResponse = await axios({
            method: "get",
            url: this.AppSettings.APIServer.admin.get_role_hardware_limits,
            params: { roleId: this.roleId },
            headers: {
              'Authorization': `Bearer ${currentUser.loginToken}`
            }
          });
          
          if (limitsResponse.data.status === true) {
            // Apply fetched limits to our structure
            const fetchedLimits = limitsResponse.data.data.hardwareLimits;
            fetchedLimits.forEach(limit => {
              const computerId = limit.computerId;
              const hardwareSpecId = limit.hardwareSpecId;
              if (this.hardwareLimits[computerId] && this.hardwareLimits[computerId][hardwareSpecId]) {
                this.hardwareLimits[computerId][hardwareSpecId].maximum = limit.maximumAmountForRole;
              }
            });
          }
        }
      } catch (error) {
        console.error('Error fetching data:', error);
        this.$store.commit('showMessage', { 
          text: "Error loading hardware limits", 
          color: "red" 
        });
      } finally {
        this.isFetching = false;
      }
    },
    async save() {
      this.isSubmitting = true;
      try {
        const currentUser = this.$store.getters.user;
        
        const response = await axios({
          method: "post",
          url: this.AppSettings.APIServer.admin.save_role_hardware_limits,
          data: { 
            roleId: this.roleId,
            hardwareLimits: this.formatHardwareLimitsForBackend()
          },
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${currentUser.loginToken}`
          }
        });

        if (response.data.status === true) {
          this.$store.commit('showMessage', { 
            text: "Hardware limits saved successfully", 
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
        console.error('Error saving hardware limits:', error);
        this.$store.commit('showMessage', { 
          text: "Error saving hardware limits", 
          color: "red" 
        });
      } finally {
        this.isSubmitting = false;
      }
    },
    close() {
      this.$emit('emitModalClose');
    },
    getHardwareIcon(type) {
      const icons = {
        cpu: 'mdi-cpu-64-bit',
        gpu: 'mdi-expansion-card',
        ram: 'mdi-memory',
        disk: 'mdi-harddisk',
        network: 'mdi-ethernet'
      };
      return icons[type] || 'mdi-chip';
    },
    hasCustomLimits(computerId) {
      const limits = this.hardwareLimits[computerId];
      if (!limits) return false;
      return Object.values(limits).some(limit => limit.maximum !== null);
    },
    hasCustomLimit(computerId, hardwareSpecId) {
      const limit = this.hardwareLimits[computerId]?.[hardwareSpecId];
      return limit && limit.maximum !== null;
    },
    resetHardwareLimit(computerId, hardwareSpecId) {
      if (this.hardwareLimits[computerId] && this.hardwareLimits[computerId][hardwareSpecId]) {
        this.hardwareLimits[computerId][hardwareSpecId] = {
          maximum: null
        };
      }
    },
    formatHardwareLimitsForBackend() {
      const formattedLimits = [];
      
      Object.entries(this.hardwareLimits).forEach(([computerId, specs]) => {
        Object.entries(specs).forEach(([hardwareSpecId, limits]) => {
          if (limits.maximum !== null && limits.maximum !== '') {
            formattedLimits.push({
              computerId: parseInt(computerId),
              hardwareSpecId: parseInt(hardwareSpecId),
              maximumAmountForRole: limits.maximum === '' ? null : parseInt(limits.maximum)
            });
          }
        });
      });
      
      return formattedLimits;
    },
    getFilteredHardwareSpecs(computer) {
      // Filter out GPU specs that have an internalId
      return computer.hardwareSpecs.filter(spec => {
        if (spec.type === 'gpu' && spec.internalId) {
          return false;
        }
        return true;
      });
    },
    getSystemMaximum(computer, spec) {
      // For GPUs without internalId, count all GPU specs (including those with internalId)
      if (spec.type === 'gpu' && !spec.internalId) {
        return computer.hardwareSpecs.filter(s => s.type === 'gpu').length;
      }
      // For other hardware types, use the regular maximumAmount
      return spec.maximumAmount;
    },
    handleInputChange(computerId, hardwareSpecId, value) {
      // Convert empty string to null
      if (value === '' || value === null || value === undefined) {
        this.hardwareLimits[computerId][hardwareSpecId].maximum = null;
      } else {
        this.hardwareLimits[computerId][hardwareSpecId].maximum = parseInt(value);
      }
    }
  }
}
</script>

<style scoped lang="scss">
.help-text {
  color: #666;
  font-size: 0.8em;
  margin-top: 4px;
}
.v-expansion-panel-header {
  min-height: 48px;
}
.v-expansion-panel-content__wrap {
  padding: 16px;
}
.hardware-spec-section {
  padding: 8px 0;
}
.hardware-spec-header {
  display: flex;
  align-items: center;
  font-size: 14px;
}
.hardware-spec-info {
  margin-top: 4px;
  margin-bottom: 8px;
}
</style>