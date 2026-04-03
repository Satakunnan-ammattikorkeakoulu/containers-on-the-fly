<template>
  <v-container>
    <v-row class="text-center">
      <v-col cols="12">
        <h4 class="m-0">Admin</h4>
        <h2 class="m-0">Usage Analytics</h2>
        <p class="analytics-description">
          Analytics are based on the audit log, which retains data for
          <strong>{{ retentionDays > 0 ? 'the last ' + retentionDays + ' days' : 'an unlimited period' }}</strong>.
        </p>
      </v-col>
    </v-row>

    <!-- Date range filters -->
    <v-row class="justify-center">
      <v-col cols="12" md="3">
        <v-text-field
          v-model="dateFrom"
          label="Date From (start of day)"
          type="date"
          :max="dateTo || undefined"
          @update:model-value="onFilterChange"
        ></v-text-field>
      </v-col>
      <v-col cols="12" md="3">
        <v-text-field
          v-model="dateTo"
          label="Date To (end of day)"
          type="date"
          :min="dateFrom || undefined"
          @update:model-value="onFilterChange"
        ></v-text-field>
      </v-col>
    </v-row>
    <v-row class="justify-center" style="margin-top: -8px; margin-bottom: 20px;">
      <v-col cols="12" md="6" class="text-center">
        <span class="date-range-info" v-html="dateRangeText"></span>
        <v-menu v-if="dateRangeText" location="bottom center" :close-on-content-click="true">
          <template v-slot:activator="{ props }">
            <span class="refresh-link" v-bind="props">Quick Filters</span>
          </template>
          <v-list density="compact">
            <v-list-item v-for="preset in quickPresets" :key="preset.label" @click="applyPreset(preset.days)">
              <v-list-item-title>{{ preset.label }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
        <span v-if="dateRangeText" class="refresh-link" @click="fetch">Refresh Data</span>
      </v-col>
    </v-row>

    <!-- Loading -->
    <Loading v-if="loading" />

    <!-- Charts -->
    <template v-if="!loading && analyticsData">
      <!-- Row 1: Platform Activity (full width) -->
      <v-row class="mt-4">
        <v-col cols="12">
          <v-card variant="outlined">
            <v-card-title class="chart-title">Platform Activity</v-card-title>
            <p class="chart-description">Daily reservation and login activity over time.</p>
            <v-card-text>
              <AnalyticsLineChart :data="analyticsData.dailyActivity" />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Row 2: Reservation Statuses + Actions by Type -->
      <v-row>
        <v-col cols="12" md="5">
          <v-card variant="outlined" class="fill-height">
            <v-card-title class="chart-title">Reservation Statuses</v-card-title>
            <p class="chart-description">Breakdown of reservations by their current status.</p>
            <v-card-text>
              <AnalyticsDoughnutChart :data="analyticsData.reservationStatuses" />
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="7">
          <v-card variant="outlined" class="fill-height">
            <v-card-title class="chart-title">Actions by Type</v-card-title>
            <p class="chart-description">All audit log action types ranked by frequency.</p>
            <v-card-text>
              <AnalyticsBarChart
                :data="analyticsData.actionCounts"
                labelKey="action"
                valueKey="count"
              />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Row 3: Top Users + Reservations by Server -->
      <v-row>
        <v-col cols="12" md="6">
          <v-card variant="outlined" class="fill-height">
            <v-card-title class="chart-title">Top Users</v-card-title>
            <p class="chart-description">Most active users by number of audit log events.</p>
            <v-card-text>
              <AnalyticsBarChart
                :data="analyticsData.topUsers"
                labelKey="email"
                valueKey="count"
                color="#66BB6A"
              />
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="6">
          <v-card variant="outlined" class="fill-height">
            <v-card-title class="chart-title">Reservations by Server</v-card-title>
            <p class="chart-description">Number of reservations per container server.</p>
            <v-card-text>
              <AnalyticsBarChart
                :data="analyticsData.reservationsByComputer"
                labelKey="computerName"
                valueKey="count"
                color="#FFA726"
              />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </template>
  </v-container>
</template>

<script>
  /**
   * Admin analytics dashboard showing usage charts derived from audit log
   * and reservation data. Displays platform activity trends, reservation
   * status breakdown, action type distribution, top users, and per-server
   * reservation counts.
   */
  import axios from 'axios'
  import { useMainStore } from '@/store/store'
  import Loading from '/src/components/global/Loading.vue'
  import AnalyticsLineChart from '/src/components/admin/AnalyticsLineChart.vue'
  import AnalyticsDoughnutChart from '/src/components/admin/AnalyticsDoughnutChart.vue'
  import AnalyticsBarChart from '/src/components/admin/AnalyticsBarChart.vue'

  export default {
    name: 'PageAdminAnalytics',
    components: {
      Loading,
      AnalyticsLineChart,
      AnalyticsDoughnutChart,
      AnalyticsBarChart,
    },
    setup() {
      const store = useMainStore()
      return { store }
    },
    data() {
      const today = new Date()
      const weekAgo = new Date(today)
      weekAgo.setDate(weekAgo.getDate() - 7)
      return {
        loading: true,
        dateFrom: weekAgo.toISOString().split('T')[0],
        dateTo: today.toISOString().split('T')[0],
        analyticsData: null,
        retentionDays: null,
        quickPresets: [
          { label: 'Today', days: 0 },
          { label: 'Yesterday', days: 1 },
          { label: 'Last 3 days', days: 3 },
          { label: 'Last 5 days', days: 5 },
          { label: 'Last week', days: 7 },
          { label: 'Last 2 weeks', days: 14 },
          { label: 'Last month', days: 30 },
          { label: 'Last year', days: 365 },
        ],
      }
    },
    computed: {
      /** Text showing how many days the current date range covers. */
      dateRangeText() {
        if (!this.dateFrom || !this.dateTo) return ''
        const from = new Date(this.dateFrom)
        const to = new Date(this.dateTo)
        const diffMs = to - from
        if (diffMs < 0) return ''
        const days = Math.round(diffMs / (1000 * 60 * 60 * 24)) + 1
        const fromStr = `${from.getDate()}.${from.getMonth() + 1}.${from.getFullYear()}`
        const toStr = `${to.getDate()}.${to.getMonth() + 1}.${to.getFullYear()}`
        return `Viewing data for <b>${days} days</b> between <b>${fromStr}</b> - <b>${toStr}</b>`
      },
    },
    mounted() {
      this.fetch()
    },
    methods: {
      /** Re-fetch when a date filter changes. */
      onFilterChange() {
        if (this.dateFrom && this.dateTo && this.dateFrom > this.dateTo) return
        this.fetch()
      },
      /** Apply a quick filter preset by setting dateFrom and dateTo. */
      applyPreset(days) {
        const today = new Date()
        const from = new Date(today)
        if (days === 1) {
          // Yesterday only
          from.setDate(from.getDate() - 1)
          this.dateFrom = from.toISOString().split('T')[0]
          this.dateTo = from.toISOString().split('T')[0]
        } else {
          from.setDate(from.getDate() - days)
          this.dateFrom = from.toISOString().split('T')[0]
          this.dateTo = today.toISOString().split('T')[0]
        }
        this.fetch()
      },
      /** Fetch analytics data from the backend. */
      fetch() {
        let _this = this
        _this.loading = true

        axios({
          method: "post",
          url: this.$appSettings.APIServer.admin.get_analytics,
          data: {
            dateFrom: _this.dateFrom || '',
            dateTo: _this.dateTo || '',
          },
          headers: { "Authorization": `Bearer ${_this.store.user.loginToken}` },
        })
        .then(function (response) {
          if (response.data.status === true) {
            _this.analyticsData = response.data.data
            _this.retentionDays = response.data.data.retentionDays
          } else {
            _this.store.showMessage({ text: response.data.message || "Failed to fetch analytics.", color: "red" })
          }
          _this.loading = false
        })
        .catch(function (error) {
          console.error("Analytics fetch error:", error)
          _this.store.showMessage({ text: "Failed to fetch analytics data.", color: "red" })
          _this.loading = false
        })
      },
    },
  }
</script>

<style scoped>
.chart-title {
  font-size: 16px;
  padding-top: 20px;
  padding-bottom: 0;
}

.chart-description {
  font-size: 14px;
  opacity: 0.5;
  margin: 2px 16px 0 16px;
}

.date-range-info {
  font-size: 14px;
  opacity: 0.5;
}

.refresh-link {
  font-size: 14px;
  margin-left: 8px;
  cursor: pointer;
  color: #42A5F5;
  text-decoration: none;
}

.refresh-link:hover {
  text-decoration: underline;
}

.analytics-description {
  font-size: 14px;
  opacity: 0.6;
  margin-top: 6px;
  margin-bottom: 0;
}
</style>
