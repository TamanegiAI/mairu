// Constants
const API_BASE_URL = 'http://localhost:8000';
const TOKEN_CHECK_INTERVAL = 5 * 60 * 1000; // 5 minutes

// State management
let authTabId = null;
let authInProgress = false;
let tokenCheckTimer = null;
let processedCodes = new Set(); // Track processed auth codes

// Token management
class TokenManager {
    static async getStoredTokens() {
        return new Promise((resolve) => {
            chrome.storage.local.get(['accessToken', 'refreshToken', 'expiry'], (result) => {
                resolve({
                    accessToken: result.accessToken,
                    refreshToken: result.refreshToken,
                    expiry: result.expiry ? new Date(result.expiry) : null
                });
            });
        });
    }

    static async storeTokens(accessToken, refreshToken, expiry) {
        return new Promise((resolve) => {
            chrome.storage.local.set({
                accessToken,
                refreshToken,
                expiry: expiry ? expiry.toISOString() : null,
                lastUpdated: new Date().toISOString()
            }, resolve);
        });
    }

    static async clearTokens() {
        return new Promise((resolve) => {
            chrome.storage.local.remove(['accessToken', 'refreshToken', 'expiry', 'lastUpdated'], resolve);
        });
    }

    static isTokenExpired(expiry) {
        if (!expiry) return true;
        const expiryDate = new Date(expiry);
        const now = new Date();
        // Consider token expired 5 minutes before actual expiry
        return expiryDate.getTime() - now.getTime() < 5 * 60 * 1000;
    }

    static async refreshToken(refreshToken) {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    refresh_token: refreshToken,
                    token_uri: 'https://oauth2.googleapis.com/token',
                    client_id: chrome.runtime.getManifest().oauth2.client_id,
                    scopes: chrome.runtime.getManifest().oauth2.scopes
                })
            });

            if (!response.ok) {
                throw new Error('Token refresh failed');
            }

            const data = await response.json();
            await this.storeTokens(
                data.token,
                data.refresh_token,
                new Date(data.expiry)
            );
            return data.token;
        } catch (error) {
            console.error('Token refresh failed:', error);
            await this.clearTokens();
            throw error;
        }
    }

    static async validateAndRefreshToken() {
        const tokens = await this.getStoredTokens();
        if (!tokens.accessToken) return null;

        if (this.isTokenExpired(tokens.expiry)) {
            if (!tokens.refreshToken) {
                await this.clearTokens();
                return null;
            }

            try {
                return await this.refreshToken(tokens.refreshToken);
            } catch (error) {
                return null;
            }
        }

        return tokens.accessToken;
    }
}

// Authentication handling
async function handleAuthCallback(url) {
    try {
        const urlObj = new URL(url);
        const code = urlObj.searchParams.get('code');
        
        if (!code) {
            throw new Error('No authorization code found');
        }

        // Check if this code has already been processed
        if (processedCodes.has(code)) {
            console.log('Auth code already processed, ignoring duplicate');
            return;
        }

        // Add code to processed set
        processedCodes.add(code);

        // Clean up old codes (keep only last 10)
        if (processedCodes.size > 10) {
            const codesArray = Array.from(processedCodes);
            processedCodes = new Set(codesArray.slice(-10));
        }

        const response = await fetch(`${API_BASE_URL}/auth/callback?code=${code}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `Auth callback failed: ${response.statusText}`);
        }

        const data = await response.json();
        await TokenManager.storeTokens(
            data.access_token,
            data.refresh_token,
            new Date(Date.now() + 3600 * 1000) // Default 1 hour expiry
        );

        // Notify popup of successful authentication
        chrome.runtime.sendMessage({
            type: 'AUTH_SUCCESS',
            token: data.access_token
        }).catch(() => {
            console.log('Popup not available to receive auth success message');
        });

        startTokenCheck();
    } catch (error) {
        console.error('Auth callback error:', error);
        chrome.runtime.sendMessage({
            type: 'AUTH_ERROR',
            error: error.message
        }).catch(() => {
            console.log('Popup not available to receive auth error message');
        });
    } finally {
        authInProgress = false;
    }
}

// Token check interval
function startTokenCheck() {
    if (tokenCheckTimer) {
        clearInterval(tokenCheckTimer);
    }
    
    tokenCheckTimer = setInterval(async () => {
        await TokenManager.validateAndRefreshToken();
    }, TOKEN_CHECK_INTERVAL);
}

// Event Listeners
chrome.runtime.onInstalled.addListener(() => {
    console.log('Extension installed');
    startTokenCheck();
    processedCodes.clear(); // Clear processed codes on install
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (tabId === authTabId && changeInfo.url && changeInfo.url.includes('localhost:8000/auth/callback')) {
        console.log('Auth callback detected');
        
        // Process the callback before closing the tab
        handleAuthCallback(changeInfo.url).then(() => {
            // Close the auth tab after processing
            chrome.tabs.remove(tabId);
            authTabId = null;
        });
    }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'START_AUTH') {
        if (authInProgress) {
            console.log('Auth already in progress');
            return;
        }

        authInProgress = true;
        chrome.tabs.create({ url: message.authUrl }, (tab) => {
            authTabId = tab.id;
            console.log('Created auth tab:', authTabId);
        });
    }

    if (message.type === 'CHECK_TOKEN') {
        TokenManager.validateAndRefreshToken()
            .then(token => {
                sendResponse({ isValid: !!token, token });
            });
        return true; // Required for async response
    }

    if (message.type === 'CLEAR_AUTH') {
        TokenManager.clearTokens()
            .then(() => {
                sendResponse({ success: true });
            });
        return true;
    }
}); 