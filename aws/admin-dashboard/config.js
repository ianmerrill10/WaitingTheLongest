/**
 * Animal Rescue Admin Dashboard - Configuration
 *
 * IMPORTANT: Update these values after deploying AWS infrastructure
 */

const CONFIG = {
    // AWS Cognito Configuration (Update after deployment)
    COGNITO: {
        REGION: 'us-east-1',
        USER_POOL_ID: 'YOUR_USER_POOL_ID',
        CLIENT_ID: 'YOUR_CLIENT_ID',
        DOMAIN: 'your-domain.auth.us-east-1.amazoncognito.com'
    },

    // Google OAuth Configuration (Get from Google Cloud Console)
    GOOGLE: {
        CLIENT_ID: 'YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com'
    },

    // API Gateway Configuration (Update after deployment)
    API: {
        BASE_URL: 'https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod',
        ENDPOINTS: {
            STATS: '/admin/stats',
            STATES: '/admin/states',
            SHELTERS: '/admin/shelters'
        }
    },

    // App Settings
    APP: {
        PAGE_SIZE: 25,
        TOAST_DURATION: 3000
    }
};

// OAuth URLs (constructed from config)
CONFIG.AUTH = {
    LOGIN_URL: `https://${CONFIG.COGNITO.DOMAIN}/oauth2/authorize?` +
        `client_id=${CONFIG.COGNITO.CLIENT_ID}&` +
        `response_type=token&` +
        `scope=openid+email+profile&` +
        `redirect_uri=${encodeURIComponent(window.location.origin + window.location.pathname)}`,

    LOGOUT_URL: `https://${CONFIG.COGNITO.DOMAIN}/logout?` +
        `client_id=${CONFIG.COGNITO.CLIENT_ID}&` +
        `logout_uri=${encodeURIComponent(window.location.origin + window.location.pathname)}`
};
