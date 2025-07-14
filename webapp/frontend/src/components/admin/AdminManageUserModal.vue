<template>
  <v-form ref="form">
    <v-dialog v-model="isOpen" persistent max-width="900px">
      <v-card>
        <v-card-text v-if="item">
          <v-container>
            <v-row>
              <v-col cols="12" style="margin-bottom: 15px;">
                <h2 class="title" v-if="isCreatingNew">Create new User</h2>
                <h2 class="title" v-else>Edit User</h2>
              </v-col>

              <!-- EMAIL -->
              <v-col cols="12">
                <v-text-field 
                  type="text" 
                  id="email" 
                  :rules="[rules.required, rules.email]" 
                  v-model="data.email" 
                  label="Email*">
                </v-text-field>
              </v-col>

              <!-- PASSWORD -->
              <v-col cols="12">
                <v-text-field 
                  type="password" 
                  :rules="isCreatingNew ? [rules.required, rules.newPassword] : [rules.newPassword]" 
                  v-model="data.password" 
                  :label="isCreatingNew ? 'Password*' : 'Password (leave empty to keep current)'">
                </v-text-field>
              </v-col>

              <!-- ROLES -->
              <v-col cols="12">
                <v-checkbox 
                  v-model="data.roles" 
                  label="admin" 
                  value="admin">
                </v-checkbox>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="red" text @click="closeDialog">Cancel</v-btn>
          <v-btn color="blue" text @click="submit" :disabled="isSubmitting">
            <span v-if="isCreatingNew">Add User</span>
            <span v-else>Save User</span>
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-form>
</template>

<script>
const axios = require('axios').default;

export default {
  name: "AdminManageUserModal",
  props: {
    propData: [Number, String], // Contains the ID of the user to edit, or "new" if creating new
  },
  data() {
    return {
      item: this.propData,
      data: { roles: [] },
      isCreatingNew: false,
      isOpen: true,
      isFetching: true,
      isSubmitting: false,
      modalKey: new Date().toString(),
      dataName: "user",
      rules: {
        required: value => !!value || "Required",
        newPassword: value => {
          if (!value || value === "") return true; // Allow empty for existing users
          if (value.length < 5) return "Password must be at least 5 characters long";
          return true;
        },
        email: value => {
          const pattern = /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
          return pattern.test(value) || 'Please enter a valid email address';
        },
      }
    };
  },
  created() {
    if (this.item === "new") {
      this.isCreatingNew = true;
      this.isFetching = false;
    } else {
      this.isFetching = true;
      this.fetchData();
    }
  },
  methods: {
    closeDialog() {
      this.isOpen = false;
    },
    submit() {
      if (!this.$refs.form.validate()) return;
      this.isSubmitting = true;
      let userId = this.item === "new" ? -1 : this.item;

      let _this = this;
      let currentUser = this.$store.getters.user;

      axios({
        method: "post",
        url: this.AppSettings.APIServer.admin.save_user,
        data: { userId: userId, data: this.data },
        headers: { "Authorization": `Bearer ${currentUser.loginToken}` }
      })
      .then(function(response) {
        if (response.data.status === true) {
          _this.closeDialog();
          _this.$store.commit('showMessage', { text: "User saved successfully", color: "green" });
        } else {
          _this.$store.commit('showMessage', { text: response.data.message, color: "red" });
        }
        _this.isSubmitting = false;
      })
      .catch(function(error) {
        if (error.response && (error.response.status === 400 || error.response.status === 401)) {
          _this.$store.commit('showMessage', { text: error.response.data.detail, color: "red" });
        } else {
          console.log(error);
          _this.$store.commit('showMessage', { text: "Unknown error while trying to save user", color: "red" });
        }
        _this.isSubmitting = false;
      });
    },
    fetchData() {
      let _this = this;
      let currentUser = this.$store.getters.user;

      axios({
        method: "get",
        url: this.AppSettings.APIServer.admin.get_user,
        params: { userId: this.item },
        headers: { "Authorization": `Bearer ${currentUser.loginToken}` }
      })
      .then(function(response) {
        if (response.data.status === true) {
          // Fix: Access the user data from the nested structure
          _this.data = response.data.data.user;
          if (!_this.data.roles) {
            _this.data.roles = [];
          }
        } else {
          console.log("Failed getting user...");
          _this.$store.commit('showMessage', { text: "There was an error getting user information", color: "red" });
        }
        _this.isFetching = false;
      })
      .catch(function(error) {
        if (error.response && (error.response.status === 400 || error.response.status === 401)) {
          _this.$store.commit('showMessage', { text: error.response.data.detail, color: "red" });
        } else {
          console.log(error);
          _this.$store.commit('showMessage', { text: "Unknown error while trying to get user information", color: "red" });
        }
        _this.isFetching = false;
      });
    }
  },
  watch: {
    isOpen: function(newVal) {
      if (newVal === false) {
        this.$emit("emitModalClose");
      }
    }
  }
};
</script>

<style scoped lang="scss">
.title {
  margin-top: 40px;
}

.help-text {
  margin-top: -7px;
}
</style> 