<template>
  <v-container>
    <v-row class="text-center">
      <v-col cols="12">
        <v-img
          :src="require('/src/assets/images/front_bg.png')"
          class="my-3"
          contain
          height="350"
        />
      </v-col>

      <v-col class="mb-4">
        <h3 class="color-blue dim">Login to</h3>
        <h1 class="color-blue">{{appName}}</h1>
        <p class="color-blue dim" style="margin-top: 30px;" v-if="loginPageInfo && loginPageInfo.trim()" v-html="loginPageInfo.replace(/\n/g, '<br>')"></p>
      </v-col>

      <v-col class="mb-5" cols="12">
        <v-form ref="form" v-model="form['valid']" lazy-validation>
          <v-text-field v-on:keyup.enter="submitLoginForm" type="text" style="max-width: 300px; margin: 0 auto;" :label="usernameField" v-model="form['email']" :rules="validation['email']" required></v-text-field>
          <v-text-field v-on:keyup.enter="submitLoginForm" type="password" style="max-width: 300px; margin: 0 auto;" :label="passwordField" v-model="form['password']" :rules="validation['password']" required></v-text-field>
          <v-btn :disabled="!form['valid'] || isLoggingIn" color="success" @click="submitLoginForm" label="Login">Login</v-btn>
        </v-form>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
  const axios = require('axios').default;
  
  export default {
    name: 'PageLogin',

    data: () => ({
      snackbar: true,
      isLoggingIn: false,
      form: {
        email: "",
        password: "",
        valid: true,
      },
      validation: {
        email: [
          v => !!v || 'Username is required',
        ],
        password: [
          v => !!v || 'Password is required',
        ],
      }
    }),
    mounted() {
      // If user is already logged in, redirect to /user/reservations page.
      if (this.isLoggedIn) {
        this.$router.push("/user/reservations")
      }
    },
    computed: {
      isLoggedIn() {
        return this.$store.getters.isLoggedIn || false;
      },
      appName() {
        return this.$store.getters.appName
      },
      loginText() {
        return this.$store.getters.loginText
      },
      usernameField() {
        return this.$store.getters.usernameField
      },
      passwordField() {
        return this.$store.getters.passwordField
      },
      loginPageInfo() {
        return this.$store.getters.loginPageInfo
      }
    },
    methods: {
      submitLoginForm() {
        if (!this.$refs.form.validate()) return
        let _this = this
        let bodyFormData = new FormData()
        bodyFormData.append("username", this.form.email)
        bodyFormData.append("password", this.form.password)
        this.isLoggingIn = true

        axios({
          method: "post",
          url: this.AppSettings.APIServer.user.login,
          data: bodyFormData,
          headers: { "Content-Type": "multipart/form-data" },
        })
        .then(function (response) {
            // Success
            if (response.data && response.data.access_token) {
              // Set user data
              _this.$store.commit("setUser", { loginToken: response.data.access_token, callback: (res) => {
                //console.log(res)
                // Token OK, redirect user to reservations page
                if (res.success) {
                  _this.$router.push("/user/reservations");
                }
                else {
                  _this.$store.commit('showMessage', { text: "Error logging in.", color: "red" })
                }
              }});
            }
            else {
              //console.log("Failed to login.")
              _this.$store.commit('showMessage', { text: response.data.message, color: "red" })
            }
            _this.isLoggingIn = false
        })
        .catch(function (error) {
            // Error
            if (error.response && error.response.status == 400) {
              _this.$store.commit('showMessage', { text: error.response.data.detail, color: "alert" })
            }
            else {
              console.log(error)
              _this.$store.commit('showMessage', { text: "Unknown error.", color: "alert" })
            }
            _this.isLoggingIn = false
        });
      }
    }
  }
</script>

<style scoped>
  .color-violet {
    color: #6d4c7d;
  }
  .color-blue {
    color: #047093;
  }
  .dim {
    opacity: 0.8;
  }
</style>
