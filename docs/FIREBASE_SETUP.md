# Firebase Google Sign-In setup

The Google button is already integrated in the frontend and API. Complete these steps to enable it.

1. Go to the [Firebase console](https://console.firebase.google.com/) and create a project.
2. In **Project overview**, add a **Web** app. Copy its Firebase configuration values.
3. In **Authentication → Sign-in method**, enable **Google**, select a support email, and save.
4. Create `frontend/.env` from `frontend/.env.example` and enter:

   ```env
   VITE_FIREBASE_API_KEY=...
   VITE_FIREBASE_AUTH_DOMAIN=...
   VITE_FIREBASE_PROJECT_ID=...
   VITE_FIREBASE_APP_ID=...
   ```

5. In Firebase **Project settings → Service accounts**, generate a new private key. Save the JSON file at `backend/secrets/firebase-service-account.json`. Do not commit or share this file.
6. Add these values to the existing root `.env`:

   ```env
   FIREBASE_PROJECT_ID=your-firebase-project-id
   FIREBASE_SERVICE_ACCOUNT_PATH=backend/secrets/firebase-service-account.json
   ```

7. Install the new backend dependency: `cd backend` then `python -m pip install -r requirements.txt`.
8. Install the updated frontend dependency: `cd frontend` then `npm install`.
9. Restart both servers. Google Sign-In creates or finds the app user through Firebase, then issues this application’s JWT session.

## Local phone testing

The website itself can be opened over local Wi-Fi using its IP address. Google web authentication may require an authorized HTTPS domain; browser security and Firebase’s authorized-domain rules can reject a plain local-network IP. Test Google Sign-In on `localhost` first. For phone Google authentication, use a secure development URL or the Firebase Auth Emulator before deployment.
