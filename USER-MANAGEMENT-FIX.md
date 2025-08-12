# User Management Setup Fix

## Issues Resolved

### 1. **No Redirect to Setup Page on Fresh Install**
- **Problem**: Users were taken directly to dashboard instead of admin setup
- **Solution**: Added `AuthCheck` component that checks if setup is required on app load
- **Location**: `/src/components/auth-check.tsx`

### 2. **"Not Found" Error During Admin Creation**
- **Problem**: API endpoint mismatch between frontend and backend
- **Frontend was calling**: `/api/auth/setup-admin`
- **Backend endpoint was**: `/api/auth/setup`
- **Solution**: Updated frontend to use correct endpoint `/api/auth/setup`
- **Location**: `/src/app/setup/page.tsx`

### 3. **Improper Response from Setup Endpoint**
- **Problem**: Backend was returning simple message instead of User object
- **Solution**: Updated backend to return proper User model after creation
- **Location**: `/backend/server.py` line 375

## Files Modified

1. **`/src/components/auth-check.tsx`** (NEW)
   - Client-side authentication and setup check
   - Redirects to `/setup` if no admin exists
   - Redirects to `/login` if not authenticated
   - Shows loading state during checks

2. **`/src/app/layout.tsx`**
   - Added AuthCheck wrapper to ensure auth state is checked
   - Wraps all pages with authentication logic

3. **`/src/app/setup/page.tsx`**
   - Fixed API endpoint from `/api/auth/setup-admin` to `/api/auth/setup`
   - Properly handles the setup flow

4. **`/backend/server.py`**
   - Updated `/api/auth/setup` endpoint to return User model
   - Ensures proper response format for frontend

## How It Works Now

### First-Time Setup Flow:
1. User visits app for the first time
2. `AuthCheck` component loads and checks `/api/auth/setup-required`
3. If no admin exists, user is redirected to `/setup`
4. User fills in admin account details
5. Form submits to `/api/auth/setup`
6. Backend creates admin user and returns User object
7. User is redirected to `/login?setup=complete`
8. User can now login with created credentials

### Subsequent Visits:
1. User visits app
2. `AuthCheck` component verifies setup is complete
3. Checks for authentication token
4. If no token, redirects to `/login`
5. If token exists, validates it with `/api/auth/me`
6. If valid, allows access to dashboard
7. If invalid, clears token and redirects to `/login`

## Testing Instructions

### Test Fresh Install:
```bash
# 1. Delete the database to simulate fresh install
rm data/kasa_monitor.db

# 2. Start the application
docker-compose up -d
# OR
python backend/server.py & npm run dev

# 3. Visit http://localhost:3000
# You should be redirected to /setup
```

### Test Admin Creation:
1. Fill in the setup form with:
   - Full Name: Test Admin
   - Username: admin
   - Email: admin@example.com
   - Password: password123
   - Confirm Password: password123

2. Click "Create Administrator Account"
3. Should redirect to login page
4. Login with created credentials
5. Should access dashboard successfully

## API Endpoints

### Setup Check:
- **GET** `/api/auth/setup-required`
- Returns: `{ "setup_required": true/false }`

### Admin Creation:
- **POST** `/api/auth/setup`
- Body: `{ username, email, full_name, password }`
- Returns: User object with admin role

### Authentication Check:
- **GET** `/api/auth/me`
- Headers: `Authorization: Bearer <token>`
- Returns: Current user object

## Security Considerations

1. **Setup Lock**: Once an admin is created, `/api/auth/setup` returns 400 error
2. **Token Validation**: All requests validate JWT tokens
3. **Client Storage**: Tokens stored in localStorage (consider httpOnly cookies for production)
4. **Password Requirements**: Minimum 8 characters enforced
5. **Role Assignment**: First user is automatically admin with full permissions

## Known Limitations

1. **Client-Side Routing**: Auth checks happen client-side, not server-side
2. **Token Storage**: Using localStorage instead of httpOnly cookies
3. **No Rate Limiting**: Setup endpoint has no rate limiting

## Future Improvements

1. Add server-side middleware for better security
2. Implement httpOnly cookie storage for tokens
3. Add rate limiting to prevent brute force
4. Add email verification for admin account
5. Implement password strength requirements
6. Add audit logging for admin creation