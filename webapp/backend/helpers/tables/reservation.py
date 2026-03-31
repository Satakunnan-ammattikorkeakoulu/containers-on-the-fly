"""Reservation table management functionality.

Provides CRUD operations for the Reservation database table, including
lookup by date or status, creation, deletion, and editing of reservation records.
"""
from database import Reservation, Session
from datetime import datetime
from sqlalchemy import select

def get_reservations(filter = None):
    """Find reservations with an optional filter.

    If no filter is given, returns all reservations. When a filter is provided,
    it first attempts to parse it as a datetime and match against startDate or
    endDate. If parsing fails, it treats the filter as a status string.

    Args:
        filter: A datetime string in '%Y-%m-%d %H:%M:%S' format to match
            against startDate/endDate, or a status string (e.g. 'reserved',
            'started', 'stopped'). If None, all reservations are returned.

    Returns:
        A list of matching Reservation objects, or None if a filter was
        provided but no match was found.
    """

    with Session() as session:
        all_reservations_list = []

        if filter is None:
            all_reservations = session.execute(select(Reservation)).scalars().all()
            for reservation in all_reservations:
                all_reservations_list.append(reservation)
            return all_reservations_list

        if filter:
            try:
                filter = datetime.strptime(filter, '%Y-%m-%d %H:%M:%S')
                found_reservation = session.execute(select(Reservation).where(Reservation.startDate == filter)).scalars().all()
                if found_reservation:
                    return found_reservation
                found_reservation = session.execute(select(Reservation).where(Reservation.endDate == filter)).scalars().all()
                if found_reservation:
                    return found_reservation
            except ValueError:
                found_reservation = session.execute(select(Reservation).where(Reservation.status == filter)).scalars().all()
                if found_reservation:
                    return found_reservation



def get_reservation(filter = None):
    """Find a single reservation by its reservation ID.

    Args:
        filter: The reservation ID to look up. If None, returns None.

    Returns:
        A single-element list containing the matching Reservation object,
        or None if no reservation matches or no filter is provided.
    """
    with Session() as session:
        if filter != None:
            reservations = session.execute(select(Reservation).where(Reservation.reservationId == filter)).scalar_one_or_none()
            if reservations != None: return [reservations]
            else: return None
        return reservations



def add_reservation(startDate, endDate, userId, computerId, containerId):
    """Add a new reservation to the system.

    Creates a reservation with status 'reserved'.

    Args:
        startDate: The datetime when the reservation starts.
        endDate: The datetime when the reservation ends.
        userId: The ID of the user making the reservation.
        computerId: The ID of the computer to reserve.
        containerId: The ID of the container to associate with the reservation.
    """
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

def remove_reservation(reservation_id):
    """Remove a reservation from the system by its ID.

    Args:
        reservation_id: The ID of the reservation to be removed.
    """
    with Session() as session:
        reservation = session.execute(select(Reservation).where(Reservation.reservationId == reservation_id)).scalar_one_or_none()
        session.delete(reservation)
        session.commit()

def edit_reservation(reservation_id, new_startDate = None, new_endDate = None, new_status = None):
    """Edit an existing reservation's attributes.

    Only the provided (non-None) fields are updated; others remain unchanged.

    Args:
        reservation_id: The ID of the reservation to be edited.
        new_startDate: The new start datetime, or None to keep current.
        new_endDate: The new end datetime, or None to keep current.
        new_status: The new status string (e.g. 'reserved', 'started',
            'stopped'), or None to keep current.

    Returns:
        The updated Reservation object.
    """
    with Session() as session:
        reservation = session.execute(select(Reservation).where(Reservation.reservationId == reservation_id)).scalar_one_or_none()
        if new_startDate != None:
            reservation.startDate = new_startDate
        if new_endDate != None:
            reservation.endDate = new_endDate
        if new_status != None:
            reservation.status = new_status
        session.commit()
        return reservation
