<template>
  <div>
    <v-data-table
      :headers="table.headers"
      :items="data"
      :sort-by="'roleId'"
      :sort-desc="false"
      class="elevation-1">

      <!-- Name column with description for built-in roles -->
      <template v-slot:item.name="{item}">
        {{ item.name }}
        <br v-if="isBuiltInRole(item.name)">
        <span v-if="isBuiltInRole(item.name)" class="role-description">
          {{ getRoleDescription(item.name) }}
        </span>
      </template>

      <!-- Mount count display -->
      <template v-slot:item.mountCount="{item}">
        {{ item.mountCount || 0 }}
      </template>

      <!-- Actions -->
      <template v-slot:item.actions="{item}">
        <!-- Regular role management actions -->
        <template v-if="!isBuiltInRole(item.name)">
          <a class="link-action" @click="emitEditRole(item.roleId)">Edit Role</a>
          <br>
          <a class="link-action" @click="emitRemoveRole(item.roleId)">Remove Role</a>
          <br>
        </template>
        <!-- Mounts action available for all roles -->
        <a class="link-action" @click="emitManageMounts(item)">Mounts</a>
      </template>

      <!-- Format the timestamps -->
      <template v-slot:item.createdAt="{item}">
        {{ isBuiltInRole(item.name) ? '-' : parseTime(item.createdAt) }}
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
        { text: 'Mounts', value: 'mountCount', sortable: true },
        { text: 'Created At', value: 'createdAt', sortable: true },
        { text: 'Actions', value: 'actions', sortable: false },
      ],
    }
  }),
  mounted () {
    this.data = this.propItems;
  },
  watch: {
    propItems: {
      handler(newVal) {
        this.data = newVal;
      },
      immediate: true,
    },
  },
  methods: {
    isBuiltInRole(name) {
      return name === "everyone" || name === "admin";
    },
    getRoleDescription(name) {
      if (name === "everyone") {
        return "Built-in role for all users in the system. Everyone belongs to this role automatically.";
      } else if (name === "admin") {
        return "Built-in role for system administrators.";
      }
      return "";
    },
    emitEditRole(roleId) {
      this.$emit('emitEditRole', roleId);
    },
    emitRemoveRole(roleId) {
      this.$emit('emitRemoveRole', roleId);
    },
    parseTime(timestamp) {
      return DisplayTime(timestamp);
    },
    emitManageMounts(role) {
      this.$emit('emitManageMounts', role);
    }
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
.role-description {
  color: #666;
  font-style: italic;
  font-size: 0.85em;
  display: inline-block;
  margin-top: 4px;
}
</style> 