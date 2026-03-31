"""Container table management functionality.

Provides CRUD operations for the Container database table, including
lookup by name or ID, creation, deletion, and editing of container records.
"""
from database import Container, Session
from sqlalchemy import select

def get_containers(filter = None):
  """Find containers with an optional filter.

  If no filter is given, returns all containers. When a filter is provided,
  it first attempts to match by container name, then by container ID.

  Args:
      filter: A container name (str) or container ID (int-like str) to
          search for. If None, all containers are returned.

  Returns:
      A list of matching Container objects, or None if a filter was
      provided but no match was found.
  """
  with Session() as session:
    if filter != None:
      containers = session.execute(select(Container).where(Container.name == filter)).scalar_one_or_none()
      if containers != None: return [containers]
      else:
        try:
          containers = session.execute(select(Container).where(Container.containerId == int(filter))).scalar_one_or_none()
          if containers != None: return [containers]
          else: return None
        except:
          return None
    else: containers = session.execute(select(Container)).scalars().all()
    return containers

def add_container(name, public, description, imageName):
  """Add a new container to the system.

  Args:
      name: The name of the container to be added.
      public: Whether the container is publicly visible.
      description: A text description of the container.
      imageName: The Docker image name associated with this container.

  Returns:
      The created Container object fetched from the database, or None
      if a container with the given name already exists.
  """
  with Session() as session:
    duplicate = session.execute(select(Container).where(Container.name == name)).scalar_one_or_none()
    if duplicate != None:
        return None
    new_container = Container(name = name, public = public, description = description, imageName = imageName)
    session.add(new_container)
    session.commit()
    return session.execute(select(Container).where(Container.name == name)).scalar_one_or_none()

def remove_container(container_id):
  """Remove a container from the system by its ID.

  Args:
      container_id: The ID of the container to be removed.
  """
  with Session() as session:
    container = session.execute(select(Container).where(Container.containerId == container_id)).scalar_one_or_none()
    session.delete(container)
    session.commit()

def edit_container(container_id, new_name = None, new_public = None, new_description = None, new_image_name = None):
  """Edit an existing container's attributes.

  Only the provided (non-None) fields are updated; others remain unchanged.

  Args:
      container_id: The ID of the container to be edited.
      new_name: The new name for the container, or None to keep current.
      new_public: The new public visibility flag, or None to keep current.
      new_description: The new description, or None to keep current.
      new_image_name: The new Docker image name, or None to keep current.

  Returns:
      The updated Container object.
  """
  with Session() as session:
    container = session.execute(select(Container).where(Container.containerId == container_id)).scalar_one_or_none()
    if new_name != None: container.name = new_name
    if new_public != None: container.public = new_public
    if new_description != None: container.description = new_description
    if new_image_name != None: container.imageName = new_image_name
    session.commit()
    return container
