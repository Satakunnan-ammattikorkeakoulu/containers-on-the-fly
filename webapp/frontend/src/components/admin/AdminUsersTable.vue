<template>
  <div>
    <a v-if="hasLongItems" class="link-toggle-read-all" @click="toggleReadAll">{{ !readAll ? "Read all" : "Read less" }}</a>
    <v-data-table
      :headers="table.headers"
      :items="data"
      :sort-by="'userId'"
      :sort-desc="true"
      class="elevation-1">
      
      <!-- Actions -->
      <template v-slot:item.actions="{item}">
        <a class="link-action" @click="emitEditUser(item.userId)">Edit User</a>
      </template>

      <!-- Created At -->
      <template v-slot:item.createdAt="{item}">
        {{ item.createdAt ? parseTime(item.createdAt) : '-' }}
      </template>

      <!-- Roles -->
      <template v-slot:item.roles="{item}">
        {{ Array.isArray(item.roles) ? item.roles.join(', ') : item.roles }}
      </template>
      
      <!-- Password Set -->
      <template v-slot:item.hasPassword="{item}">
        <v-icon v-if="item.hasPassword" color="green">mdi-check</v-icon>
        <v-icon v-else color="red">mdi-close</v-icon>
      </template>
    </v-data-table>
  </div>
</template>

<script>
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
        { text: 'User ID', value: 'userId' },
        { text: 'Email', value: 'email' },
        { text: 'Roles', value: 'roles' },
        { text: 'Password Set', value: 'hasPassword' },
        { text: 'Created At', value: 'createdAt' },
        { text: 'Actions', value: 'actions' },
      ],
    }
  }),
  mounted () {
    this.data = this.propItems
  },
  methods: {
    emitEditUser(userId) {
      this.$emit('emitEditUser', userId)
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
      if (!timestamp) return '-';
      return DisplayTime(timestamp);
    },
  },
  watch: {
    propItems: {
      handler(newVal) {
        this.data = newVal
      },
      immediate: true,
    },
  }
}
</script>

<style scoped lang="scss">
.link-action {
  margin-right: 10px;
  cursor: pointer;
  color: #1976D2;
  text-decoration: none;
}
</style>