<template>
  <div :style="{ height: chartHeight + 'px' }">
    <Bar v-if="chartData" :data="chartData" :options="chartOptions" />
    <p v-else class="text-center text-grey">No data available.</p>
  </div>
</template>

<script>
  /**
   * Horizontal bar chart for displaying ranked data (action counts, top users, etc.).
   * Wraps vue-chartjs Bar component with dark-theme styling.
   */
  import { Bar } from 'vue-chartjs'
  import {
    Chart,
    CategoryScale,
    LinearScale,
    BarElement,
    Tooltip,
    Legend,
  } from 'chart.js'

  Chart.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend)

  export default {
    name: 'AnalyticsBarChart',
    components: { Bar },
    props: {
      /** Array of data objects to chart. */
      data: {
        type: Array,
        required: true,
      },
      /** Key in each data object to use as the bar label. */
      labelKey: {
        type: String,
        required: true,
      },
      /** Key in each data object to use as the bar value. */
      valueKey: {
        type: String,
        required: true,
      },
      /** Bar color. */
      color: {
        type: String,
        default: '#42A5F5',
      },
    },
    computed: {
      /** Scale chart height based on number of bars, with a minimum. */
      chartHeight() {
        const barCount = this.data ? this.data.length : 0
        return Math.max(200, barCount * 30 + 60)
      },
      chartData() {
        if (!this.data || this.data.length === 0) return null
        return {
          labels: this.data.map(d => d[this.labelKey]),
          datasets: [{
            data: this.data.map(d => d[this.valueKey]),
            backgroundColor: this.color,
            borderRadius: 3,
          }],
        }
      },
      chartOptions() {
        return {
          responsive: true,
          maintainAspectRatio: false,
          indexAxis: 'y',
          scales: {
            x: {
              beginAtZero: true,
              ticks: { color: 'rgba(255,255,255,0.7)', precision: 0 },
              grid: { color: 'rgba(255,255,255,0.08)' },
            },
            y: {
              ticks: { color: 'rgba(255,255,255,0.7)' },
              grid: { display: false },
            },
          },
          plugins: {
            legend: { display: false },
          },
        }
      },
    },
  }
</script>
