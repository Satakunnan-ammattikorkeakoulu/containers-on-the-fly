<template>
  <v-container>

    <v-row class="text-center">
      <v-col cols="12">
        <h4>Admin</h4>
        <h2>All Computers (Container Servers)</h2>
      </v-col>
    </v-row>

    <v-row class="text-center">
      <v-col cols="12">
        <v-btn color="green" @click="addComputer">Create New Computer</v-btn>
      </v-col>
    </v-row>

    <v-row v-if="!isFetching">
      <v-col cols="12">
        <div v-if="data && data.length > 0" style="margin-top: 50px">
          <AdminComputersTable 
            v-on:emitEditComputer="editComputer" 
            v-on:emitRemoveComputer="removeComputer" 
            v-on:emitFetchMonitoring="fetchMonitoringData"
            v-bind:propItems="data" 
            v-bind:propMonitoringData="monitoringData"
            v-bind:propActiveServers="activeServers"
            v-bind:propLastUpdateTime="lastUpdateTime"
          />
        </div>
        <p v-else class="dim text-center">No computers.</p>
      </v-col>
    </v-row>
    <v-row v-else>
      <v-col cols="12">
        <Loading class="loading" />
      </v-col>
    </v-row>
    <AdminManageComputerModal @click.stop="dialog = true" v-if="selectedItem" v-on:emitModalClose="closeDialog" :propData="selectedItem" :key="dialogKey"></AdminManageComputerModal>
  </v-container>
</template>

<script>
  const axios = require('axios').default;
  import Loading from '/src/components/global/Loading.vue';
  import AdminComputersTable from '/src/components/admin/AdminComputersTable.vue';
  import AdminManageComputerModal from '/src/components/admin/AdminManageComputerModal.vue';
  
  export default {
    name: 'PageAdminComputers',

    components: {
    Loading,
    AdminComputersTable,
    AdminManageComputerModal
},
    data: () => ({
      intervalFetch: null,
      intervalMonitoring: null,
      isFetching: false,
      data: [],
      isCreatingNew: false,
      selectedItem: undefined,
      dialog: false,
      dialogKey: new Date().getTime(),
      tableName: "computers",
      monitoringData: {},
      activeServers: {},
      lastUpdateTime: {},
    }),
    mounted () {
      this.isFetching = true
      this.fetch()

      // Keep updating data every 30 seconds
      this.intervalFetch = setInterval(() => { this.fetch()}, 30000)
      
      // Check server status every 30 seconds (will be called after initial fetch)
      this.intervalMonitoring = setInterval(() => { this.checkServerStatus()}, 30000)
    },
    methods: {
      addComputer() {
        this.selectedItem = "new";
        this.dialogKey = new Date().getTime();
        this.dialog = true;
      },
      editComputer(computerId) {
        this.dialogKey = new Date().getTime();
        this.selectedItem = computerId;
        this.dialog = true;
      },
      removeComputer(computerId) {
        let result = window.confirm("Do you really want to remove the computer? It will be marked as removed in the database and as not public anymore.")
        if (!result) return
        let params = {
          "computerId": computerId,
        }

        let _this = this
        let currentUser = this.$store.getters.user

        axios({
          method: "post",
          url: this.AppSettings.APIServer.admin.remove_computer,
          params: params,
          headers: {
            "Authorization" : `Bearer ${currentUser.loginToken}`
          }
        })
        .then(function (response) {
          //console.log(response)
            // Success
            if (response.data.status == true) {
              _this.$store.commit('showMessage', { text: "Computer removed.", color: "green" })
              _this.fetch()
            }
            // Fail
            else {
              console.log("Failed removing computer...")
              console.log(response)
              let msg = response && response.data && response.data.message ? response.data.message : "There was an error removing the container."
              _this.$store.commit('showMessage', { text: msg, color: "red" })
            }
        })
        .catch(function (error) {
            // Error
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.$store.commit('showMessage', { text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.$store.commit('showMessage', { text: "Unknown error.", color: "red" })
            }
        });
      },
      closeDialog() {
        this.dialog = false;
        this.fetch();
      },
      fetch() {
        let _this = this
        let currentUser = this.$store.getters.user

        axios({
          method: "get",
          url: this.AppSettings.APIServer.admin.get_computers,
          //params: { }
          headers: {"Authorization" : `Bearer ${currentUser.loginToken}`}
        })
        .then(function (response) {
          //console.log(response)
            // Success
            if (response.data.status == true) {
              _this.data = response.data.data[_this.tableName]
              // Check server status after data is loaded
              _this.checkServerStatus()
            }
            // Fail
            else {
              console.log("Failed getting "+_this.tableName+"...")
              _this.$store.commit('showMessage', { text: "There was an error getting "+_this.tableName+".", color: "red" })
            }
            _this.isFetching = false
        })
        .catch(function (error) {
            // Error
            if (error.response && (error.response.status == 400 || error.response.status == 401)) {
              _this.$store.commit('showMessage', { text: error.response.data.detail, color: "red" })
            }
            else {
              console.log(error)
              _this.$store.commit('showMessage', { text: "Unknown error while trying to get "+_this.tableName+".", color: "red" })
            }
            _this.isFetching = false
        });

        this.isFetching = false
      },
      
      async checkServerStatus() {
        // Get monitoring data for all servers to check their status
        if (!this.data || this.data.length === 0) return;
        
        let _this = this;
        let currentUser = this.$store.getters.user;
        
        // Clear previous active status but don't clear lastUpdateTime
        this.activeServers = {};
        
        // Check each server's monitoring data
        for (const server of this.data) {
          try {
            const response = await axios({
              method: "get",
              url: `${this.AppSettings.APIServer.admin.get_server_monitoring}/${server.computerId}/monitoring`,
              headers: {"Authorization": `Bearer ${currentUser.loginToken}`}
            });
            
            if (response.data.status === true && response.data.data) {
              // Check multiple sources for last update time
              let lastUpdated = null;
              
              // Try to get lastUpdated from metrics
              if (response.data.data.metrics && response.data.data.metrics.lastUpdated) {
                // The backend sends UTC time without Z suffix
                // We need to parse it as UTC by using DisplayTime's logic
                const timestamp = response.data.data.metrics.lastUpdated;
                // Parse it with Z to get UTC time
                const utcDate = new Date(timestamp + 'Z');
                lastUpdated = utcDate.getTime();
              }
              // If not in metrics, check logs for timestamps
              else if (response.data.data.logs) {
                // Check each log type for recent activity
                const logTypes = ['backend', 'frontend', 'docker_utility'];
                for (const logType of logTypes) {
                  if (response.data.data.logs[logType] && response.data.data.logs[logType].lastUpdated) {
                    const timestamp = response.data.data.logs[logType].lastUpdated;
                    // Parse it with Z to get UTC time
                    const utcDate = new Date(timestamp + 'Z');
                    const logTime = utcDate.getTime();
                    if (!lastUpdated || logTime > lastUpdated) {
                      lastUpdated = logTime;
                    }
                  }
                }
              }
              
              // Store the last update time
              if (lastUpdated) {
                _this.$set(_this.lastUpdateTime, server.computerId, lastUpdated);
                
                // Consider active if data is less than 7 minutes old
                const timeDiff = Date.now() - lastUpdated;
                
                if (timeDiff < 7 * 60 * 1000) {
                  _this.$set(_this.activeServers, server.computerId, true);
                }
              }
              
              // Even if no timestamp, if we got data, the server responded
              // So we can consider it active
              if (!lastUpdated && response.data.data.metrics) {
                _this.$set(_this.activeServers, server.computerId, true);
                _this.$set(_this.lastUpdateTime, server.computerId, Date.now());
              }
            }
          } catch (error) {
            // Server is not responding or has no monitoring data
            // Don't update lastUpdateTime if the request failed
          }
        }
      },
      
      async fetchMonitoringData(computerId) {
        let _this = this;
        let currentUser = this.$store.getters.user;
        
        // Set loading state for this server
        this.$set(this.monitoringData, computerId, { loading: true });
        
        try {
          const response = await axios({
            method: "get",
            url: `${this.AppSettings.APIServer.admin.get_server_monitoring}/${computerId}/monitoring`,
            headers: {"Authorization": `Bearer ${currentUser.loginToken}`}
          });
          
          if (response.data.status === true) {
            const data = response.data.data;
            
            // Update monitoring data for this server
            _this.$set(_this.monitoringData, computerId, {
              loading: false,
              metrics: data.metrics || {
                cpu: { usage: null, cores: null },
                memory: { total: null, used: null, percentage: null },
                disk: { total: null, used: null, free: null, percentage: null },
                docker: { running: null, total: null },
                load: { avg1: null, avg5: null, avg15: null },
                uptime: { days: null, hours: null, minutes: null }
              },
              logs: {
                backend: data.logs?.backend?.content || '',
                frontend: data.logs?.frontend?.content || '',
                backendDockerUtil: data.logs?.docker_utility?.content || ''
              },
              version: data.version || { software: null, updated: null },
              lastUpdated: data.metrics?.lastUpdated ? new Date(data.metrics.lastUpdated + 'Z') : null
            });
            
            // Update active status and last update time
            let lastUpdated = null;
            
            // Try to get lastUpdated from metrics
            if (data.metrics && data.metrics.lastUpdated) {
              const timestamp = data.metrics.lastUpdated;
              // Parse it with Z to get UTC time
              const utcDate = new Date(timestamp + 'Z');
              lastUpdated = utcDate.getTime();
            }
            // If not in metrics, check logs for timestamps
            else if (data.logs) {
              // Check each log type for recent activity
              const logTypes = ['backend', 'frontend', 'docker_utility'];
              for (const logType of logTypes) {
                if (data.logs[logType] && data.logs[logType].lastUpdated) {
                  const timestamp = data.logs[logType].lastUpdated;
                  // Parse it with Z to get UTC time
                  const utcDate = new Date(timestamp + 'Z');
                  const logTime = utcDate.getTime();
                  if (!lastUpdated || logTime > lastUpdated) {
                    lastUpdated = logTime;
                  }
                }
              }
            }
            
            if (lastUpdated) {
              _this.$set(_this.lastUpdateTime, computerId, lastUpdated);
              const timeDiff = Date.now() - lastUpdated;
              if (timeDiff < 7 * 60 * 1000) {
                _this.$set(_this.activeServers, computerId, true);
              }
            } else if (data.metrics) {
              // Even if no timestamp, if we got data, the server responded
              _this.$set(_this.activeServers, computerId, true);
              _this.$set(_this.lastUpdateTime, computerId, Date.now());
            }
          } else {
            // No data available
            _this.$set(_this.monitoringData, computerId, {
              loading: false,
              metrics: null,
              logs: null,
              version: null,
              lastUpdated: null
            });
          }
        } catch (error) {
          // Failed to fetch monitoring data
          _this.$set(_this.monitoringData, computerId, {
            loading: false,
            metrics: null,
            logs: null,
            version: null,
            lastUpdated: null
          });
        }
      }
    },
    beforeDestroy() {
      clearInterval(this.intervalFetch)
      clearInterval(this.intervalMonitoring)
    },
  }
</script>

<style scoped lang="scss">
  .loading {
    margin: 60px auto;
  }
</style>