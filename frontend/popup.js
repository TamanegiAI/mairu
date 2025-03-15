// API Base URL
const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
const authButton = document.getElementById('auth-button');
const logoutButton = document.getElementById('logout-button');
const authStatus = document.getElementById('auth-status');
const mainContent = document.getElementById('main-content');
const sheetSelect = document.getElementById('sheet-select');
const loadSheetsBtn = document.getElementById('load-sheets-btn');
const templateIdInput = document.getElementById('template-id');
const loadColumnsBtn = document.getElementById('load-columns-btn');
const mappingContainer = document.getElementById('mapping-container');
const rowIndexInput = document.getElementById('row-index');
const emailToInput = document.getElementById('email-to');
const emailCcInput = document.getElementById('email-cc');
const emailSubjectInput = document.getElementById('email-subject');
const emailBodyInput = document.getElementById('email-body');
const generateDocBtn = document.getElementById('generate-doc-btn');
const sendEmailBtn = document.getElementById('send-email-btn');
const scheduleDatetimeInput = document.getElementById('schedule-datetime');
const scheduleEmailBtn = document.getElementById('schedule-email-btn');
const statusMessage = document.getElementById('status-message');
const loadingIndicator = document.getElementById('loading-indicator');
const progressBar = document.getElementById('progress-bar');

// State variables
let isAuthenticated = false;
let columns = [];
let generatedDocId = null;
let cachedSheets = [];

// API Helper
class APIHelper {
    static async makeAuthenticatedRequest(endpoint, options = {}) {
        try {
            // Check token validity
            const tokenCheck = await new Promise((resolve) => {
                chrome.runtime.sendMessage({ type: 'CHECK_TOKEN' }, resolve);
            });

            if (!tokenCheck || !tokenCheck.isValid) {
                throw new Error('No valid token available');
            }

            // Add authorization header
            const headers = {
                ...options.headers,
                'Authorization': `Bearer ${tokenCheck.token}`
            };

            // Make the request
            const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                ...options,
                headers
            });

            if (response.status === 401) {
                // Token might be invalid, clear auth and show login
                await new Promise((resolve) => {
                    chrome.runtime.sendMessage({ type: 'CLEAR_AUTH' }, resolve);
                });
                showUnauthenticatedUI();
                throw new Error('Authentication required');
            }

            if (!response.ok) {
                throw new Error(`API request failed: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            showStatus(error.message, 'error');
            throw error;
        }
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', initializeApp);
authButton.addEventListener('click', authenticate);
logoutButton.addEventListener('click', logout);
loadSheetsBtn.addEventListener('click', loadSheets);
loadColumnsBtn.addEventListener('click', loadColumns);
generateDocBtn.addEventListener('click', generateDocument);
sendEmailBtn.addEventListener('click', confirmSendEmail);
scheduleEmailBtn.addEventListener('click', scheduleEmail);
sheetSelect.addEventListener('change', handleSheetChange);

// Initialize the app
async function initializeApp() {
    console.log('Initializing app...');
    
    try {
        // Check token validity
        const tokenCheck = await new Promise((resolve) => {
            chrome.runtime.sendMessage({ type: 'CHECK_TOKEN' }, resolve);
        });

        if (tokenCheck && tokenCheck.isValid) {
            console.log('Valid token found');
            isAuthenticated = true;
            showAuthenticatedUI();
            await loadSheets();
        } else {
            console.log('No valid token found');
            showUnauthenticatedUI();
        }
    } catch (error) {
        console.error('Initialization error:', error);
        showUnauthenticatedUI();
    }

    // Listen for auth status updates
    chrome.runtime.onMessage.addListener((message) => {
        console.log('Received message:', message);
        if (message.type === 'AUTH_SUCCESS') {
            console.log('Auth success message received');
            isAuthenticated = true;
            showAuthenticatedUI();
            loadSheets();
        } else if (message.type === 'AUTH_ERROR') {
            showStatus('Authentication failed: ' + message.error, 'error');
            showUnauthenticatedUI();
        }
    });
}

// Authenticate with Google
async function authenticate() {
    try {
        showStatus('Starting authentication...', 'info');
        
        const response = await fetch(`${API_BASE_URL}/auth/url`);
        const data = await response.json();
        
        // Send message to background script to open auth URL
        chrome.runtime.sendMessage({ 
            type: 'START_AUTH',
            authUrl: data.authorization_url
        });
        
        showStatus('Please complete authentication in the opened tab...', 'info');
    } catch (error) {
        console.error('Authentication error:', error);
        showStatus('Failed to start authentication process.', 'error');
    }
}

// Logout function
async function logout() {
    try {
        await new Promise((resolve) => {
            chrome.runtime.sendMessage({ type: 'CLEAR_AUTH' }, resolve);
        });
        showUnauthenticatedUI();
        showStatus('Logged out successfully.', 'success');
    } catch (error) {
        console.error('Logout error:', error);
        showStatus('Failed to log out.', 'error');
    }
}

// Load Google Sheets
async function loadSheets() {
    if (cachedSheets.length > 0) {
        updateSheetSelect(cachedSheets);
        return;
    }

    try {
        showStatus('Loading sheets...', 'info');
        showLoadingIndicator(true);
        
        const sheets = await APIHelper.makeAuthenticatedRequest('/sheets');
        cachedSheets = sheets;
        updateSheetSelect(sheets);
        
        showStatus('Sheets loaded successfully.', 'success');
    } catch (error) {
        console.error('Error loading sheets:', error);
        if (error.message === 'Authentication required') {
            showUnauthenticatedUI();
        }
    } finally {
        showLoadingIndicator(false);
    }
}

// Update sheet select dropdown
function updateSheetSelect(sheets) {
    // Clear existing options
    sheetSelect.innerHTML = '<option value="">Select a Google Sheet</option>';
    
    // Add new options
    sheets.forEach(sheet => {
        const option = document.createElement('option');
        option.value = sheet.id;
        option.textContent = sheet.name;
        sheetSelect.appendChild(option);
    });
}

// Handle sheet selection change
function handleSheetChange() {
  // Clear existing mappings
  mappingContainer.innerHTML = '';
  columns = [];
}

// Load columns from selected sheet
async function loadColumns() {
  const sheetId = sheetSelect.value;
  
  if (!sheetId) {
    showStatus('Please select a sheet first.', 'error');
    return;
  }
  
  try {
    showStatus('Loading columns...', 'info');
    
    const response = await fetch(`${API_BASE_URL}/columns/${sheetId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to load columns: ${response.statusText}`);
    }
    
    columns = await response.json();
    
    // Clear existing mappings
    mappingContainer.innerHTML = '';
    
    // Create mapping fields
    columns.forEach(column => {
      const mappingItem = document.createElement('div');
      mappingItem.className = 'mapping-item';
      
      const placeholderInput = document.createElement('input');
      placeholderInput.type = 'text';
      placeholderInput.className = 'text-input';
      placeholderInput.placeholder = 'Placeholder (e.g., {{name}})';
      placeholderInput.dataset.columnIndex = column.index;
      
      const columnNameSpan = document.createElement('span');
      columnNameSpan.textContent = column.name;
      
      mappingItem.appendChild(placeholderInput);
      mappingItem.appendChild(columnNameSpan);
      
      mappingContainer.appendChild(mappingItem);
    });
    
    showStatus('Columns loaded successfully.', 'success');
  } catch (error) {
    console.error('Error loading columns:', error);
    showStatus(`Error loading columns: ${error.message}`, 'error');
  }
}

// Generate document from template
async function generateDocument() {
  const sheetId = sheetSelect.value;
  const templateId = templateIdInput.value;
  const rowIndex = parseInt(rowIndexInput.value);
  
  if (!sheetId || !templateId) {
    showStatus('Please select a sheet and enter a template ID.', 'error');
    return;
  }
  
  // Get mappings
  const mappings = {};
  const mappingItems = mappingContainer.querySelectorAll('.mapping-item');
  
  mappingItems.forEach(item => {
    const placeholderInput = item.querySelector('input');
    const placeholder = placeholderInput.value;
    const columnIndex = placeholderInput.dataset.columnIndex;
    
    if (placeholder) {
      const column = columns.find(col => col.index === parseInt(columnIndex));
      if (column) {
        mappings[placeholder] = column.name;
      }
    }
  });
  
  try {
    // First, save the column mappings
    await fetch(`${API_BASE_URL}/map_columns`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        sheet_id: sheetId,
        template_id: templateId,
        mappings: mappings
      })
    });
    
    // Then generate the document
    showStatus('Generating document...', 'info');
    showLoadingIndicator(true);
    
    const response = await fetch(`${API_BASE_URL}/generate_document`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        sheet_id: sheetId,
        template_id: templateId,
        row_index: rowIndex
      })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to generate document: ${response.statusText}`);
    }
    
    const result = await response.json();
    generatedDocId = result.document_id;
    
    showStatus(`Document generated successfully! ID: ${generatedDocId}`, 'success');
    
    // Enable email buttons
    sendEmailBtn.disabled = false;
    scheduleEmailBtn.disabled = false;
  } catch (error) {
    console.error('Error generating document:', error);
    showStatus(`Error generating document: ${error.message}`, 'error');
  } finally {
    showLoadingIndicator(false);
  }
}

// Confirm sending email
function confirmSendEmail() {
    const confirmation = confirm('Are you sure you want to send this email?');
    if (confirmation) {
        sendEmail();
    }
}

// Send email with generated document
async function sendEmail() {
  if (!generatedDocId) {
    showStatus('Please generate a document first.', 'error');
    return;
  }
  
  const to = emailToInput.value;
  const cc = emailCcInput.value;
  const subject = emailSubjectInput.value;
  const body = emailBodyInput.value;
  
  if (!to || !subject) {
    showStatus('Please enter recipient email and subject.', 'error');
    return;
  }
  
  try {
    showStatus('Sending email...', 'info');
    showLoadingIndicator(true);
    
    const response = await fetch(`${API_BASE_URL}/send_email`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        to: to,
        cc: cc,
        subject: subject,
        body: body,
        document_id: generatedDocId
      })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to send email: ${response.statusText}`);
    }
    
    const result = await response.json();
    
    showStatus('Email sent successfully!', 'success');
  } catch (error) {
    console.error('Error sending email:', error);
    showStatus(`Error sending email: ${error.message}`, 'error');
  } finally {
    showLoadingIndicator(false);
  }
}

// Schedule email for later
async function scheduleEmail() {
  if (!generatedDocId) {
    showStatus('Please generate a document first.', 'error');
    return;
  }
  
  const to = emailToInput.value;
  const cc = emailCcInput.value;
  const subject = emailSubjectInput.value;
  const body = emailBodyInput.value;
  const scheduledTime = scheduleDatetimeInput.value;
  
  if (!to || !subject || !scheduledTime) {
    showStatus('Please enter recipient email, subject, and scheduled time.', 'error');
    return;
  }
  
  try {
    showStatus('Scheduling email...', 'info');
    showLoadingIndicator(true);
    
    const response = await fetch(`${API_BASE_URL}/schedule_email`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        to: to,
        cc: cc,
        subject: subject,
        body: body,
        document_id: generatedDocId,
        scheduled_time: new Date(scheduledTime).toISOString()
      })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to schedule email: ${response.statusText}`);
    }
    
    const result = await response.json();
    
    showStatus(`Email scheduled successfully for ${new Date(scheduledTime).toLocaleString()}!`, 'success');
  } catch (error) {
    console.error('Error scheduling email:', error);
    showStatus(`Error scheduling email: ${error.message}`, 'error');
  } finally {
    showLoadingIndicator(false);
  }
}

// UI Helper Functions
function showAuthenticatedUI() {
    console.log('Showing authenticated UI');
    authButton.style.display = 'none';
    logoutButton.style.display = 'block';
    authStatus.textContent = 'Authenticated';
    authStatus.className = 'status success';
    mainContent.classList.remove('hidden');
}

function showUnauthenticatedUI() {
    console.log('Showing unauthenticated UI');
    authButton.style.display = 'block';
    logoutButton.style.display = 'none';
    authStatus.textContent = 'Not authenticated';
    authStatus.className = 'status error';
    mainContent.classList.add('hidden');
}

function showStatus(message, type) {
    statusMessage.textContent = message;
    statusMessage.className = `status ${type}`;
}

function showLoadingIndicator(isLoading) {
    loadingIndicator.style.display = isLoading ? 'block' : 'none';
    progressBar.style.width = isLoading ? '100%' : '0%';
}