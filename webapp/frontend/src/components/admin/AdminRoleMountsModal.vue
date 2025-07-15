<template>
  <v-dialog v-model="isOpen" persistent max-width="1200px">
    <v-card>
      <v-card-title>
        <span class="headline">Manage Role Mounts - {{ roleName }}</span>
      </v-card-title>
      <v-card-text>
        <v-container>
          <!-- Loading state -->
          <v-row v-if="isFetching">
            <v-col cols="12" class="text-center">
              <Loading />
            </v-col>
          </v-row>

          <!-- Content when loaded -->
          <template v-else>
            <!-- Computers and their mounts -->
            <v-expansion-panels>
              <v-expansion-panel
                v-for="computer in computers"
                :key="computer.computerId"
              >
                <v-expansion-panel-header>
                  {{ computer.name }}
                </v-expansion-panel-header>
                <v-expansion-panel-content>
                  <!-- Add new mount form -->
                  <v-form 
                    :ref="`mountForm-${computer.computerId}`"
                    v-model="computerForms[computer.computerId].valid"
                  >
                    <v-row>
                      <v-col cols="12" md="5">
                        <v-text-field
                          v-model="computerForms[computer.computerId].hostPath"
                          label="Host Path*"
                          :rules="[rules.required]"
                          hint="Path on the host machine"
                          persistent-hint
                        ></v-text-field>
                      </v-col>
                      <v-col cols="12" md="5">
                        <v-text-field
                          v-model="computerForms[computer.computerId].containerPath"
                          label="Container Path*"
                          :rules="[rules.required]"
                          hint="Path inside the container"
                          persistent-hint
                        ></v-text-field>
                      </v-col>
                      <v-col cols="6" md="1">
                        <v-checkbox
                          v-model="computerForms[computer.computerId].readOnly"
                          label="Read Only"
                        ></v-checkbox>
                      </v-col>
                      <v-col cols="6" md="1">
                        <v-btn
                          color="primary"
                          @click="addMount(computer.computerId)"
                          :disabled="!computerForms[computer.computerId].valid || isSubmitting"
                          :loading="isSubmitting"
                        >
                          Add
                        </v-btn>
                      </v-col>
                    </v-row>
                  </v-form>

                  <!-- Existing mounts table -->
                  <v-data-table
                    :headers="mountsHeaders"
                    :items="getMountsForComputer(computer.computerId)"
                    :loading="isLoadingMounts"
                    class="elevation-1 mt-4"
                    hide-default-footer
                    dense
                  >
                    <template v-slot:item.readOnly="{ item }">
                      <v-chip
                        small
                        :color="item.readOnly ? 'warning' : 'success'"
                        text-color="white"
                      >
                        {{ item.readOnly ? 'Read Only' : 'Read Write' }}
                      </v-chip>
                    </template>
                    <template v-slot:item.actions="{ item }">
                      <v-btn
                        small
                        color="error"
                        text
                        @click="removeMount(computer.computerId, item)"
                        :loading="isSubmitting"
                      >
                        Remove
                      </v-btn>
                    </template>
                    <template v-slot:no-data>
                      No mounts configured
                    </template>
                  </v-data-table>
                </v-expansion-panel-content>
              </v-expansion-panel>
            </v-expansion-panels>
          </template>
        </v-container>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="blue darken-1" text @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
const axios = require('axios').default;
import Loading from '/src/components/global/Loading.vue';

export default {
  name: 'AdminRoleMountsModal',
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
  data: () => ({
    isOpen: true,
    isFetching: true,
    isSubmitting: false,
    isLoadingMounts: false,
    computers: [],
    computerForms: {},
    mounts: [], // All mounts for this role
    mountsHeaders: [
      { text: 'Host Path', value: 'hostPath' },
      { text: 'Container Path', value: 'containerPath' },
      { text: 'Read Only', value: 'readOnly', width: '100px' },
      { text: 'Actions', value: 'actions', sortable: false, width: '100px' }
    ],
    rules: {
      required: v => !!v || 'This field is required'
    }
  }),
  mounted() {
    this.fetchData();
  },
  methods: {
    async fetchData() {
      try {
        const currentUser = this.$store.getters.user;
        const response = await axios({
          method: "get",
          url: this.AppSettings.APIServer.admin.get_computers,
          headers: {"Authorization": `Bearer ${currentUser.loginToken}`}
        });

        if (response.data.status) {
          this.computers = response.data.data.computers;
          
          // Initialize form data for each computer
          this.computers.forEach(computer => {
            this.$set(this.computerForms, computer.computerId, {
              valid: false,
              hostPath: '',
              containerPath: '',
              readOnly: false
            });
          });

          // TODO: Fetch existing mounts for this role
          // Mock data for now
          this.mounts = [
            {
              computerId: this.computers[0]?.computerId,
              hostPath: '/data/shared',
              containerPath: '/mnt/shared',
              readOnly: true
            }
          ];
        } else {
          this.$store.commit('showMessage', { 
            text: "Failed to fetch computers", 
            color: "error" 
          });
        }
      } catch (error) {
        console.error(error);
        this.$store.commit('showMessage', { 
          text: "Error fetching data", 
          color: "error" 
        });
      } finally {
        this.isFetching = false;
      }
    },

    getMountsForComputer(computerId) {
      return this.mounts.filter(mount => mount.computerId === computerId);
    },

    async addMount(computerId) {
      if (!this.$refs[`mountForm-${computerId}`][0].validate()) return;
      
      this.isSubmitting = true;
      try {
        const newMount = {
          computerId,
          ...this.computerForms[computerId]
        };
        
        // TODO: Add API call to create new mount
        // Mock success for now
        this.mounts.push(newMount);
        
        // Reset form
        this.computerForms[computerId] = {
          valid: false,
          hostPath: '',
          containerPath: '',
          readOnly: false
        };
        this.$refs[`mountForm-${computerId}`][0].resetValidation();
        
      } catch (error) {
        console.error(error);
        this.$store.commit('showMessage', { 
          text: "Error adding mount", 
          color: "error" 
        });
      } finally {
        this.isSubmitting = false;
      }
    },

    async removeMount(computerId, mount) {
      const confirm = window.confirm("Are you sure you want to remove this mount?");
      if (!confirm) return;

      this.isSubmitting = true;
      try {
        // TODO: Add API call to remove mount
        // Mock success for now
        this.mounts = this.mounts.filter(m => 
          m.computerId !== computerId ||
          m.hostPath !== mount.hostPath || 
          m.containerPath !== mount.containerPath
        );
      } catch (error) {
        console.error(error);
        this.$store.commit('showMessage', { 
          text: "Error removing mount", 
          color: "error" 
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
.headline {
  font-size: 1.25rem;
  font-weight: 500;
}
.v-expansion-panels {
  margin-top: 1rem;
}
</style> 