// Copyright (c) Meta Platforms, Inc. and affiliates
/**
 * Configuration handling for the docstring generation web application.
 * 
 * This file provides functions for loading and saving configuration for the
 * docstring generation process.
 */

/**
 * Load the default configuration from the server.
 */
function loadDefaultConfig() {
    $.ajax({
        url: '/api/default_config',
        type: 'GET',
        success: function(config) {
            applyConfigToForm(config);
        },
        error: function(xhr, status, error) {
            console.error('Error loading default configuration:', error);
            showMessage('warning', 'Failed to load default configuration. Using fallback values.');
        }
    });
}

/**
 * Apply a configuration object to the form inputs.
 * 
 * @param {Object} config - The configuration object to apply
 */
function applyConfigToForm(config) {
    // Set LLM configuration
    if (config.llm) {
        $('#llm-type').val(config.llm.type || 'claude');
        $('#llm-api-key').val(config.llm.api_key || '');
        $('#llm-model').val(config.llm.model || 'claude-3-5-haiku-latest');
        $('#llm-temperature').val(config.llm.temperature || 0.1);
        $('#llm-max-tokens').val(config.llm.max_tokens || 4096);
    }
    
    // Set flow control configuration
    if (config.flow_control) {
        $('#max-reader-search-attempts').val(config.flow_control.max_reader_search_attempts || 2);
        $('#max-verifier-rejections').val(config.flow_control.max_verifier_rejections || 1);
        $('#status-sleep-time').val(config.flow_control.status_sleep_time || 1);
    }
    
    // Set docstring options
    if (config.docstring_options) {
        $('#overwrite-docstrings').prop('checked', config.docstring_options.overwrite_docstrings || false);
    }
}

/**
 * Build a configuration object from the form inputs.
 * 
 * @returns {Object} The configuration object
 */
function buildConfigFromForm() {
    return {
        llm: {
            type: $('#llm-type').val(),
            api_key: $('#llm-api-key').val(),
            model: $('#llm-model').val(),
            temperature: parseFloat($('#llm-temperature').val()),
            max_tokens: parseInt($('#llm-max-tokens').val())
        },
        flow_control: {
            max_reader_search_attempts: parseInt($('#max-reader-search-attempts').val()),
            max_verifier_rejections: parseInt($('#max-verifier-rejections').val()),
            status_sleep_time: parseFloat($('#status-sleep-time').val())
        },
        docstring_options: {
            overwrite_docstrings: $('#overwrite-docstrings').is(':checked')
        }
    };
} 