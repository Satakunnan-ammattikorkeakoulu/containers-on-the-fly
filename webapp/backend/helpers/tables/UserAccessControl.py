# User access control (blacklist/whitelist) table management functionality
from database import UserBlacklist, UserWhitelist, Session

def getBlacklistedEmails():
    """
    Get all blacklisted email addresses.
    
    Returns:
        List of email addresses
    """
    with Session() as session:
        blacklist = session.query(UserBlacklist).all()
        return [entry.email for entry in blacklist if entry.email]

def setBlacklistedEmails(emails: list):
    """
    Set the complete blacklist (replace all existing entries).
    
    Args:
        emails: List of email addresses
        
    Returns:
        Boolean indicating success
    """
    try:
        with Session() as session:
            # Remove all existing entries
            session.query(UserBlacklist).delete()
            
            # Add new entries
            for email in emails:
                if email and email.strip():
                    blacklist_entry = UserBlacklist(email=email.strip())
                    session.add(blacklist_entry)
            
            session.commit()
            return True
    except Exception as e:
        print(f"Error setting blacklisted emails: {e}")
        return False

def getWhitelistedEmails():
    """
    Get all whitelisted email addresses.
    
    Returns:
        List of email addresses
    """
    with Session() as session:
        whitelist = session.query(UserWhitelist).all()
        return [entry.email for entry in whitelist if entry.email]

def setWhitelistedEmails(emails: list):
    """
    Set the complete whitelist (replace all existing entries).
    
    Args:
        emails: List of email addresses
        
    Returns:
        Boolean indicating success
    """
    try:
        with Session() as session:
            # Remove all existing entries
            session.query(UserWhitelist).delete()
            
            # Add new entries
            for email in emails:
                if email and email.strip():
                    whitelist_entry = UserWhitelist(email=email.strip())
                    session.add(whitelist_entry)
            
            session.commit()
            return True
    except Exception as e:
        print(f"Error setting whitelisted emails: {e}")
        return False 