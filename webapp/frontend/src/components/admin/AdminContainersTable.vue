<template>
  <div>
    <a v-if="hasLongItems" class="link-toggle-read-all" @click="toggleReadAll">{{ !readAll ? "Expand Issues" : "Collapse Issues" }}</a>
    <v-data-table
      :headers="table.headers"
      :items="data"
      :sort-by="[{key: 'containerId', order: 'desc'}]"
      class="elevation-1">

      <!-- Public status with colored labels -->
      <template v-slot:item.public="{item}">
        <v-chip
          :color="item.public ? 'green' : 'orange'"
          text-color="white"
          size="small"
        >
          {{ item.public ? 'Public' : 'Private' }}
        </v-chip>
      </template>

      <!-- Created At -->
      <template v-slot:item.createdAt="{item}">
        {{ item.createdAt ? parseTime(item.createdAt) : '' }}
      </template>

      <!-- Updated At -->
      <template v-slot:item.updatedAt="{item}">
        {{ item.updatedAt ? parseTime(item.updatedAt) : '' }}
      </template>

      <!-- Actions -->
      <template v-slot:item.actions="{item}">
        <v-menu>
          <template v-slot:activator="{ props }">
            <a class="actions-link" v-bind="props">
              Actions <v-icon size="small">mdi-chevron-down</v-icon>
            </a>
          </template>
          <v-list density="compact">
            <v-list-item @click="emitEditContainer(item.containerId)">
              <template v-slot:prepend><v-icon size="small">mdi-pencil-outline</v-icon></template>
              <v-list-item-title>Edit Container</v-list-item-title>
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
   * Displays a sortable data table of all container images (Docker image definitions).
   * Shows container ID, public/private visibility, name, image name, description,
   * and timestamps. Actions menu allows editing or removing a container image.
   * Used in PageAdminContainers.
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
      readAll: false,
      hasLongItems: false,
      table: {
        headers: [
          { title: 'Container ID', key: 'containerId' },
          { title: 'Public', key: 'public' },
          { title: 'name', key: 'name' },
          { title: 'Image name', key: 'imageName' },
          { title: 'Description', key: 'description' },
          { title: 'Created At', key: 'createdAt' },
          { title: 'Updated At', key: 'updatedAt' },
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
  .actions-link {
    color: #2196f3;
    cursor: pointer;
    text-decoration: none;
    white-space: nowrap;
    &:hover {
      text-decoration: underline;
    }
  }

  .destructive-action .v-list-item-title,
  .destructive-action .v-icon {
    color: #ef5350;
  }

  .link-toggle-read-all {
    margin-bottom: 20px;
    font-size: 14px;
    display: inline-block;
    padding-left: 15px;
    width: auto;
  }
</style>