<template>
  <v-container>

    <v-row class="text-center">
      <v-col cols="12">
        <h4>Admin</h4>
        <h2>All Hardware</h2>
      </v-col>
    </v-row>

    <v-row v-if="!isFetching">
      <v-col cols="12">
        <div v-if="data && data.length > 0" style="margin-top: 50px">
          <AdminHardwareTable v-bind:propItems="data" />
        </div>
        <p v-else class="dim text-center">No users.</p>
      </v-col>
    </v-row>
    <v-row v-else>
      <v-col cols="12">
        <Loading class="loading" />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
  import axios from 'axios';
  import Loading from '/src/components/global/Loading.vue';
  import AdminHardwareTable from '/src/components/admin/AdminHardwareTable.vue';
  import { useMainStore } from '@/store/store'

  export default {
    name: 'PageAdminHardware',

    setup() {
      const store = useMainStore()
      return { store }
    },

    components: {
      Loading,
      AdminHardwareTable,
    },
    data: () => ({
      intervalFetch: null,
      isFetching: false,
      data: [],
      tableName: "hardware",
    }),
    mounted () {
      this.isFetching = true
      this.fetch()

      // Keep updating data every 30 seconds
      this.intervalFetch = setInterval(() => { this.fetch()}, 30000)
    },
    methods: {
      fetch() {
        let _this = this
        let currentUser = this.store.user

        axios({
          method: "get",
          url: this.$appSettings.APIServer.admin.get_hardware,
          //params: { }
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
          //console.log(response)
            // Success
            if (response.data.status == true) {
              _this.data = response.data.data[_this.tableName]
            }
            // Fail
            else {
              console.log("Failed getting "+_this.tableName+"...")
              _this.store.showMessage({ text: "There was an error getting "+_this.tableName+".", color: "red" })
            }
            _this.isFetching = false
        })
        .catch(function (error) {
            // Error
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.store.showMessage({ text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.store.showMessage({ text: "Unknown error while trying to get "+_this.tableName+".", color: "red" })
            }
            _this.isFetching = false
        });

        this.isFetching = false
      },
    },
    beforeDestroy() {
      clearInterval(this.intervalFetch)
    },
  }
</script>

<style scoped lang="scss">
  .loading {
    margin: 60px auto;
  }
</style>