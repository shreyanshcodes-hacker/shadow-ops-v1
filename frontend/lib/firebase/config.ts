/**
 * Firebase Client Configuration
 * Extracts safe public NEXT_PUBLIC_* variables for Firebase Web SDK initialization.
 */

export const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || "AIzaSyBEZHLrLGRMxkFL48yD7LOWxUaCg4dyRcY",
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || "shadow-ops-6957d.firebaseapp.com",
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "shadow-ops-6957d",
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || "shadow-ops-6957d.firebasestorage.app",
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "96713617472",
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || "1:96713617472:web:9d4db960807aa3e3cbafa5",
};

export const isFirebaseConfigured = Boolean(
  firebaseConfig.apiKey &&
  firebaseConfig.projectId &&
  firebaseConfig.apiKey !== "dummy-api-key"
);
