// Global variables
let currentSection = 'setup';
let buildingType = '';

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    // Set up navigation
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const section = this.getAttribute('data-section');
            showSection(section);

            // Update active nav link
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });

    // Mobile menu toggle
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const sidebar = document.getElementById('sidebar');

    mobileMenuToggle.addEventListener('click', function() {
        sidebar.classList.toggle('active');
    });

    // Load materials data
    loadMaterials();
});

// Navigation functions
function showSection(section) {
    currentSection = section;

    // Hide all sections
    document.querySelectorAll('main > section').forEach(s => {
        s.style.display = 'none';
    });

    // Show selected section
    const sectionMap = {
        'setup': 'setupSection',
        'blueprint': 'blueprintSection',
        'room': 'roomSection',
        'estimate': 'estimateSection',
        'materials': 'materialsSection',
        'labor': 'laborSection'
    };

    const sectionElement = document.getElementById(sectionMap[section]);
    if (sectionElement) {
        sectionElement.style.display = 'block';
    }

    // Update page title and description
    const titles = {
        'setup': 'Project Setup',
        'blueprint': 'Blueprint Upload',
        'room': 'Manual Room / NEC',
        'estimate': 'Manual Estimate',
        'materials': 'Materials & Pricing',
        'labor': 'Labor Rates'
    };

    const descriptions = {
        'setup': 'Configure your project settings',
        'blueprint': 'Upload your blueprints for analysis',
        'room': 'Calculate requirements for specific rooms',
        'estimate': 'Create manual estimates',
        'materials': 'Browse and price materials',
        'labor': 'Compare labor rates by state'
    };

    document.getElementById('pageTitle').textContent = titles[section] + ' - Judith Estimator';
    document.getElementById('pageDescription').textContent = descriptions[section];
}

// Building type functions
function setType(type) {
    buildingType = type;
    document.getElementById('codeSection').style.display = 'block';
    document.getElementById('commercialOptions').style.display = 'none';

    // Scroll to code section
    setTimeout(() => {
        document.getElementById('codeSection').scrollIntoView({ behavior: 'smooth' });
    }, 100);
}

function showCommercialOptions() {
    document.getElementById('commercialOptions').style.display = 'block';
    document.getElementById('codeSection').style.display = 'none';
}

function continueToWorkflow() {
    // In a real app, this would save the configuration
    // For now, just show the workflow options
    const workflowSection = document.getElementById('workflowSection');
    if (workflowSection) {
        workflowSection.style.display = 'block';
        workflowSection.scrollIntoView({ behavior: 'smooth' });
    }
}

// NEC calculation
async function runNec() {
    const sqft = document.getElementById('sqft').value;
    const amps = document.getElementById('amps').value;

    if (!sqft || !amps) {
        alert('Please enter both square footage and circuit amps.');
        return;
    }

    try {
        const response = await fetch('/api/nec', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                sqft: parseFloat(sqft),
                amps: parseFloat(amps)
            })
        });

        const data = await response.json();
        const output = document.getElementById('necout');
        output.textContent = data.report;
        output.style.display = 'block';
    } catch (error) {
        console.error('Error calculating NEC:', error);
        alert('Error calculating NEC. Please try again.');
    }
}

// Material functions
function loadMaterials() {
    fetch('/api/materials')
        .then(response => response.json())
        .then(data => {
            const materialsList = document.getElementById('materialsList');
            if (materialsList) {
                materialsList.innerHTML = '';

                data.forEach(material => {
                    const item = document.createElement('div');
                    item.className = 'material-item';
                    item.innerHTML = `
                        <span class="material-name">${material.description}</span>
                        <span class="material-price">$${material.unit_price}</span>
                    `;
                    materialsList.appendChild(item);
                });

                materialsList.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error loading materials:', error);
        });
}

async function searchMaterials() {
    const query = document.getElementById('mq').value;

    if (!query) {
        alert('Please enter a search query.');
        return;
    }

    try {
        const response = await fetch('/api/price-search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query
            })
        });

        const data = await response.json();
        const output = document.getElementById('matout');
        output.textContent = JSON.stringify(data, null, 2);
        output.style.display = 'block';

        // Hide materials list when showing search results
        const materialsList = document.getElementById('materialsList');
        if (materialsList) {
            materialsList.style.display = 'none';
        }
    } catch (error) {
        console.error('Error searching materials:', error);
        alert('Error searching materials. Please try again.');
    }
}

// Labor rate functions
async function compareLaborRates() {
    const state = document.getElementById('state').value;

    if (!state) {
        alert('Please enter a state.');
        return;
    }

    try {
        const response = await fetch('/api/labor-compare', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                state: state
            })
        });

        const data = await response.json();
        const output = document.getElementById('laborout');
        output.textContent = JSON.stringify(data, null, 2);
        output.style.display = 'block';
    } catch (error) {
        console.error('Error comparing labor rates:', error);
        alert('Error comparing labor rates. Please try again.');
    }
}

// Estimate functions
async function saveEstimate() {
    const title = document.getElementById('title').value;
    const description = document.getElementById('desc').value;

    if (!title || !description) {
        alert('Please enter both title and description.');
        return;
    }

    try {
        const response = await fetch('/api/estimate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title: title,
                desc: description
            })
        });

        const data = await response.json();
        const output = document.getElementById('estout');
        output.textContent = JSON.stringify(data, null, 2);
        output.style.display = 'block';
    } catch (error) {
        console.error('Error saving estimate:', error);
        alert('Error saving estimate. Please try again.');
    }
}

// Blueprint upload
async function uploadBlueprint() {
    const fileInput = document.getElementById('blueprintFile');
    const file = fileInput.files[0];

    if (!file) {
        alert('Please select a file to upload.');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        const statusDiv = document.getElementById('blueprintStatus');

        if (response.ok) {
            statusDiv.textContent = `File uploaded successfully: ${data.filename}`;
            statusDiv.style.display = 'block';
        } else {
            statusDiv.textContent = `Error: ${data.error || 'Unknown error'}`;
            statusDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('Error uploading file:', error);
        alert('Error uploading file. Please try again.');
    }
}

function clearBlueprint() {
    document.getElementById('blueprintFile').value = '';
    document.getElementById('blueprintStatus').style.display = 'none';
}
