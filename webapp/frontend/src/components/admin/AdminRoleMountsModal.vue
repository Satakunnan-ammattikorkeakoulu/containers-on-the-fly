<template>
  <v-dialog v-model="isOpen" persistent max-width="1200px">
    <v-card>
      <v-card-title class="pt-6">
        <span class="headline">Manage Role Mounts - {{ roleName }}</span>
      </v-card-title>
      
      <v-card-text>
        <!-- Description section -->
        <v-alert
          type="info"
          outlined
          class="mb-4"
        >
          <div class="text-body-2">
            <strong>Role Mounts</strong> allow you to automatically mount folders from the host system into containers for users with this role.
            You can configure different mounts for each server/computer. The path to the folder will be automatically created if it does not exist (both host and container paths).
          </div>
          <div class="mt-3 text-body-2">
            <strong>Available template variables:</strong>
            <ul class="mt-1 ml-4">
              <li><code>&#123;email&#125;</code> - User's email address with special characters removed (e.g., "test@foo.com" becomes "testfoocom")</li>
              <li><code>&#123;userid&#125;</code> - User's database ID (e.g., "123")</li>
            </ul>
          </div>
          <div class="mt-2 text-caption" style="color: rgba(255, 255, 255, 0.75);">
            Example: <code>/data/users/&#123;email&#125;</code> → <code>/home/user/persistent</code>
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
            <!-- Computers and their mounts -->
            <v-expansion-panels>
              <v-expansion-panel
                v-for="computer in computers"
                :key="computer.computerId"
              >
                <v-expansion-panel-title>
                  {{ getComputerTitle(computer) }}
                </v-expansion-panel-title>
                <v-expansion-panel-text>
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
                        size="small"
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
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </template>
        </v-container>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="blue darken-1" variant="text" @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
/**
 * Modal dialog for managing host-to-container volume mounts for a specific role.
 * Displays an expansion panel per computer where admins can add or remove mounts
 * with host path, container path, and read-only settings. Supports template
 * variables ({email}, {userid}) for per-user mount paths.
 *
 * Props:
 *   roleId   - The ID of the role being configured.
 *   roleName - The display name of the role (shown in the header).
 *
 * Emits:
 *   emitModalClose - When the modal is closed.
 */
import axios from 'axios';
import Loading from '/src/components/global/Loading.vue';
import { useMainStore } from '@/store/store'

export default {
  name: 'AdminRoleMountsModal',
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
  data: () => ({
    isOpen: true,
    isFetching: false,
    isSubmitting: false,
    isLoadingMounts: false,
    computers: [],
    computerForms: {},
    mounts: [], // All mounts for this role
    mountsHeaders: [
      { title: 'Host Path', key: 'hostPath' },
      { title: 'Container Path', key: 'containerPath' },
      { title: 'Access', key: 'readOnly' },
      { title: 'Actions', key: 'actions', sortable: false }
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
        const currentUser = this.store.user;
        
        // Fetch computers
        const computersResponse = await axios({
          method: "get",
          url: this.$appSettings.APIServer.admin.get_computers,
          headers: {"Authorization": `Bearer ${currentUser.loginToken}`}
        });

        if (computersResponse.data.status) {
          this.computers = computersResponse.data.data.computers;
          
          // Initialize form data for each computer
          this.computers.forEach(computer => {
            this.computerForms[computer.computerId] = {
              valid: false,
              hostPath: '',
              containerPath: '',
              readOnly: false
            };
          });

          // Fetch existing mounts for this role
          const mountsResponse = await axios({
            method: "get",
            url: this.$appSettings.APIServer.admin.get_role_mounts,
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
          this.store.showMessage({
            text: "Failed to fetch computers", 
            color: "error" 
          });
        }
      } catch (error) {
        console.error(error);
        this.store.showMessage({
          text: "Error fetching data", 
          color: "error" 
        });
      } finally {
        this.isFetching = false;
      }
    },

    /** Filters the full mounts list to only those belonging to the given computer. */
    getMountsForComputer(computerId) {
      return this.mounts.filter(mount => mount.computerId === computerId);
    },

    /** Validates the form, appends the new mount, and saves all mounts to the backend. */
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
        const currentUser = this.store.user;
        const response = await axios({
          method: "post",
          url: this.$appSettings.APIServer.admin.save_role_mounts,
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
          
          this.store.showMessage({
            text: "Mount added successfully", 
            color: "success" 
          });
        } else {
          this.store.showMessage({
            text: response.data.message || "Failed to add mount", 
            color: "error" 
          });
        }
      } catch (error) {
        console.error(error);
        this.store.showMessage({
          text: "Error adding mount", 
          color: "error" 
        });
      } finally {
        this.isSubmitting = false;
      }
    },

    /** Confirms removal, removes the mount locally, and persists the updated list to the backend. */
    async removeMount(computerId, mountToRemove) {
      const confirm = window.confirm("Are you sure you want to remove this mount?");
      if (!confirm) return;

      this.isSubmitting = true;
      try {
        // Remove from local array
        const updatedMounts = this.mounts.filter(mount => 
          !(mount.computerId === computerId && 
            mount.hostPath === mountToRemove.hostPath && 
            mount.containerPath === mountToRemove.containerPath)
        );
        
        // Save updated mounts to backend
        const currentUser = this.store.user;
        const response = await axios({
          method: "post",
          url: this.$appSettings.APIServer.admin.save_role_mounts,
          data: {
            roleId: this.roleId,
            mounts: updatedMounts
          },
          headers: {"Authorization": `Bearer ${currentUser.loginToken}`}
        });

        if (response.data.status) {
          // Update local state
          this.mounts = updatedMounts;
          
          this.store.showMessage({
            text: "Mount removed successfully", 
            color: "success" 
          });
        } else {
          this.store.showMessage({
            text: response.data.message || "Failed to remove mount", 
            color: "error" 
          });
        }
      } catch (error) {
        console.error(error);
        this.store.showMessage({
          text: "Error removing mount", 
          color: "error" 
        });
      } finally {
        this.isSubmitting = false;
      }
    },

    close() {
      this.$emit('emitModalClose');
    },

    /** Returns the computer name with mount count appended, e.g. "Server1 (3 mounts)". */
    getComputerTitle(computer) {
      const mountCount = this.getMountsForComputer(computer.computerId).length;
      if (mountCount > 0) {
        const mountText = mountCount === 1 ? 'mount' : 'mounts';
        return `${computer.name} (${mountCount} ${mountText})`;
      }
      return computer.name;
    }
  },
}
</script>