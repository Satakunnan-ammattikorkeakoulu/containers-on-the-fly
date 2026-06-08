"""Server-side pagination, sorting, and counting helpers for SQLAlchemy queries.

Provides reusable utilities that apply ORDER BY, LIMIT, and OFFSET to
SQLAlchemy select statements based on Vuetify 3 v-data-table-server parameters.
"""

from sqlalchemy import asc, desc, func, select


MAX_ITEMS_PER_PAGE = 50


def apply_pagination(stmt, sort_by, page, items_per_page, allowed_sort_keys):
    """Apply sorting and pagination to a SQLAlchemy select statement.

    Args:
        stmt: The base SQLAlchemy select statement.
        sort_by: List of dicts with 'key' and 'order' from the frontend.
        page: 1-based page number.
        items_per_page: Number of items per page. -1 means all (no limit).
        allowed_sort_keys: Dict mapping frontend key names to SQLAlchemy
            column objects. Keys not in this whitelist are ignored.

    Returns:
        The modified statement with ORDER BY and LIMIT/OFFSET applied.
    """
    # Apply sorting
    for sort_item in sort_by:
        key = sort_item.key if hasattr(sort_item, 'key') else sort_item.get('key')
        order = sort_item.order if hasattr(sort_item, 'order') else sort_item.get('order', 'desc')
        if key in allowed_sort_keys:
            column = allowed_sort_keys[key]
            stmt = stmt.order_by(desc(column) if order == "desc" else asc(column))

    # Apply pagination (skip if itemsPerPage is -1, meaning "all")
    if items_per_page != -1:
        clamped = min(max(items_per_page, 1), MAX_ITEMS_PER_PAGE)
        offset = (max(page, 1) - 1) * clamped
        stmt = stmt.limit(clamped).offset(offset)

    return stmt


def get_total_count(session, base_stmt):
    """Execute a COUNT query based on a select statement's WHERE clauses.

    Wraps the given statement as a subquery and counts its rows, which is
    more reliable than replacing columns with func.count() when the
    statement has joins or distinct clauses.

    Args:
        session: Active SQLAlchemy session.
        base_stmt: A select statement whose matching rows should be counted.

    Returns:
        Integer count of matching rows.
    """
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    return session.execute(count_stmt).scalar()
