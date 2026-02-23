// Debug utility to test authentication flow
export const debugAuth = {
  // Test if backend is reachable
  testBackendConnection: async () => {
    try {
      const response = await fetch('/api/v1/health', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      console.log('🏥 Backend health check:', response.status, response.statusText);

      if (response.ok) {
        const data = await response.text();
        console.log('✅ Backend is reachable:', data);
        return true;
      } else {
        console.error('❌ Backend health check failed:', response.status);
        return false;
      }
    } catch (error) {
      console.error('❌ Backend connection failed:', error);
      return false;
    }
  },

  // Test login endpoint specifically
  testLoginEndpoint: async (email: string, password: string) => {
    try {
      console.log('🔐 Testing login with:', { email, password: '***' });

      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });

      console.log('📡 Login response status:', response.status, response.statusText);
      console.log('📡 Login response headers:', Object.fromEntries(response.headers.entries()));

      const responseText = await response.text();
      console.log('📡 Login response body:', responseText);

      if (response.ok) {
        try {
          const data = JSON.parse(responseText);
          console.log('✅ Login successful:', data);
          return { success: true, data };
        } catch (e) {
          console.log('✅ Login successful (no JSON):', responseText);
          return { success: true, data: responseText };
        }
      } else {
        try {
          const error = JSON.parse(responseText);
          console.error('❌ Login failed:', error);
          return { success: false, error };
        } catch (e) {
          console.error('❌ Login failed:', responseText);
          return { success: false, error: responseText };
        }
      }
    } catch (error) {
      console.error('❌ Login request failed:', error);
      return { success: false, error: error instanceof Error ? error.message : String(error) };
    }
  },

  // Check current environment
  checkEnvironment: () => {
    console.log('🌍 Environment check:');
    console.log('- API_BASE_URL:', import.meta.env.VITE_API_BASE_URL);
    console.log('- BYPASS_AUTH:', import.meta.env.VITE_BYPASS_AUTH);
    console.log('- ENVIRONMENT:', import.meta.env.VITE_ENVIRONMENT);
    console.log('- Current URL:', window.location.href);
    console.log('- Local Storage tokens:', {
      access_token: localStorage.getItem('access_token')?.substring(0, 20) + '...',
      user: localStorage.getItem('user'),
    });
  },
};

// Auto-run environment check in development
if (import.meta.env.DEV) {
  debugAuth.checkEnvironment();
}