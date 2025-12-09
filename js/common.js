// common.js (trimmed to key parts; other helpers as you already have)

const API = {
  async post(action, data = {}) {
    try {
      showLoading(true);

      const payload = {
        action,
        ...data
      };

      // Important: no headers, no mode => simple request (no CORS preflight)[web:90][web:102]
      const response = await fetch(CONFIG.API_URL, {
        method: 'POST',
        body: JSON.stringify(payload),
        redirect: 'follow'
      });

      const text = await response.text();
      let result;
      try {
        result = JSON.parse(text);
      } catch (e) {
        console.error('JSON parse error:', text);
        throw new Error('Invalid response from server');
      }

      showLoading(false);
      return result;
    } catch (error) {
      showLoading(false);
      console.error('API Error:', error);
      showError('Connection error: ' + error.message);
      return { success: false, error: error.message };
    }
  },

  async getStatus() {
    try {
      const response = await fetch(CONFIG.API_URL);
      const text = await response.text();
      return JSON.parse(text);
    } catch (error) {
      console.error('API Status Error:', error);
      return { success: false, error: error.message };
    }
  }
};

// keep the rest of the common.js exactly as previously provided (navigation, toasts, etc.)
console.log('✅ Common.js loaded successfully');
