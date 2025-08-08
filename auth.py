import bcrypt
from database import AttendanceDatabase
from typing import Optional

class AuthManager:
    def __init__(self, db: AttendanceDatabase):
        """Initialize the authentication manager with database connection."""
        self.db = db
        self.default_password = "1122"
        self._ensure_default_password()
    
    def _ensure_default_password(self):
        """Ensure the default password is set in the database."""
        stored_password_hash = self.db.get_setting("admin_password_hash")
        if not stored_password_hash:
            # Set default password hash
            default_hash = self.hash_password(self.default_password)
            self.db.set_setting("admin_password_hash", default_hash)
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception as e:
            print(f"Error verifying password: {e}")
            return False
    
    def authenticate_admin(self, password: str) -> bool:
        """Authenticate admin password for employee management operations."""
        stored_password_hash = self.db.get_setting("admin_password_hash")
        if not stored_password_hash:
            # If no password is set, use default
            return password == self.default_password
        
        return self.verify_password(password, stored_password_hash)
    
    def change_admin_password(self, current_password: str, new_password: str) -> bool:
        """Change the admin password."""
        if not self.authenticate_admin(current_password):
            return False
        
        new_hash = self.hash_password(new_password)
        return self.db.set_setting("admin_password_hash", new_hash)
    
    def get_current_admin_password_hint(self) -> str:
        """Get a hint about the current admin password (for development/testing)."""
        stored_password_hash = self.db.get_setting("admin_password_hash")
        if not stored_password_hash:
            return "Default password: 1122"
        else:
            return "Custom password set"

if __name__ == "__main__":
    # Test the authentication functionality
    from database import AttendanceDatabase
    
    db = AttendanceDatabase()
    auth = AuthManager(db)
    
    # Test default password
    print("Testing default password '1122':", auth.authenticate_admin("1122"))
    print("Testing wrong password 'wrong':", auth.authenticate_admin("wrong"))
    
    # Test changing password
    print("Changing password from '1122' to 'newpass':", auth.change_admin_password("1122", "newpass"))
    print("Testing old password '1122':", auth.authenticate_admin("1122"))
    print("Testing new password 'newpass':", auth.authenticate_admin("newpass"))
    
    # Change back to default for testing
    print("Changing back to default:", auth.change_admin_password("newpass", "1122"))
    print("Testing default password again:", auth.authenticate_admin("1122"))

