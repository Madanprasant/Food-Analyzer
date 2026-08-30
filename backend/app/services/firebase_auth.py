from __future__ import annotations

from app.core.config import Settings


class FirebaseConfigurationError(RuntimeError):
    pass


class FirebaseAuthService:
    """Verifies Firebase ID tokens before issuing this API's own session token."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def verify_google_id_token(self, id_token: str) -> dict:
        if not self.settings.firebase_project_id or not self.settings.firebase_service_account_path:
            raise FirebaseConfigurationError("Google Sign-In is not configured. Add Firebase project and service-account settings first.")
        if not self.settings.firebase_service_account_path.is_file():
            raise FirebaseConfigurationError("FIREBASE_SERVICE_ACCOUNT_PATH does not point to a readable JSON file.")
        try:
            import firebase_admin
            from firebase_admin import auth, credentials
        except ImportError as error:
            raise FirebaseConfigurationError("Firebase Admin dependency is missing. Install backend requirements.") from error
        try:
            try:
                firebase_admin.get_app()
            except ValueError:
                firebase_admin.initialize_app(credentials.Certificate(str(self.settings.firebase_service_account_path)), {"projectId": self.settings.firebase_project_id})
            claims = auth.verify_id_token(id_token)
        except Exception as error:
            raise FirebaseConfigurationError("Google identity token could not be verified.") from error
        if not claims.get("email") or not claims.get("uid"):
            raise FirebaseConfigurationError("Google account did not provide a usable email identity.")
        return claims
