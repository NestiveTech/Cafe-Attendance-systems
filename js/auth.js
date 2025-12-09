// auth.js

const SESSION_KEY = 'cafeterrain_session';
const SESSION_EXPIRY = 24 * 60 * 60 * 1000;

async function login(email, password) {
  try {
    if (!email || !password) {
      showError('Email and password are required');
      return { success: false, error: 'Email and password are required' };
    }

    if (!isValidEmail(email)) {
      showError('Invalid email format');
      return { success: false, error: 'Invalid email format' };
    }

    const result = await API.post('login', { email, password });

    if (result.success && result.user) {
      saveSession(result.user);
      showSuccess('Login successful');
      console.log('✅ Login successful:', email);
      return result;
    }

    showError(result.error || 'Login failed');
    return result;
  } catch (error) {
    console.error('Login Error:', error);
    showError('Login failed: ' + error.message);
    return { success: false, error: 'Login failed: ' + error.message };
  }
}

// rest of auth.js exactly as earlier (register, changeUserPassword, session helpers, guards, etc.)
console.log('✅ Auth.js loaded successfully');
