<template>
  <div>
    <a v-if="hasLongItems" class="link-toggle-read-all" @click="toggleReadAll">{{ !readAll ? "Expand Issues" : "Collapse Issues" }}</a>
    <v-data-table
      :headers="table.headers"
      :items="data"
      :sort-by="'containerId'"
      :sort-desc="true"
      class="elevation-1">

      <!-- Public status with colored labels -->
      <template v-slot:item.public="{item}">
        <v-chip
          :color="item.public ? 'green' : 'orange'"
          text-color="white"
          small
        >
          {{ item.public ? 'Public' : 'Private' }}
        </v-chip>
      </template>

      <!-- Actions -->
      <template v-slot:item.actions="{item}">
        <a class="link-action" @click="emitEditContainer(item.containerId)">Edit Container</a>
        <a class="link-action" @click="emitRemoveContainer(item.containerId)">Remove Container</a>
      </template>
    </v-data-table>
  </div>
</template>

<script>
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
          { text: 'Container ID', value: 'containerId' },
          { text: 'Public', value: 'public' },
          { text: 'name', value: 'name' },
          { text: 'Image name', value: 'imageName' },
          { text: 'Description', value: 'description' },
          { text: 'Created At', value: 'createdAt' },
          { text: 'Updated At', value: 'updatedAt' },
          { text: 'Actions', value: 'actions' },
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
  .link-action {
    display: block;
    min-width: 150px;
    margin: 10px 0px;
  }

  .link-toggle-read-all {
    margin-bottom: 20px;
    font-size: 14px;
    display: inline-block;
    padding-left: 15px;
    width: auto;
  }
</style>