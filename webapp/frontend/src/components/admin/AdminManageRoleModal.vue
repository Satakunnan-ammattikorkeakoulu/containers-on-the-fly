<template>
    <v-form ref="form">
      <v-dialog v-model="isOpen" persistent max-width="600px">
        <v-card>
          <v-card-text v-if="item">
            <v-container>
              <v-row>
                <v-col cols="12" style="margin-bottom: 15px;">
                  <h2 class="title" v-if="isCreatingNew">Create new Role</h2>
                  <h2 class="title" v-else>Edit Role</h2>
                </v-col>
  
                <!-- NAME -->
                <v-col cols="12">
                  <v-text-field 
                    type="text" 
                    id="name" 
                    :rules="[rules.required]" 
                    v-model="data.name" 
                    label="Role Name*"
                    :disabled="isBuiltInRole">
                  </v-text-field>
                  <p class="help-text">Name of the role (e.g. "teacher", "student")</p>
                  <p v-if="isBuiltInRole" class="built-in-notice">This is a built-in role and cannot be modified.</p>
                </v-col>
              </v-row>
            </v-container>
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn color="blue darken-1" text @click="close">Close</v-btn>
            <v-btn 
              color="blue darken-1" 
              text 
              @click="save" 
              :loading="isSubmitting"
              :disabled="isBuiltInRole">
              Save
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </v-form>
  </template>
  
  <script>
  // Add axios back
  const axios = require('axios').default;

  export default {
    name: "AdminManageRoleModal",
    props: {
      propData: [ Number, String ], // Contains the ID of the role to edit, or "new" if creating new
    },
    data() {
      return {
        item: this.propData,
        data: {},
        isCreatingNew: false,
        isOpen: true,
        isFetching: true,
        isSubmitting: false,
        modalKey: new Date().toString(),
        rules: {
          required: value => !!value || "Required",
        }
      }
    },
    computed: {
      isBuiltInRole() {
        return this.data.roleId === 0 || this.data.roleId === 1;
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
    watch: {
      propData: {
        handler(newVal) {
          this.item = newVal;
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
        immediate: true,
      },
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