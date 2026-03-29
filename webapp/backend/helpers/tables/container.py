# Container table management functionality
from database import Container, Session
from sqlalchemy import select

def get_containers(filter = None):
  '''
  Finds containers with the given optional filter. If no filter is given, finds all containers in the system.
    Parameters:
      filter: Additional filters. Example usage: ...
    Returns:
      All found containers in a list.
  '''
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
  '''
  Adds the given container in the system.
    Parameters:
      name: The name of the container to be added.
      public: Boolean. Whether the container is public or not.
    Returns:
      The created container object fetched from database. Or None if provided name already exists.
  '''
  with Session() as session:
    duplicate = session.execute(select(Container).where(Container.name == name)).scalar_one_or_none()
    if duplicate != None:
        return None
    new_container = Container(name = name, public = public, description = description, imageName = imageName)
    session.add(new_container)
    session.commit()
    return session.execute(select(Container).where(Container.name == name)).scalar_one_or_none()

def remove_container(container_id):
  '''
  Removes the given container in the system.
    Parameters:
      container_id: The container id to be removed.
    Returns:
      Nothing
  '''
  with Session() as session:
    container = session.execute(select(Container).where(Container.containerId == container_id)).scalar_one_or_none()
    session.delete(container)
    session.commit()

def edit_container(container_id, new_name = None, new_public = None, new_description = None, new_image_name = None):
  '''
  Edits the given container in the system.
    Parameters:
      container_id: The container id to be edited.
      new_name: The new name for the given container.
      new_public: The new boolean for publicity of the container.
      new_description: The new description for the given container.
      new_image_name: The new image name for the given container.
    Returns:
      The edited container object fetched from database. Or None if name or publicity isn't provided.
  '''
  with Session() as session:
    container = session.execute(select(Container).where(Container.containerId == container_id)).scalar_one_or_none()
    if new_name != None: container.name = new_name
    if new_public != None: container.public = new_public
    if new_description != None: container.description = new_description
    if new_image_name != None: container.imageName = new_image_name
    session.commit()
    return container
