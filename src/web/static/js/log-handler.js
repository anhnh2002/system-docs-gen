// Copyright (c) Meta Platforms, Inc. and affiliates
/**
 * Log message handler for the docstring generation web application.
 * 
 * This file provides functions for displaying and managing log messages
 * in the web interface.
 */

// Maximum number of log lines to keep in the UI
const MAX_LOG_LINES = 5000;

/**
 * Add a log message to the log container.
 * 
 * @param {string} level - The log level (info, warning, error, debug)
 * @param {string} message - The log message to display
 */
function addLogMessage(level, message) {
    // Create a CSS class based on the log level
    let logClass = 'log-info';
    switch (level.toLowerCase()) {
        case 'warning':
        case 'warn':
            logClass = 'log-warning';
            break;
        case 'error':
        case 'critical':
            logClass = 'log-error';
            break;
        case 'debug':
            logClass = 'log-debug';
            break;
    }
    
    // Create the log line element
    const logLine = $(`<div class="log-line ${logClass}"></div>`);
    logLine.text(message);
    
    // Add the log line to the log content
    $('#log-content').append(logLine);
    
    // Trim log lines if necessary
    const logLines = $('#log-content .log-line');
    if (logLines.length > MAX_LOG_LINES) {
        // Remove the oldest lines
        logLines.slice(0, logLines.length - MAX_LOG_LINES).remove();
    }
    
    // Scroll to the bottom of the log container
    const logContainer = $('#log-container');
    logContainer.scrollTop(logContainer[0].scrollHeight);
} 