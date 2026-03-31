"""User access control (blacklist/whitelist) table management functionality.

Provides bulk get and set operations for the UserBlacklist and UserWhitelist
database tables, used to control which email addresses can access the system.
"""
from database import UserBlacklist, UserWhitelist, Session
from sqlalchemy import select, delete

def get_blacklisted_emails():
    """Get all blacklisted email addresses.

    Returns:
        A list of email address strings from the blacklist.
    """
    with Session() as session:
        blacklist = session.execute(select(UserBlacklist)).scalars().all()
        return [entry.email for entry in blacklist if entry.email]

def set_blacklisted_emails(emails: list):
    """Replace the entire blacklist with a new set of email addresses.

    All existing blacklist entries are deleted before the new ones are added.
    Empty or whitespace-only entries are skipped.

    Args:
        emails: A list of email address strings to set as the new blacklist.

    Returns:
        True if the operation succeeded, False if an exception occurred.
    """
    try:
        with Session() as session:
            # Remove all existing entries
            session.execute(delete(UserBlacklist))

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

def get_whitelisted_emails():
    """Get all whitelisted email addresses.

    Returns:
        A list of email address strings from the whitelist.
    """
    with Session() as session:
        whitelist = session.execute(select(UserWhitelist)).scalars().all()
        return [entry.email for entry in whitelist if entry.email]

def set_whitelisted_emails(emails: list):
    """Replace the entire whitelist with a new set of email addresses.

    All existing whitelist entries are deleted before the new ones are added.
    Empty or whitespace-only entries are skipped.

    Args:
        emails: A list of email address strings to set as the new whitelist.

    Returns:
        True if the operation succeeded, False if an exception occurred.
    """
    try:
        with Session() as session:
            # Remove all existing entries
            session.execute(delete(UserWhitelist))

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
