<template>
  <div style="height: 300px;">
    <LineChart v-if="chartData" :data="chartData" :options="chartOptions" />
    <p v-else class="text-center text-grey">No activity data available.</p>
  </div>
</template>

<script>
  /**
   * Line chart showing daily platform activity (reservations vs logins).
   * Wraps vue-chartjs Line component with dark-theme styling.
   */
  import { Line as LineChart } from 'vue-chartjs'
  import {
    Chart,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Tooltip,
    Legend,
    Filler,
  } from 'chart.js'

  Chart.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler)

  export default {
    name: 'AnalyticsLineChart',
    components: { LineChart },
    props: {
      /** Array of {day, reservations, logins} objects. */
      data: {
        type: Array,
        required: true,
      },
    },
    computed: {
      chartData() {
        if (!this.data || this.data.length === 0) return null
        return {
          labels: this.data.map(d => d.day),
          datasets: [
            {
              label: 'Reservations',
              data: this.data.map(d => d.reservations),
              borderColor: '#42A5F5',
              backgroundColor: 'rgba(66, 165, 245, 0.1)',
              fill: true,
              tension: 0.3,
              pointRadius: this.data.length > 60 ? 0 : 3,
            },
            {
              label: 'Logins',
              data: this.data.map(d => d.logins),
              borderColor: '#66BB6A',
              backgroundColor: 'rgba(102, 187, 106, 0.1)',
              fill: true,
              tension: 0.3,
              pointRadius: this.data.length > 60 ? 0 : 3,
            },
          ],
        }
      },
      chartOptions() {
        return {
          responsive: true,
          maintainAspectRatio: false,
          interaction: {
            mode: 'index',
            intersect: false,
          },
          scales: {
            x: {
              ticks: { color: 'rgba(255,255,255,0.7)', maxTicksLimit: 12 },
              grid: { color: 'rgba(255,255,255,0.08)' },
            },
            y: {
              beginAtZero: true,
              ticks: {
                color: 'rgba(255,255,255,0.7)',
                precision: 0,
              },
              grid: { color: 'rgba(255,255,255,0.08)' },
            },
          },
          plugins: {
            legend: { labels: { color: 'rgba(255,255,255,0.85)' } },
            tooltip: { mode: 'index', intersect: false },
          },
        }
      },
    },
  }
</script>
