"""User whitelisting table management functionality.

Provides operations for managing the UserWhitelist database table, including
viewing, adding, and removing whitelisted email addresses.
"""
from click import password_option
from database import UserWhitelist, Session
from sqlalchemy import select

def view_all(opt_filter = None):
    """Retrieve all whitelisted users, optionally filtered by email.

    Args:
        opt_filter: An email address to filter by. If None, all
            whitelisted users are returned.

    Returns:
        A list of UserWhitelist objects matching the filter, or all
        whitelisted users if no filter is provided.
    """

    with Session() as session:
        all_whitelisted_users_list = []
        if opt_filter != None:
            all_whitelisted_users = session.execute(select(UserWhitelist).where(UserWhitelist.email == opt_filter)).scalars().all()
            for user in all_whitelisted_users:
                all_whitelisted_users_list.append(user)
            return all_whitelisted_users_list
        else:
            all_whitelisted_users = session.execute(select(UserWhitelist)).scalars().all()
        return all_whitelisted_users



def add_to_whitelist(emails):
    """Add an email address to the whitelist.

    Checks for duplicates before adding.

    Args:
        emails: The email address to add to the whitelist.

    Returns:
        A dict with key 'msg' set to 'success' if the email was added,
        or None if the email already exists in the whitelist.
    """
    with Session() as session:
        whitelisted = session.execute(select(UserWhitelist).where(UserWhitelist.email == emails)).scalar_one_or_none()
        if whitelisted != None:
            return None
        else:
            session.add(
                UserWhitelist(
                    email = emails
                )
            )
            session.commit()
            return {"msg": "success"}


def remove_from_whitelist(email):
    """Remove an email address from the whitelist.

    Args:
        email: The email address to remove from the whitelist.

    Returns:
        A dict with key 'msg' set to 'success' if the email was removed,
        or None if the email was not found in the whitelist.
    """
    with Session() as session:
        whitelisted = session.execute(select(UserWhitelist).where(UserWhitelist.email == email)).scalar_one_or_none()
        if whitelisted == None:
            return None
        else:
            session.delete(whitelisted)
            session.commit()
            return {"msg": "success"}
