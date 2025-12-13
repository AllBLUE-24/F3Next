// lib/firebase.js
import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

const firebaseConfig = {
  // 🔴 HARDCODE THESE VALUES DIRECTLY (No process.env)
  apiKey: "AIzaSyDPpx0TS0bFYGG_T63LDYOlokAXvT524Eg",
  authDomain: "f3next-24.firebaseapp.com", // 👈 This fixes your specific error
  projectId: "f3next-24",
  storageBucket: "f3next-24.firebasestorage.app",
  messagingSenderId: "389878630116",
  appId: "1:389878630116:web:850f506eb895b732680ef1",
  measurementId: "G-2GQ86H9NJQ",
};
// Initialize Firebase
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();