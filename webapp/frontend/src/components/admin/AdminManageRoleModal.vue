<template>
  <v-dialog v-model="isOpen" persistent max-width="500px">
    <v-card>
      <v-card-title>
        <span class="headline">{{ modalTitle }}</span>
      </v-card-title>
      <v-card-text>
        <v-container>
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
        <v-btn color="blue darken-1" text @click="close">Cancel</v-btn>
        <v-btn color="blue darken-1" text @click="save" :loading="isSubmitting">Save</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
// Add axios back
const axios = require('axios').default;

export default {
  name: "AdminManageRoleModal",
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
        const currentUser = this.$store.getters.user;
        const response = await axios({
          method: "post",
          url: this.AppSettings.APIServer.admin.save_role,
          params: { 
            roleId: this.isCreatingNew ? null : this.item 
          },
          data: {
            name: this.data.name
          },
          headers: {"Authorization": `Bearer ${currentUser.loginToken}`}
        });

        if (response.data.status) {
          this.$store.commit('showMessage', { 
            text: this.isCreatingNew ? "Role created successfully" : "Role updated successfully", 
            color: "success" 
          });
          this.close(); // This will trigger the refresh
        } else {
          this.$store.commit('showMessage', { 
            text: response.data.message, 
            color: "error" 
          });
        }
      } catch (error) {
        console.error(error);
        this.$store.commit('showMessage', { 
          text: "Error saving role", 
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