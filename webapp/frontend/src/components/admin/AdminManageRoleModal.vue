<template>
  <v-dialog v-model="isOpen" persistent max-width="500px">
    <v-card>
      <v-card-title class="pt-6">
        <span class="headline">{{ modalTitle }}</span>
      </v-card-title>
      <v-card-text>
        <v-container>
          <v-alert
            v-if="isCreatingNew"
            variant="outlined"
            color="info"
            class="mb-4"
          >
            <div class="text-body-2">
              Roles define what users can do when reserving containers. After creating a role, you can configure:
              <ul class="mt-1" style="padding-left: 20px;">
                <li><strong>Hardware Limits</strong> — maximum GPUs, CPUs, and other resources users can request</li>
                <li><strong>Reservation Limits</strong> — minimum/maximum duration and how many active reservations are allowed</li>
                <li><strong>Mounts</strong> — host folders automatically mounted into user containers</li>
              </ul>
              <div class="mt-1">Users can have multiple roles and will inherit the most permissive limits across all their assigned roles.</div>
            </div>
          </v-alert>
          <v-form ref="form" v-model="isValid">
            <v-row>
              <v-col cols="12">
                <v-text-field
                  v-model="data.name"
                  :rules="rules.name"
                  label="Role Name"
                  required
                ></v-text-field>
              </v-col>
            </v-row>
          </v-form>
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
import axios from 'axios';
import { useMainStore } from '@/store/store'

export default {
  name: "AdminManageRoleModal",
  setup() {
    const store = useMainStore()
    return { store }
  },
  props: {
    propData: {
      type: Object,
      default: null
    }
  },
  data() {
    return {
      isOpen: true,
      isValid: false,
      isSubmitting: false,
      data: {
        name: this.propData ? this.propData.name : ""  // Initialize with prop data
      },
      rules: {
        name: [v => !!v || 'Role name is required']
      }
    }
  },
  computed: {
    isCreatingNew() {
      return this.propData === null;  // Make sure this is explicit
    },
    modalTitle() {
      return this.isCreatingNew ? 'Create New Role' : 'Edit Role';
    },
    item() {
      return this.propData ? this.propData.roleId : null;
    }
  },
  watch: {
    propData: {
      handler(newVal) {
        if (newVal) {
          this.data.name = newVal.name;
        }
      },
      immediate: true
    }
  },
  mounted() {
    this.isCreatingNew = this.item === "new";
    if (this.isCreatingNew) {
      this.data = {
        name: "",
      };
      this.isFetching = false;
    } else {
      // TODO: Add backend call to fetch role details
      // For now using mock data
      if (this.item === 0) {
        this.data = {
          roleId: 0,
          name: "everyone",
        };
      } else if (this.item === 1) {
        this.data = {
          roleId: 1,
          name: "admin",
        };
      }
      this.isFetching = false;
    }
  },
  methods: {
    async save() {
      if (!this.$refs.form.validate()) return;
      
      this.isSubmitting = true;
      try {
        const currentUser = this.store.user;  // Get user the same way as other components
        
        const response = await axios({
          method: "post",
          url: this.$appSettings.APIServer.admin.save_role,
          params: { 
            roleId: this.isCreatingNew ? null : this.item,
            name: this.data.name
          },
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${currentUser.loginToken}`  // Use currentUser.loginToken
          }
        });

        //console.log('Role save response:', response.data);

        if (response.data.status === true) {
          this.$emit('emitModalClose', true);
        } else {
          this.store.showMessage({ text: response.data.message, color: "red" });
        }
      } catch (error) {
        console.error('Role save error:', error);
        if (error.response && (error.response.status === 400 || error.response.status === 401)) {
          this.store.showMessage({ text: error.response.data.detail, color: "red" });
        } else {
          this.store.showMessage({ text: "Unknown error while trying to save role", color: "red" });
        }
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
  .help-text {
    color: #666;
    font-size: 0.8em;
    margin-top: 4px;
  }
  .built-in-notice {
    color: #f44336;
    font-size: 0.9em;
    margin-top: 8px;
  }
  </style>