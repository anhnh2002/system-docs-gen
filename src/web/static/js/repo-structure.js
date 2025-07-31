// Copyright (c) Meta Platforms, Inc. and affiliates
/**
 * Repository structure visualization for the docstring generation web application.
 * 
 * This file provides functions for rendering and updating the repository structure
 * visualization using D3.js.
 */

// Store the current repository structure
let currentRepoStructure = null;

// Keep track of the current focus path
let currentFocusPath = null;

// D3 visualization settings
const margin = { top: 20, right: 20, bottom: 20, left: 20 };
let width = 600;
let height = 500;
let nodeRadius = 7;
let maxLabelLength = 20;

/**
 * Update the repository structure visualization.
 * 
 * @param {Object} repoStructure - The repository structure object from the server
 */
function updateRepoStructure(repoStructure) {
    // If there's no repo structure, show placeholder
    if (!repoStructure || !repoStructure.tree || Object.keys(repoStructure.tree).length === 0) {
        $('#repo-structure').html(`
            <div class="text-center py-4">
                <p>No repository structure available</p>
            </div>
        `);
        return;
    }
    
    // Store the previous focus path
    const prevFocusPath = currentFocusPath;
    
    // Update the current state
    currentRepoStructure = repoStructure;
    currentFocusPath = repoStructure.focus_path;
    
    // Update dimensions based on container size
    const container = document.getElementById('repo-structure');
    width = container.clientWidth - margin.left - margin.right;
    height = container.clientHeight - margin.top - margin.bottom;
    
    // Clear existing visualization
    $('#repo-structure').empty();
    
    // Create SVG container
    const svg = d3.select('#repo-structure')
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);
    
    // Create hierarchy from the data
    const root = d3.hierarchy(repoStructure.tree);
    
    // Set node size based on number of nodes to avoid overlapping
    const nodeCount = root.descendants().length;
    const dynamicRadius = Math.max(3, Math.min(7, 10 - Math.log(nodeCount)));
    nodeRadius = dynamicRadius;
    
    // Create tree layout
    const treeLayout = d3.tree()
        .size([height, width - 160]);
    
    // Compute the tree layout
    treeLayout(root);
    
    // Add links between nodes
    svg.selectAll('.link')
        .data(root.links())
        .enter()
        .append('path')
        .attr('class', 'link')
        .attr('d', d => {
            return `M${d.source.y},${d.source.x}
                   C${(d.source.y + d.target.y) / 2},${d.source.x}
                    ${(d.source.y + d.target.y) / 2},${d.target.x}
                    ${d.target.y},${d.target.x}`;
        })
        .attr('fill', 'none')
        .attr('stroke', '#ccc')
        .attr('stroke-width', 1.5);
    
    // Add nodes
    const nodes = svg.selectAll('.node')
        .data(root.descendants())
        .enter()
        .append('g')
        .attr('class', 'node')
        .attr('transform', d => `translate(${d.y},${d.x})`)
        .attr('id', d => `node-${d.data.path.replace(/[\/\.]/g, '_')}`); // Add ID for easier selection
    
    // Add node circles
    nodes.append('circle')
        .attr('r', nodeRadius)
        .attr('class', d => {
            let classes = 'repo-node ';
            
            // Add status class
            if (d.data.type === 'file') {
                classes += `repo-node-${d.data.status || 'not-started'}`;
            } else {
                // For directories, determine status based on children
                const hasCompleteChildren = d.descendants().slice(1).some(node => 
                    node.data.type === 'file' && node.data.status === 'complete');
                const hasInProgressChildren = d.descendants().slice(1).some(node => 
                    node.data.type === 'file' && node.data.status === 'in_progress');
                
                if (hasCompleteChildren && !hasInProgressChildren) {
                    classes += 'repo-node-complete';
                } else if (hasInProgressChildren) {
                    classes += 'repo-node-in-progress';
                } else {
                    classes += 'repo-node-not-started';
                }
            }
            
            // Add focus class if this is the focused node
            if (d.data.path === currentFocusPath) {
                classes += ' repo-node-focus';
            }
            
            return classes;
        })
        .style('fill', d => {
            if (d.data.type === 'dir') {
                // Check children status for directory coloring
                const completeCount = d.descendants().slice(1).filter(node => 
                    node.data.type === 'file' && node.data.status === 'complete').length;
                const totalFiles = d.descendants().slice(1).filter(node => 
                    node.data.type === 'file').length;
                const progress = totalFiles > 0 ? completeCount / totalFiles : 0;
                
                // Use color gradient based on completion percentage
                if (progress === 1) return '#198754';  // All complete - green
                if (progress > 0) return '#ffc107';    // Some complete - yellow
                return '#6c757d';  // None complete - grey
            } else {
                // Colors for files based on status
                return d.data.status === 'complete' ? '#198754' : 
                       d.data.status === 'in_progress' ? '#ffc107' : '#f8f9fa';
            }
        })
        .style('stroke', d => d.data.path === currentFocusPath ? '#dc3545' : '#6c757d')
        .style('stroke-width', d => d.data.path === currentFocusPath ? 2 : 1);
    
    // Add node labels
    nodes.append('text')
        .attr('dy', 3)
        .attr('x', d => d.children ? -nodeRadius * 1.5 : nodeRadius * 1.5)
        .attr('text-anchor', d => d.children ? 'end' : 'start')
        .attr('class', 'repo-node-label')
        .text(d => {
            const name = d.data.name;
            if (name.length > maxLabelLength) {
                return name.substring(0, maxLabelLength - 3) + '...';
            }
            return name;
        })
        .append('title')  // Add tooltip with full name
        .text(d => d.data.name);
    
    // Find the focused node if it exists
    if (currentFocusPath) {
        const focusedNode = root.descendants().find(d => d.data.path === currentFocusPath);
        if (focusedNode) {
            // If focus has changed, trigger the zoom animation
            if (prevFocusPath !== currentFocusPath) {
                zoomToNode(svg, focusedNode, width, height);
            }
        }
    }
}

/**
 * Zoom to a specific node in the visualization.
 * 
 * @param {Object} svg - The D3 SVG selection
 * @param {Object} node - The node to zoom to
 * @param {number} width - The width of the container
 * @param {number} height - The height of the container
 */
function zoomToNode(svg, node, width, height) {
    // Calculate the scale factor based on how deep the node is in the tree
    const depth = node.depth;
    const scale = Math.max(1, Math.min(2, 1 + depth * 0.2));
    
    // Calculate translation to center the node
    const x = node.x;
    const y = node.y;
    const tx = width/2 - y * scale;
    const ty = height/2 - x * scale;
    
    // Apply the zoom transformation
    svg.transition()
        .duration(750)
        .attr('transform', `translate(${margin.left + tx},${margin.top + ty}) scale(${scale})`);
    
    // Add a highlight animation to the node
    const nodeId = `#node-${node.data.path.replace(/[\/\.]/g, '_')} circle`;
    d3.select(nodeId)
        .classed('highlight-focus', true)
        .transition()
        .duration(750)
        .on('end', function() {
            d3.select(this).classed('highlight-focus', false);
        });
}

/**
 * Update the status of a file in the repository structure.
 * 
 * @param {string} file_path - The path of the file to update
 * @param {string} status - The new status (not_started, in_progress, complete)
 */
function updateFileStatus(file_path, status) {
    if (!currentRepoStructure) return;
    
    // Find the file in the tree
    function updateNodeStatus(node) {
        if (node.path === file_path) {
            // Only update if the status is actually changing
            if (node.status !== status) {
                node.status = status;
                return true;
            }
            return false;
        }
        
        if (node.children) {
            for (const child of node.children) {
                if (updateNodeStatus(child)) {
                    return true;
                }
            }
        }
        
        return false;
    }
    
    // Update the node status
    if (updateNodeStatus(currentRepoStructure.tree)) {
        // If the file status has changed, update the visualization
        if (status === 'in_progress') {
            currentRepoStructure.focus_path = file_path;
        }
        updateRepoStructure(currentRepoStructure);
    }
}

// Initialize the visualization when the document is ready
$(document).ready(function() {
    // If we receive a docstring_updated event, update the repository structure
    if (socket) {
        socket.on('docstring_updated', function(data) {
            if (data.component && currentRepoStructure) {
                updateFileStatus(data.component, 'complete');
            }
        });
    }
});

// Handle window resize to update visualization
$(window).on('resize', function() {
    if (currentRepoStructure) {
        updateRepoStructure(currentRepoStructure);
    }
}); 