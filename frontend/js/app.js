// Simple and working drag & drop implementation
document.addEventListener('DOMContentLoaded', function() {
    console.log('App initializing...');
    
    // Get DOM elements
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const uploadPreview = document.getElementById('uploadPreview');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const fileStats = document.getElementById('fileStats');
    const removeFile = document.getElementById('removeFile');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const resultsSection = document.getElementById('resultsSection');
    const downloadTemplate = document.getElementById('downloadTemplate');

    // State
    let selectedFile = null;
    let analysisResults = null;

    // Check if elements exist
    if (!uploadArea) {
        console.error('Upload area not found');
        return;
    }

    console.log('Elements found, setting up event listeners...');

    // Click to select file
    uploadArea.addEventListener('click', () => {
        console.log('Upload area clicked');
        if (fileInput) {
            fileInput.click();
        }
    });

    // Drag and drop events
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.add('dragover');
        console.log('Drag over');
    });

    uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.remove('dragover');
        console.log('Drag leave');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.remove('dragover');
        console.log('Drop event');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });

    // File input change
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFile(e.target.files[0]);
            }
        });
    }

    // Remove file
    if (removeFile) {
        removeFile.addEventListener('click', removeSelectedFile);
    }

    // Analyze button
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', analyzeData);
    }

    // Download template
    if (downloadTemplate) {
        downloadTemplate.addEventListener('click', downloadCSVTemplate);
    }

    // Download results buttons
    const downloadResultsBtn = document.getElementById('downloadResults');
    const downloadChartsBtn = document.getElementById('downloadCharts');
    
    if (downloadResultsBtn) {
        downloadResultsBtn.addEventListener('click', downloadResults);
    }
    
    if (downloadChartsBtn) {
        downloadChartsBtn.addEventListener('click', downloadCharts);
    }

    function handleFile(file) {
        console.log('File selected:', file.name);
        
        // Check if it's a CSV file
        if (!file.name.toLowerCase().endsWith('.csv')) {
            alert('Vui lòng chọn file CSV!');
            return;
        }

        selectedFile = file;
        displayFilePreview(file);
        
        if (analyzeBtn) {
            analyzeBtn.disabled = false;
        }
    }

    function displayFilePreview(file) {
        if (fileName) {
            fileName.textContent = file.name;
        }
        if (fileSize) {
            fileSize.textContent = formatFileSize(file.size);
        }
        
        // Parse CSV to get basic stats
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const csv = e.target.result;
                const lines = csv.split('\n');
                const headers = lines[0].split(',').map(h => h.trim());
                const dataRows = lines.slice(1).filter(line => line.trim());
                
                if (fileStats) {
                    fileStats.innerHTML = `
                        <div><strong>Dòng dữ liệu:</strong> ${dataRows.length}</div>
                        <div><strong>Cột:</strong> ${headers.length}</div>
                        <div><strong>Headers:</strong> ${headers.slice(0, 3).join(', ')}${headers.length > 3 ? '...' : ''}</div>
                    `;
                }
            } catch (error) {
                console.error('Error parsing CSV:', error);
                if (fileStats) {
                    fileStats.innerHTML = '<div>Không thể đọc file CSV</div>';
                }
            }
        };
        reader.readAsText(file);
        
        if (uploadArea) {
            uploadArea.style.display = 'none';
        }
        if (uploadPreview) {
            uploadPreview.style.display = 'flex';
        }
    }

    function removeSelectedFile() {
        selectedFile = null;
        if (fileInput) {
            fileInput.value = '';
        }
        if (uploadArea) {
            uploadArea.style.display = 'block';
        }
        if (uploadPreview) {
            uploadPreview.style.display = 'none';
        }
        if (analyzeBtn) {
            analyzeBtn.disabled = true;
        }
        if (resultsSection) {
            resultsSection.style.display = 'none';
        }
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Analysis function
    async function analyzeData() {
        if (!selectedFile) return;

        console.log('Starting analysis...');

        // Show loading state
        if (analyzeBtn) {
            analyzeBtn.disabled = true;
            const span = analyzeBtn.querySelector('span');
            if (span) {
                span.textContent = 'Đang phân tích...';
            }
        }
        if (loadingSpinner) {
            loadingSpinner.style.display = 'inline-block';
        }

        try {
            const formData = new FormData();
            formData.append('csv_file', selectedFile);

            const response = await fetch('http://127.0.0.1:5000/api/analyze_csv', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            console.log('Analysis result:', result);
            analysisResults = result;
            displayResults(result);

        } catch (error) {
            console.error('Error analyzing data:', error);
            alert('Có lỗi xảy ra khi phân tích dữ liệu. Vui lòng thử lại.');
        } finally {
            // Hide loading state
            if (analyzeBtn) {
                analyzeBtn.disabled = false;
                const span = analyzeBtn.querySelector('span');
                if (span) {
                    span.textContent = 'Phân tích dữ liệu';
                }
            }
            if (loadingSpinner) {
                loadingSpinner.style.display = 'none';
            }
        }
    }

    // Analyze image function
    async function analyzeImage() {
        const imageInput = document.getElementById('imageInput');
        const imagePreview = document.getElementById('imagePreview');
        const imageEvaluation = document.getElementById('imageEvaluation');

        if (!imageInput || !imageInput.files || imageInput.files.length === 0) {
            alert('Vui lòng chọn một ảnh để phân tích!');
            return;
        }

        const imageFile = imageInput.files[0];

        // Show loading state
        if (imageEvaluation) {
            imageEvaluation.textContent = 'Đang phân tích ảnh...';
        }

        try {
            const formData = new FormData();
            formData.append('image_file', imageFile);

            const response = await fetch('http://127.0.0.1:5000/api/analyze_image', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            console.log('Image analysis result:', result);

            if (imageEvaluation) {
                imageEvaluation.textContent = `Đánh giá: ${result.analysis.evaluation} (Độ tin cậy: ${(result.analysis.confidence * 100).toFixed(2)}%)`;
            }

            if (imagePreview) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    imagePreview.src = e.target.result;
                    imagePreview.style.display = 'block';
                };
                reader.readAsDataURL(imageFile);
            }
        } catch (error) {
            console.error('Error analyzing image:', error);
            alert('Có lỗi xảy ra khi phân tích ảnh. Vui lòng thử lại.');
        }
    }

    // Add event listener for image analysis
    const analyzeImageBtn = document.getElementById('analyzeImageBtn');
    if (analyzeImageBtn) {
        analyzeImageBtn.addEventListener('click', analyzeImage);
    }

    // Display results
    function displayResults(data) {
        console.log('Displaying results:', data);

        // Clear previous results
        const resultsContainer = document.getElementById('resultsContainer');
        if (resultsContainer) {
            resultsContainer.innerHTML = '';
        }

        // Display analysis plots and evaluations
        if (data.analysis_plots && resultsContainer) {
            data.analysis_plots.forEach(plot => {
                const plotDiv = document.createElement('div');
                plotDiv.classList.add('result-item');

                const img = document.createElement('img');
                img.src = `http://127.0.0.1:5000/results/${plot.filename}`; // Ensure correct URL
                img.alt = plot.title;
                img.classList.add('result-image');

                const title = document.createElement('h3');
                title.textContent = plot.title;

                const evaluation = document.createElement('p');
                evaluation.textContent = plot.evaluation;

                plotDiv.appendChild(img);
                plotDiv.appendChild(title);
                plotDiv.appendChild(evaluation);

                resultsContainer.appendChild(plotDiv);
            });
        }

        // Show results section
        if (resultsSection) {
            resultsSection.style.display = 'block';
            resultsSection.scrollIntoView({ behavior: 'smooth' });
        }
    }

    // Chart creation functions (only if Chart.js is available)
    function createTimeSeriesChart(timeSeriesData) {
        const canvas = document.getElementById('timeSeriesChart');
        if (!canvas || typeof Chart === 'undefined') return;
        
        const ctx = canvas.getContext('2d');
        
        if (window.timeSeriesChart) {
            window.timeSeriesChart.destroy();
        }

        window.timeSeriesChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: timeSeriesData ? timeSeriesData.labels : [],
                datasets: [{
                    label: 'PM2.5 (μg/m³)',
                    data: timeSeriesData ? timeSeriesData.values : [],
                    borderColor: '#4CAF50',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'PM2.5 (μg/m³)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Thời gian'
                        }
                    }
                }
            }
        });
    }

    function createDistributionChart(distributionData) {
        const canvas = document.getElementById('distributionChart');
        if (!canvas || typeof Chart === 'undefined') return;
        
        const ctx = canvas.getContext('2d');
        
        if (window.distributionChart) {
            window.distributionChart.destroy();
        }

        window.distributionChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: distributionData ? distributionData.bins : [],
                datasets: [{
                    label: 'Tần suất',
                    data: distributionData ? distributionData.frequencies : [],
                    backgroundColor: 'rgba(76, 175, 80, 0.6)',
                    borderColor: '#4CAF50',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Tần suất'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'PM2.5 (μg/m³)'
                        }
                    }
                }
            }
        });
    }

    function createCorrelationChart(correlationData) {
        const canvas = document.getElementById('correlationChart');
        if (!canvas || typeof Chart === 'undefined') return;
        
        const ctx = canvas.getContext('2d');
        
        if (window.correlationChart) {
            window.correlationChart.destroy();
        }

        window.correlationChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: correlationData ? correlationData.features : [],
                datasets: [{
                    label: 'Hệ số tương quan',
                    data: correlationData ? correlationData.values : [],
                    backgroundColor: 'rgba(33, 150, 243, 0.6)',
                    borderColor: '#2196F3',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Hệ số tương quan'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Yếu tố khí tượng'
                        }
                    }
                }
            }
        });
    }

    function createImportanceChart(importanceData) {
        const canvas = document.getElementById('importanceChart');
        if (!canvas || typeof Chart === 'undefined') return;
        
        const ctx = canvas.getContext('2d');
        
        if (window.importanceChart) {
            window.importanceChart.destroy();
        }

        window.importanceChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: importanceData ? importanceData.features : [],
                datasets: [{
                    label: 'Tầm quan trọng',
                    data: importanceData ? importanceData.values : [],
                    backgroundColor: 'rgba(255, 152, 0, 0.6)',
                    borderColor: '#FF9800',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Tầm quan trọng'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Yếu tố khí tượng'
                        }
                    }
                }
            }
        });
    }

    function updateAQIAnalysis(aqiData) {
        if (!aqiData) return;

        const goodCount = document.getElementById('aqiGoodCount');
        const moderateCount = document.getElementById('aqiModerateCount');
        const unhealthyCount = document.getElementById('aqiUnhealthyCount');
        const veryUnhealthyCount = document.getElementById('aqiVeryUnhealthyCount');

        if (goodCount) goodCount.textContent = aqiData.good || 0;
        if (moderateCount) moderateCount.textContent = aqiData.moderate || 0;
        if (unhealthyCount) unhealthyCount.textContent = aqiData.unhealthy || 0;
        if (veryUnhealthyCount) veryUnhealthyCount.textContent = aqiData.very_unhealthy || 0;
    }

    // Download functions
    function downloadCSVTemplate() {
        const template = `T2MDEW,T2M,PS,TQV,TQL,H1000,HLML,RHOA,CIG,WS
20.5,25.3,101325,35.2,2.1,150.5,65.2,1.22,2000,3.5
21.2,26.1,101300,36.8,2.3,148.9,64.8,1.21,1950,4.2
19.8,24.7,101350,34.5,1.9,152.1,66.1,1.23,2050,2.8`;
        
        const blob = new Blob([template], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'meteorological_data_template.csv';
        a.click();
        window.URL.revokeObjectURL(url);
    }

    function downloadResults() {
        if (!analysisResults) return;
        
        // Create CSV content
        let csvContent = 'Feature,Value\n';
        csvContent += `RMSE,${analysisResults.model_info?.test_rmse || 'N/A'}\n`;
        csvContent += `R² Score,${analysisResults.r2_score || 'N/A'}\n`;
        csvContent += `Sample Count,${analysisResults.sample_count || 'N/A'}\n`;
        csvContent += `Mean PM2.5,${analysisResults.statistics?.mean || 'N/A'}\n`;
        csvContent += `Max PM2.5,${analysisResults.statistics?.max || 'N/A'}\n`;
        csvContent += `Min PM2.5,${analysisResults.statistics?.min || 'N/A'}\n`;
        csvContent += `Std PM2.5,${analysisResults.statistics?.std || 'N/A'}\n`;
        
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `air_quality_analysis_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
    }

    function downloadCharts() {
        alert('Tính năng tải biểu đồ sẽ được cập nhật trong phiên bản tiếp theo');
    }

    // Smooth scrolling for navigation
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Update active navigation link
    window.addEventListener('scroll', () => {
        const sections = document.querySelectorAll('section[id]');
        const navLinks = document.querySelectorAll('.nav-link');
        
        let current = '';
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            if (scrollY >= (sectionTop - 200)) {
                current = section.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${current}`) {
                link.classList.add('active');
            }
        });
    });

    console.log('App initialized successfully');
});
