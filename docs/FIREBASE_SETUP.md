# ShadowOps — Firebase Setup Guide

ShadowOps utilizes **Firebase Authentication** as its primary identity and session authority. This guide documents how to create, configure, and connect your Firebase project.

---

## 1. Firebase Project Creation

1. Navigate to the [Firebase Console](https://console.firebase.google.com/).
2. Click **Add Project** and name it `shadow-ops` (or your company slug).
3. Disable Google Analytics (optional, not required for ShadowOps).
4. Click **Create Project**.

---

## 2. Enable Authentication Providers

1. In the Firebase Console left sidebar, click **Build** → **Authentication**.
2. Click **Get Started**.
3. Under the **Sign-in method** tab, enable:
   - **Email/Password**: Toggle "Enable". Keep "Email link (passwordless sign-in)" disabled.
   - **Google** (Optional): Configure project support email.
   - **GitHub** (Optional): Provide GitHub OAuth Client ID and Secret.

---

## 3. Configure Authorized Domains

Under **Authentication** → **Settings** → **Authorized domains**, add:
- `localhost` (Default for local development)
- `127.0.0.1`
- Your production custom domain or Railway frontend domain (e.g., `shadowops.up.railway.app`)

---

## 4. Email Verification & Password Reset Templates

1. Under **Authentication** → **Templates**:
   - Customize **Email address verification**: Set your application name to `ShadowOps` and configure the reply-to address.
   - Customize **Password reset**: Set the action URL to redirect users back to `https://[YOUR_DOMAIN]/reset-password`.

---

## 5. Web App Configuration (Frontend Variables)

1. Go to **Project Settings** (gear icon) → **General**.
2. Under "Your apps", click the **Web icon (`</>`)**.
3. Register app with nickname `shadowops-web`.
4. Copy the `firebaseConfig` object values into your `frontend/.env.local` or root `.env`:
   ```bash
   NEXT_PUBLIC_FIREBASE_API_KEY="AIzaSy..."
   NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN="shadow-ops-xxxx.firebaseapp.com"
   NEXT_PUBLIC_FIREBASE_PROJECT_ID="shadow-ops-xxxx"
   NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET="shadow-ops-xxxx.appspot.com"
   NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID="123456789012"
   NEXT_PUBLIC_FIREBASE_APP_ID="1:123456789012:web:abcdef123456"
   ```

---

## 6. Service Account Generation (Backend Variables)

1. In **Project Settings**, switch to the **Service accounts** tab.
2. Ensure **Firebase Admin SDK** is selected with "Python".
3. Click **Generate new private key** and confirm.
4. Save the downloaded JSON securely.
5. Extract the following fields into your backend environment:
   ```bash
   FIREBASE_PROJECT_ID="shadow-ops-xxxx"
   FIREBASE_CLIENT_EMAIL="firebase-adminsdk-xxxxx@shadow-ops-xxxx.iam.gserviceaccount.com"
   FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   ```
   > [!CAUTION]
   > **NEVER** expose `FIREBASE_PRIVATE_KEY` or `FIREBASE_CLIENT_EMAIL` to the frontend or git repositories.
