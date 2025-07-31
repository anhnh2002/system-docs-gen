// Copyright (c) Meta Platforms, Inc. and affiliates
/**
 * Main JavaScript for the docstring generation web application.
 * 
 * This file provides the main functionality for the web interface, including
 * event handling, configuration, and communication with the server.
 */

// Global state variables
let socket = null;
let processRunning = false;
let startTime = 0;
let timerInterval = null;
let apiTestModal = null;

// Document ready handler
$(document).ready(function() {
    // Load default configuration
    loadDefaultConfig();
    
    // Set up form submission handler
    $('#config-form').on('submit', function(e) {
        e.preventDefault();
        startGeneration();
    });
    
    // Set up test API button handler
    $('#test-api-button').on('click', function() {
        testApiConnection();
    });
    
    // Initialize the API test modal
    apiTestModal = new bootstrap.Modal(document.getElementById('api-test-modal'));
    
    // Check if a process is already running
    checkProcessStatus();
    
    // Initialize the agent workflow visualization
    initAgentWorkflow();
    
    // Handle window resize
    $(window).on('resize', function() {
        initAgentWorkflow();
    });
});

/**
 * Test the API connection with the configured settings.
 */
function testApiConnection() {
    // Show the modal
    apiTestModal.show();
    
    // Set the modal content to loading state
    $('#api-test-result').html(`
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Testing API...</span>
            </div>
            <p class="mt-2">Testing API connection...</p>
        </div>
    `);
    
    // Get the API configuration
    const config = {
        llm_type: $('#llm-type').val(),
        api_key: $('#llm-api-key').val(),
        model: $('#llm-model').val()
    };
    
    // Send a test request to the server
    $.ajax({
        url: '/api/test_api',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(config),
        success: function(response) {
            if (response.status === 'success') {
                $('#api-test-result').html(`
                    <div class="alert alert-success">
                        <h5><i class="fas fa-check-circle"></i> API Connection Successful</h5>
                        <p>${response.message || 'The API connection is working correctly.'}</p>
                        <hr>
                        <div class="card p-2 bg-light">
                            <small class="text-muted">Response from model:</small>
                            <p class="mb-0">${response.model_response || 'No response provided.'}</p>
                        </div>
                    </div>
                `);
            } else {
                $('#api-test-result').html(`
                    <div class="alert alert-danger">
                        <h5><i class="fas fa-exclamation-circle"></i> API Connection Failed</h5>
                        <p>${response.message || 'Failed to connect to the API.'}</p>
                        <hr>
                        <p class="mb-0">Please check your API key and other settings.</p>
                    </div>
                `);
            }
        },
        error: function(xhr, status, error) {
            $('#api-test-result').html(`
                <div class="alert alert-danger">
                    <h5><i class="fas fa-exclamation-circle"></i> API Connection Failed</h5>
                    <p>Error: ${error}</p>
                    <hr>
                    <p class="mb-0">Please check your API key and other settings.</p>
                </div>
            `);
        }
    });
}

/**
 * Check if a process is already running.
 */
function checkProcessStatus() {
    $.ajax({
        url: '/api/status',
        type: 'GET',
        success: function(data) {
            processRunning = data.is_running;
            
            if (processRunning) {
                // Process is running, switch to the running view
                showRunningView();
                
                // Connect to Socket.IO
                setupSocketHandlers();
                
                // Start the timer
                startTimer();
                
                // Load completeness data initially
                loadCompletenessData();
            } else {
                // Show the configuration view
                showConfigView();
            }
        },
        error: function(xhr, status, error) {
            console.error('Error checking process status:', error);
            showMessage('error', 'Error checking process status: ' + error);
        }
    });
}

/**
 * Set up Socket.IO event handlers.
 */
function setupSocketHandlers() {
    // Create Socket.IO connection if it doesn't exist
    if (!socket) {
        socket = io();
        
        // Status update handler
        socket.on('status_update', function(data) {
            console.log('Status update received:', data);
            
            if (data.status) {
                updateStatusVisualizer(data.status);
            }
            
            if (data.repo_structure) {
                updateRepoStructure(data.repo_structure);
            }
        });
        
        // Log message handler
        socket.on('log_message', function(data) {
            addLogMessage(data.level, data.message);
            
            // If this is a docstring generation success message, refresh completeness
            if (data.message && (
                data.message.includes('Successfully updated docstring for') || 
                data.message.includes('Completed docstring generation for')
            )) {
                // Wait a brief moment for file changes to be detected
                setTimeout(loadCompletenessData, 500);
            }
        });
        
        // Raw log message handler (for system prints)
        socket.on('log_line', function(data) {
            addLogMessage('info', data);
            
            // Check if this is a message about docstring generation
            if (typeof data === 'string' && (
                data.includes('Successfully updated docstring') ||
                data.includes('Completed docstring generation')
            )) {
                // Refresh the completeness data
                setTimeout(loadCompletenessData, 500);
            }
        });
        
        // Error handler
        socket.on('error', function(data) {
            addLogMessage('error', data.message);
            showMessage('error', data.message);
        });
        
        // Completion handler
        socket.on('complete', function(data) {
            processRunning = false;
            $('#start-button').prop('disabled', false).text('Start Generation');
            addLogMessage('info', data.message);
            showMessage('success', 'Docstring generation completed');
            stopTimer();
            
            // Final completeness refresh
            loadCompletenessData();
        });
        
        // Disconnection handler
        socket.on('disconnect', function() {
            addLogMessage('warning', 'Connection to server lost');
        });
    }
}

/**
 * Start the docstring generation process.
 */
function startGeneration() {
    if (processRunning) {
        showMessage('warning', 'Generation already in progress');
        return;
    }
    
    // Get the repository path
    const repoPath = $('#repo-path').val();
    if (!repoPath) {
        showMessage('error', 'Please enter a repository path');
        return;
    }
    
    // Disable the start button
    $('#start-button').prop('disabled', true).text('Starting...');
    
    // Get the configuration
    const config = buildConfigFromForm();
    
    // Clear log content
    $('#log-content').empty();
    
    // Send the request to start generation
    $.ajax({
        url: '/api/start',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            repo_path: repoPath,
            config: config
        }),
        success: function(data) {
            if (data.status === 'success') {
                // Mark as running
                processRunning = true;
                
                // Show the running view
                showRunningView();
                
                // Connect to Socket.IO
                setupSocketHandlers();
                
                // Start the timer
                startTimer();
                
                // Make the completeness section visible and load initial data
                $('#completeness-section').removeClass('d-none');
                loadCompletenessData();
                
                // Show success message
                showMessage('success', data.message);
            } else {
                // Show error message
                showMessage('error', data.message);
                $('#start-button').prop('disabled', false).text('Start Generation');
            }
        },
        error: function(xhr, status, error) {
            showMessage('error', 'Error starting generation: ' + error);
            $('#start-button').prop('disabled', false).text('Start Generation');
        }
    });
}

/**
 * Stop the docstring generation process.
 */
function stopGeneration() {
    if (!processRunning) {
        showMessage('warning', 'No generation in progress');
        return;
    }
    
    // Confirm stop
    if (!confirm('Are you sure you want to stop the docstring generation process?')) {
        return;
    }
    
    // Send the request to stop generation
    $.ajax({
        url: '/api/stop',
        type: 'POST',
        success: function(data) {
            if (data.status === 'success') {
                processRunning = false;
                $('#start-button').prop('disabled', false).text('Start Generation');
                showMessage('success', data.message);
                stopTimer();
                
                // Add log message
                addLogMessage('warning', 'Generation process stopped by user');
            } else {
                showMessage('error', data.message);
            }
        },
        error: function(xhr, status, error) {
            showMessage('error', 'Error stopping generation: ' + error);
        }
    });
}

/**
 * Show the configuration view.
 */
function showConfigView() {
    $('#main-content').addClass('d-none');
    $('#sidebar').removeClass('col-md-3').addClass('col-md-12');
    $('#config-section').removeClass('d-none');
    $('#completeness-section').addClass('d-none');
}

/**
 * Show the running view.
 */
function showRunningView() {
    $('#config-section').addClass('d-none');
    $('#completeness-section').removeClass('d-none');
    $('#sidebar').removeClass('col-md-12').addClass('col-md-3');
    $('#main-content').removeClass('d-none');
    
    // Make sure the agent workflow is initialized
    setTimeout(function() {
        initAgentWorkflow();
    }, 100);
    
    // Add a stop button to the header
    if ($('#stop-button').length === 0) {
        $('header').append(`
            <button id="stop-button" class="btn btn-danger btn-sm position-absolute" style="right: 1rem; top: 1rem;">
                <i class="fas fa-stop"></i> Stop Generation
            </button>
        `);
        
        // Add click handler
        $('#stop-button').on('click', function() {
            stopGeneration();
        });
    }
}

/**
 * Show a message to the user.
 * 
 * @param {string} type - The type of message (success, error, warning, info)
 * @param {string} message - The message to show
 */
function showMessage(type, message) {
    // Create alert if it doesn't exist
    if ($('#alert-container').length === 0) {
        $('body').append(`
            <div id="alert-container" style="position: fixed; top: 20px; right: 20px; z-index: 9999;"></div>
        `);
    }
    
    // Create a unique ID for the alert
    const id = 'alert-' + Date.now();
    
    // Add the alert to the container
    $('#alert-container').append(`
        <div id="${id}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `);
    
    // Automatically remove the alert after 5 seconds
    setTimeout(() => {
        $(`#${id}`).alert('close');
    }, 5000);
}

/**
 * Start the timer.
 */
function startTimer() {
    // Set the start time
    startTime = Date.now();
    
    // Clear any existing timer
    if (timerInterval) {
        clearInterval(timerInterval);
    }
    
    // Update every second
    timerInterval = setInterval(() => {
        const elapsedSeconds = Math.floor((Date.now() - startTime) / 1000);
        const minutes = Math.floor(elapsedSeconds / 60);
        const seconds = elapsedSeconds % 60;
        
        // Format as MM:SS
        const formattedTime = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        // Update the display
        $('#progress-time').text(`Elapsed: ${formattedTime}`);
    }, 1000);
}

/**
 * Stop the timer.
 */
function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

/**
 * Load completeness data from the server.
 */
function loadCompletenessData() {
    // Only load data if the completeness section is visible
    if ($('#completeness-section').hasClass('d-none')) {
        return;
    }
    
    $.ajax({
        url: '/api/completeness',
        type: 'GET',
        success: function(response) {
            if (response.status === 'success' && response.data) {
                updateCompletenessView(response.data);
            } else {
                $('#completeness-data').html(`
                    <div class="alert alert-warning mb-0">
                        ${response.message || 'Failed to load completeness data'}
                    </div>
                `);
            }
        },
        error: function(xhr, status, error) {
            console.error('Error loading completeness data:', error);
            $('#completeness-data').html(`
                <div class="alert alert-danger mb-0">
                    Error loading completeness data: ${error}
                </div>
            `);
        }
    });
} 