// Copyright (c) Meta Platforms, Inc. and affiliates
/**
 * Status visualizer for the docstring generation web application.
 * 
 * This file provides functions for rendering and updating the agent status
 * visualization in the web interface.
 */

// Define the agent workflow structure
const agentWorkflow = {
    nodes: [
        { id: "reader", label: "Reader", x: 150, y: 80, isAgent: true },
        { id: "searcher", label: "Searcher", x: 350, y: 80, isAgent: true },
        { id: "writer", label: "Writer", x: 150, y: 200, isAgent: true },
        { id: "verifier", label: "Verifier", x: 350, y: 200, isAgent: true }
    ],
    labels: [
        { id: "input", label: "Input", x: 30, y: 140 },
        { id: "output", label: "Output", x: 470, y: 140 }
    ],
    links: [
        { source: "input", target: "reader" },
        { source: "reader", target: "searcher" },
        { source: "searcher", target: "reader" },
        { source: "reader", target: "writer" },
        { source: "writer", target: "verifier" },
        { source: "verifier", target: "output" },
        { source: "verifier", target: "reader" }
    ]
};

// Keep track of the current active agent
let currentActiveAgent = null;

// Initialize the agent workflow visualization
function initAgentWorkflow() {
    const container = document.getElementById('agent-workflow');
    if (!container) return;

    // Check if container is visible and has dimensions
    const width = container.clientWidth || 600;
    const height = container.clientHeight || 200;

    // Clear any existing content
    d3.select(container).selectAll("*").remove();

    // Create SVG container
    const svg = d3.select(container)
        .append("svg")
        .attr("width", width)
        .attr("height", height)
        .append("g")
        .attr("transform", `translate(${Math.max(0, (width - 500) / 2)}, 0)`);

    // Add arrowhead marker definition
    svg.append("defs").append("marker")
        .attr("id", "arrowhead")
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 20)
        .attr("refY", 0)
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .attr("orient", "auto")
        .append("path")
        .attr("d", "M0,-5L10,0L0,5")
        .attr("fill", "#adb5bd");

    // Helper function to get node coordinates by id
    function getNodeCoords(id) {
        const agentNode = agentWorkflow.nodes.find(n => n.id === id);
        if (agentNode) return { x: agentNode.x, y: agentNode.y };
        
        const labelNode = agentWorkflow.labels.find(n => n.id === id);
        if (labelNode) return { x: labelNode.x, y: labelNode.y };
        
        return null;
    }

    // Draw links
    svg.selectAll(".workflow-link")
        .data(agentWorkflow.links)
        .enter()
        .append("path")
        .attr("class", "workflow-link")
        .attr("d", d => {
            const source = getNodeCoords(d.source);
            const target = getNodeCoords(d.target);
            
            if (!source || !target) return "";
            
            // Create curved paths
            const dx = target.x - source.x;
            const dy = target.y - source.y;
            const dr = Math.sqrt(dx * dx + dy * dy) * 1.5;
            
            return `M${source.x},${source.y}A${dr},${dr} 0 0,1 ${target.x},${target.y}`;
        });

    // Draw agent nodes (circles)
    const nodes = svg.selectAll(".workflow-node")
        .data(agentWorkflow.nodes)
        .enter()
        .append("g")
        .attr("class", d => `workflow-node ${d.id}`)
        .attr("transform", d => `translate(${d.x}, ${d.y})`);

    // Add node circles for agents
    nodes.append("circle")
        .attr("r", 35);

    // Add node labels for agents
    nodes.append("text")
        .attr("class", "workflow-label")
        .attr("dy", ".35em")
        .text(d => d.label);

    // Add non-agent labels (input/output)
    const textLabels = svg.selectAll(".workflow-text")
        .data(agentWorkflow.labels)
        .enter()
        .append("g")
        .attr("class", d => `workflow-text ${d.id}`)
        .attr("transform", d => `translate(${d.x}, ${d.y})`);
    
    // Add text for non-agent nodes
    textLabels.append("text")
        .attr("class", "workflow-text-label")
        .attr("dy", ".35em")
        .attr("text-anchor", "middle")
        .style("font-size", "14px")
        .style("font-weight", "bold")
        .style("fill", "#444")
        .text(d => d.label);

    // Add event listeners to highlight nodes on hover
    nodes.on("mouseover", function() {
        d3.select(this).style("opacity", 0.8);
    }).on("mouseout", function() {
        d3.select(this).style("opacity", 1);
    });
    
    // If we have a stored active agent, highlight it
    if (currentActiveAgent) {
        updateAgentWorkflow(currentActiveAgent);
    }
    
    console.log("Agent workflow initialized with dimensions:", width, "x", height);
}

// Ensure the workflow is initialized as soon as the document is ready
$(document).ready(function() {
    // Delay initialization slightly to ensure DOM is fully ready
    setTimeout(initAgentWorkflow, 100);
    
    // Also handle window resize
    $(window).on('resize', function() {
        initAgentWorkflow();
    });
    
    // Poll to ensure the graph is visible (workaround for tabs/containers that might be hidden initially)
    let checkCount = 0;
    const checkInterval = setInterval(function() {
        const container = document.getElementById('agent-workflow');
        if (container && container.clientWidth > 0 && container.clientHeight > 0) {
            initAgentWorkflow();
            clearInterval(checkInterval);
        } else if (checkCount > 20) { // Stop after 20 attempts (10 seconds)
            clearInterval(checkInterval);
        }
        checkCount++;
    }, 500);
});

/**
 * Update the status visualizer with the current status.
 * 
 * @param {Object} status - The status object from the server
 */
function updateStatusVisualizer(status) {
    console.log("Updating status visualizer with:", status);
    
    // Update the agent workflow visualization
    updateAgentWorkflow(status.active_agent);
    
    // If there's no active agent, show placeholder
    if (!status.active_agent) {
        $('#status-visualizer').html(`
            <div class="text-center py-2">
                <p>No active agent</p>
            </div>
        `);
        return;
    }
    
    // Update component info and status message
    let statusHtml = `<div class="text-center mb-2">Processing with <strong>${status.active_agent}</strong></div>`;
    
    if (status.status_message) {
        statusHtml += `<div class="alert alert-info py-2 mb-2">${status.status_message}</div>`;
    }
    
    if (status.current_component) {
        statusHtml += `
            <div class="component-info">
                <div><strong>Current Processing Component:</strong> ${status.current_component}</div>
                <div class="text-muted mt-1"><small>Current Processing File: ${status.current_file}</small></div>
            </div>
        `;
    }
    
    $('#status-visualizer').html(statusHtml);
}

/**
 * Update the agent workflow visualization with the active agent.
 * 
 * @param {string} activeAgent - The name of the active agent
 */
function updateAgentWorkflow(activeAgent) {
    // Store the active agent
    currentActiveAgent = activeAgent;
    
    // Make sure the workflow is initialized 
    if ($('#agent-workflow svg').length === 0) {
        initAgentWorkflow();
        return; // The initialization will handle setting the active agent
    }
    
    console.log("Updating agent workflow with active agent:", activeAgent);
    
    // Remove active class from all nodes
    d3.selectAll(".workflow-node").classed("active", false);
    
    if (!activeAgent) {
        return;
    }
    
    // Skip non-agent entities
    if (activeAgent.toLowerCase() === 'system' || 
        activeAgent.toLowerCase() === 'input' || 
        activeAgent.toLowerCase() === 'output') {
        return;
    }
    
    // Normalize the agent name to lowercase
    const agentLower = activeAgent.toLowerCase();
    
    // Map certain agent names to our workflow nodes
    let nodeId = null;
    if (agentLower.includes('reader')) nodeId = 'reader';
    else if (agentLower.includes('searcher')) nodeId = 'searcher';
    else if (agentLower.includes('writer')) nodeId = 'writer';
    else if (agentLower.includes('verifier')) nodeId = 'verifier';
    
    // Add active class to the current agent node
    if (nodeId) {
        const node = d3.select(`.workflow-node.${nodeId}`);
        if (!node.empty()) {
            node.classed("active", true);
            console.log("Activated node:", nodeId);
            // Briefly animate the node to draw attention
            node.select("circle")
                .transition()
                .duration(300)
                .attr("r", 40)
                .transition()
                .duration(300)
                .attr("r", 35);
        } else {
            console.warn("Could not find node for agent:", activeAgent, "mapped to:", nodeId);
        }
    } else {
        console.warn("Could not map agent name to a node:", activeAgent);
    }
}

/**
 * Update the progress information.
 * 
 * @param {Object} progress - The progress object from the server
 */
function updateProgress(progress) {
    // Calculate percentage
    const total = progress.total_components || 0;
    const processed = progress.processed_components || 0;
    const percentage = total > 0 ? Math.floor((processed / total) * 100) : 0;
    
    // Update progress bar
    $('#progress-bar').css('width', `${percentage}%`);
    $('#progress-bar').attr('aria-valuenow', percentage);
    $('#progress-bar').text(`${percentage}%`);
    
    // Update progress text
    $('#progress-text').text(`${processed}/${total} components processed`);
} 