// lib/firebase.js — only initializes when Firebase is configured
import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

const hasFirebaseConfig = !!(
  process.env.NEXT_PUBLIC_FIREBASE_API_KEY &&
  process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID
);

let app = null;
let _auth = null;
let _googleProvider = null;

if (hasFirebaseConfig) {
  const firebaseConfig = {
    apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
    authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
    storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
    appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
    measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID,
  };
  app = initializeApp(firebaseConfig);
  _auth = getAuth(app);
  _googleProvider = new GoogleAuthProvider();
}

export const auth = _auth;
export const googleProvider = _googleProvider;
export const isFirebaseConfigured = hasFirebaseConfig;