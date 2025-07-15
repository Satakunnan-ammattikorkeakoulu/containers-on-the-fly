<template>
  <div>
    <v-data-table
      :headers="table.headers"
      :items="data"
      :sort-by="'roleId'"
      :sort-desc="false"
      class="elevation-1">

      <!-- Actions -->
      <template v-slot:item.actions="{item}">
        <template v-if="item.roleId > 1">  <!-- Only show actions for non-built-in roles -->
          <a class="link-action" @click="emitEditRole(item.roleId)">Edit Role</a>
          <a class="link-action" @click="emitRemoveRole(item.roleId)">Remove Role</a>
        </template>
        <span v-else class="built-in-role">Built-in Role</span>
      </template>

      <!-- Format the timestamps -->
      <template v-slot:item.createdAt="{item}">
        {{ parseTime(item.createdAt) }}
      </template>
    </v-data-table>
  </div>
</template>

<script>
import { DisplayTime } from '/src/helpers/time.js'

export default {
  name: 'AdminRolesTable',
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
        { text: 'Role ID', value: 'roleId', sortable: true },
        { text: 'Name', value: 'name', sortable: true },
        { text: 'Created At', value: 'createdAt', sortable: true },
        { text: 'Actions', value: 'actions', sortable: false },
      ],
    }
  }),
  mounted () {
    this.data = this.propItems;
  },
  methods: {
    emitEditRole(roleId) {
      this.$emit('emitEditRole', roleId);
    },
    emitRemoveRole(roleId) {
      this.$emit('emitRemoveRole', roleId);
    },
    parseTime(timestamp) {
      return DisplayTime(timestamp);
    },
  },
}
</script>

<style scoped lang="scss">
.link-action {
  margin-right: 10px;
  cursor: pointer;
  color: #1976d2;
  &:hover {
    text-decoration: underline;
  }
}
.built-in-role {
  color: #666;
  font-style: italic;
}
</style> 