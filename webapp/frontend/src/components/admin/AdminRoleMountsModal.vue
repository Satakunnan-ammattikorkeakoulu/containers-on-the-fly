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
                          hint="Path on the host machine (without ending slash /)"
                          persistent-hint
                        ></v-text-field>
                      </v-col>
                      <v-col cols="12" md="5">
                        <v-text-field
                          v-model="computerForms[computer.computerId].containerPath"
                          label="Container Path*"
                          :rules="[rules.required]"
                          hint="Path inside the container (without ending slash /), user home directory is /home/user"
                          persistent-hint
                        ></v-text-field>
                      </v-col>
                      <v-col cols="12" md="2">
                        <v-checkbox
                          v-model="computerForms[computer.computerId].readOnly"
                          label="Read Only"
                        ></v-checkbox>
                      </v-col>
                    </v-row>
                    <v-row>
                      <v-col cols="12">
                        <v-btn 
                          color="green" 
                          @click="addMount(computer.computerId)"
                          :loading="isSubmitting"
                        >
                          Add Mount
                        </v-btn>
                      </v-col>
                    </v-row>
                  </v-form>

                  <v-divider class="my-4"></v-divider>

                  <!-- Existing mounts table -->
                  <v-data-table
                    :headers="mountsHeaders"
                    :items="getMountsForComputer(computer.computerId)"
                    :loading="isLoadingMounts"
                    class="elevation-1"
                  >
                    <template v-slot:item.readOnly="{ item }">
                      <v-chip :color="item.readOnly ? 'orange' : 'green'">
                        {{ item.readOnly ? 'Read Only' : 'Read/Write' }}
                      </v-chip>
                    </template>
                    <template v-slot:item.actions="{ item }">
                      <v-btn 
                        small 
                        color="red" 
                        @click="removeMount(computer.computerId, item)"
                        :loading="isSubmitting"
                      >
                        Remove
                      </v-btn>
                    </template>
                    <template v-slot:no-data>
                      <div class="text-center pa-4">
                        No mounts configured
                      </div>
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
    isFetching: false,
    isSubmitting: false,
    isLoadingMounts: false,
    computers: [],
    computerForms: {},
    mounts: [], // All mounts for this role
    mountsHeaders: [
      { text: 'Host Path', value: 'hostPath' },
      { text: 'Container Path', value: 'containerPath' },
      { text: 'Access', value: 'readOnly' },
      { text: 'Actions', value: 'actions', sortable: false }
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
        this.isFetching = true;
        const currentUser = this.$store.getters.user;
        
        // Fetch computers
        const computersResponse = await axios({
          method: "get",
          url: this.AppSettings.APIServer.admin.get_computers,
          headers: {"Authorization": `Bearer ${currentUser.loginToken}`}
        });

        if (computersResponse.data.status) {
          this.computers = computersResponse.data.data.computers;
          
          // Initialize form data for each computer
          this.computers.forEach(computer => {
            this.$set(this.computerForms, computer.computerId, {
              valid: false,
              hostPath: '',
              containerPath: '',
              readOnly: false
            });
          });

          // Fetch existing mounts for this role
          const mountsResponse = await axios({
            method: "get",
            url: this.AppSettings.APIServer.admin.get_role_mounts,
            params: { roleId: this.roleId },
            headers: {"Authorization": `Bearer ${currentUser.loginToken}`}
          });

          if (mountsResponse.data.status) {
            this.mounts = mountsResponse.data.data.mounts;
          } else {
            console.warn("Failed to fetch mounts:", mountsResponse.data.message);
            this.mounts = [];
          }
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
        // Create new mount locally first
        const newMount = {
          computerId,
          ...this.computerForms[computerId]
        };
        
        // Add to local array
        const updatedMounts = [...this.mounts, newMount];
        
        // Save all mounts to backend
        const currentUser = this.$store.getters.user;
        const response = await axios({
          method: "post",
          url: this.AppSettings.APIServer.admin.save_role_mounts,
          data: {
            roleId: this.roleId,
            mounts: updatedMounts
          },
          headers: {"Authorization": `Bearer ${currentUser.loginToken}`}
        });

        if (response.data.status) {
          // Update local state
          this.mounts = updatedMounts;
          
          // Reset form
          this.computerForms[computerId] = {
            valid: false,
            hostPath: '',
            containerPath: '',
            readOnly: false
          };
          this.$refs[`mountForm-${computerId}`][0].resetValidation();
          
          this.$store.commit('showMessage', { 
            text: "Mount added successfully", 
            color: "success" 
          });
        } else {
          this.$store.commit('showMessage', { 
            text: response.data.message || "Failed to add mount", 
            color: "error" 
          });
        }
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
        // Remove from local array
        const updatedMounts = this.mounts.filter(m => 
          m.computerId !== computerId ||
          m.hostPath !== mount.hostPath || 
          m.containerPath !== mount.containerPath
        );
        
        // Save updated mounts to backend
        const currentUser = this.$store.getters.user;
        const response = await axios({
          method: "post",
          url: this.AppSettings.APIServer.admin.save_role_mounts,
          data: {
            roleId: this.roleId,
            mounts: updatedMounts
          },
          headers: {"Authorization": `Bearer ${currentUser.loginToken}`}
        });

        if (response.data.status) {
          // Update local state
          this.mounts = updatedMounts;
          
          this.$store.commit('showMessage', { 
            text: "Mount removed successfully", 
            color: "success" 
          });
        } else {
          this.$store.commit('showMessage', { 
            text: response.data.message || "Failed to remove mount", 
            color: "error" 
          });
        }
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