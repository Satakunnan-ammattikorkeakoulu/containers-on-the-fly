<template>
  <div>
    <a v-if="hasLongItems" class="read-all-toggle" @click="toggleReadAll">{{ !readAll ? "Read all" : "Read less" }}</a>
    <v-data-table
      :headers="table.headers"
      :items="data"
      :sort-by="[{key: 'hardwareSpecId', order: 'desc'}]"
      class="elevation-1">
    </v-data-table>
  </div>
</template>

<script>
  /**
   * Displays a read-only data table of hardware specifications across all computers.
   * Shows CPU, RAM, and GPU details including min/max amounts and user-facing defaults.
   * Used in the admin computers page to inspect hardware configuration per computer.
   */
  import { DisplayTime } from '/src/helpers/time.js'

  export default {
    name: 'AdminUsersTable',
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
          { title: 'Hardware ID', key: 'hardwareSpecId' },
          { title: 'Computer ID', key: 'computerId' },
          { title: 'Type', key: 'type' },
          { title: 'Format', key: 'format' },
          { title: 'GPU ID (Internal ID)', key: 'internalId' },
          { title: 'Max', key: 'maximumAmount' },
          { title: 'Min', key: 'minimumAmount' },
          { title: 'Max for Users', key: 'maximumAmountForUser' },
          { title: 'Default for Users', key: 'defaultAmountForUser' },
        ],
      }
    }),
    mounted () {
      this.data = this.propItems
    },
    methods: {
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
  .read-all-toggle {
    margin-bottom: 20px;
    font-size: 14px;
    display: inline-block;
    padding-left: 15px;
    width: auto;
  }
</style>