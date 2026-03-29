# Reservation table management functionality
from database import Reservation, Session
from datetime import datetime

def getReservations(filter = None):
    '''
    Find reservations with the given optional filter. If no filter is given, finds all reservations in the system.
    Parameters:
        filter: Additional filters. Example usage: ...
    Returns:
        All found reservations in a list.
    '''
    
    with Session() as session:
        all_reservations_list = []

        if filter is None:
            all_reservations = session.query(Reservation)
            for reservation in all_reservations:
                all_reservations_list.append(reservation)
            return all_reservations_list
        
        if filter:
            try:
                filter = datetime.strptime(filter, '%Y-%m-%d %H:%M:%S')
                found_reservation = session.query(Reservation).filter(Reservation.startDate == filter).all()
                if found_reservation:
                    return found_reservation
                found_reservation = session.query(Reservation).filter(Reservation.endDate == filter).all()
                if found_reservation:
                    return found_reservation
            except ValueError:
                found_reservation = session.query(Reservation).filter(Reservation.status == filter).all()
                if found_reservation:
                    return found_reservation



def getReservation(filter = None):
    '''
    Find reservation with the given optional filter which in this case is reservationId.
    Parameters:
        Additional filters: Example usage: ...
    Returns:
        Found reservation in list.
    '''
    with Session() as session:
        if filter != None:
            reservations = session.query(Reservation).filter(Reservation.reservationId == filter).first()
            if reservations != None: return [reservations]
            else: return None
        return reservations
    


def addReservation(startDate, endDate, userId, computerId, containerId):
    '''
    Adds the given reservation in the system.
        Parameters:
            startDate: The date the reservation is going to start.
            endDate: The date the reservation is going to start.
            status: Reserved, started or stopped.
        Returns:
            The created reservation object fetched from database. Or none if for that date reservation already exists.
     '''
    with Session() as session:
        session.add(
            Reservation(
                startDate = startDate,
                endDate = endDate,
                userId = userId,
                computerId = computerId,
                reservedContainerId = containerId,
                status = "reserved"
            )
        )
        session.commit()

def removeReservation(reservation_id):
    '''
    Removes the given reservation from the system.
        Parameters:
            reservation: The reservation id of the reservation to be removed.
        Returns: 
            Nothing
    '''
    with Session() as session:
        reservation = session.query(Reservation).filter(Reservation.reservationId == reservation_id).first()
        session.delete(reservation)
        session.commit()

def editReservation(reservation_id, new_startDate = None, new_endDate = None, new_status = None):
    '''
    Edits the given reservation in the system.
        Parameters:
            reservation: The reservation id of the reservation to be edited.
            new_startDate: The new start date for the reservation.
            new_endDate: The new end date for the reservation.
            new_status: The new status for the reservation.
        Returns:
            The edited reservation object fetched from database. Or none if startDate, endDate or status isn't provided
    '''
    with Session() as session:
        reservation = session.query(Reservation).filter(Reservation.reservationId == reservation_id).first()
        if new_startDate != None:
            reservation.startDate = new_startDate
        if new_endDate != None:
            reservation.endDate = new_endDate
        if new_status != None:
            reservation.status = new_status
        session.commit()
        return reservation