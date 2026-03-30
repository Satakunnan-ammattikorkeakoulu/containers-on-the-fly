<template>
  <div>
    <v-data-table
      :headers="table.headers"
      :items="data"
      :sort-by="[{key: 'roleId', order: 'asc'}]"
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
        <v-menu>
          <template v-slot:activator="{ props }">
            <a class="actions-link" v-bind="props">
              Actions <v-icon size="small">mdi-chevron-down</v-icon>
            </a>
          </template>
          <v-list density="compact">
            <v-list-item v-if="!isBuiltInRole(item.name)" @click="emitEditRole(item.roleId)">
              <v-list-item-title>Edit Name</v-list-item-title>
            </v-list-item>
            <v-list-item @click="emitManageMounts(item)">
              <v-list-item-title>Mounts</v-list-item-title>
            </v-list-item>
            <v-list-item @click="emitManageReservationLimits(item)">
              <v-list-item-title>Reservation Limits</v-list-item-title>
            </v-list-item>
            <v-list-item v-if="!isBuiltInRole(item.name)" @click="emitManageHardwareLimits(item)">
              <v-list-item-title>Hardware Limits</v-list-item-title>
            </v-list-item>
            <v-list-item v-if="!isBuiltInRole(item.name)" @click="emitRemoveRole(item.roleId)">
              <v-list-item-title>Remove Role</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
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
        { title: 'Role ID', key: 'roleId', sortable: true },
        { title: 'Name', key: 'name', sortable: true },
        { title: 'Mounts', key: 'mountCount', sortable: true },
        { title: 'Created At', key: 'createdAt', sortable: true },
        { title: '', key: 'actions', sortable: false },
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
    },
    emitManageHardwareLimits(role) {
      this.$emit('emitManageHardwareLimits', role);
    },
    emitManageReservationLimits(role) {
      this.$emit('emitManageReservationLimits', role);
    }
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
.role-description {
  color: #666;
  font-style: italic;
  font-size: 0.85em;
  display: inline-block;
  margin-top: 4px;
}
</style> 