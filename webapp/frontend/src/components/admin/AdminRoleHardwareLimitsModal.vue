<template>
  <v-dialog v-model="isOpen" persistent max-width="1200px">
    <v-card>
      <v-card-title class="pt-6">
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
          <div class="mt-2 text-caption" style="color: rgba(255, 255, 255, 0.75);">
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
                <v-expansion-panel-title>
                  <div>
                    <v-icon size="small" class="mr-2">mdi-server</v-icon>
                    {{ computer.name }}
                    <v-chip
                      v-if="hasCustomLimits(computer.computerId)"
                      size="x-small"
                      color="primary"
                      class="ml-2"
                    >
                      Customized
                    </v-chip>
                  </div>
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-row
                    v-for="spec in getFilteredHardwareSpecs(computer)"
                    :key="spec.hardwareSpecId"
                    class="mb-4"
                  >
                    <v-col cols="12">
                      <div class="hardware-spec-section">
                        <div class="hardware-spec-header">
                          <v-icon size="small" class="mr-1">{{ getHardwareIcon(spec.type) }}</v-icon>
                          <span class="font-weight-medium">{{ spec.displayName || spec.type.toUpperCase() }}</span>
                        </div>
                        <div class="hardware-spec-info text-caption text-grey">
                          Current user max: {{ spec.maximumAmountForUser }} | Low-priority user max: {{ spec.maximumAmountForUserLowPriority }} | System max: {{ getSystemMaximum(computer, spec) }}
                        </div>
                        <div class="d-flex align-center flex-wrap mt-2">
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
                            clearable
                            class="flex-grow-1 mr-2"
                            style="max-width: 300px;"
                          >
                            <template v-slot:append>
                              <v-tooltip bottom>
                                <template v-slot:activator="{ props }">
                                  <v-icon v-bind="props" size="small">mdi-information-outline</v-icon>
                                </template>
                                <span>Maximum amount users with this role can reserve (0-{{ getSystemMaximum(computer, spec) }}). Leave blank to inherit the computer default.</span>
                              </v-tooltip>
                            </template>
                          </v-text-field>
                          <v-text-field
                            v-model.number="hardwareLimits[computer.computerId][spec.hardwareSpecId].maximumLowPriority"
                            type="number"
                            label="Override Low-Priority Max"
                            :placeholder="spec.maximumAmountForUserLowPriority.toString()"
                            :min="0"
                            :max="getSystemMaximum(computer, spec)"
                            dense
                            outlined
                            hide-details
                            clearable
                            class="flex-grow-1"
                            style="max-width: 300px;"
                          >
                            <template v-slot:append>
                              <v-tooltip bottom>
                                <template v-slot:activator="{ props }">
                                  <v-icon v-bind="props" size="small">mdi-information-outline</v-icon>
                                </template>
                                <span>Maximum amount users with this role can reserve in a low-priority reservation (0-{{ getSystemMaximum(computer, spec) }}). Leave blank to inherit the normal Override Max.</span>
                              </v-tooltip>
                            </template>
                          </v-text-field>
                        </div>
                      </div>
                    </v-col>
                  </v-row>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </template>
        </v-container>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="blue darken-1" variant="text" @click="close">Cancel</v-btn>
        <v-btn color="blue darken-1" variant="text" @click="save" :loading="isSubmitting">Save</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
/**
 * Modal dialog for configuring per-role hardware allocation limits on each computer.
 * Displays an expansion panel per computer, allowing admins to override the default
 * maximum CPU, RAM, and GPU amounts for users assigned to this role.
 *
 * Props:
 *   roleId   - The ID of the role being configured.
 *   roleName - The display name of the role (shown in the header).
 *
 * Emits:
 *   emitModalClose - When the modal is closed; passes true on successful save.
 */
import axios from 'axios';
import Loading from '../global/Loading.vue';
import { useMainStore } from '@/store/store'

export default {
  name: "AdminRoleHardwareLimitsModal",
  setup() {
    const store = useMainStore()
    return { store }
  },
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
        const currentUser = this.store.user;
        
        // Fetch available computers
        const response = await axios({
          method: "get",
          url: this.$appSettings.APIServer.admin.get_computers,
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
                maximum: null,
                maximumLowPriority: null
              };
            });
          });

          // Fetch existing role hardware limits from backend
          const limitsResponse = await axios({
            method: "get",
            url: this.$appSettings.APIServer.admin.get_role_hardware_limits,
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
                this.hardwareLimits[computerId][hardwareSpecId].maximumLowPriority = limit.maximumAmountForRoleLowPriority;
              }
            });
          }
        }
      } catch (error) {
        console.error('Error fetching data:', error);
        this.store.showMessage({
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
        const currentUser = this.store.user;
        
        const response = await axios({
          method: "post",
          url: this.$appSettings.APIServer.admin.save_role_hardware_limits,
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
          this.store.showMessage({
            text: "Hardware limits saved successfully", 
            color: "green" 
          });
          this.$emit('emitModalClose', true);
        } else {
          this.store.showMessage({
            text: response.data.message, 
            color: "red" 
          });
        }
      } catch (error) {
        console.error('Error saving hardware limits:', error);
        this.store.showMessage({
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
    /** Returns true if the given computer has any non-null override limits set. */
    hasCustomLimits(computerId) {
      const limits = this.hardwareLimits[computerId];
      if (!limits) return false;
      return Object.values(limits).some(limit => limit.maximum !== null || limit.maximumLowPriority !== null);
    },
    /** Converts the nested hardwareLimits object into a flat array for the backend API. */
    formatHardwareLimitsForBackend() {
      const formattedLimits = [];

      const normalize = (value) => {
        if (value === null || value === undefined || value === '') return null;
        return parseInt(value);
      };

      Object.entries(this.hardwareLimits).forEach(([computerId, specs]) => {
        Object.entries(specs).forEach(([hardwareSpecId, limits]) => {
          const normal = normalize(limits.maximum);
          const low = normalize(limits.maximumLowPriority);
          if (normal === null && low === null) return;
          formattedLimits.push({
            computerId: parseInt(computerId),
            hardwareSpecId: parseInt(hardwareSpecId),
            maximumAmountForRole: normal,
            maximumAmountForRoleLowPriority: low
          });
        });
      });

      return formattedLimits;
    },
    /**
     * Returns hardware specs for the computer, excluding individual GPU entries
     * (those with internalId) since the aggregate GPU spec already represents them.
     */
    getFilteredHardwareSpecs(computer) {
      return computer.hardwareSpecs.filter(spec => {
        if (spec.type === 'gpu' && spec.internalId) {
          return false;
        }
        return true;
      });
    },
    /**
     * Returns the system-wide maximum for a hardware spec.
     * For GPUs, this is the total count of individual GPU entries on the computer.
     * For CPU/RAM, this is the configured maximumAmount.
     */
    getSystemMaximum(computer, spec) {
      if (spec.type === 'gpu' && !spec.internalId) {
        return computer.hardwareSpecs.filter(s => s.type === 'gpu').length;
      }
      return spec.maximumAmount;
    },
  }
}
</script>

<style scoped lang="scss">
.help-text {
  margin-top: 4px;
}
.v-expansion-panel-title {
  min-height: 48px;
}
.v-expansion-panel-text__wrap {
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