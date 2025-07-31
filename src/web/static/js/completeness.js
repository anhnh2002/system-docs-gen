// Copyright (c) Meta Platforms, Inc. and affiliates
/**
 * Completeness visualization for the docstring generation web application.
 * 
 * This file provides functions for rendering and updating the completeness
 * visualization in the web interface.
 */

/**
 * Update the completeness view with the evaluation results.
 * 
 * @param {Object} completenessData - The completeness evaluation data from the server
 */
function updateCompletenessView(completenessData) {
    if (!completenessData || !completenessData.files) {
        $('#completeness-data').html(`
            <div class="alert alert-warning mb-0">
                No completeness data available
            </div>
        `);
        return;
    }
    
    // Calculate overall statistics
    const totalFiles = completenessData.files.length;
    let totalClasses = 0;
    let totalClassesWithDocs = 0;
    let totalFunctions = 0;
    let totalFunctionsWithDocs = 0;
    
    completenessData.files.forEach(file => {
        if (file.classes) {
            totalClasses += file.classes.length;
            totalClassesWithDocs += file.classes.filter(c => c.has_docstring).length;
        }
        if (file.functions) {
            totalFunctions += file.functions.length;
            totalFunctionsWithDocs += file.functions.filter(f => f.has_docstring).length;
        }
    });
    
    const classCompleteness = totalClasses > 0 ? Math.round((totalClassesWithDocs / totalClasses) * 100) : 0;
    const functionCompleteness = totalFunctions > 0 ? Math.round((totalFunctionsWithDocs / totalFunctions) * 100) : 0;
    const totalComponents = totalClasses + totalFunctions;
    const totalComponentsWithDocs = totalClassesWithDocs + totalFunctionsWithDocs;
    const overallCompleteness = totalComponents > 0 ? Math.round((totalComponentsWithDocs / totalComponents) * 100) : 0;
    
    // Create the HTML for the completeness view
    let html = `
        <div class="mb-3">
            <h5>Overall Completeness: ${overallCompleteness}%</h5>
            <div class="progress mb-2">
                <div class="progress-bar bg-success" role="progressbar" style="width: ${overallCompleteness}%;" aria-valuenow="${overallCompleteness}" aria-valuemin="0" aria-valuemax="100">${overallCompleteness}%</div>
            </div>
            <div class="row">
                <div class="col-6">
                    <small>Classes: ${totalClassesWithDocs}/${totalClasses} (${classCompleteness}%)</small>
                </div>
                <div class="col-6">
                    <small>Functions: ${totalFunctionsWithDocs}/${totalFunctions} (${functionCompleteness}%)</small>
                </div>
            </div>
        </div>
        
        <h5>Files (${totalFiles})</h5>
        <div class="table-responsive">
            <table class="table table-sm completeness-table">
                <thead>
                    <tr>
                        <th>File</th>
                        <th class="text-center">Classes</th>
                        <th class="text-center">Functions</th>
                        <th class="progress-cell">Completeness</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    // Sort files by completeness (lowest first)
    const sortedFiles = [...completenessData.files].sort((a, b) => {
        const aTotal = (a.classes?.length || 0) + (a.functions?.length || 0);
        const aWithDocs = (a.classes?.filter(c => c.has_docstring).length || 0) + 
                        (a.functions?.filter(f => f.has_docstring).length || 0);
        const aPercentage = aTotal > 0 ? (aWithDocs / aTotal) : 1;
        
        const bTotal = (b.classes?.length || 0) + (b.functions?.length || 0);
        const bWithDocs = (b.classes?.filter(c => c.has_docstring).length || 0) + 
                        (b.functions?.filter(f => f.has_docstring).length || 0);
        const bPercentage = bTotal > 0 ? (bWithDocs / bTotal) : 1;
        
        return aPercentage - bPercentage;
    });
    
    // Add rows for each file
    sortedFiles.forEach(file => {
        const classes = file.classes || [];
        const functions = file.functions || [];
        const classesWithDocs = classes.filter(c => c.has_docstring).length;
        const functionsWithDocs = functions.filter(f => f.has_docstring).length;
        const totalInFile = classes.length + functions.length;
        const totalWithDocsInFile = classesWithDocs + functionsWithDocs;
        const fileCompleteness = totalInFile > 0 ? Math.round((totalWithDocsInFile / totalInFile) * 100) : 100;
        
        // Determine the row color based on completeness
        let rowClass = '';
        if (fileCompleteness === 100) {
            rowClass = 'table-success';
        } else if (fileCompleteness >= 50) {
            rowClass = 'table-warning';
        } else {
            rowClass = 'table-danger';
        }
        
        html += `
            <tr class="${rowClass}">
                <td><small>${file.file.split('/').pop()}</small></td>
                <td class="text-center"><small>${classesWithDocs}/${classes.length}</small></td>
                <td class="text-center"><small>${functionsWithDocs}/${functions.length}</small></td>
                <td>
                    <div class="progress progress-bar-mini">
                        <div class="progress-bar bg-success" role="progressbar" style="width: ${fileCompleteness}%;" aria-valuenow="${fileCompleteness}" aria-valuemin="0" aria-valuemax="100"></div>
                    </div>
                    <small class="d-block text-end">${fileCompleteness}%</small>
                </td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    // Update the completeness data container
    $('#completeness-data').html(html);
} 