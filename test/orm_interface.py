from dataclasses import dataclass, field

from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table
from sqlalchemy.orm import RelationshipProperty, registry, relationship
import classes.example_classes

metadata = MetaData()


t_Parent1 = Table(
    'Parent1', metadata,
    Column('id', Integer, primary_key=True),
    Column('obj', String(256), nullable=False),
    Column('polymorphic_type', String)
)

t_Parent2 = Table(
    'Parent2', metadata,
    Column('id', Integer, primary_key=True),
    Column('obj2', String(256), nullable=False),
    Column('value', Integer, nullable=False),
    Column('polymorphic_type', String)
)

t_MultipleInheritance = Table(
    'MultipleInheritance', metadata,
    Column('id', Integer, primary_key=True),
    Column('parent1_id', ForeignKey('Parent1.id'), nullable=False),
    Column('parent2_id', ForeignKey('Parent2.id'), nullable=False)
)

mapper_registry = registry(metadata=metadata)

m_Parent1 = mapper_registry.map_imperatively(classes.example_classes.Parent1, t_Parent1, polymorphic_on = "polymorphic_type", polymorphic_identity = "Parent1")

m_Parent2 = mapper_registry.map_imperatively(classes.example_classes.Parent2, t_Parent2, polymorphic_on = "polymorphic_type", polymorphic_identity = "Parent2")

m_MultipleInheritance = mapper_registry.map_imperatively(classes.example_classes.MultipleInheritance, t_MultipleInheritance, properties = dict(parent1=relationship('Parent1',foreign_keys=[t_MultipleInheritance.c.parent1_id]), 
parent2=relationship('Parent2',foreign_keys=[t_MultipleInheritance.c.parent2_id])))
