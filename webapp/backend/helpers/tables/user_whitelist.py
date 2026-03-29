# User whitelisting table management functionality
from click import password_option
from database import UserWhitelist, Session

def viewAll(opt_filter = None):
    '''
    Get all users from UserWhitelist
    Make a list and append all those users into the list
    Return the list
    '''

    with Session() as session:
        all_whitelisted_users_list = []
        if opt_filter != None:
            all_whitelisted_users = session.query(UserWhitelist).filter(UserWhitelist.email == opt_filter).all()
            for user in all_whitelisted_users:
                all_whitelisted_users_list.append(user)
            return all_whitelisted_users_list
        else:
            all_whitelisted_users = session.query(UserWhitelist).all()
        return all_whitelisted_users

    

def addToWhitelist(emails):
    '''
    Checks if the user with the given email already exists in the whitelist,
    If it doesn't then the email/emails get added.
    '''
    with Session() as session:
        whitelisted = session.query(UserWhitelist).filter(UserWhitelist.email == emails).first()
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


def removeFromWhitelist(email):
    '''
    Checks if the email user is inputting is the same as the one in the whitelist,
    If emails are the same then remove it.
    And if the email wasn't found in the whitelist, then the user gets notified of that and nothing is removed.
    '''
    with Session() as session:
        whitelisted = session.query(UserWhitelist).filter(UserWhitelist.email == email).first()
        if whitelisted == None:
            return None
        else:
            session.delete(whitelisted)
            session.commit()
            return {"msg": "success"}
        
