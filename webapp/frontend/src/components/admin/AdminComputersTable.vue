<template>
  <div>
    <a v-if="hasLongItems" class="read-all-toggle" @click="toggleReadAll">{{ !readAll ? "Read all" : "Read less" }}</a>
    <v-data-table
      :headers="table.headers"
      :items="data"
      :sort-by="[{key: 'computerId', order: 'desc'}]"
      v-model:expanded="expanded"
      item-value="computerId"
      class="elevation-1">

      <!-- Status Badge -->
      <template v-slot:item.status="{item}">
        <div class="text-center">
          <v-tooltip bottom>
            <template v-slot:activator="{ props }">
              <div v-bind="props">
                <v-chip
                  size="small"
                  :color="getStatusColor(item)"
                  text-color="white"
                >
                  {{ getStatusText(item) }}
                </v-chip>
                <div class="caption text-grey mt-1" v-if="lastUpdateTime[item.computerId]">
                  {{ formatLastUpdate(lastUpdateTime[item.computerId]) }}
                </div>
                <div class="caption text-grey mt-1" v-else>
                  No data
                </div>
              </div>
            </template>
            <span v-if="lastUpdateTime[item.computerId]">
              Last update: {{ formatDirectTimestamp(lastUpdateTime[item.computerId]) }} ({{ store.appTimezone || 'UTC' }})
              <br>
              Status: {{ getStatusColor(item) === 'green' ? 'Online (< 7 min ago)' : 'Offline (> 7 min ago)' }}
            </span>
            <span v-else>
              No monitoring data received
            </span>
          </v-tooltip>
        </div>
      </template>

      <!-- Public -->
      <template v-slot:item.public="{item}">
        <v-chip size="small" :color="item.public ? 'green' : 'red'" text-color="white">
          {{ item.public ? 'Public' : 'Not Public' }}
        </v-chip>
      </template>

      <!-- Created -->
      <template v-slot:item.createdAt="{item}">
        <v-tooltip v-if="item.createdAt" location="bottom" :text="parseTime(item.createdAt)">
          <template v-slot:activator="{ props }">
            <span v-bind="props">{{ parseRelativeTime(item.createdAt) }}</span>
          </template>
        </v-tooltip>
      </template>

      <!-- Updated -->
      <template v-slot:item.updatedAt="{item}">
        <v-tooltip v-if="item.updatedAt" location="bottom" :text="parseTime(item.updatedAt)">
          <template v-slot:activator="{ props }">
            <span v-bind="props">{{ parseRelativeTime(item.updatedAt) }}</span>
          </template>
        </v-tooltip>
      </template>

      <!-- Actions -->
      <template v-slot:item.actions="{item}">
        <v-menu>
          <template v-slot:activator="{ props }">
            <a v-bind="props">
              Actions <v-icon size="small">mdi-chevron-down</v-icon>
            </a>
          </template>
          <v-list density="compact">
            <v-list-item @click="toggleExpand(item)">
              <template v-slot:prepend><v-icon size="small">mdi-chart-line</v-icon></template>
              <v-list-item-title>{{ isExpanded(item) ? 'Hide' : 'Show' }} Monitoring</v-list-item-title>
            </v-list-item>
            <v-list-item @click="emitEditComputer(item.computerId)">
              <template v-slot:prepend><v-icon size="small">mdi-pencil-outline</v-icon></template>
              <v-list-item-title>Edit Computer</v-list-item-title>
            </v-list-item>
            <v-divider class="my-1" />
            <v-list-item @click="emitRemoveComputer(item.computerId)" class="destructive-action">
              <template v-slot:prepend><v-icon size="small">mdi-delete-outline</v-icon></template>
              <v-list-item-title>Remove Computer</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </template>

      <!-- Expanded content -->
      <template v-slot:expanded-row="{ columns, item }">
        <td :colspan="columns.length" class="pa-0">
          <v-card flat class="ma-4">
            <v-card-title class="headline">
              <v-icon class="mr-2">mdi-monitor-eye</v-icon>
              Server Monitoring - {{ item.name }}
            </v-card-title>
            
            <v-card-text>
              <!-- Loading state -->
              <div v-if="monitoringData[item.computerId] && monitoringData[item.computerId].loading" class="text-center pa-8">
                <v-progress-circular indeterminate color="primary"></v-progress-circular>
                <p class="mt-4">Loading monitoring data...</p>
              </div>
              
              <!-- Monitoring data -->
              <div v-else-if="monitoringData[item.computerId] && !monitoringData[item.computerId].loading && monitoringData[item.computerId].metrics">
                <!-- Last Updated Info -->
                <div class="mb-4" v-if="monitoringData[item.computerId].lastUpdated">
                  <p class="caption mb-0">
                    Last Updated: {{ formatTimestamp(monitoringData[item.computerId].lastUpdated) }}
                  </p>
                </div>
                
                <!-- Hardware Metrics Section -->
                <div class="mb-6">
                  <h6 class="text-h6 mb-4">System Hardware Metrics</h6>
                  
                  <v-row>
                    <!-- CPU Usage -->
                    <v-col cols="12" md="3">
                      <v-card variant="outlined" class="pa-3">
                        <div class="d-flex align-center mb-2">
                          <v-icon class="mr-2" color="blue">mdi-chip</v-icon>
                          <span class="font-weight-medium">CPU Usage</span>
                        </div>
                        <div class="text-center">
                          <v-progress-circular
                            v-if="monitoringData[item.computerId].metrics.cpu.usage !== null"
                            :value="monitoringData[item.computerId].metrics.cpu.usage"
                            :color="getCpuColor(monitoringData[item.computerId].metrics.cpu.usage)"
                            size="60"
                            width="6"
                            class="mb-2"
                          >
                            <span class="text-h6">{{ Math.round(monitoringData[item.computerId].metrics.cpu.usage || 0) }}%</span>
                          </v-progress-circular>
                          <div v-else class="text-h6 mb-2 text-grey">
                            No data
                          </div>
                          <div class="caption text-grey">
                            {{ monitoringData[item.computerId].metrics.cpu.cores !== null ? `${monitoringData[item.computerId].metrics.cpu.cores} cores` : 'No data' }}
                          </div>
                        </div>
                      </v-card>
                    </v-col>
                    
                    <!-- Memory Usage -->
                    <v-col cols="12" md="3">
                      <v-card variant="outlined" class="pa-3">
                        <div class="d-flex align-center mb-2">
                          <v-icon class="mr-2" color="green">mdi-memory</v-icon>
                          <span class="font-weight-medium">Memory</span>
                        </div>
                        <div class="text-center">
                          <v-progress-circular
                            v-if="monitoringData[item.computerId].metrics.memory.percentage !== null"
                            :value="monitoringData[item.computerId].metrics.memory.percentage"
                            :color="getMemoryColor(monitoringData[item.computerId].metrics.memory.percentage)"
                            size="60"
                            width="6"
                            class="mb-2"
                          >
                            <span class="text-h6">{{ Math.round(monitoringData[item.computerId].metrics.memory.percentage || 0) }}%</span>
                          </v-progress-circular>
                          <div v-else class="text-h6 mb-2 text-grey">
                            No data
                          </div>
                          <div class="caption text-grey">
                            {{ monitoringData[item.computerId].metrics.memory.used !== null && monitoringData[item.computerId].metrics.memory.total !== null ? 
                               `${formatBytes(monitoringData[item.computerId].metrics.memory.used)} / ${formatBytes(monitoringData[item.computerId].metrics.memory.total)}` : 
                               'No data' }}
                          </div>
                        </div>
                      </v-card>
                    </v-col>
                    
                    <!-- Disk Usage -->
                    <v-col cols="12" md="3">
                      <v-card variant="outlined" class="pa-3">
                        <div class="d-flex align-center mb-2">
                          <v-icon class="mr-2" color="teal">mdi-harddisk</v-icon>
                          <span class="font-weight-medium">Disk (/)</span>
                        </div>
                        <div class="text-center">
                          <v-progress-circular
                            v-if="monitoringData[item.computerId].metrics.disk.percentage !== null"
                            :value="monitoringData[item.computerId].metrics.disk.percentage"
                            :color="getDiskColor(monitoringData[item.computerId].metrics.disk.percentage)"
                            size="60"
                            width="6"
                            class="mb-2"
                          >
                            <span class="text-h6">{{ Math.round(monitoringData[item.computerId].metrics.disk.percentage || 0) }}%</span>
                          </v-progress-circular>
                          <div v-else class="text-h6 mb-2 text-grey">
                            No data
                          </div>
                          <div class="caption text-grey">
                            {{ monitoringData[item.computerId].metrics.disk.used !== null && monitoringData[item.computerId].metrics.disk.total !== null ? 
                               `${formatBytes(monitoringData[item.computerId].metrics.disk.used)} / ${formatBytes(monitoringData[item.computerId].metrics.disk.total)}` : 
                               'No data' }}
                          </div>
                        </div>
                      </v-card>
                    </v-col>
                    
                    <!-- Docker Status -->
                    <v-col cols="12" md="3">
                      <v-card variant="outlined" class="pa-3">
                        <div class="d-flex align-center mb-2">
                          <v-icon class="mr-2" color="cyan">mdi-docker</v-icon>
                          <span class="font-weight-medium">Docker</span>
                        </div>
                        <div class="d-flex justify-space-between">
                          <div class="text-center">
                            <div class="caption text-grey">Running</div>
                            <div class="text-subtitle-2">{{ monitoringData[item.computerId].metrics.docker.running !== null ? monitoringData[item.computerId].metrics.docker.running : '-' }}</div>
                          </div>
                          <div class="text-center">
                            <div class="caption text-grey">Total</div>
                            <div class="text-subtitle-2">{{ monitoringData[item.computerId].metrics.docker.total !== null ? monitoringData[item.computerId].metrics.docker.total : '-' }}</div>
                          </div>
                        </div>
                      </v-card>
                    </v-col>
                  </v-row>
                  
                  <!-- Additional Metrics Row -->
                  <v-row class="mt-4">
                    <!-- System Load -->
                    <v-col cols="12" md="4">
                      <v-card variant="outlined" class="pa-3">
                        <div class="d-flex align-center mb-2">
                          <v-icon class="mr-2" color="orange">mdi-gauge</v-icon>
                          <span class="font-weight-medium">System Load</span>
                        </div>
                        <div class="text-center">
                          <div class="text-h6 mb-1">
                            {{ monitoringData[item.computerId].metrics.load.avg1 !== null ? monitoringData[item.computerId].metrics.load.avg1 : 'No data' }}
                          </div>
                          <div class="caption text-grey">
                            1m: {{ monitoringData[item.computerId].metrics.load.avg1 !== null ? monitoringData[item.computerId].metrics.load.avg1 : '-' }}<br>
                            5m: {{ monitoringData[item.computerId].metrics.load.avg5 !== null ? monitoringData[item.computerId].metrics.load.avg5 : '-' }}<br>
                            15m: {{ monitoringData[item.computerId].metrics.load.avg15 !== null ? monitoringData[item.computerId].metrics.load.avg15 : '-' }}
                          </div>
                        </div>
                      </v-card>
                    </v-col>
                    
                    <!-- Uptime -->
                    <v-col cols="12" md="4">
                      <v-card variant="outlined" class="pa-3">
                        <div class="d-flex align-center mb-2">
                          <v-icon class="mr-2" color="purple">mdi-clock-outline</v-icon>
                          <span class="font-weight-medium">Uptime</span>
                        </div>
                        <div class="text-center">
                          <div class="text-h6 mb-1">
                            {{ monitoringData[item.computerId].metrics.uptime.days !== null ? `${monitoringData[item.computerId].metrics.uptime.days}d` : 'No data' }}
                          </div>
                          <div class="caption text-grey">
                            {{ monitoringData[item.computerId].metrics.uptime.hours !== null && monitoringData[item.computerId].metrics.uptime.minutes !== null ? 
                               `${monitoringData[item.computerId].metrics.uptime.hours}h ${monitoringData[item.computerId].metrics.uptime.minutes}m` : 
                               'No data' }}
                          </div>
                        </div>
                      </v-card>
                    </v-col>
                    
                    <!-- Software Version -->
                    <v-col cols="12" md="4">
                      <v-card variant="outlined" class="pa-3">
                        <div class="d-flex align-center mb-2">
                          <v-icon class="mr-2" color="indigo">mdi-tag</v-icon>
                          <span class="font-weight-medium">Software Version</span>
                        </div>
                        <div class="text-center">
                          <div class="text-h6 mb-1">
                            {{ monitoringData[item.computerId].version?.software || 'Unknown' }}
                          </div>
                          <div class="caption text-grey">
                            {{ monitoringData[item.computerId].version?.updated ? `Updated: ${formatTimestamp(new Date(monitoringData[item.computerId].version.updated))}` : 'No data' }}
                          </div>
                        </div>
                      </v-card>
                    </v-col>
                  </v-row>
                </div>
                
                <v-divider class="my-6"></v-divider>
                
                <!-- PM2 Logs Section -->
                <div class="mb-4">
                  <h6 class="text-h6 mb-4">PM2 Application Logs</h6>
                  <p class="body-2 text-grey mb-4">
                    Logs from PM2 processes. Latest logs are at the top.
                  </p>
                </div>
                
                <!-- Backend Logs -->
                <div class="mb-6">
                  <div class="d-flex align-center mb-2">
                    <v-icon class="mr-2" color="blue">mdi-server</v-icon>
                    <h6 class="text-subtitle-1 font-weight-medium">Backend Application</h6>
                    <v-spacer></v-spacer>
                    <v-chip
                      size="small"
                      :color="monitoringData[item.computerId].logs.backend ? 'green' : 'grey'"
                      text-color="white"
                    >
                      {{ monitoringData[item.computerId].logs.backend ? 'Active' : 'No Data' }}
                    </v-chip>
                  </div>
                  <v-textarea
                    :value="reverseLogOrder(monitoringData[item.computerId].logs.backend)"
                    readonly
                    outlined
                    rows="10"
                    placeholder="Backend logs will appear here..."
                    class="logs-textarea"
                  ></v-textarea>
                </div>
                
                <!-- Frontend Logs -->
                <div class="mb-6">
                  <div class="d-flex align-center mb-2">
                    <v-icon class="mr-2" color="green">mdi-web</v-icon>
                    <h6 class="text-subtitle-1 font-weight-medium">Frontend Application</h6>
                    <v-spacer></v-spacer>
                    <v-chip
                      size="small"
                      :color="monitoringData[item.computerId].logs.frontend ? 'green' : 'grey'"
                      text-color="white"
                    >
                      {{ monitoringData[item.computerId].logs.frontend ? 'Active' : 'No Data' }}
                    </v-chip>
                  </div>
                  <v-textarea
                    :value="reverseLogOrder(monitoringData[item.computerId].logs.frontend)"
                    readonly
                    outlined
                    rows="10"
                    placeholder="Frontend logs will appear here..."
                    class="logs-textarea"
                  ></v-textarea>
                </div>
                
                <!-- Container Server Daemon Logs -->
                <div class="mb-6">
                  <div class="d-flex align-center mb-2">
                    <v-icon class="mr-2" color="orange">mdi-docker</v-icon>
                    <h6 class="text-subtitle-1 font-weight-medium">Container Server Daemon</h6>
                    <v-spacer></v-spacer>
                    <v-chip
                      size="small"
                      :color="monitoringData[item.computerId].logs.backendDockerUtil ? 'green' : 'grey'"
                      text-color="white"
                    >
                      {{ monitoringData[item.computerId].logs.backendDockerUtil ? 'Active' : 'No Data' }}
                    </v-chip>
                  </div>
                  <v-textarea
                    :value="reverseLogOrder(monitoringData[item.computerId].logs.backendDockerUtil)"
                    readonly
                    outlined
                    rows="10"
                    placeholder="Container server daemon logs will appear here..."
                    class="logs-textarea"
                  ></v-textarea>
                </div>
              </div>
              
              <!-- No data available -->
              <v-alert 
                v-else
                type="info" 
                outlined
                class="mb-4"
              >
                <div class="d-flex align-center">
                  <v-icon class="mr-2">mdi-information-outline</v-icon>
                  <span>No monitoring data available for this server yet. The server may not have submitted any data, or monitoring might not be running on this server.</span>
                </div>
              </v-alert>
            </v-card-text>
            
            <v-card-actions>
              <v-spacer></v-spacer>
              <v-btn variant="text" @click="toggleExpand(item)">Close</v-btn>
            </v-card-actions>
          </v-card>
        </td>
      </template>
    </v-data-table>
  </div>
</template>

<script>
  /**
   * Displays a sortable data table of all container servers (computers) with online/offline
   * status indicators based on monitoring heartbeat data. Each row is expandable to show
   * detailed server monitoring: CPU, memory, disk usage, Docker container counts, system
   * load, uptime, software version, and PM2 application logs.
   * Actions menu allows editing the computer, viewing monitoring, or removing the computer.
   * Used in PageAdminComputers.
   */
  import { DisplayTime, RelativeTime } from '/src/helpers/time.js'
  import { useMainStore } from '@/store/store'

  export default {
    name: 'AdminComputersTable',
    setup() {
      const store = useMainStore()
      return { store }
    },
    props: {
      propItems: {
        type: Array,
        required: true,
      },
      propMonitoringData: {
        type: Object,
        default: () => ({})
      },
      propActiveServers: {
        type: Object,
        default: () => ({})
      },
      propLastUpdateTime: {
        type: Object,
        default: () => ({})
      }
    },
    data: () => ({
      data: [],
      readAll: false,
      hasLongItems: false,
      expanded: [],
      monitoringData: {},
      loadingMonitoring: {},
      lastUpdateTime: {},
      table: {
        headers: [
          { title: 'Computer ID', key: 'computerId' },
          { title: 'Status', key: 'status', align: 'center' },
          { title: 'Public', key: 'public' },
          { title: 'Name', key: 'name' },
          { title: 'IP', key: 'ip' },
          { title: 'Created', key: 'createdAt' },
          { title: 'Updated', key: 'updatedAt' },
          { title: '', key: 'actions', sortable: false },
        ],
      }
    }),
    mounted () {
      this.data = this.propItems
      this.monitoringData = this.propMonitoringData
      this.lastUpdateTime = this.propLastUpdateTime || {}
    },
    methods: {
      emitEditComputer(computerId) {
        this.$emit('emitEditComputer', computerId)
      },
      emitRemoveComputer(computerId) {
        this.$emit('emitRemoveComputer', computerId)
      },
      toggleReadAll() {
        this.readAll = !this.readAll;
      },
      getText(text) {
        if (this.readAll) return text;
        else {
          if (!this.hasLongItems) this.hasLongItems = true;
          return text.slice(0,10) + "...";
        }
      },
      parseTime(timestamp) {
        return DisplayTime(timestamp)
      },
      parseRelativeTime(timestamp) {
        if (!timestamp) return '-'
        return RelativeTime(timestamp)
      },
      /** Toggles the expanded monitoring panel for a computer row (single-expand mode). */
      toggleExpand(item) {
        const index = this.expanded.indexOf(item.computerId);
        if (index >= 0) {
          this.expanded.splice(index, 1);
        } else {
          this.expanded = [item.computerId]; // Single expand mode
          this.fetchMonitoringData(item.computerId);
        }
      },
      isExpanded(item) {
        return this.expanded.includes(item.computerId);
      },
      fetchMonitoringData(computerId) {
        this.$emit('emitFetchMonitoring', computerId);
      },
      /** Returns 'green' if the server reported a heartbeat within the threshold, 'grey' otherwise. */
      getStatusColor(item) {
        return this.propActiveServers[item.computerId] ? 'green' : 'grey';
      },
      getStatusText(item) {
        return this.propActiveServers[item.computerId] ? 'Online' : 'Offline';
      },
      // Color helpers for metrics
      getCpuColor(usage) {
        if (usage === null || usage === undefined) return 'grey';
        if (usage < 50) return 'green';
        if (usage < 80) return 'orange';
        return 'red';
      },
      getMemoryColor(percentage) {
        if (percentage === null || percentage === undefined) return 'grey';
        if (percentage < 70) return 'green';
        if (percentage < 90) return 'orange';
        return 'red';
      },
      getDiskColor(percentage) {
        if (percentage === null || percentage === undefined) return 'grey';
        if (percentage < 80) return 'green';
        if (percentage < 95) return 'orange';
        return 'red';
      },
      // Format bytes to human readable
      formatBytes(bytes) {
        if (bytes === null || bytes === undefined) return '0 B';
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
      },
      /** Reverses log line order so the most recent entries appear at the top. */
      reverseLogOrder(logContent) {
        if (!logContent || logContent.trim() === '') return logContent;
        
        // Split by lines, reverse, and rejoin
        return logContent
          .split('\n')
          .reverse()
          .join('\n');
      },
      formatTimestamp(date) {
        // Convert date to ISO string and use DisplayTime for consistent timezone handling
        const isoString = date.toISOString().replace('Z', ''); // Remove Z so DisplayTime can add it
        return DisplayTime(isoString);
      },
      formatDirectTimestamp(timestamp) {
        // The timestamp is in UTC milliseconds
        // Convert to ISO string and pass to DisplayTime
        const date = new Date(timestamp);
        // Create ISO string without timezone suffix so DisplayTime can add Z
        const isoString = date.toISOString().replace('Z', '');
        return DisplayTime(isoString);
      },
      /** Converts a UTC millisecond timestamp into a human-readable relative time string (e.g. "5m ago"). */
      formatLastUpdate(timestamp) {
        if (!timestamp) return 'No data';
        const now = Date.now();
        const diff = now - timestamp;
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);
        
        if (seconds < 60) return `${seconds}s ago`;
        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;
        return `${days}d ago`;
      }
    },
    watch: {
      propItems: {
        handler(newVal) {
          this.data = newVal
        },
        immediate: true,
      },
      propMonitoringData: {
        handler(newVal) {
          this.monitoringData = newVal;
        },
        deep: true
      },
      propLastUpdateTime: {
        handler(newVal) {
          this.lastUpdateTime = newVal;
        },
        deep: true
      }
    },
  }
</script>

<style scoped lang="scss">
  .destructive-action .v-list-item-title,
  .destructive-action .v-icon {
    color: #ef5350;
  }

  .read-all-toggle {
    margin-bottom: 20px;
    font-size: 14px;
    display: inline-block;
    padding-left: 15px;
    width: auto;
  }

  // Logs textarea styling
  .logs-textarea {
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace !important;
    font-size: 12px !important;
    line-height: 1.4 !important;
  }

  :deep(.logs-textarea textarea) {
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace !important;
    font-size: 12px !important;
    line-height: 1.4 !important;
    color: rgba(255, 255, 255, 0.87) !important;
    background-color: #1e1e1e !important;
  }

  :deep(.logs-textarea .v-text-field__details) {
    display: none !important;
  }

  // Status chip styling
  .v-chip {
    &.v-chip--small {
      height: 24px !important;
      font-size: 11px !important;
    }
  }

  // Expanded content styling
  .headline {
    font-size: 20px !important;
    font-weight: 500 !important;
  }

  .font-weight-medium {
    font-weight: 500 !important;
  }

  .text-h6 {
    font-weight: 600 !important;
    color: rgba(255, 255, 255, 0.87) !important;
  }

  .body-2 {
    line-height: 1.5 !important;
  }

  .caption {
    font-size: 12px !important;
  }
</style>