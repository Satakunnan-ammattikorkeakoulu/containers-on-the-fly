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
        <br v-if="item.roleId <= 1">
        <span v-if="item.roleId <= 1" class="role-description">
          {{ getRoleDescription(item.roleId) }}
        </span>
      </template>

      <!-- Actions -->
      <template v-slot:item.actions="{item}">
        <!-- Regular role management actions -->
        <template v-if="item.roleId > 1">
          <a class="link-action" @click="emitEditRole(item.roleId)">Edit Role</a>
          <a class="link-action" @click="emitRemoveRole(item.roleId)">Remove Role</a>
        </template>
        <!-- Mounts action available for all roles -->
        <a class="link-action" @click="emitManageMounts(item)">Mounts</a>
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
  watch: {
    propItems: {
      handler(newVal) {
        this.data = newVal;
      },
      immediate: true,
    },
  },
  methods: {
    getRoleDescription(roleId) {
      if (roleId === 0) {
        return "Built-in role for all users in the system. Everyone belongs to this role automatically.";
      } else if (roleId === 1) {
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