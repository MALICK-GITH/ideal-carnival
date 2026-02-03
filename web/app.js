class TwentyOneCollectorUI {
    constructor() {
        this.apiBase = 'http://localhost:3000/api/collect';
        this.collectionChart = null;
        this.optionsChart = null;
        this.isRunning = false;
        this.autoRefreshInterval = null;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initCharts();
        this.loadInitialData();
        this.startAutoRefresh();
    }

    setupEventListeners() {
        // Control buttons
        document.getElementById('startBtn').addEventListener('click', () => this.startCollector());
        document.getElementById('stopBtn').addEventListener('click', () => this.stopCollector());
        document.getElementById('collectBtn').addEventListener('click', () => this.collectOnce());
        document.getElementById('refreshBtn').addEventListener('click', () => this.refreshData());
        document.getElementById('loadDataBtn').addEventListener('click', () => this.loadRecentData());

        // Enter key on interval input
        document.getElementById('intervalInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.updateInterval();
            }
        });
    }

    initCharts() {
        // Collection evolution chart
        const ctx1 = document.getElementById('collectionChart').getContext('2d');
        this.collectionChart = new Chart(ctx1, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Données collectées',
                    data: [],
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        // Options distribution chart
        const ctx2 = document.getElementById('optionsChart').getContext('2d');
        this.optionsChart = new Chart(ctx2, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        '#007bff',
                        '#28a745',
                        '#ffc107',
                        '#dc3545',
                        '#6f42c1',
                        '#fd7e14'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    async loadInitialData() {
        try {
            await Promise.all([
                this.updateStatus(),
                this.updateStatistics(),
                this.loadRecentData()
            ]);
        } catch (error) {
            this.addLog('error', 'Erreur lors du chargement initial: ' + error.message);
        }
    }

    async updateStatus() {
        try {
            const response = await fetch(`${this.apiBase}/21/status`);
            const data = await response.json();
            
            this.isRunning = data.status.isRunning;
            const statusElement = document.getElementById('collectorStatus');
            const startBtn = document.getElementById('startBtn');
            const stopBtn = document.getElementById('stopBtn');
            
            if (this.isRunning) {
                statusElement.textContent = 'En cours';
                statusElement.className = 'badge bg-success status-running';
                startBtn.disabled = true;
                stopBtn.disabled = false;
            } else {
                statusElement.textContent = 'Arrêté';
                statusElement.className = 'badge bg-secondary';
                startBtn.disabled = false;
                stopBtn.disabled = true;
            }
        } catch (error) {
            this.addLog('error', 'Erreur lors de la mise à jour du statut: ' + error.message);
        }
    }

    async updateStatistics() {
        try {
            const response = await fetch(`${this.apiBase}/21/stats`);
            const data = await response.json();
            
            if (data.success) {
                const stats = data.statistics;
                document.getElementById('totalData').textContent = stats.totalRows || 0;
                document.getElementById('totalEvents').textContent = stats.uniqueEvents || 0;
                document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
                
                // Update options chart
                if (stats.optionTypes) {
                    this.updateOptionsChart(stats.optionTypes);
                }
            }
        } catch (error) {
            this.addLog('error', 'Erreur lors de la mise à jour des statistiques: ' + error.message);
        }
    }

    updateOptionsChart(optionTypes) {
        const labels = Object.keys(optionTypes);
        const data = Object.values(optionTypes);
        
        this.optionsChart.data.labels = labels;
        this.optionsChart.data.datasets[0].data = data;
        this.optionsChart.update();
    }

    async loadRecentData() {
        const limit = document.getElementById('limitInput').value;
        const tbody = document.getElementById('dataTableBody');
        
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center">
                    <div class="loading-spinner"></div>
                    Chargement des données...
                </td>
            </tr>
        `;

        try {
            const response = await fetch(`${this.apiBase}/21/data?limit=${limit}`);
            const data = await response.json();
            
            if (data.success && data.data.length > 0) {
                this.renderDataTable(data.data);
                this.addLog('info', `${data.data.length} entrées chargées`);
            } else {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center text-muted">
                            Aucune donnée disponible
                        </td>
                    </tr>
                `;
            }
        } catch (error) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-danger">
                        Erreur: ${error.message}
                    </td>
                </tr>
            `;
            this.addLog('error', 'Erreur lors du chargement des données: ' + error.message);
        }
    }

    renderDataTable(data) {
        const tbody = document.getElementById('dataTableBody');
        tbody.innerHTML = '';
        
        data.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><code>${row.event_id}</code></td>
                <td>${new Date(row.collected_at).toLocaleString()}</td>
                <td><span class="badge bg-primary">${row.option_type || 'N/A'}</span></td>
                <td><strong>${row.odd || 'N/A'}</strong></td>
                <td>
                    ${row.round_state ? 
                        `<span class="badge bg-success">Live</span>` : 
                        '<span class="badge bg-secondary">Inactif</span>'
                    }
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-info" onclick="ui.showEventDetails('${row.event_id}')">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    async showEventDetails(eventId) {
        try {
            const response = await fetch(`${this.apiBase}/21/event/${eventId}`);
            const data = await response.json();
            
            if (data.success) {
                const modal = new bootstrap.Modal(document.getElementById('eventModal'));
                document.getElementById('eventDetails').textContent = JSON.stringify(data.data, null, 2);
                modal.show();
            }
        } catch (error) {
            this.addLog('error', 'Erreur lors du chargement des détails: ' + error.message);
        }
    }

    async startCollector() {
        const interval = document.getElementById('intervalInput').value;
        
        try {
            const response = await fetch(`${this.apiBase}/21/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ intervalMs: parseInt(interval) })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addLog('success', `Collecteur démarré (intervalle: ${interval}ms)`);
                await this.updateStatus();
            } else {
                this.addLog('error', 'Erreur lors du démarrage: ' + data.message);
            }
        } catch (error) {
            this.addLog('error', 'Erreur lors du démarrage: ' + error.message);
        }
    }

    async stopCollector() {
        try {
            const response = await fetch(`${this.apiBase}/21/stop`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addLog('warning', 'Collecteur arrêté');
                await this.updateStatus();
            } else {
                this.addLog('error', 'Erreur lors de l\'arrêt: ' + data.message);
            }
        } catch (error) {
            this.addLog('error', 'Erreur lors de l\'arrêt: ' + error.message);
        }
    }

    async collectOnce() {
        try {
            this.addLog('info', 'Lancement d\'une collecte manuelle...');
            
            const response = await fetch(`${this.apiBase}/21`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addLog('success', `Collecte terminée: ${data.data.collected} événements`);
                await this.updateStatistics();
                await this.loadRecentData();
            } else {
                this.addLog('error', 'Erreur lors de la collecte: ' + data.message);
            }
        } catch (error) {
            this.addLog('error', 'Erreur lors de la collecte: ' + error.message);
        }
    }

    async refreshData() {
        this.addLog('info', 'Actualisation des données...');
        await Promise.all([
            this.updateStatus(),
            this.updateStatistics(),
            this.loadRecentData()
        ]);
    }

    async updateInterval() {
        if (this.isRunning) {
            await this.stopCollector();
            await new Promise(resolve => setTimeout(resolve, 1000));
            await this.startCollector();
        }
    }

    startAutoRefresh() {
        this.autoRefreshInterval = setInterval(() => {
            this.updateStatus();
            this.updateStatistics();
        }, 5000); // Refresh every 5 seconds
    }

    addLog(type, message) {
        const logsContainer = document.getElementById('logsContainer');
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type}`;
        logEntry.innerHTML = `<span class="text-muted">[${timestamp}]</span> ${message}`;
        
        logsContainer.appendChild(logEntry);
        logsContainer.scrollTop = logsContainer.scrollHeight;
        
        // Keep only last 50 logs
        while (logsContainer.children.length > 50) {
            logsContainer.removeChild(logsContainer.firstChild);
        }
    }

    updateCollectionChart(timestamp, count) {
        const chart = this.collectionChart;
        
        chart.data.labels.push(timestamp);
        chart.data.datasets[0].data.push(count);
        
        // Keep only last 20 points
        if (chart.data.labels.length > 20) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }
        
        chart.update();
    }
}

// Initialize the UI when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.ui = new TwentyOneCollectorUI();
    
    // Update connection status
    window.addEventListener('online', () => {
        document.getElementById('connectionStatus').className = 'badge bg-success';
        document.getElementById('connectionStatus').innerHTML = '<i class="fas fa-circle me-1"></i>Connecté';
    });
    
    window.addEventListener('offline', () => {
        document.getElementById('connectionStatus').className = 'badge bg-danger';
        document.getElementById('connectionStatus').innerHTML = '<i class="fas fa-circle me-1"></i>Déconnecté';
    });
});
