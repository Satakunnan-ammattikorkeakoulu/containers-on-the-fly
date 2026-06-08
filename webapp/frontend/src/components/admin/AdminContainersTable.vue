<template>
  <div>
    <v-data-table
      :headers="table.headers"
      :items="data"
      :sort-by="[{key: 'containerId', order: 'desc'}]"
      class="elevation-1">

      <!-- Name with tooltip showing details -->
      <template v-slot:item.name="{item}">
        <v-tooltip bottom>
          <template v-slot:activator="{ props }">
            <span v-bind="props">
              <v-chip
                :color="item.public ? 'green' : 'orange'"
                text-color="white"
                size="x-small"
                class="mr-2"
              >
                {{ item.public ? 'Public' : 'Private' }}
              </v-chip><span class="link-hint">{{ item.name }}</span>
            </span>
          </template>
          <div style="max-width: 350px;">
            <div><strong>ID:</strong> {{ item.containerId }}</div>
            <div><strong>Image:</strong> {{ item.imageName }}</div>
            <div><strong>Username:</strong> {{ item.containerUsername || 'user' }}</div>
            <div v-if="item.imageSize"><strong>Size:</strong> {{ formatSize(item.imageSize) }}</div>
            <div v-if="item.lastBuiltAt"><strong>Last Built:</strong> {{ parseTime(item.lastBuiltAt) }}</div>
            <div><strong>Created:</strong> {{ item.createdAt ? parseTime(item.createdAt) : '—' }}</div>
            <div v-if="item.updatedAt"><strong>Updated:</strong> {{ parseTime(item.updatedAt) }}</div>
            <div v-if="item.description" class="mt-1"><strong>Description:</strong> {{ item.description }}</div>
          </div>
        </v-tooltip>
      </template>

      <!-- Image name -->
      <template v-slot:item.imageName="{item}">
        <span style="font-family: monospace; font-size: 12px;">{{ item.imageName }}</span>
      </template>

      <!-- Status -->
      <template v-slot:item.buildStatus="{item}">
        <div>
          <v-chip
            v-if="!item.dockerfileCommands"
            color="grey"
            text-color="white"
            size="small"
          >
            Externally Managed
          </v-chip>
          <v-chip
            v-else-if="item.buildStatus === 'success'"
            color="green"
            text-color="white"
            size="small"
          >
            Build Success
          </v-chip>
          <v-chip
            v-else-if="item.buildStatus === 'building'"
            color="orange"
            text-color="white"
            size="small"
          >
            <v-progress-circular indeterminate size="12" width="2" class="mr-1"></v-progress-circular>
            Building...
          </v-chip>
          <v-chip
            v-else-if="item.buildStatus === 'pending'"
            color="yellow"
            size="small"
          >
            Build Queued
          </v-chip>
          <v-chip
            v-else-if="item.buildStatus === 'failed'"
            color="red"
            text-color="white"
            size="small"
          >
            Build Failed
          </v-chip>
          <v-chip
            v-else
            color="grey"
            text-color="white"
            size="small"
          >
            Not Built
          </v-chip>
        </div>
      </template>

      <!-- Size -->
      <template v-slot:item.imageSize="{item}">
        <span v-if="item.imageSize" style="white-space: nowrap;">{{ formatSize(item.imageSize) }}</span>
        <span v-else class="text-muted">-</span>
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
            <v-list-item @click="emitEditContainer(item.containerId)">
              <template v-slot:prepend><v-icon size="small">mdi-pencil-outline</v-icon></template>
              <v-list-item-title>Edit Container</v-list-item-title>
            </v-list-item>
            <v-list-item v-if="item.dockerfileCommands" @click="emitRebuildContainer(item.containerId)">
              <template v-slot:prepend><v-icon size="small">mdi-hammer-wrench</v-icon></template>
              <v-list-item-title>Rebuild Image</v-list-item-title>
            </v-list-item>
            <v-list-item v-if="item.dockerfileCommands" @click="emitViewBuildLog(item.containerId)">
              <template v-slot:prepend><v-icon size="small">mdi-text-box-outline</v-icon></template>
              <v-list-item-title>View Build Log</v-list-item-title>
            </v-list-item>
            <v-divider class="my-1" />
            <v-list-item @click="emitRemoveContainer(item.containerId)" class="destructive-action">
              <template v-slot:prepend><v-icon size="small">mdi-delete-outline</v-icon></template>
              <v-list-item-title>Remove Container</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </template>
    </v-data-table>
  </div>
</template>

<script>
  /**
   * Displays a sortable data table of all container images.
   * Shows name (with tooltip for details), image name, build status with size,
   * and actions. Hover over the name to see ID, username, description, dates, etc.
   */
  import { DisplayTime } from '/src/helpers/time.js'

  export default {
    name: 'AdminContainersTable',
    props: {
      propItems: {
        type: Array,
        required: true,
      }
    },
    data: () => ({
      data: [],
      table: {
        headers: [
          { title: 'Name', key: 'name' },
          { title: 'Image', key: 'imageName' },
          { title: 'Status', key: 'buildStatus', sortable: false },
          { title: 'Size', key: 'imageSize', sortable: true },
          { title: '', key: 'actions', sortable: false },
        ],
      }
    }),
    mounted () {
      this.data = this.propItems
    },
    methods: {
      emitEditContainer(containerId) {
        this.$emit('emitEditContainer', containerId)
      },
      emitRemoveContainer(containerId) {
        this.$emit('emitRemoveContainer', containerId)
      },
      emitRebuildContainer(containerId) {
        this.$emit('emitRebuildContainer', containerId)
      },
      emitViewBuildLog(containerId) {
        this.$emit('emitViewBuildLog', containerId)
      },
      parseTime(timestamp) {
        return DisplayTime(timestamp)
      },
      /** Format byte size to human-readable string. */
      formatSize(bytes) {
        if (!bytes) return '—';
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        let size = bytes;
        let unitIndex = 0;
        while (size >= 1024 && unitIndex < units.length - 1) {
          size /= 1024;
          unitIndex++;
        }
        return `${size.toFixed(1)} ${units[unitIndex]}`;
      },
    },
    watch: {
      propItems: {
        handler(newVal) {
          this.data = newVal
        },
        immediate: true,
      },
    },
  }
</script>

<style scoped lang="scss">
  .destructive-action .v-list-item-title,
  .destructive-action .v-icon {
    color: #ef5350;
  }
</style>
