<template>
  <div style="height: 280px;">
    <Doughnut v-if="chartData" :data="chartData" :options="chartOptions" />
    <p v-else class="text-center text-grey">No reservation data available.</p>
  </div>
</template>

<script>
  /**
   * Doughnut chart showing reservation status breakdown.
   * Wraps vue-chartjs Doughnut component with dark-theme styling.
   */
  import { Doughnut } from 'vue-chartjs'
  import {
    Chart,
    ArcElement,
    Tooltip,
    Legend,
  } from 'chart.js'

  Chart.register(ArcElement, Tooltip, Legend)

  const STATUS_COLORS = {
    reserved: '#42A5F5',
    started: '#66BB6A',
    stopping: '#FFA726',
    stopped: '#BDBDBD',
    error: '#EF5350',
    restart_error: '#FF7043',
    paused: '#FFA726',
  }

  export default {
    name: 'AnalyticsDoughnutChart',
    components: { Doughnut },
    props: {
      /** Object mapping status names to counts, e.g. {started: 25, stopped: 10}. */
      data: {
        type: Object,
        required: true,
      },
    },
    computed: {
      chartData() {
        const entries = Object.entries(this.data || {})
        if (entries.length === 0) return null
        return {
          labels: entries.map(([status]) => status),
          datasets: [{
            data: entries.map(([, count]) => count),
            backgroundColor: entries.map(([status]) => STATUS_COLORS[status] || '#9E9E9E'),
            borderColor: '#1e1e1e',
            borderWidth: 2,
          }],
        }
      },
      chartOptions() {
        return {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'right',
              labels: { color: 'rgba(255,255,255,0.85)', padding: 16 },
            },
          },
        }
      },
    },
  }
</script>
